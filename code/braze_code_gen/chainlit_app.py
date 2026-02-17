"""Chainlit UI for Braze SDK Landing Page Generator.

Chat-based interface using Chainlit's Step model for per-node progress
and real-time token streaming via WebSocket.
"""

import asyncio
import logging
import os
from pathlib import Path
from queue import Queue, Empty
from threading import Event
from typing import Optional

from dotenv import load_dotenv
import chainlit as cl

from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig
from braze_code_gen.ui.chainlit_callbacks import ChainlitTokenCallbackHandler

load_dotenv()
logger = logging.getLogger(__name__)

NODE_LABELS = {
    "planning": "Planning Agent",
    "research": "Research Agent",
    "code_generation": "Code Generation Agent",
    "validation": "Validation Agent",
    "refinement": "Refinement Agent",
    "finalization": "Finalization Agent",
}

# Known workflow edges (static). Validation routing is dynamic — see _predict_next_node.
_NEXT_NODE = {
    "planning": "research",
    "research": "code_generation",
    "code_generation": "validation",
    "refinement": "validation",
}

FIRST_NODE = "planning"
MAX_REFINEMENT_ITERATIONS = 3


def _predict_next_node(
    node_name: str, status: str, refinement_count: int
) -> Optional[str]:
    """Predict the next workflow node so we can open a Step proactively."""
    if node_name == "validation":
        passed = "complete" in status.lower() and "issues" not in status.lower()
        if passed or refinement_count >= MAX_REFINEMENT_ITERATIONS:
            return "finalization"
        return "refinement"
    if node_name == "finalization":
        return None
    return _NEXT_NODE.get(node_name)


@cl.on_chat_start
async def on_chat_start():
    """Initialize session: create Orchestrator, auto-configure if env vars present."""
    orchestrator = Orchestrator(
        export_dir="/tmp/braze_exports",
        enable_browser_testing=True,
    )
    cl.user_session.set("orchestrator", orchestrator)
    cl.user_session.set("stop_event", Event())
    cl.user_session.set("api_configured", False)

    api_key = os.getenv("BRAZE_API_KEY", "")
    sdk_endpoint = os.getenv("BRAZE_SDK_ENDPOINT", "")

    if api_key and len(api_key) >= 32 and sdk_endpoint:
        config = BrazeAPIConfig(
            api_key=api_key, sdk_endpoint=sdk_endpoint, validated=True
        )
        orchestrator.set_braze_api_config(config)
        cl.user_session.set("api_configured", True)
        await cl.Message(
            content=(
                "API configuration loaded from environment.\n\n"
                "Describe the landing page you want to build."
            ),
        ).send()
    else:
        res = await cl.AskUserMessage(
            content=(
                "Welcome to the **Braze Landing Page Generator**.\n\n"
                "Please enter your **Braze API Key** (min 32 characters):"
            ),
            timeout=300,
        ).send()
        if not res:
            return
        api_key = res["output"].strip()
        if len(api_key) < 32:
            await cl.Message(content="Invalid API key. Must be at least 32 characters.").send()
            return

        res2 = await cl.AskUserMessage(
            content="Please enter your **Braze SDK Endpoint** (e.g. `sdk.iad-01.braze.com`):",
            timeout=300,
        ).send()
        if not res2:
            return
        sdk_endpoint = res2["output"].strip()
        if not sdk_endpoint:
            await cl.Message(content="SDK endpoint is required.").send()
            return

        try:
            config = BrazeAPIConfig(
                api_key=api_key, sdk_endpoint=sdk_endpoint, validated=True
            )
            orchestrator.set_braze_api_config(config)
            cl.user_session.set("api_configured", True)
            await cl.Message(
                content="API configuration validated. Now describe the landing page you want to build.",
            ).send()
        except Exception as e:
            await cl.Message(content=f"Validation error: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user prompt — run the generation workflow with streaming Steps.

    Strategy: LangGraph's ``graph.stream()`` only yields chunks **after** each
    node finishes.  The backend's ``node_start`` event therefore arrives at the
    same instant as ``node_complete`` — far too late to stream tokens into.

    To get real-time token streaming we open each Step **proactively**, before
    the node starts processing, and predict the next node when the current one
    completes.  Tokens produced by the LLM callbacks flow into the already-open
    Step via ``stream_token()``.
    """
    if not cl.user_session.get("api_configured"):
        await cl.Message(content="Please configure your API credentials first.").send()
        return

    orchestrator: Orchestrator = cl.user_session.get("orchestrator")
    stop_event: Event = cl.user_session.get("stop_event")
    stop_event.clear()

    # Thread-safe queues (sync callback thread → async consumer)
    token_queue: Queue = Queue()
    update_queue: Queue = Queue()

    token_callback = ChainlitTokenCallbackHandler(token_queue, stop_event)

    # Stop button
    stop_action = cl.Action(
        name="stop_generation", label="Stop Generation", payload={}
    )
    await cl.Message(
        content="Starting generation...", actions=[stop_action]
    ).send()

    # --- Sync-to-async bridge ---
    def _run_sync():
        """Run the sync generator in a background thread."""
        try:
            for update in orchestrator.generate_streaming(
                user_message=message.content,
                callbacks=[token_callback],
                stop_event=stop_event,
            ):
                update_queue.put(update)
            update_queue.put(None)  # sentinel
        except KeyboardInterrupt:
            update_queue.put({"type": "cancelled", "message": "Generation cancelled by user"})
            update_queue.put(None)
        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            update_queue.put({"type": "error", "message": str(e)})
            update_queue.put(None)

    # --- Helpers for Step lifecycle ---
    async def _open_step(node_name: str) -> cl.Step:
        label = NODE_LABELS.get(node_name, node_name)
        step = cl.Step(name=label, type="llm")
        await step.__aenter__()
        return step

    async def _close_step(step: cl.Step, fallback_output: str = ""):
        """Close a Step.  If no tokens were streamed, set *fallback_output*."""
        if not step.output:
            step.output = fallback_output or "Done"
        await step.__aexit__(None, None, None)

    # Open the first Step *before* the executor starts so that tokens produced
    # during the very first node have somewhere to go.
    active_step = await _open_step(FIRST_NODE)
    tokens_streamed = False
    refinement_count = 0

    loop = asyncio.get_event_loop()
    thread_future = loop.run_in_executor(None, _run_sync)

    try:
        while True:
            # 1) Drain token queue (high frequency)
            while True:
                try:
                    tok = token_queue.get_nowait()
                    if active_step and tok.get("type") == "token":
                        await active_step.stream_token(tok["token"])
                        tokens_streamed = True
                except Empty:
                    break

            # 2) Check for orchestrator lifecycle events
            try:
                update = update_queue.get_nowait()
            except Empty:
                if thread_future.done():
                    break
                await asyncio.sleep(0.02)
                continue

            if update is None:
                break

            update_type = update.get("type")

            # Skip node_start — it arrives simultaneously with node_complete
            # and is useless for timing.  Steps are opened proactively instead.
            if update_type == "node_start":
                continue

            if update_type == "node_complete":
                node_name = update.get("node", "")
                status = update.get("status", "Complete")

                if node_name == "refinement":
                    refinement_count += 1

                # Close current step (keep streamed tokens if any)
                if active_step:
                    if not tokens_streamed:
                        active_step.output = status
                    await _close_step(active_step, fallback_output=status)
                    active_step = None
                    tokens_streamed = False

                # Proactively open the *next* step so tokens stream in
                next_node = _predict_next_node(node_name, status, refinement_count)
                if next_node:
                    active_step = await _open_step(next_node)

            elif update_type == "complete":
                if active_step:
                    await _close_step(active_step)
                    active_step = None
                    tokens_streamed = False

                export_path = update.get("export_file_path")
                if export_path and Path(export_path).exists():
                    file_element = cl.File(
                        name="braze_landing_page.html",
                        path=export_path,
                        display="inline",
                    )
                    await cl.Message(
                        content="**Generation Complete!** Download your landing page below.",
                        elements=[file_element],
                    ).send()
                else:
                    await cl.Message(content="Generation complete.").send()

            elif update_type == "error":
                if active_step:
                    active_step.output = f"Error: {update.get('message', 'Unknown')}"
                    await _close_step(active_step)
                    active_step = None
                    tokens_streamed = False
                await cl.Message(
                    content=f"**Error**: {update.get('message', 'Unknown error')}"
                ).send()

            elif update_type == "cancelled":
                if active_step:
                    active_step.output = "Cancelled"
                    await _close_step(active_step)
                    active_step = None
                    tokens_streamed = False
                await cl.Message(content="Generation cancelled.").send()

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        if active_step:
            try:
                active_step.output = f"Error: {e}"
                await active_step.__aexit__(None, None, None)
            except Exception:
                pass
        await cl.Message(content=f"Error: {e}").send()
    finally:
        if not thread_future.done():
            stop_event.set()
        try:
            await asyncio.wait_for(asyncio.wrap_future(thread_future), timeout=10)
        except (asyncio.TimeoutError, Exception):
            pass


@cl.action_callback("stop_generation")
async def on_stop(action: cl.Action):
    """Handle stop button click."""
    stop_event: Event = cl.user_session.get("stop_event")
    if stop_event:
        stop_event.set()
    await cl.Message(content="Cancellation requested...").send()

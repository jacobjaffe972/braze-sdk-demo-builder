"""Streamlit UI for Braze SDK Landing Page Generator.

This module provides a web interface for generating Braze SDK landing pages
with real-time token-level streaming updates and cancellation support.
"""

import os
import logging
from pathlib import Path
from typing import Optional

# IMPORTANT: Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Braze Landing Page Generator",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
CSS_PATH = Path(__file__).parent / "streamlit_styles.css"
if CSS_PATH.exists():
    st.html(f"<style>{CSS_PATH.read_text()}</style>")

# ============================================
# Session State Initialization
# ============================================

def init_session_state():
    """Initialize all session state variables."""
    from threading import Event

    # Orchestrator instance
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = Orchestrator(
            export_dir="/tmp/braze_exports",
            enable_browser_testing=True
        )

    # API Configuration
    if "api_config" not in st.session_state:
        st.session_state.api_config = None

    # Streaming Control (UI-agnostic cancellation using threading.Event)
    if "streaming_active" not in st.session_state:
        st.session_state.streaming_active = False

    if "stop_event" not in st.session_state:
        st.session_state.stop_event = Event()

    # Results
    if "export_path" not in st.session_state:
        st.session_state.export_path = None

    if "branding_data" not in st.session_state:
        st.session_state.branding_data = None

    if "generation_complete" not in st.session_state:
        st.session_state.generation_complete = False

    # Status Tracking (using node-based state instead of list manipulation)
    if "node_states" not in st.session_state:
        st.session_state.node_states = {}

    # Agent Output (for token streaming)
    if "agent_output" not in st.session_state:
        st.session_state.agent_output = ""

    if "current_agent" not in st.session_state:
        st.session_state.current_agent = ""

# Initialize on app load
init_session_state()

# ============================================
# Agent Output Fragment (Auto-Updating)
# ============================================

@st.fragment(run_every=0.1 if st.session_state.streaming_active else None)
def agent_output_fragment():
    """Auto-updating fragment for real-time agent thinking display."""

    if st.session_state.agent_output or st.session_state.streaming_active:
        # Header with Braze logo
        st.html("""
        <div class="agent-sidebar-header">
            <div class="braze-logo-small"></div>
            <span>Agent Thinking</span>
        </div>
        """)

        # Agent name
        if st.session_state.current_agent:
            st.caption(f"🤖 Current Agent: {st.session_state.current_agent}")

        # Token stream output
        if st.session_state.agent_output:
            st.markdown(st.session_state.agent_output)

        # Thinking spinner if actively streaming
        if st.session_state.streaming_active:
            st.html('<div class="thinking-spinner"></div>')
    elif st.session_state.get("agent_output") == "":
        st.caption("Agent output will appear here during generation")

# Call fragment in sidebar context
with st.sidebar:
    agent_output_fragment()

# Braze header
st.html("""
<div class="braze-header">
    <div class="braze-logo"></div>
    <span class="braze-title">Landing Page Generator</span>
</div>
""")

# ============================================
# Config Panel
# ============================================

with st.container():
    st.subheader("API Configuration")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        api_key = st.text_input(
            "Braze API Key",
            type="password",
            key="api_key_input",
            placeholder="Enter your Braze API key",
            help="Required: Min 32 characters",
            disabled=st.session_state.streaming_active,
            value=os.getenv("BRAZE_API_KEY", "")
        )

    with col2:
        sdk_endpoint = st.text_input(
            "SDK Endpoint",
            key="sdk_endpoint_input",
            placeholder="sdk.iad-01.braze.com",
            help="Braze SDK endpoint for Web SDK initialization",
            disabled=st.session_state.streaming_active,
            value=os.getenv("BRAZE_SDK_ENDPOINT", "")
        )

    with col3:
        st.write("")  # Spacer for button alignment
        validate = st.button(
            "Validate",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.streaming_active,
            key="validate_btn"
        )

    # Validation Handler
    if validate:
        if not api_key or len(api_key) < 32:
            st.error("❌ Invalid API key format. Must be at least 32 characters.")
        elif not sdk_endpoint:
            st.error("❌ SDK endpoint is required (e.g., sdk.iad-01.braze.com)")
        else:
            try:
                config = BrazeAPIConfig(
                    api_key=api_key,
                    sdk_endpoint=sdk_endpoint,
                    validated=True
                )
                st.session_state.api_config = config
                st.session_state.orchestrator.set_braze_api_config(config)
                st.success("✅ API configuration validated. Ready to generate.")
            except Exception as e:
                st.error(f"❌ Validation error: {str(e)}")

# ============================================
# Prompt Panel
# ============================================

with st.container():
    st.subheader("Describe Your Landing Page")

    prompt = st.text_area(
        "Prompt",
        placeholder="Create a landing page with push notifications for https://example.com",
        label_visibility="collapsed",
        height=120,
        key="prompt_input",
        disabled=st.session_state.streaming_active,
        help="Describe the features you want in your landing page. Include a website URL for automatic branding."
    )

    st.caption("💡 Tip: Include a website URL for automatic branding extraction")

    # Generate and Stop buttons
    col1, col2 = st.columns([3, 1])

    with col1:
        generate = st.button(
            "🚀 Generate Landing Page",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.streaming_active or not st.session_state.api_config,
            key="generate_btn"
        )

    with col2:
        stop = st.button(
            "⏹ Stop",
            type="secondary",
            use_container_width=True,
            disabled=not st.session_state.streaming_active,
            key="stop_btn"
        )

# ============================================
# Status Panel (during generation)
# ============================================

if st.session_state.node_states:
    with st.container():
        st.html('<div class="status-card-header">⚙️ Generation Progress</div>')

        # Display node states in order
        for node_name, node_data in st.session_state.node_states.items():
            status = node_data.get("status", "pending")
            message = node_data.get("message", node_name)

            if status == "running":
                with st.spinner(message):
                    st.write("")  # Placeholder
            elif status == "success":
                st.success(f"✓ {message}")
            elif status == "error":
                st.error(f"✗ {message}")
            else:
                st.info(f"⋯ {message}")

# ============================================
# Results Panel (after completion)
# ============================================

if st.session_state.generation_complete:
    with st.container():
        st.html('<div class="success-card-header">✅ Generation Complete</div>')

        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.export_path and Path(st.session_state.export_path).exists():
                with open(st.session_state.export_path, "rb") as f:
                    st.download_button(
                        label="📥 Download HTML",
                        data=f,
                        file_name="braze_landing_page.html",
                        mime="text/html",
                        type="primary",
                        use_container_width=True
                    )
            else:
                st.error("Export file not found")

        with col2:
            show_branding = st.button(
                "🎨 View Branding Data",
                use_container_width=True
            )

        # Show branding JSON if button clicked
        if show_branding and st.session_state.branding_data:
            st.json(st.session_state.branding_data)

# ============================================
# Generation Handler
# ============================================

from braze_code_gen.ui.streamlit_callbacks import StreamlitTokenCallbackHandler

# Generate button handler
if generate:
    if not st.session_state.api_config:
        st.error("❌ Please validate your API configuration first")
    elif not prompt:
        st.error("❌ Please describe what you want to generate")
    else:
        # Initialize streaming state
        st.session_state.streaming_active = True
        st.session_state.stop_event.clear()  # Reset stop event
        st.session_state.node_states = {}
        st.session_state.agent_output = ""
        st.session_state.current_agent = ""
        st.session_state.generation_complete = False

        # Create callback handler for token streaming
        token_callback = StreamlitTokenCallbackHandler()

        # Status container for dynamic updates
        status_container = st.empty()

        try:
            # Stream from orchestrator (pass stop_event for UI-agnostic cancellation)
            for update in st.session_state.orchestrator.generate_streaming(
                user_message=prompt,
                max_refinement_iterations=3,
                callbacks=[token_callback],
                stop_event=st.session_state.stop_event  # Pass threading.Event
            ):
                update_type = update.get("type")

                if update_type == "node_complete":
                    # Node completed - update state
                    node_name = update.get("node", "Unknown")
                    status_msg = update.get("status", "")
                    st.session_state.node_states[node_name] = {
                        "status": "success",
                        "message": status_msg if status_msg else f"{node_name} completed"
                    }

                    # Update status display
                    with status_container.container():
                        st.html('<div class="status-card-header">⚙️ Generation Progress</div>')
                        for node, data in st.session_state.node_states.items():
                            if data["status"] == "success":
                                st.success(f"✓ {data['message']}")
                            elif data["status"] == "running":
                                st.info(f"⚙️ {data['message']}")
                            elif data["status"] == "error":
                                st.error(f"✗ {data['message']}")

                elif update_type == "complete":
                    # Store results
                    st.session_state.export_path = update.get("export_file_path")
                    st.session_state.branding_data = update.get("branding_data")
                    st.session_state.generation_complete = True

                elif update_type == "cancelled":
                    st.info("🛑 Generation cancelled by user")
                    break

                elif update_type == "error":
                    error_msg = update.get("message", "Unknown error")
                    st.error(f"❌ Generation Failed: {error_msg}")
                    break

        except KeyboardInterrupt:
            st.info("🛑 Streaming cancelled by user")

        except Exception as e:
            logger.error(f"Error during generation: {e}", exc_info=True)
            st.error(f"❌ Error: {str(e)}")

        finally:
            # Clean up
            st.session_state.streaming_active = False
            st.rerun()

# Stop button handler
if stop:
    st.session_state.stop_event.set()  # Signal cancellation via threading.Event
    st.session_state.streaming_active = False
    st.info("Cancellation requested...")
    st.rerun()

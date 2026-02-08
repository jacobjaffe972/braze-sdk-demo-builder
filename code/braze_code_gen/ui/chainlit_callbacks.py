"""LangChain callback handler for Chainlit token streaming."""

import logging
from queue import Queue
from typing import Any, Dict, List
from threading import Event

from langchain_core.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)


class ChainlitTokenCallbackHandler(BaseCallbackHandler):
    """Routes LLM tokens to the async Chainlit side via a thread-safe queue.

    Because LangChain callbacks fire on the LLM's synchronous thread,
    we cannot call async Chainlit methods directly. Instead we push
    each token into a stdlib ``queue.Queue`` which the async consumer
    in ``chainlit_app.py`` drains to call ``step.stream_token()``.
    """

    def __init__(self, token_queue: Queue, stop_event: Event):
        self.token_queue = token_queue
        self.stop_event = stop_event
        self.text = ""
        self.current_agent = ""

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        self.text = ""
        self.current_agent = (
            kwargs.get("tags", ["Agent"])[0] if "tags" in kwargs else "Agent"
        )
        logger.info(f"LLM started for {self.current_agent}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        # Check cancellation
        if self.stop_event.is_set():
            logger.info("Token streaming cancelled by user")
            raise KeyboardInterrupt("Streaming cancelled by user")

        self.text += token
        self.token_queue.put({"type": "token", "token": token})

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info(f"LLM completed for {self.current_agent}")

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        logger.error(f"LLM error: {error}")

"""LangChain callback handlers for Streamlit token streaming."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
import streamlit as st

logger = logging.getLogger(__name__)


class StreamlitTokenCallbackHandler(BaseCallbackHandler):
    """Callback handler for token-level streaming to Streamlit.

    This handler intercepts LLM token generation and updates Streamlit
    session state for real-time display in the UI.
    """

    def __init__(self):
        """Initialize callback handler."""
        self.text = ""
        self.current_agent = ""

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts generating.

        Args:
            serialized: LLM configuration
            prompts: Input prompts
            **kwargs: Additional arguments
        """
        # Clear previous output
        st.session_state.agent_output = ""
        self.text = ""

        # Detect which agent is running (from kwargs or serialized)
        agent_name = kwargs.get("tags", ["Unknown Agent"])[0] if "tags" in kwargs else "Agent"
        st.session_state.current_agent = agent_name

        logger.info(f"LLM started for {agent_name}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when LLM generates a new token.

        Args:
            token: New token string
            **kwargs: Additional arguments
        """
        # Check for cancellation via threading.Event (UI-agnostic)
        if st.session_state.stop_event.is_set():
            logger.info("Token streaming cancelled by user")
            raise KeyboardInterrupt("Streaming cancelled by user")

        # Accumulate tokens
        self.text += token
        st.session_state.agent_output = self.text

        # Fragment will auto-update display
        logger.debug(f"Token received: {token[:20]}...")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes generating.

        Args:
            response: LLM response
            **kwargs: Additional arguments
        """
        # Keep final output in session state
        logger.info(f"LLM completed for {st.session_state.current_agent}")

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error.

        Args:
            error: Exception raised
            **kwargs: Additional arguments
        """
        error_msg = f"\n\n❌ Error: {str(error)}"
        st.session_state.agent_output += error_msg
        logger.error(f"LLM error: {error}")

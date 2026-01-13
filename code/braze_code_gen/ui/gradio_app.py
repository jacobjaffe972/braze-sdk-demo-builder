"""Gradio UI for Braze SDK Landing Page Generator.

This module provides a web interface for generating Braze SDK landing pages
with real-time streaming updates and preview capabilities.
"""

import os
import re
import logging
from typing import List, Tuple, Optional, Generator, Dict, Any

import gradio as gr

from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig
from braze_code_gen.utils.sdk_suggestions import get_feature_suggestions, format_suggestion_label

logger = logging.getLogger(__name__)


class BrazeCodeGenUI:
    """Gradio UI wrapper for Braze Code Generator."""

    def __init__(
        self,
        export_dir: str = "/tmp/braze_exports",
        enable_browser_testing: bool = True
    ):
        """Initialize UI.

        Args:
            export_dir: Directory for exported HTML files
            enable_browser_testing: Whether to enable Playwright browser testing
        """
        self.export_dir = export_dir
        self.enable_browser_testing = enable_browser_testing

        # Create export directory
        os.makedirs(export_dir, exist_ok=True)

        # Initialize orchestrator (API config will be set later)
        self.orchestrator = Orchestrator(
            braze_api_config=None,
            enable_browser_testing=enable_browser_testing,
            export_dir=export_dir
        )

        # State tracking
        self.current_api_config: Optional[BrazeAPIConfig] = None
        self.last_generated_html: Optional[str] = None
        self.last_export_path: Optional[str] = None
        self.last_branding_data: Optional[Dict] = None

        logger.info("BrazeCodeGenUI initialized")

    def validate_api_config(
        self,
        api_key: str,
        sdk_endpoint: str
    ) -> Tuple[str, Optional[BrazeAPIConfig], Dict, Dict]:
        """Validate Braze API configuration.

        Args:
            api_key: Braze API key
            sdk_endpoint: Braze SDK endpoint for Web SDK initialization

        Returns:
            Tuple of (status_message, api_config, api_section_update, chat_section_update)
        """
        # Validation checks
        if not api_key or len(api_key) < 32:
            return (
                "❌ Invalid API key format. Braze API keys must be at least 32 characters.",
                None,
                gr.Accordion(open=True),  # Keep API section open
                gr.Accordion(open=False)  # Keep chat section closed
            )

        if not sdk_endpoint:
            return (
                "❌ SDK endpoint is required for Web SDK initialization (e.g., sdk.iad-01.braze.com)",
                None,
                gr.Accordion(open=True),
                gr.Accordion(open=False)
            )

        # Create config
        config = BrazeAPIConfig(
            api_key=api_key,
            sdk_endpoint=sdk_endpoint,
            validated=True
        )

        # Store and set in orchestrator
        self.current_api_config = config
        self.orchestrator.set_braze_api_config(config)

        logger.info(f"API configuration validated: {sdk_endpoint}")

        return (
            "✅ API configuration validated! You can now generate landing pages.",
            config,
            gr.Accordion(open=False),  # Close API section
            gr.Accordion(open=True)    # Open chat section
        )

    def extract_website_url(self, message: str) -> Optional[str]:
        """Extract website URL from message.

        Args:
            message: User message

        Returns:
            Optional[str]: Extracted URL or None
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, message)
        return urls[0] if urls else None

    def generate_streaming(
        self,
        message: str,
        history: List
    ) -> Generator[List, None, None]:
        """Generate landing page with streaming updates.

        Args:
            message: User message with feature requests
            history: Chat history (list of ChatMessage objects or dicts)

        Yields:
            List: Updated chat history
        """
        # DEBUG: Log incoming history
        logger.info(f"=== INCOMING HISTORY ===")
        logger.info(f"Type: {type(history)}")
        logger.info(f"Value: {history}")
        if history:
            for i, msg in enumerate(history):
                logger.info(f"  [{i}] type={type(msg)}, value={msg}")

        # Validate API config
        if not self.current_api_config:
            yield history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": "⚠️ Please configure Braze API first (Section 1)"}
            ]
            return

        if not message.strip():
            yield history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": "⚠️ Please provide a feature request"}
            ]
            return

        # Extract website URL
        website_url = self.extract_website_url(message)

        # Add user message to history
        history = history + [{"role": "user", "content": message}]

        # DEBUG: Log what we're yielding
        logger.info(f"=== YIELDING HISTORY (after user message) ===")
        logger.info(f"Type: {type(history)}")
        logger.info(f"Length: {len(history)}")
        for i, msg in enumerate(history):
            logger.info(f"  [{i}] type={type(msg)}, keys={msg.keys() if isinstance(msg, dict) else 'N/A'}, value={msg}")

        yield history

        # Add assistant message placeholder
        history = history + [{"role": "assistant", "content": ""}]

        # Start generation
        status_updates = []
        final_message = ""

        try:
            # Stream updates from orchestrator
            for update in self.orchestrator.generate_streaming(
                user_message=message,
                website_url=website_url,
                max_refinement_iterations=3
            ):
                update_type = update.get("type")

                if update_type == "node_complete":
                    # Add status update
                    status = update.get("status", "")
                    status_updates.append(status)

                    # Update chat with accumulated status
                    current_response = "\n".join(status_updates)
                    history[-1] = {"role": "assistant", "content": current_response}
                    yield history

                elif update_type == "message":
                    # Agent message
                    content = update.get("content", "")
                    if content:
                        final_message = content

                elif update_type == "complete":
                    # Workflow complete - store export path and branding
                    export_path = update.get("export_file_path")
                    if export_path:
                        self.last_export_path = export_path
                        logger.info(f"Stored export path: {export_path}")

                    branding = update.get("branding_data")
                    if branding:
                        self.last_branding_data = branding
                        logger.info("Stored branding data")

                elif update_type == "error":
                    # Error occurred
                    error_msg = update.get("message", "Unknown error")
                    status_updates.append(f"\n❌ Error: {error_msg}")
                    history[-1] = {"role": "assistant", "content": "\n".join(status_updates)}
                    yield history
                    return

            # Get final state from orchestrator
            # Since streaming doesn't return final state directly, we'll format success message
            success_message = "\n".join(status_updates)
            success_message += "\n\n✅ **Generation Complete!**\n\n"
            success_message += "Switch to **Section 3: Preview & Export** to view and download your landing page."

            history[-1] = {"role": "assistant", "content": success_message}
            yield history

        except Exception as e:
            logger.error(f"Error during generation: {e}", exc_info=True)
            error_message = "\n".join(status_updates) if status_updates else ""
            error_message += f"\n\n❌ **Error**: {str(e)}"
            history[-1] = {"role": "assistant", "content": error_message}
            yield history

    def get_preview_html(self) -> str:
        """Get HTML preview for iframe.

        Returns:
            str: HTML content or placeholder message
        """
        if self.last_export_path and os.path.exists(self.last_export_path):
            try:
                with open(self.last_export_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading generated HTML: {e}")
                return "<p>Error loading preview</p>"

        return "<p>No landing page generated yet. Generate one in Section 2 first.</p>"

    def get_branding_data(self) -> Dict:
        """Get branding data for display.

        Returns:
            Dict: Branding data or empty dict
        """
        if self.last_branding_data:
            return self.last_branding_data
        return {"message": "No branding data available yet"}

    def export_html_file(self) -> Optional[str]:
        """Export HTML file for download.

        Returns:
            Optional[str]: File path for download or None
        """
        if self.last_export_path and os.path.exists(self.last_export_path):
            return self.last_export_path
        return None

    def insert_suggestion(self, suggestion_id: str, current_message: str) -> str:
        """Insert a feature suggestion into the message box.

        Args:
            suggestion_id: Feature suggestion ID
            current_message: Current message in text box

        Returns:
            str: Updated message
        """
        from braze_code_gen.utils.sdk_suggestions import get_suggestion_prompt

        suggestion_prompt = get_suggestion_prompt(suggestion_id)
        if not suggestion_prompt:
            return current_message

        # If message is empty, use suggestion as-is
        if not current_message.strip():
            return suggestion_prompt

        # Otherwise append to existing message
        return f"{current_message}\n\n{suggestion_prompt}"


def create_gradio_interface(
    export_dir: str = "/tmp/braze_exports",
    enable_browser_testing: bool = True,
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 7860
) -> gr.Blocks:
    """Create and configure Gradio interface.

    Args:
        export_dir: Directory for exported HTML files
        enable_browser_testing: Whether to enable browser testing
        share: Whether to create public Gradio share link
        server_name: Server host
        server_port: Server port

    Returns:
        gr.Blocks: Configured Gradio interface
    """
    # Initialize UI wrapper
    ui = BrazeCodeGenUI(
        export_dir=export_dir,
        enable_browser_testing=enable_browser_testing
    )

    # Get feature suggestions
    suggestions = get_feature_suggestions()

    # Create Gradio interface
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan"),
        title="Braze SDK Landing Page Generator"
    ) as demo:

        # Header
        gr.Markdown(
            """
            # 🚀 Braze SDK Landing Page Generator

            Create branded demo landing pages for Braze SDK integration in 3 easy steps.
            """
        )

        # State management
        api_config_state = gr.State(None)

        # ====================================================================
        # SECTION 1: API Configuration
        # ====================================================================

        with gr.Accordion("1️⃣ Configure Braze API", open=True) as api_section:
            gr.Markdown(
                """
                Enter your Braze API credentials to get started.
                These will be used to initialize the SDK in generated landing pages.
                """
            )

            with gr.Row():
                with gr.Column(scale=2):
                    api_key_input = gr.Textbox(
                        label="Braze API Key",
                        placeholder="Enter your Braze API key",
                        type="password",
                        lines=1,
                        value=os.getenv("BRAZE_API_KEY", "")
                    )
                with gr.Column(scale=2):
                    sdk_endpoint_input = gr.Textbox(
                        label="SDK Endpoint",
                        placeholder="sdk.iad-01.braze.com",
                        value=os.getenv("BRAZE_SDK_ENDPOINT", ""),
                        lines=1,
                        info="Used for braze.initialize() baseUrl (e.g., sdk.iad-01.braze.com)"
                    )
                with gr.Column(scale=1):
                    validate_btn = gr.Button(
                        "✓ Validate & Continue",
                        variant="primary",
                        size="lg"
                    )

            validation_status = gr.Markdown("")

        # ====================================================================
        # SECTION 2: Chat Interface
        # ====================================================================

        with gr.Accordion("2️⃣ Generate Landing Page", open=False) as chat_section:
            gr.Markdown(
                """
                Describe the landing page you want to create. Include:
                - Braze SDK features needed (push notifications, user tracking, etc.)
                - Customer website URL for branding (optional)

                Or click a quick suggestion below to get started!
                """
            )

            with gr.Row():
                # Chat interface
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        value=[],  # Initialize with empty list for messages format
                        height=450,
                        show_label=False,
                        avatar_images=(None, "https://www.braze.com/favicon.ico")
                        # Gradio 6+ automatically detects message format from data structure
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="Your Request",
                            placeholder="Example: Create a landing page with push notifications and user tracking for https://nike.com",
                            lines=3,
                            scale=4
                        )
                        submit_btn = gr.Button("Generate", variant="primary", scale=1)

                # Quick suggestions sidebar
                with gr.Column(scale=1):
                    gr.Markdown("### 💡 Quick Suggestions")

                    # Create buttons for each suggestion
                    suggestion_buttons = []
                    for suggestion in suggestions[:6]:  # Show top 6
                        btn = gr.Button(
                            format_suggestion_label(suggestion),
                            size="sm",
                            variant="secondary"
                        )
                        suggestion_buttons.append((btn, suggestion["id"]))

        # ====================================================================
        # SECTION 3: Preview & Export
        # ====================================================================

        with gr.Accordion("3️⃣ Preview & Export", open=False) as export_section:
            gr.Markdown(
                """
                Preview your generated landing page and download the HTML file.
                """
            )

            with gr.Tabs():
                # Preview tab
                with gr.Tab("🔍 Preview"):
                    preview_html = gr.HTML(
                        label="Landing Page Preview",
                        value="<p>Generate a landing page first to see preview</p>"
                    )
                    refresh_preview_btn = gr.Button("🔄 Refresh Preview", size="sm")

                # Branding tab
                with gr.Tab("🎨 Branding"):
                    branding_json = gr.JSON(
                        label="Extracted Branding Data",
                        value={"message": "No branding data yet"}
                    )
                    refresh_branding_btn = gr.Button("🔄 Refresh Branding", size="sm")

            # Export section
            gr.Markdown("### 📥 Download")
            with gr.Row():
                download_file = gr.File(
                    label="HTML File",
                    interactive=False,
                    visible=True
                )
                export_btn = gr.Button("📦 Prepare Download", variant="primary")

        # ====================================================================
        # Event Handlers
        # ====================================================================

        # API validation
        validate_btn.click(
            fn=ui.validate_api_config,
            inputs=[api_key_input, sdk_endpoint_input],
            outputs=[validation_status, api_config_state, api_section, chat_section]
        )

        # Message submission (both button and Enter key)
        # Note: Chatbot value must be initialized as None or [] for messages format
        def submit_message(message, history):
            # Ensure history is a list (handle None case)
            if history is None:
                history = []
            # Important: yield from the generator to make this function itself a generator
            yield from ui.generate_streaming(message, history)

        submit_btn.click(
            fn=submit_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot]
        ).then(
            fn=lambda: "",  # Clear input
            outputs=[msg_input]
        ).then(
            fn=lambda: gr.Accordion(open=True),  # Open export section
            outputs=[export_section]
        )

        msg_input.submit(
            fn=submit_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot]
        ).then(
            fn=lambda: "",
            outputs=[msg_input]
        ).then(
            fn=lambda: gr.Accordion(open=True),
            outputs=[export_section]
        )

        # Feature suggestion buttons
        for btn, suggestion_id in suggestion_buttons:
            btn.click(
                fn=lambda sid=suggestion_id, msg=msg_input: ui.insert_suggestion(sid, msg),
                inputs=[msg_input],
                outputs=[msg_input]
            )

        # Preview and export
        refresh_preview_btn.click(
            fn=ui.get_preview_html,
            outputs=[preview_html]
        )

        refresh_branding_btn.click(
            fn=ui.get_branding_data,
            outputs=[branding_json]
        )

        export_btn.click(
            fn=ui.export_html_file,
            outputs=[download_file]
        )

        # Footer
        gr.Markdown(
            """
            ---
            **Braze SDK Landing Page Generator** | Powered by Claude Code & LangGraph
            """
        )

    return demo


def launch_ui(
    export_dir: str = "/tmp/braze_exports",
    enable_browser_testing: bool = True,
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    **kwargs
):
    """Launch Gradio UI.

    Args:
        export_dir: Directory for exported HTML files
        enable_browser_testing: Whether to enable browser testing
        share: Whether to create public share link
        server_name: Server hostname
        server_port: Server port
        **kwargs: Additional arguments for gr.Blocks.launch()
    """
    demo = create_gradio_interface(
        export_dir=export_dir,
        enable_browser_testing=enable_browser_testing
    )

    logger.info(f"Launching Gradio UI on {server_name}:{server_port}")

    demo.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        allowed_paths=[export_dir],  # Allow access to export directory
        **kwargs
    )


if __name__ == "__main__":
    # Simple launch for testing
    launch_ui()

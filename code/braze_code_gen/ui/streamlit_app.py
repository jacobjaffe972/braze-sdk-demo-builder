"""Streamlit UI for Braze SDK Landing Page Generator.

This module provides a web interface for generating Braze SDK landing pages
with real-time token-level streaming updates and cancellation support.
"""

import os
import logging
import base64
from pathlib import Path
from typing import Optional

# IMPORTANT: Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig

logger = logging.getLogger(__name__)

# Page configuration with dark theme
st.set_page_config(
    page_title="Braze Landing Page Generator",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Load custom CSS
CSS_PATH = Path(__file__).parent / "streamlit_styles.css"
if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text()}</style>", unsafe_allow_html=True)
else:
    st.error(f"CSS file not found at {CSS_PATH}")

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

    # Token-level streaming state (NEW)
    if "current_node_name" not in st.session_state:
        st.session_state.current_node_name = None
    if "node_thinking_text" not in st.session_state:
        st.session_state.node_thinking_text = {}  # {node_name: accumulated_tokens}
    if "node_start_times" not in st.session_state:
        st.session_state.node_start_times = {}  # Track when each node started

# Initialize on app load
init_session_state()

# ============================================
# Agent Output Fragment (Auto-Updating)
# ============================================

@st.fragment(run_every=0.1 if st.session_state.streaming_active else None)
def agent_output_fragment():
    """Simplified sidebar for current agent status."""

    if st.session_state.streaming_active:
        # Header with Braze logo
        st.html("""
        <div class="agent-sidebar-header">
            <div class="braze-logo-small"></div>
            <span>Active Agent</span>
        </div>
        """)

        # Current agent name
        if st.session_state.current_agent:
            st.caption(f"🤖 {st.session_state.current_agent}")

        # Thinking spinner
        st.html('<div class="thinking-spinner"></div>')

    elif st.session_state.get("agent_output") == "":
        st.caption("Agent will activate during generation...")

# Call fragment in sidebar context
with st.sidebar:
    agent_output_fragment()

# Main container wrapper
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Load and encode the Braze logo
logo_path = Path(__file__).parent / "assets" / "braze-logo.webp"
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/webp;base64,{logo_data}" alt="Braze" class="braze-logo-large">'
else:
    # Fallback if logo not found
    logo_html = '<div class="braze-logo-large" style="background: #ea580c; border-radius: 50%;"></div>'

# New Chat-Based UI header with Braze logo
st.markdown(f"""
    <div class="braze-main-header">
        {logo_html}
        <h1 class="gradient-heading">Generate Braze SDK Demos</h1>
        <p class="gradient-subheading">Explain what you want to build then let our agents do the rest.</p>
    </div>
""", unsafe_allow_html=True)

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
            "Generate Landing Page",
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
# Generation Progress with Token Streaming
# ============================================

@st.fragment(run_every=0.1 if st.session_state.streaming_active else None)
def progress_display_fragment():
    """Auto-updating fragment for real-time progress with token streaming."""

    if st.session_state.node_states:
        with st.container():
            st.html('<div class="status-card-header">⚙️ Generation Progress</div>')

            # Define node order for consistent display
            node_order = ["planning", "research", "code_generation", "validation", "refinement", "finalization"]

            for node_name in node_order:
                if node_name not in st.session_state.node_states:
                    continue

                node_data = st.session_state.node_states[node_name]
                status = node_data.get("status", "pending")
                message = node_data.get("message", node_name)

                # Determine if this is the currently active node
                is_active = (st.session_state.current_node_name == node_name and
                           st.session_state.streaming_active)

                if status == "running" or is_active:
                    # ACTIVE NODE - Show spinner + token stream
                    with st.container():
                        # Spinner with node name
                        st.html(f'''
                        <div class="node-active-container">
                            <div class="thinking-spinner"></div>
                            <span class="node-active-text">⚙️ {message}</span>
                        </div>
                        ''')

                        # Token stream display (expandable)
                        thinking_text = st.session_state.node_thinking_text.get(node_name, "")
                        if thinking_text:
                            with st.expander("🧠 Agent Thinking (Live)", expanded=True):
                                st.markdown(f'<div class="thinking-container">{thinking_text}</div>',
                                          unsafe_allow_html=True)

                elif status == "success":
                    # COMPLETED NODE - Green checkmark
                    st.success(f"✓ {message}")

                elif status == "error":
                    # ERROR NODE - Red X
                    st.error(f"✗ {message}")

                else:
                    # PENDING NODE - Grey info
                    st.info(f"⋯ {message}")

# Render the fragment
progress_display_fragment()

# ============================================
# Results Panel (after completion)
# ============================================

if st.session_state.generation_complete:
    with st.container():
        st.html('<div class="success-card-header">✅ Generation Complete</div>')

        col1 = st.columns(1)[0]  # Single column for download button only

        with col1:
            if st.session_state.export_path and Path(st.session_state.export_path).exists():
                st.markdown('<div class="download-button">', unsafe_allow_html=True)
                with open(st.session_state.export_path, "rb") as f:
                    st.download_button(
                        label="📥 Download HTML",
                        data=f,
                        file_name="braze_landing_page.html",
                        mime="text/html",
                        type="primary",
                        use_container_width=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("Export file not found")

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

        # Create a placeholder for token streaming display
        token_stream_placeholder = st.empty()

        # Counter for periodic UI updates during token streaming
        token_update_counter = 0

        try:
            # Stream from orchestrator (pass stop_event for UI-agnostic cancellation)
            for update in st.session_state.orchestrator.generate_streaming(
                user_message=prompt,
                max_refinement_iterations=3,
                callbacks=[token_callback],
                stop_event=st.session_state.stop_event  # Pass threading.Event
            ):
                update_type = update.get("type")

                if update_type == "node_start":
                    # Node starting - set as current active node (NEW)
                    node_name = update.get("node", "Unknown")
                    st.session_state.current_node_name = node_name
                    st.session_state.node_thinking_text[node_name] = ""  # Initialize empty

                    # Mark as running in node_states
                    st.session_state.node_states[node_name] = {
                        "status": "running",
                        "message": f"{node_name} in progress..."
                    }

                    # Update token stream display placeholder
                    with token_stream_placeholder.container():
                        st.info(f"🧠 {node_name} starting...")

                elif update_type == "node_complete":
                    # Node completed - update state
                    node_name = update.get("node", "Unknown")
                    status_msg = update.get("status", "")
                    st.session_state.node_states[node_name] = {
                        "status": "success",
                        "message": status_msg if status_msg else f"{node_name} completed"
                    }

                    # Display final tokens for this node before clearing
                    thinking_text = st.session_state.node_thinking_text.get(node_name, "")
                    if thinking_text:
                        with token_stream_placeholder.container():
                            with st.expander(f"✓ {node_name} - Final Output ({len(thinking_text)} chars)", expanded=False):
                                st.markdown(f'<div class="thinking-container">{thinking_text[:500]}...</div>',
                                          unsafe_allow_html=True)

                    # Clear current node tracking (node is done - NEW)
                    if st.session_state.current_node_name == node_name:
                        st.session_state.current_node_name = None

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

# Close main container
st.markdown('</div>', unsafe_allow_html=True)

# Streamlit Migration Implementation Guide

**Version**: 1.1
**Date**: 2026-01-18
**Project**: Braze SDK Landing Page Generator
**Estimated Effort**: 40-56 hours (1.5-2 weeks)
**Status**: Updated to address backend/frontend decoupling

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Setup & Configuration](#phase-1-setup--configuration)
4. [Phase 2: Core UI Migration](#phase-2-core-ui-migration)
5. [Phase 3: Token-Level Streaming](#phase-3-token-level-streaming)
6. [Phase 4: Stop Button Implementation](#phase-4-stop-button-implementation)
7. [Phase 5: Agent Sidebar with Braze Logo](#phase-5-agent-sidebar-with-braze-logo)
8. [Phase 6: Polish & Testing](#phase-6-polish--testing)
9. [Phase 7: Documentation & Deployment](#phase-7-documentation--deployment)
10. [Testing Guide](#testing-guide)
11. [Troubleshooting](#troubleshooting)
12. [Appendix](#appendix)

---

## Overview

This guide provides step-by-step instructions for migrating the Braze SDK Landing Page Generator from Gradio to Streamlit with enhanced features:

### Migration Goals
- ✅ Migrate from Gradio to Streamlit framework
- ✅ Add token-level streaming for real-time agent output
- ✅ Implement stop button to cancel generation mid-stream
- ✅ Add thinking spinner status indicator
- ✅ Display Braze logo in agent sidebar response
- ❌ **Skip**: Feature suggestion chips (not required)

### Architecture Comparison

**Current (Gradio)**:
```
User Input → Generator Function → Orchestrator Stream
→ Yield Status Updates → HTML Rendering with Spinners
```

**New (Streamlit)**:
```
User Input → Session State + Fragment → Orchestrator Stream (with Event)
→ LangChain Callbacks → Token Display + Container Updates
→ Auto-Rerun Fragment → Real-Time UI Updates
→ Threading Event → UI-Agnostic Cancellation
```

---

## Prerequisites

### Required Knowledge
- Python 3.10+
- Streamlit fundamentals
- LangChain callbacks
- Session state management
- CSS/HTML basics

### Tools & Versions
```bash
python>=3.10
streamlit>=1.30.0
langchain>=0.1.0
langgraph>=0.0.40
```

### Current Project Structure
```
code-gen-agent/
├── code/
│   └── braze_code_gen/
│       ├── agents/
│       │   └── orchestrator.py
│       ├── core/
│       │   ├── models.py
│       │   ├── workflow.py
│       │   └── llm_factory.py
│       └── ui/
│           ├── gradio_app.py       # Current implementation
│           ├── theme.py
│           └── styles.css
```

---

## Phase 1: Setup & Configuration

**Duration**: 4-6 hours

### Step 1.1: Install Streamlit

```bash
# Add to code/requirements.txt
echo "streamlit>=1.30.0" >> code/requirements.txt

# Install
pip install streamlit>=1.30.0
```

### Step 1.2: Create Streamlit Configuration

Create `.streamlit/config.toml` in project root:

```toml
[theme]
# Braze brand colors
primaryColor = "#3accdd"              # Braze teal
backgroundColor = "#f8fafc"           # slate-50
secondaryBackgroundColor = "#ffffff"  # white
textColor = "#334155"                 # slate-700
font = "sans serif"

[theme.base]
base = "light"

[server]
headless = true
port = 7860
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

### Step 1.3: Create Custom CSS File

Create `code/braze_code_gen/ui/streamlit_styles.css`:

```css
/* ============================================
   Braze Landing Page Generator - Streamlit Styles
   ============================================ */

/* Root CSS Variables */
:root {
    --braze-teal: #3accdd;
    --braze-coral: #f64060;
    --braze-blue: #2196F3;
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    --slate-300: #cbd5e1;
    --slate-400: #94a3b8;
    --slate-500: #64748b;
    --slate-700: #334155;
    --slate-900: #0f172a;
    --green-500: #10b981;
    --green-700: #065f46;
    --red-500: #ef4444;
}

/* Hide Streamlit Branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Braze Header */
.braze-header {
    background: white;
    border-bottom: 1px solid var(--slate-200);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin: -16px -16px 24px -16px;
    border-radius: 12px 12px 0 0;
}

.braze-logo {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--braze-teal), var(--braze-blue));
    border-radius: 8px;
    flex-shrink: 0;
}

.braze-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--slate-900);
    margin: 0;
}

/* Status Card */
.status-card-header {
    font-size: 16px;
    font-weight: 600;
    color: var(--slate-700);
    margin-bottom: 12px;
}

/* Success Card */
.success-card-header {
    font-size: 16px;
    font-weight: 600;
    color: var(--green-700);
    margin-bottom: 16px;
}

/* Agent Sidebar Header */
.agent-sidebar-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: linear-gradient(135deg, var(--braze-teal), var(--braze-blue));
    border-radius: 8px;
    margin-bottom: 16px;
}

.braze-logo-small {
    width: 24px;
    height: 24px;
    background: white;
    border-radius: 4px;
    flex-shrink: 0;
}

.agent-sidebar-header span {
    color: white;
    font-weight: 600;
    font-size: 14px;
}

/* Thinking Spinner */
.thinking-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: var(--braze-teal);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: inline-block;
    margin-left: 8px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Status Spinner (in main area) */
.status-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid var(--slate-200);
    border-top-color: var(--braze-teal);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: inline-block;
    margin-right: 8px;
}

/* Responsive Design */
@media (max-width: 640px) {
    .braze-header {
        padding: 12px 16px;
    }

    .braze-title {
        font-size: 16px;
    }
}
```

### Step 1.4: Create Main Streamlit App File

Create `code/braze_code_gen/ui/streamlit_app.py`:

```python
"""Streamlit UI for Braze SDK Landing Page Generator.

This module provides a web interface for generating Braze SDK landing pages
with real-time token-level streaming updates and cancellation support.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import streamlit as st

# Imports will be added in later phases
# from braze_code_gen.agents.orchestrator import Orchestrator
# from braze_code_gen.core.models import BrazeAPIConfig

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

# Braze header
st.html("""
<div class="braze-header">
    <div class="braze-logo"></div>
    <span class="braze-title">Landing Page Generator</span>
</div>
""")

# Placeholder content
st.write("Streamlit UI - Under Construction")
```

### Step 1.5: Test Basic Setup

```bash
# Test Streamlit launches
streamlit run code/braze_code_gen/ui/streamlit_app.py

# Should open browser at http://localhost:7860
# Verify:
# - Braze header displays
# - Custom CSS loads
# - No errors in console
```

**Checkpoint**: ✅ Basic Streamlit app launches with Braze branding

---

## Phase 2: Core UI Migration

**Duration**: 10-14 hours

### Step 2.1: Initialize Session State

Add to `streamlit_app.py` after page config:

```python
# ============================================
# Session State Initialization
# ============================================

def init_session_state():
    """Initialize all session state variables."""
    from threading import Event

    # Orchestrator instance
    if "orchestrator" not in st.session_state:
        from braze_code_gen.agents.orchestrator import Orchestrator
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
```

### Step 2.2: Build Config Panel

Replace placeholder with:

```python
# ============================================
# Config Panel
# ============================================

from braze_code_gen.core.models import BrazeAPIConfig

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
```

### Step 2.3: Build Prompt Panel

Add after config panel:

```python
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
```

### Step 2.4: Build Status Panel

Add after prompt panel:

```python
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
```

### Step 2.5: Build Results Panel

Add after status panel:

```python
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
```

**Checkpoint**: ✅ All UI panels render correctly, buttons respond to clicks

---

## Phase 3: Token-Level Streaming

**Duration**: 12-16 hours

### Step 3.1: Create Callback Handler

Create `code/braze_code_gen/ui/streamlit_callbacks.py`:

```python
"""LangChain callback handlers for Streamlit token streaming."""

import logging
from typing import Any, Dict, List, Optional

from langchain.callbacks.base import BaseCallbackHandler
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
```

### Step 3.2: Modify Orchestrator for Callbacks and Cancellation

Update `code/braze_code_gen/agents/orchestrator.py`:

```python
from threading import Event
from typing import Optional, Generator, Dict, Any, List
from langchain.callbacks.base import BaseCallbackHandler

# Add to generate_streaming method signature
def generate_streaming(
    self,
    user_message: str,
    website_url: Optional[str] = None,
    max_refinement_iterations: int = 3,
    callbacks: Optional[List[BaseCallbackHandler]] = None,  # NEW
    stop_event: Optional[Event] = None  # NEW - UI-agnostic cancellation
) -> Generator[Dict[str, Any], None, None]:
    """Generate landing page with streaming updates.

    Args:
        user_message: User's feature request
        website_url: Optional customer website URL for branding
        max_refinement_iterations: Max refinement attempts
        callbacks: Optional LangChain callbacks for token streaming
        stop_event: Optional threading.Event for cancellation signaling

    Yields:
        Dict with update type and data
    """
    # ... existing code ...

    # Pass callbacks to workflow
    if callbacks:
        self.workflow.set_callbacks(callbacks)  # Will implement in workflow

    # Check for cancellation before each major step
    for update in self.workflow.stream_workflow(...):
        # Check cancellation via threading.Event (UI-agnostic)
        if stop_event and stop_event.is_set():
            yield {
                "type": "cancelled",
                "message": "Generation cancelled by user"
            }
            return

        yield update
```

### Step 3.3: Update Workflow to Support Callbacks

Update `code/braze_code_gen/core/workflow.py`:

```python
# Add to WorkflowOrchestrator class
class WorkflowOrchestrator:
    def __init__(self, ...):
        # ... existing init ...
        self.callbacks = []

    def set_callbacks(self, callbacks: List[BaseCallbackHandler]) -> None:
        """Set LangChain callbacks for streaming.

        Args:
            callbacks: List of callback handlers
        """
        self.callbacks = callbacks

    def stream_workflow(self, ...):
        # Pass callbacks to LLM invocations
        # This will vary based on your LLM factory implementation
        # Ensure all LLM calls include: callbacks=self.callbacks
```

### Step 3.4: Create Agent Output Fragment

Add to `streamlit_app.py`:

```python
# ============================================
# Agent Output Fragment (Auto-Updating)
# ============================================

@st.fragment(run_every=0.1 if st.session_state.streaming_active else None)
def agent_output_fragment():
    """Auto-updating fragment for real-time agent thinking display."""

    if st.session_state.agent_output or st.session_state.streaming_active:
        with st.sidebar:
            # Header with Braze logo
            st.html("""
            <div class="agent-sidebar-header">
                <div class="braze-logo-small"></div>
                <span>Agent Thinking</span>
            </div>
            """)

            # Agent name
            if st.session_state.current_agent:
                st.caption(f"Current: {st.session_state.current_agent}")

            # Token stream output
            if st.session_state.agent_output:
                st.markdown(st.session_state.agent_output)

            # Thinking spinner if actively streaming
            if st.session_state.streaming_active:
                st.html('<div class="thinking-spinner"></div>')
    elif st.session_state.get("agent_output") == "":
        with st.sidebar:
            st.caption("Agent output will appear here during generation")

# Call fragment in main app (add near top of file after init)
agent_output_fragment()
```

### Step 3.5: Implement Main Streaming Loop

Add generation handler to `streamlit_app.py`:

```python
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

                if update_type == "node_start":
                    # Node started - event-based approach
                    node_name = update.get("node_name", "Unknown")
                    st.session_state.node_states[node_name] = {
                        "status": "running",
                        "message": update.get("message", f"Processing {node_name}...")
                    }

                elif update_type == "node_end":
                    # Node completed - update state
                    node_name = update.get("node_name", "Unknown")
                    status = update.get("status", "success")  # success, error
                    st.session_state.node_states[node_name] = {
                        "status": status,
                        "message": update.get("message", f"{node_name} completed")
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
```

**Checkpoint**: ✅ Token-level streaming displays in sidebar, status updates appear progressively

---

## Phase 4: Stop Button Implementation

**Duration**: 2-3 hours

### Step 4.1: Cancellation Architecture (Already Implemented)

The cancellation mechanism has been implemented in previous steps using a **UI-agnostic approach**:

**Key Design**:
- Uses `threading.Event` instead of Streamlit session state flags
- Orchestrator accepts `stop_event` parameter (no Streamlit dependency)
- Callback handler checks `stop_event.is_set()` (UI-agnostic)
- UI sets the event via `stop_event.set()` on button click

**Benefits**:
- ✅ Backend remains UI-agnostic (can work with any frontend)
- ✅ Orchestrator can be tested without Streamlit
- ✅ Can be reused with CLI, API, or other UIs
- ✅ Clean separation of concerns

### Step 4.2: Cancellation Flow

The cancellation is already wired up across the stack:

**1. Orchestrator** (Step 3.2):
```python
def generate_streaming(self, ..., stop_event: Optional[Event] = None):
    for update in self.workflow.stream_workflow(...):
        if stop_event and stop_event.is_set():
            yield {"type": "cancelled", "message": "Generation cancelled"}
            return
        yield update
```

**2. Callback Handler** (Step 3.1):
```python
def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
    if st.session_state.stop_event.is_set():
        raise KeyboardInterrupt("Streaming cancelled by user")
    # ... rest of token handling ...
```

**3. UI Stop Button** (Step 3.5):
```python
if stop:
    st.session_state.stop_event.set()  # Signal cancellation
    st.session_state.streaming_active = False
    st.info("Cancellation requested...")
    st.rerun()
```

### Step 4.3: UI Button States

Already implemented in Step 2.3:

```python
# Generate button - disabled when streaming
disabled=st.session_state.streaming_active or not st.session_state.api_config

# Stop button - disabled when not streaming
disabled=not st.session_state.streaming_active
```

### Step 4.4: Test Cancellation

```bash
# Test scenarios:
# 1. Click stop during planning phase
# 2. Click stop during code generation
# 3. Click stop during validation
# 4. Multiple rapid clicks on stop button
# 5. Cancel then immediately start new generation
```

**Checkpoint**: ✅ Stop button cancels generation at any phase, UI updates correctly

---

## Phase 5: Agent Sidebar with Braze Logo

**Duration**: 2-3 hours

### Step 5.1: CSS Already Added

CSS for agent sidebar already added in Phase 1.3:
- `.agent-sidebar-header` - Header container
- `.braze-logo-small` - Small Braze logo
- `.thinking-spinner` - Animated spinner

### Step 5.2: Fragment Already Implemented

Fragment with logo already created in Phase 3.4:

```python
@st.fragment(run_every=0.1 if st.session_state.streaming_active else None)
def agent_output_fragment():
    # ... renders sidebar with logo ...
```

### Step 5.3: Enhancement - Agent Name Display

Update fragment to show which agent is currently running:

```python
# In agent_output_fragment()
if st.session_state.current_agent:
    st.caption(f"🤖 Current Agent: {st.session_state.current_agent}")
```

### Step 5.4: Enhancement - Token Count

Optional: Show token count in sidebar:

```python
# Add to session state init
if "token_count" not in st.session_state:
    st.session_state.token_count = 0

# Update in callback handler
def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
    # ... existing code ...
    st.session_state.token_count += 1

# Display in fragment
if st.session_state.streaming_active:
    st.caption(f"Tokens: {st.session_state.token_count}")
```

**Checkpoint**: ✅ Sidebar displays Braze logo, agent name, and thinking spinner

---

## Phase 6: Polish & Testing

**Duration**: 6-8 hours

### Step 6.1: CSS Refinement

Test and refine:
- [ ] Braze header alignment
- [ ] Spinner animation smoothness
- [ ] Success/error card colors
- [ ] Mobile responsiveness
- [ ] Dark mode support (optional)

### Step 6.2: Error Handling

Add comprehensive error handling:

```python
# In generate handler
try:
    # ... streaming logic ...
except KeyboardInterrupt:
    st.info("🛑 Streaming cancelled")
except TimeoutError:
    st.error("❌ Request timed out. Please try again.")
except ConnectionError:
    st.error("❌ Network error. Check your connection.")
except Exception as e:
    logger.exception("Unexpected error during generation")
    st.error(f"❌ Unexpected error: {str(e)}")
    st.error("Please refresh the page and try again.")
finally:
    st.session_state.streaming_active = False
```

### Step 6.3: Validation Improvements

```python
# Enhanced API validation
def validate_api_config(api_key: str, sdk_endpoint: str) -> tuple[bool, str]:
    """Validate API configuration with detailed feedback."""

    # API key validation
    if not api_key:
        return False, "API key is required"
    if len(api_key) < 32:
        return False, f"API key too short ({len(api_key)} chars, need 32+)"

    # SDK endpoint validation
    if not sdk_endpoint:
        return False, "SDK endpoint is required"
    if not sdk_endpoint.endswith(".braze.com"):
        return False, "SDK endpoint must be a .braze.com domain"

    # Format validation
    import re
    endpoint_pattern = r'^sdk\.[a-z0-9-]+\.braze\.com$'
    if not re.match(endpoint_pattern, sdk_endpoint):
        return False, "SDK endpoint format: sdk.{instance}.braze.com"

    return True, "Valid"
```

### Step 6.4: Loading States

Add loading indicators:

```python
# During validation
if validate:
    with st.spinner("Validating API credentials..."):
        valid, message = validate_api_config(api_key, sdk_endpoint)
        if valid:
            st.success(f"✅ {message}")
        else:
            st.error(f"❌ {message}")
```

### Step 6.5: User Feedback

Add helpful messages:

```python
# Empty state
if not st.session_state.api_config:
    st.info("👆 Please validate your API configuration to begin")

# After validation
if st.session_state.api_config and not prompt:
    st.info("👇 Describe your landing page to generate")

# During streaming
if st.session_state.streaming_active:
    st.caption("⚠️ Generation in progress. Do not close this window.")
```

**Checkpoint**: ✅ All error states handled, loading indicators smooth, helpful messages displayed

---

## Phase 7: Documentation & Deployment

**Duration**: 4-6 hours

### Step 7.1: Create Launch Script

Create `launch_streamlit.sh`:

```bash
#!/bin/bash
# Launch Braze SDK Landing Page Generator (Streamlit UI)

set -e

echo "==================================="
echo "Braze Landing Page Generator"
echo "Streamlit UI"
echo "==================================="

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating venv..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating .venv..."
    source .venv/bin/activate
else
    echo "No virtual environment found. Using system Python."
fi

# Check dependencies
echo "Checking dependencies..."
python -c "import streamlit" 2>/dev/null || {
    echo "Streamlit not installed. Installing..."
    pip install streamlit>=1.30.0
}

# Launch Streamlit
echo "Launching Streamlit UI..."
echo "Access at: http://localhost:7860"
echo ""

streamlit run code/braze_code_gen/ui/streamlit_app.py \
    --server.port 7860 \
    --server.headless true \
    --browser.gatherUsageStats false
```

Make executable:
```bash
chmod +x launch_streamlit.sh
```

### Step 7.2: Update README

Update `code/braze_code_gen/README.md`:

```markdown
## Launching the UI

### Streamlit UI (New)

```bash
# Option 1: Using launch script
./launch_streamlit.sh

# Option 2: Direct streamlit command
streamlit run code/braze_code_gen/ui/streamlit_app.py

# Option 3: Custom port
streamlit run code/braze_code_gen/ui/streamlit_app.py --server.port 8080
```

Then open http://localhost:7860 in your browser.

### Gradio UI (Legacy)

```bash
# Option 1: Using launch script
./launch_ui.sh

# Option 2: Python module
python -m braze_code_gen
```

Then open http://localhost:7860 in your browser.

## Features

### New in Streamlit UI

- ✨ **Token-level streaming**: Watch agents think in real-time
- ⏹ **Stop button**: Cancel generation mid-stream
- 🧠 **Agent sidebar**: See which agent is working with Braze branding
- 🎨 **Enhanced UI**: Modern Streamlit interface with custom theming

### Core Features (Both UIs)

- 🔑 API key validation
- 🎯 Natural language prompt input
- 📊 Progressive status updates
- 🌈 Automatic website branding extraction
- 📥 One-click HTML download
- 🎨 Branding data viewer
```

### Step 7.3: Create Migration Notes

Create `code/braze_code_gen/ui/STREAMLIT_MIGRATION.md`:

```markdown
# Streamlit Migration Notes

## Overview

Migrated Braze SDK Landing Page Generator from Gradio to Streamlit.

**Date**: 2026-01-16
**Effort**: ~45 hours over 2 weeks
**Status**: ✅ Complete

## Key Changes

### Added Features
1. **Token-level streaming** via LangChain callbacks
2. **Stop button** for mid-stream cancellation
3. **Agent sidebar** with Braze logo and thinking display
4. **Auto-updating fragments** for real-time UI updates

### Removed Features
1. Feature suggestion chips (not needed per requirements)

### Architecture Changes

**Gradio (Old)**:
- Event-driven callbacks
- Generator-based streaming
- HTML rendering for status

**Streamlit (New)**:
- Session state management
- Fragment-based auto-updates
- LangChain callback handlers
- Container replacement pattern

## File Structure

```
code/braze_code_gen/ui/
├── gradio_app.py              # Legacy Gradio UI
├── streamlit_app.py           # New Streamlit UI ⭐
├── streamlit_callbacks.py     # Token streaming handlers ⭐
├── streamlit_styles.css       # Custom Braze CSS ⭐
├── theme.py                   # Gradio theme (legacy)
└── styles.css                 # Gradio CSS (legacy)
```

## Known Issues

### None currently

## Future Enhancements

1. **Export history**: Track past generations with SQLite
2. **Authentication**: Add user login
3. **Multi-page**: Separate pages for config/generation/history
4. **Streamlit Cloud**: Deploy to free hosting
5. **Advanced features**:
   - Save/load prompt templates
   - Batch generation
   - Live preview iframe

## Rollback Procedure

If needed, revert to Gradio:

```bash
# Use legacy Gradio UI
python -m braze_code_gen

# Or
./launch_ui.sh
```

Both UIs are maintained in parallel.
```

### Step 7.4: Update Requirements

Verify `code/requirements.txt` includes:

```txt
# Streamlit UI
streamlit>=1.30.0
```

### Step 7.5: Testing Documentation

Create `code/braze_code_gen/ui/TESTING.md`:

```markdown
# Streamlit UI Testing Guide

## Manual Testing Checklist

### Functional Tests

- [ ] **API Configuration**
  - [ ] Empty fields show validation errors
  - [ ] Short API key rejected (<32 chars)
  - [ ] Valid credentials accepted
  - [ ] Success message displays
  - [ ] Config persists in session state

- [ ] **Prompt Input**
  - [ ] Text area accepts input
  - [ ] Disabled during streaming
  - [ ] Enabled after completion/cancellation

- [ ] **Generate Button**
  - [ ] Disabled when no API config
  - [ ] Disabled during streaming
  - [ ] Triggers streaming on click
  - [ ] Re-enabled after completion

- [ ] **Stop Button**
  - [ ] Disabled when not streaming
  - [ ] Enabled during streaming
  - [ ] Cancels generation
  - [ ] Sets cancel flag

- [ ] **Token Streaming**
  - [ ] Appears in sidebar
  - [ ] Updates in real-time (<200ms latency)
  - [ ] Shows agent name
  - [ ] Displays thinking spinner

- [ ] **Status Updates**
  - [ ] Steps appear progressively
  - [ ] Spinners show for active steps
  - [ ] Checkmarks show for completed steps
  - [ ] Final step marked complete

- [ ] **Results**
  - [ ] Success card appears
  - [ ] Download button works
  - [ ] HTML file downloads correctly
  - [ ] Branding data displays

### Performance Tests

- [ ] Token streaming latency <100ms
- [ ] Fragment reruns smooth (no flicker)
- [ ] Large HTML files download successfully
- [ ] No memory leaks after multiple generations

### Edge Cases

- [ ] Cancel during planning phase
- [ ] Cancel during code generation
- [ ] Cancel during validation
- [ ] Cancel immediately after start
- [ ] Multiple rapid generate clicks
- [ ] Empty prompt submission
- [ ] Invalid API credentials
- [ ] Network timeout
- [ ] File system errors

### Browser Compatibility

- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

### Mobile Responsiveness

- [ ] Layout adapts to mobile
- [ ] Buttons accessible
- [ ] Sidebar toggle works

## Automated Testing

```bash
# Unit tests (if implemented)
pytest code/braze_code_gen/tests/test_streamlit_ui.py

# Integration tests
pytest code/braze_code_gen/tests/test_streamlit_integration.py
```

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Token latency | <100ms | TBD |
| Fragment rerun | <50ms | TBD |
| Full generation | <60s | TBD |
| Memory usage | <500MB | TBD |
```

**Checkpoint**: ✅ Documentation complete, launch scripts work, testing guide created

---

## Testing Guide

### Quick Start Testing

```bash
# 1. Install dependencies
pip install -r code/requirements.txt

# 2. Launch Streamlit
./launch_streamlit.sh

# 3. Test basic flow
# - Validate API config
# - Enter prompt
# - Click generate
# - Watch token streaming in sidebar
# - Click stop to cancel
# - Complete generation
# - Download HTML file
```

### Functional Testing Checklist

Use the checklist in `code/braze_code_gen/ui/TESTING.md` (created in Phase 7.5)

### Performance Testing

```python
# Measure token latency
import time

class LatencyCallback(BaseCallbackHandler):
    def __init__(self):
        self.latencies = []
        self.last_time = None

    def on_llm_new_token(self, token, **kwargs):
        now = time.time()
        if self.last_time:
            latency = (now - self.last_time) * 1000  # ms
            self.latencies.append(latency)
        self.last_time = now

    def on_llm_end(self, response, **kwargs):
        avg_latency = sum(self.latencies) / len(self.latencies)
        print(f"Average token latency: {avg_latency:.2f}ms")
```

### Integration Testing

Test full workflow:

1. Fresh browser session
2. Validate API config
3. Generate landing page with website URL
4. Verify branding extraction
5. Download HTML
6. Test HTML in browser
7. Verify Braze SDK initialization

---

## Troubleshooting

### Issue: Token streaming not appearing

**Symptoms**: Sidebar stays empty during generation

**Solutions**:
1. Check fragment is called: `agent_output_fragment()`
2. Verify callback handler added to orchestrator
3. Check session state: `st.session_state.agent_output`
4. Increase fragment rerun frequency: `run_every=0.05`

### Issue: Stop button doesn't work

**Symptoms**: Generation continues after clicking stop

**Solutions**:
1. Verify session state flag set: `st.session_state.cancel_requested = True`
2. Check orchestrator checks flag in loop
3. Ensure callback handler raises KeyboardInterrupt
4. Add logging to see where cancellation is missed

### Issue: CSS not loading

**Symptoms**: Page appears unstyled

**Solutions**:
1. Verify CSS file path: `CSS_PATH = Path(__file__).parent / "streamlit_styles.css"`
2. Check file exists: `ls code/braze_code_gen/ui/streamlit_styles.css`
3. Inspect HTML source for `<style>` tags
4. Clear browser cache

### Issue: Fragment updates too slow

**Symptoms**: Token display lags behind generation

**Solutions**:
1. Reduce rerun interval: `run_every=0.05` (from 0.1)
2. Check for expensive operations in fragment
3. Profile with `streamlit run --profiler`

### Issue: Session state conflicts

**Symptoms**: State resets unexpectedly

**Solutions**:
1. Ensure `init_session_state()` called early
2. Use `if "key" not in st.session_state` guards
3. Don't overwrite state accidentally
4. Check for key name collisions

### Issue: Export file not found

**Symptoms**: Download button shows error

**Solutions**:
1. Verify export directory exists: `mkdir -p /tmp/braze_exports`
2. Check file permissions
3. Log export path: `logger.info(f"Export path: {export_path}")`
4. Ensure orchestrator saves file before returning

---

## Appendix

### A. Complete Session State Schema

```python
st.session_state = {
    # Core
    "orchestrator": Orchestrator,           # Workflow orchestrator instance
    "api_config": BrazeAPIConfig | None,    # Validated API configuration

    # Streaming Control (UI-agnostic cancellation)
    "streaming_active": bool,               # Currently generating
    "stop_event": threading.Event,          # Thread-safe cancellation signal

    # Results
    "export_path": str | None,              # Path to generated HTML
    "branding_data": dict | None,           # Extracted branding
    "generation_complete": bool,            # Generation finished successfully

    # Status (Event-based node tracking)
    "node_states": dict[str, dict],         # Node state tracking
    # Example: {
    #   "Planning": {"status": "success", "message": "Plan created"},
    #   "CodeGen": {"status": "running", "message": "Generating code..."}
    # }

    # Agent Output
    "agent_output": str,                    # Accumulated token stream
    "current_agent": str,                   # Current agent name
    "token_count": int,                     # Total tokens (optional)
}
```

### B. Update Types from Orchestrator

```python
# Update types yielded by orchestrator.generate_streaming()

# Node started (NEW - event-based approach)
{
    "type": "node_start",
    "node_name": "Planning",
    "message": "Creating feature plan..."
}

# Node completed (NEW - event-based approach)
{
    "type": "node_end",
    "node_name": "Planning",
    "status": "success",  # or "error"
    "message": "✓ Feature plan created with customer branding"
}

# Generation complete
{
    "type": "complete",
    "export_file_path": "/tmp/braze_exports/landing_page_20260116_143022.html",
    "branding_data": {...}
}

# Error occurred
{
    "type": "error",
    "message": "Validation failed: SDK not loaded"
}

# Cancelled by user
{
    "type": "cancelled",
    "message": "Generation cancelled by user"
}
```

### C. Fragment Rerun Timing

| Frequency | Use Case | Performance |
|-----------|----------|-------------|
| `0.05s` | Very responsive token streaming | High CPU usage |
| `0.1s` | **Recommended** - Good balance | Moderate CPU |
| `0.5s` | Slower updates, lower CPU | Low CPU usage |
| `None` | Disabled - no auto-rerun | No overhead |

### D. LangChain Callback Methods

```python
class BaseCallbackHandler:
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts"""

    def on_llm_new_token(self, token, **kwargs):
        """Called for each new token"""

    def on_llm_end(self, response, **kwargs):
        """Called when LLM finishes"""

    def on_llm_error(self, error, **kwargs):
        """Called on LLM error"""

    def on_chain_start(self, serialized, inputs, **kwargs):
        """Called when chain starts"""

    def on_chain_end(self, outputs, **kwargs):
        """Called when chain ends"""
```

### E. Streamlit vs Gradio Comparison

| Feature | Gradio | Streamlit |
|---------|--------|-----------|
| **Execution Model** | Event callbacks | Script reruns |
| **State Management** | `gr.State()` | `st.session_state` |
| **Streaming** | Generator yields | Callbacks + fragments |
| **Updates** | Explicit `gr.update()` | Container replacement |
| **Theming** | Python theme class | TOML config + CSS |
| **Complexity** | Lower | Medium |
| **Token Streaming** | Not native | Via callbacks |
| **Cancellation** | Not supported | Session state flags |

### F. Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Streamlit Fragments Guide](https://docs.streamlit.io/develop/concepts/architecture/fragments)
- [LangChain Callbacks](https://python.langchain.com/docs/modules/callbacks/)
- [Streamlit Session State](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Streamlit Community Forum](https://discuss.streamlit.io)

---

**Document Version**: 1.1
**Last Updated**: 2026-01-18
**Status**: Ready for implementation

## Revision History

### Version 1.1 (2026-01-18)
**Critical Architecture Improvements:**

1. **UI-Agnostic Cancellation** (Critical Fix)
   - Replaced `st.session_state.cancel_requested` with `threading.Event`
   - Orchestrator now accepts `stop_event` parameter instead of accessing Streamlit state
   - Backend is now UI-agnostic and testable without Streamlit
   - Can be reused with CLI, API, or other frontends

2. **Event-Based Status Updates** (Important Fix)
   - Replaced brittle list manipulation with node-based state dictionary
   - Orchestrator yields `node_start` and `node_end` events
   - UI maintains `node_states` dict instead of `status_steps` list
   - More robust and resilient to event order changes

3. **Updated Session State Schema**
   - Added: `stop_event: threading.Event`
   - Added: `node_states: dict[str, dict]`
   - Removed: `cancel_requested: bool`
   - Removed: `status_steps: list[dict]`

**Benefits:**
- ✅ Clean separation between backend and frontend
- ✅ Orchestrator can be unit tested without Streamlit
- ✅ More robust status tracking
- ✅ Easier to reuse backend with different UIs

### Version 1.0 (2026-01-16)
- Initial implementation guide

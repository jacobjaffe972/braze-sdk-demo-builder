# Gradio UI Patterns

## Overview

This document describes proven patterns for building Gradio chat interfaces for LangChain agents, extracted from [/code/reference_agents/app.py](../code/reference_agents/app.py).

**Key Concepts**:
- Metadata-driven UI configuration
- Agent factory integration
- Chat history management
- Example-based onboarding
- Multi-agent switching

---

## 1. Basic Gradio Chat Interface Pattern

### Pattern Description

**Intent**: Create a simple chat interface for a single agent with minimal code.

### Minimal Implementation

```python
import gradio as gr
from your_agent import create_agent

def create_demo():
    """Create and return a Gradio demo."""

    # Create the agent
    agent = create_agent("my_agent")

    # Create the respond function
    def respond(message: str, history):
        """Process the message and return a response."""
        return agent.process_message(message, history)

    # Create the Gradio interface
    demo = gr.ChatInterface(
        fn=respond,
        title="My AI Assistant",
        description="An intelligent AI assistant.",
        examples=["Hello!", "How can you help me?"]
    )

    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch()
```

### Key Components

1. **Agent Creation**: Instantiate agent before UI creation
2. **Respond Function**: Wrapper that calls agent's `process_message()`
3. **gr.ChatInterface**: Gradio's built-in chat component
4. **Examples**: Quick-start prompts for users

---

## 2. Metadata-Driven UI Pattern

### Pattern Description

**Intent**: Configure UI dynamically based on agent metadata, enabling multi-agent support without duplicating UI code.

**Source**: [/code/reference_agents/app.py](../code/reference_agents/app.py)

### Implementation

```python
import gradio as gr
from typing import List, Tuple
from deep_research.core.factory import create_agent_by_name, AGENT_ALIASES, AgentType

# Agent metadata for UI
AGENT_METADATA = {
    # LLM Chaining variants
    AgentType.LLM_CHAINING_QUERY: {
        "title": "Deep Research AI - Query Understanding",
        "description": "AI assistant that classifies queries and formats responses accordingly.",
        "examples": [
            "What is machine learning?",
            "Compare SQL and NoSQL databases",
        ]
    },
    AgentType.LLM_CHAINING_TOOLS: {
        "title": "Deep Research AI - Basic Tools",
        "description": "AI assistant with calculation and datetime capabilities.",
        "examples": [
            "What is 15% tip on $120?",
            "What day is it today?",
        ]
    },
    AgentType.REACT_DEEP_RESEARCH: {
        "title": "Deep Research AI - Deep Research",
        "description": "Multi-agent research system for comprehensive reports.",
        "examples": [
            "Research the current state of quantum computing",
            "Analyze AI's impact on healthcare delivery",
        ]
    },
    # ... more agent types
}

def create_demo(agent_name: str = "LLM_Chaining"):
    """Create and return a Gradio demo for the specified agent.

    Args:
        agent_name: Name of the agent to run (e.g., 'LLM_Chaining', 'rag_web_search')

    Returns:
        gr.ChatInterface: Configured Gradio chat interface
    """
    # Create the agent
    chat_interface = create_agent_by_name(agent_name)

    # Get metadata (use alias mapping to find actual agent type)
    if agent_name in AGENT_ALIASES:
        agent_type = AGENT_ALIASES[agent_name]
    else:
        agent_type = AgentType(agent_name.lower())

    metadata = AGENT_METADATA.get(agent_type, {
        "title": f"Deep Research AI - {agent_name}",
        "description": "Your intelligent AI assistant.",
        "examples": ["Hello!", "How can you help me?"]
    })

    # Create the respond function
    def respond(message: str, history: List[Tuple[str, str]]) -> str:
        """Process the message and return a response."""
        return chat_interface.process_message(message, history)

    # Create the Gradio interface
    demo = gr.ChatInterface(
        fn=respond,
        title=metadata["title"],
        description=metadata["description"],
        examples=metadata["examples"]
    )

    return demo
```

### Metadata Structure

```python
AGENT_METADATA = {
    AgentType.MY_AGENT: {
        "title": str,           # Window title and header
        "description": str,     # Subtitle explaining agent capabilities
        "examples": List[str],  # Quick-start example prompts
    }
}
```

### Benefits

1. **Single UI Code Path**: One `create_demo()` function handles all agents
2. **Easy Agent Addition**: Add metadata entry, no UI code changes
3. **Consistent UX**: All agents have same interface structure
4. **Example-Based Onboarding**: Users see what agent can do

---

## 3. Chat History Management Pattern

### Pattern Description

**Intent**: Pass conversation history to agent for context-aware responses.

### Gradio History Format

Gradio's `ChatInterface` passes history as:
```python
history: List[Tuple[str, str]]
# Example:
[
    ("Hello", "Hi! How can I help you?"),
    ("What's 2+2?", "The answer is 4."),
]
```

### Converting to LangChain Message Format

```python
from typing import List, Dict, Tuple

def respond(message: str, history: List[Tuple[str, str]]) -> str:
    """Process the message and return a response."""

    # Convert Gradio history to agent format
    chat_history = []
    for user_msg, assistant_msg in history:
        chat_history.append({"role": "user", "content": user_msg})
        chat_history.append({"role": "assistant", "content": assistant_msg})

    # Process message with history
    return agent.process_message(message, chat_history)
```

### Agent Implementation

```python
from langchain_core.messages import HumanMessage, AIMessage

class MyAgent(ChatInterface):
    def process_message(self, message: str, chat_history: List[Dict[str, str]]) -> str:
        """Process message with conversation history."""

        # Convert to LangChain messages
        messages = []
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=message))

        # Process with LLM
        response = self.llm.invoke(messages)
        return response.content
```

---

## 4. Advanced UI Patterns

### Pattern: Multi-Section Accordion Layout

**Use Case**: Complex workflows with initialization, generation, and export steps.

```python
import gradio as gr

def create_advanced_demo():
    """Create multi-section accordion UI."""

    with gr.Blocks() as demo:
        gr.Markdown("# Braze Code Generator")

        # Section 1: API Configuration
        with gr.Accordion("1. Configure API", open=True) as section1:
            api_key = gr.Textbox(label="API Key", type="password")
            endpoint = gr.Textbox(label="REST Endpoint", value="https://todd.braze.com")
            validate_btn = gr.Button("Validate & Continue")
            validation_status = gr.Markdown("")

        # Section 2: Chat Interface
        with gr.Accordion("2. Generate Landing Page", open=False) as section2:
            chatbot = gr.Chatbot()
            msg = gr.Textbox(
                label="Describe your landing page",
                placeholder="Include customer website URL and features"
            )
            submit = gr.Button("Generate")

        # Section 3: Preview & Export
        with gr.Accordion("3. Preview & Export", open=False) as section3:
            preview = gr.HTML(label="Preview")
            branding_data = gr.JSON(label="Extracted Branding")
            download_btn = gr.File(label="Download HTML")
            export_btn = gr.Button("Export Landing Page")

        # Event handlers
        def validate_config(api_key, endpoint):
            # Validation logic
            return "✅ Configuration valid", gr.Accordion(open=False), gr.Accordion(open=True)

        validate_btn.click(
            fn=validate_config,
            inputs=[api_key, endpoint],
            outputs=[validation_status, section1, section2]
        )

        def generate_page(message, history):
            # Generation logic
            return response, gr.Accordion(open=True)

        submit.click(
            fn=generate_page,
            inputs=[msg, chatbot],
            outputs=[chatbot, section3]
        )

    return demo
```

### Pattern: Tabbed Interface for Multiple Agents

```python
import gradio as gr

def create_tabbed_demo():
    """Create tabbed interface with multiple agents."""

    with gr.Blocks() as demo:
        gr.Markdown("# Multi-Agent System")

        with gr.Tabs():
            with gr.Tab("Research Agent"):
                research_agent_ui()

            with gr.Tab("Code Generator"):
                code_generator_ui()

            with gr.Tab("Validation Agent"):
                validation_agent_ui()

    return demo

def research_agent_ui():
    """Create UI for research agent."""
    gr.ChatInterface(
        fn=research_respond,
        title="Research Agent",
        examples=["Research quantum computing"]
    )
```

### Pattern: Real-Time Streaming Responses

```python
import gradio as gr

def create_streaming_demo():
    """Create UI with streaming responses."""

    def respond_stream(message, history):
        """Stream response token by token."""
        response = ""
        for chunk in agent.stream_message(message, history):
            response += chunk
            yield response

    demo = gr.ChatInterface(
        fn=respond_stream,
        title="Streaming Agent",
        description="Responses appear in real-time",
    )

    return demo
```

---

## 5. State Management Patterns

### Pattern: Global State with gr.State

```python
import gradio as gr

def create_stateful_demo():
    """Create UI with persistent state."""

    with gr.Blocks() as demo:
        # Hidden state component
        state = gr.State(value={"agent": None, "config": {}})

        chatbot = gr.Chatbot()
        msg = gr.Textbox()
        submit = gr.Button("Send")

        def initialize_agent(state_value):
            """Initialize agent on first load."""
            if state_value["agent"] is None:
                state_value["agent"] = create_agent("my_agent")
            return state_value

        def respond(message, history, state_value):
            """Process message with stateful agent."""
            agent = state_value["agent"]
            response = agent.process_message(message, history)
            return response, state_value

        # Initialize on load
        demo.load(fn=initialize_agent, inputs=state, outputs=state)

        # Handle message submission
        submit.click(
            fn=respond,
            inputs=[msg, chatbot, state],
            outputs=[chatbot, state]
        )

    return demo
```

### Pattern: Session-Based Context

```python
import gradio as gr
import uuid

sessions = {}

def create_session_demo():
    """Create UI with session-based context."""

    def get_or_create_session(session_id):
        """Get or create session."""
        if session_id not in sessions:
            sessions[session_id] = {
                "agent": create_agent("my_agent"),
                "context": {},
                "history": []
            }
        return sessions[session_id]

    with gr.Blocks() as demo:
        session_id = gr.State(value=str(uuid.uuid4()))

        chatbot = gr.Chatbot()
        msg = gr.Textbox()

        def respond(message, history, session_id):
            session = get_or_create_session(session_id)
            response = session["agent"].process_message(message, history)
            session["history"].append((message, response))
            return response

        msg.submit(
            fn=respond,
            inputs=[msg, chatbot, session_id],
            outputs=chatbot
        )

    return demo
```

---

## 6. Error Handling Patterns

### Pattern: Try-Catch with User Feedback

```python
def create_robust_demo():
    """Create UI with comprehensive error handling."""

    def respond_with_error_handling(message, history):
        """Process message with error handling."""
        try:
            response = agent.process_message(message, history)
            return response

        except ValueError as e:
            return f"❌ Input Error: {str(e)}\\n\\nPlease rephrase your request."

        except TimeoutError:
            return "⏱️ Request timed out. Please try a simpler query."

        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
            return "❌ An unexpected error occurred. Please try again."

    demo = gr.ChatInterface(
        fn=respond_with_error_handling,
        title="Robust Agent",
        description="Graceful error handling for better UX",
    )

    return demo
```

### Pattern: Retry Logic

```python
import time

def create_retry_demo():
    """Create UI with automatic retry."""

    def respond_with_retry(message, history, max_retries=3):
        """Process message with retry logic."""
        for attempt in range(max_retries):
            try:
                response = agent.process_message(message, history)
                return response

            except TimeoutError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return "❌ Request failed after multiple attempts. Please try again later."

            except Exception as e:
                return f"❌ Error: {str(e)}"

    demo = gr.ChatInterface(
        fn=respond_with_retry,
        title="Resilient Agent",
    )

    return demo
```

---

## 7. Launch Configuration Patterns

### Pattern: Development vs Production Launch

```python
import os

def launch_demo():
    """Launch demo with environment-specific config."""
    demo = create_demo()

    # Development mode
    if os.getenv("ENV") == "development":
        demo.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            debug=True,
        )

    # Production mode
    else:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True,
            auth=("username", "password"),  # Basic auth
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
        )
```

### Pattern: Custom Theme

```python
import gradio as gr

def create_themed_demo():
    """Create demo with custom theme."""

    # Custom theme
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="cyan",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
    )

    demo = gr.ChatInterface(
        fn=respond,
        title="Themed Agent",
        theme=theme,
    )

    return demo
```

---

## 8. Integration with Agent Factory Pattern

### Complete Example

```python
import gradio as gr
from typing import List, Tuple
from deep_research.core.factory import create_agent_by_name, AgentType

# Metadata for all agent types
AGENT_METADATA = {
    AgentType.REACT_DEEP_RESEARCH: {
        "title": "Deep Research AI",
        "description": "Multi-agent research system",
        "examples": [
            "Research the current state of quantum computing",
            "Analyze AI's impact on healthcare delivery",
        ]
    },
    AgentType.RAG_WEB_SEARCH: {
        "title": "Web Search AI",
        "description": "AI with live web search capabilities",
        "examples": [
            "What are the latest developments in quantum computing?",
            "Who is the current CEO of SpaceX?",
        ]
    },
}

def create_demo(agent_name: str = "react_multi_agent"):
    """Create Gradio demo for specified agent.

    Args:
        agent_name: Name or alias of agent to create

    Returns:
        gr.ChatInterface: Configured Gradio interface
    """
    # Step 1: Create agent using factory
    try:
        chat_interface = create_agent_by_name(agent_name)
    except ValueError as e:
        raise ValueError(f"Failed to create agent '{agent_name}': {str(e)}")

    # Step 2: Get metadata for UI configuration
    try:
        agent_type = AgentType(agent_name.lower())
    except ValueError:
        # Fallback to default metadata
        agent_type = None

    metadata = AGENT_METADATA.get(agent_type, {
        "title": f"AI Assistant - {agent_name}",
        "description": "Your intelligent AI assistant.",
        "examples": ["Hello!", "How can you help me?"]
    })

    # Step 3: Create respond function
    def respond(message: str, history: List[Tuple[str, str]]) -> str:
        """Process user message and return response.

        Args:
            message: Current user message
            history: List of (user_msg, assistant_msg) tuples

        Returns:
            str: Assistant's response
        """
        try:
            return chat_interface.process_message(message, history)
        except Exception as e:
            return f"❌ Error: {str(e)}"

    # Step 4: Create Gradio interface
    demo = gr.ChatInterface(
        fn=respond,
        title=metadata["title"],
        description=metadata["description"],
        examples=metadata["examples"],
        cache_examples=False,
    )

    return demo

def main():
    """Main entry point."""
    import sys

    # Get agent name from command line args
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "react_multi_agent"

    # Create and launch demo
    demo = create_demo(agent_name)
    demo.launch()

if __name__ == "__main__":
    main()
```

### CLI Usage

```bash
# Launch deep research agent
python app.py react_multi_agent

# Launch web search agent
python app.py rag_web_search

# Launch specific mode
python app.py react_deep_research
```

---

## 9. Best Practices

### ✅ Do:

1. **Use Metadata-Driven Configuration**
   - Separate UI config from agent logic
   - Easy to add new agents without UI code changes

2. **Provide Example Prompts**
   - Help users understand agent capabilities
   - Reduce friction for first-time users

3. **Handle Errors Gracefully**
   - Catch exceptions and return user-friendly messages
   - Log errors for debugging

4. **Keep Respond Function Simple**
   - Thin wrapper around agent.process_message()
   - Error handling, no business logic

5. **Use Chat History**
   - Pass history to agent for context
   - Enable multi-turn conversations

### ❌ Don't:

1. **Don't Put Business Logic in UI**
   ```python
   # ❌ Bad
   def respond(message, history):
       # Complex agent logic here
       if "weather" in message:
           return get_weather()
       elif "calculate" in message:
           return calculate()

   # ✅ Good
   def respond(message, history):
       return agent.process_message(message, history)
   ```

2. **Don't Hardcode Configuration**
   ```python
   # ❌ Bad
   demo = gr.ChatInterface(
       fn=respond,
       title="My Agent",  # Hardcoded
       examples=["Hello"]  # Hardcoded
   )

   # ✅ Good
   demo = gr.ChatInterface(
       fn=respond,
       title=metadata["title"],
       examples=metadata["examples"]
   )
   ```

3. **Don't Ignore Chat History**
   ```python
   # ❌ Bad
   def respond(message, history):
       return agent.process_message(message, [])  # Ignores history

   # ✅ Good
   def respond(message, history):
       return agent.process_message(message, history)
   ```

---

## 10. Testing UI Components

### Manual Testing Checklist

- [ ] Examples clickable and work correctly
- [ ] Chat history maintained across turns
- [ ] Error messages display clearly
- [ ] Loading indicators work during processing
- [ ] Mobile responsive layout
- [ ] Clear button resets conversation
- [ ] Dark mode support (if applicable)

### Automated Testing Pattern

```python
import pytest
from gradio.test_data import test_messages

def test_gradio_interface():
    """Test Gradio interface creation."""
    demo = create_demo("react_multi_agent")
    assert demo is not None

def test_respond_function():
    """Test respond function."""
    demo = create_demo("react_multi_agent")

    # Simulate user message
    response = demo.predict(
        message="Hello",
        history=[]
    )

    assert isinstance(response, str)
    assert len(response) > 0

def test_error_handling():
    """Test error handling in UI."""
    demo = create_demo("react_multi_agent")

    # Test with invalid agent (if applicable)
    # Or test with message that causes error
    response = demo.predict(
        message="__trigger_error__",
        history=[]
    )

    assert "Error" in response or "❌" in response
```

---

## Summary: UI Pattern Checklist

When creating a Gradio UI for an agent:

- [ ] Use metadata-driven configuration
- [ ] Integrate with agent factory pattern
- [ ] Provide helpful example prompts
- [ ] Pass chat history to agent
- [ ] Handle errors gracefully with user-friendly messages
- [ ] Keep respond function simple (thin wrapper)
- [ ] Add loading indicators for long operations
- [ ] Test with various input types
- [ ] Consider mobile responsiveness
- [ ] Add authentication for production deployment

---

## References

- **Source Code**: [/code/reference_agents/app.py](../code/reference_agents/app.py)
- **Factory Pattern**: [/docs/FACTORY_PATTERN.md](FACTORY_PATTERN.md)
- **Agent Patterns**: [/docs/AGENT_PATTERNS.md](AGENT_PATTERNS.md)
- **Gradio Documentation**: https://www.gradio.app/docs/chatinterface
- **Gradio Blocks**: https://www.gradio.app/docs/blocks

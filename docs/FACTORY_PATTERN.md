# Agent Factory Pattern

## Overview

This document describes the Factory Pattern implementation used to create agent instances with centralized configuration and type-safe access. The pattern enables runtime selection of agent types through string-based or enum-based resolution.

**Source**: [/code/reference_agents/core/factory.py](../code/reference_agents/core/factory.py)

---

## Pattern Components

### 1. ChatInterface Abstract Base Class

**Purpose**: Define common interface that all agents must implement.

**Location**: [/code/reference_agents/core/chat_interface.py](../code/reference_agents/core/chat_interface.py)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class ChatInterface(ABC):
    """Abstract base class defining the core chat interface functionality."""

    @abstractmethod
    def process_message(self, message: str, chat_history: List[Dict[str, str]]) -> str:
        """Process a message and return a response.

        Args:
            message: The user's input message
            chat_history: Optional list of previous chat messages

        Returns:
            str: The assistant's response
        """
        pass
```

**Key Benefits**:
- Polymorphic agent usage
- Type safety through ABC
- Consistent interface across all agents
- Easy mocking for tests

---

### 2. AgentType Enum

**Purpose**: Type-safe agent type definitions with semantic grouping.

```python
from enum import Enum

class AgentType(Enum):
    """Available agent types and their modes."""

    # LLM Chaining agents
    LLM_CHAINING_QUERY = "llm_chaining_query"
    LLM_CHAINING_TOOLS = "llm_chaining_tools"
    LLM_CHAINING_MEMORY = "llm_chaining_memory"

    # RAG agents
    RAG_WEB_SEARCH = "rag_web_search"
    RAG_DOCUMENT = "rag_document"
    RAG_CORRECTIVE = "rag_corrective"

    # ReAct agents
    REACT_TOOL_USING = "react_tool_using"
    REACT_AGENTIC_RAG = "react_agentic_rag"
    REACT_DEEP_RESEARCH = "react_deep_research"
```

**Benefits**:
- IDE autocomplete support
- Type checking at compile time
- Semantic grouping of related agents
- Documentation through naming

---

### 3. Alias Mapping

**Purpose**: Provide user-friendly names for common agent types.

```python
AGENT_ALIASES = {
    "llm_chaining": AgentType.LLM_CHAINING_MEMORY,  # Default to full version
    "llm_rag_tools": AgentType.RAG_CORRECTIVE,      # Default to most advanced
    "react_multi_agent": AgentType.REACT_DEEP_RESEARCH,  # Default to deep research
}
```

**Benefits**:
- Shorter, memorable names for CLI/UI
- Backward compatibility when adding new variants
- Default to "best" implementation

---

### 4. Factory Function

**Purpose**: Create agent instances based on type with proper initialization.

```python
def create_agent(agent_type: AgentType) -> ChatInterface:
    """Create an agent instance based on type.

    Args:
        agent_type: The type of agent to create

    Returns:
        ChatInterface: The initialized agent instance

    Raises:
        ValueError: If agent_type is unknown
    """
    from deep_research.agents.llm_chaining import LLMChainingAgent
    from deep_research.agents.llm_rag_tools import LLMRAGToolsAgent
    from deep_research.agents.react_multi_agent import ReActMultiAgent

    # Map agent types to implementations
    if agent_type in [AgentType.LLM_CHAINING_QUERY,
                      AgentType.LLM_CHAINING_TOOLS,
                      AgentType.LLM_CHAINING_MEMORY]:
        mode_map = {
            AgentType.LLM_CHAINING_QUERY: "query_understanding",
            AgentType.LLM_CHAINING_TOOLS: "basic_tools",
            AgentType.LLM_CHAINING_MEMORY: "memory"
        }
        agent = LLMChainingAgent(mode=mode_map[agent_type])

    elif agent_type in [AgentType.RAG_WEB_SEARCH,
                        AgentType.RAG_DOCUMENT,
                        AgentType.RAG_CORRECTIVE]:
        mode_map = {
            AgentType.RAG_WEB_SEARCH: "web_search",
            AgentType.RAG_DOCUMENT: "document_rag",
            AgentType.RAG_CORRECTIVE: "corrective_rag"
        }
        agent = LLMRAGToolsAgent(mode=mode_map[agent_type])
        agent.initialize()  # RAG agents need explicit initialization

    elif agent_type in [AgentType.REACT_TOOL_USING,
                        AgentType.REACT_AGENTIC_RAG,
                        AgentType.REACT_DEEP_RESEARCH]:
        mode_map = {
            AgentType.REACT_TOOL_USING: "tool_using",
            AgentType.REACT_AGENTIC_RAG: "agentic_rag",
            AgentType.REACT_DEEP_RESEARCH: "deep_research"
        }
        agent = ReActMultiAgent(mode=mode_map[agent_type])
        agent.initialize()  # ReAct agents need explicit initialization

    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return agent
```

**Key Features**:
- Lazy imports (only import when needed)
- Explicit initialization for complex agents
- Type safety through return type
- Clear error messages

---

### 5. String-Based Factory

**Purpose**: Create agents from user-friendly string names.

```python
def create_agent_by_name(name: str) -> ChatInterface:
    """Create agent by friendly name or specific mode.

    Args:
        name: Agent name or mode string

    Returns:
        ChatInterface: The initialized agent instance

    Raises:
        ValueError: If name is unknown
    """
    # Try alias first
    if name in AGENT_ALIASES:
        return create_agent(AGENT_ALIASES[name])

    # Try as direct enum value
    try:
        agent_type = AgentType(name.lower())
        return create_agent(agent_type)
    except ValueError:
        raise ValueError(
            f"Unknown agent name: {name}. "
            f"Available aliases: {list(AGENT_ALIASES.keys())}. "
            f"Available modes: {[e.value for e in AgentType]}"
        )
```

**Benefits**:
- Supports both aliases and full enum values
- Helpful error messages listing valid options
- Case-insensitive matching

---

## Usage Examples

### Example 1: Create Agent by Enum

```python
from deep_research.core.factory import create_agent, AgentType

# Type-safe creation
agent = create_agent(AgentType.REACT_DEEP_RESEARCH)

# Use the agent
response = agent.process_message(
    "Research the impact of AI on healthcare",
    chat_history=[]
)
```

### Example 2: Create Agent by Name

```python
from deep_research.core.factory import create_agent_by_name

# Using alias
agent = create_agent_by_name("react_multi_agent")

# Using full enum value
agent = create_agent_by_name("react_deep_research")

# Both work!
response = agent.process_message("Hello", [])
```

### Example 3: CLI Integration

```python
import sys
from deep_research.core.factory import create_agent_by_name

def main():
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "react_multi_agent"

    try:
        agent = create_agent_by_name(agent_name)
        print(f"Created {agent_name} agent")

        message = input("Enter your message: ")
        response = agent.process_message(message, [])
        print(response)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Adding New Agent Types

### Step 1: Define Agent Enum Value

```python
class AgentType(Enum):
    # Existing values...

    # Add your new agent type
    MY_NEW_AGENT = "my_new_agent"
```

### Step 2: Create Agent Implementation

```python
# In my_new_agent.py
from deep_research.core.chat_interface import ChatInterface

class MyNewAgent(ChatInterface):
    def __init__(self, config: dict = None):
        self.config = config or {}

    def initialize(self):
        # Setup LLMs, tools, etc.
        pass

    def process_message(self, message: str, chat_history) -> str:
        # Your implementation
        return "response"
```

### Step 3: Register in Factory

```python
def create_agent(agent_type: AgentType) -> ChatInterface:
    # Existing code...

    elif agent_type == AgentType.MY_NEW_AGENT:
        from deep_research.agents.my_new_agent import MyNewAgent
        agent = MyNewAgent()
        agent.initialize()

    # Rest of function...
```

### Step 4: (Optional) Add Alias

```python
AGENT_ALIASES = {
    # Existing aliases...
    "my_agent": AgentType.MY_NEW_AGENT,
}
```

---

## Design Patterns Used

### 1. Factory Method Pattern

**Classic GoF Pattern**: Define interface for creating objects, but let subclasses decide which class to instantiate.

**Implementation**:
- `create_agent()` = factory method
- `AgentType` = product identifier
- Concrete agents = products

### 2. Abstract Factory Pattern

**Variant**: Family of related objects (different agent modes) created through consistent interface.

### 3. Strategy Pattern

**Integration**: Different agent types = different strategies for processing messages.

---

## Best Practices

### ✅ Do:

1. **Use Enums for Type Safety**
   ```python
   agent = create_agent(AgentType.REACT_DEEP_RESEARCH)  # ✅ Type-safe
   ```

2. **Handle Initialization Explicitly**
   ```python
   agent = MyComplexAgent()
   agent.initialize()  # Explicit, clear when initialization happens
   ```

3. **Provide Clear Error Messages**
   ```python
   raise ValueError(
       f"Unknown agent: {name}. "
       f"Available: {list(AGENT_ALIASES.keys())}"
   )
   ```

4. **Use Lazy Imports**
   ```python
   # Import only when needed
   from deep_research.agents.my_agent import MyAgent
   ```

### ❌ Don't:

1. **Don't Use Magic Strings**
   ```python
   agent = create_agent("deep_research")  # ❌ No autocomplete, typo-prone
   ```

2. **Don't Initialize in Constructor**
   ```python
   def __init__(self):
       self.llm = ChatOpenAI()  # ❌ Slow, fails if API key missing
   ```

3. **Don't Silently Fail**
   ```python
   try:
       agent = create_agent(type)
   except:
       agent = DefaultAgent()  # ❌ Hides errors
   ```

---

## Testing Pattern

### Unit Test Example

```python
import pytest
from deep_research.core.factory import create_agent, AgentType

def test_create_agent_success():
    """Test successful agent creation."""
    agent = create_agent(AgentType.REACT_TOOL_USING)
    assert agent is not None
    assert hasattr(agent, 'process_message')

def test_create_agent_unknown_type():
    """Test error handling for unknown agent type."""
    with pytest.raises(ValueError, match="Unknown agent type"):
        create_agent("invalid_type")

def test_agent_interface_compliance():
    """Test that created agent implements ChatInterface."""
    from deep_research.core.chat_interface import ChatInterface

    agent = create_agent(AgentType.REACT_TOOL_USING)
    assert isinstance(agent, ChatInterface)

@pytest.mark.parametrize("agent_type", list(AgentType))
def test_all_agent_types_work(agent_type):
    """Test that all defined agent types can be created."""
    agent = create_agent(agent_type)
    assert agent is not None
```

---

## Integration with Gradio UI

From [/code/reference_agents/app.py](../code/reference_agents/app.py):

```python
def create_demo(agent_name: str = "LLM_Chaining"):
    """Create Gradio demo for specified agent."""
    # Factory creates the agent
    chat_interface = create_agent_by_name(agent_name)

    # Get metadata for UI
    if agent_name in AGENT_ALIASES:
        agent_type = AGENT_ALIASES[agent_name]
    else:
        agent_type = AgentType(agent_name.lower())

    metadata = AGENT_METADATA.get(agent_type, {
        "title": f"Deep Research AI - {agent_name}",
        "description": "Your intelligent AI assistant.",
        "examples": ["Hello!"]
    })

    # Create respond function
    def respond(message: str, history):
        return chat_interface.process_message(message, history)

    # Create Gradio interface
    demo = gr.ChatInterface(
        fn=respond,
        title=metadata["title"],
        description=metadata["description"],
        examples=metadata["examples"]
    )

    return demo
```

---

## Comparison: Factory vs Direct Instantiation

### Without Factory

```python
# ❌ Repetitive, error-prone
if mode == "deep_research":
    from deep_research.agents.react_multi_agent import ReActMultiAgent
    agent = ReActMultiAgent(mode="deep_research")
    agent.initialize()
elif mode == "tool_using":
    from deep_research.agents.react_multi_agent import ReActMultiAgent
    agent = ReActMultiAgent(mode="tool_using")
    agent.initialize()
# ... many more cases
```

### With Factory

```python
# ✅ Clean, type-safe, extensible
from deep_research.core.factory import create_agent_by_name

agent = create_agent_by_name(mode)
```

---

## References

- **Source Code**: [/code/reference_agents/core/factory.py](../code/reference_agents/core/factory.py)
- **ChatInterface**: [/code/reference_agents/core/chat_interface.py](../code/reference_agents/core/chat_interface.py)
- **Usage Example**: [/code/reference_agents/app.py](../code/reference_agents/app.py)
- **Factory Pattern (GoF)**: https://refactoring.guru/design-patterns/factory-method

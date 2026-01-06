# Reference Agent Implementation

## Purpose

This directory contains **reference implementation code** that demonstrates proven patterns for building LangChain/LangGraph multi-agent systems.

**⚠️ IMPORTANT**: This code is **NOT used in production** - it exists solely as working examples of design patterns and best practices.

---

## Why This Code Exists

During development of the Braze Code Generator, this reference implementation served as:

1. **Pattern Documentation**: Real, working examples of agent design patterns
2. **Architecture Reference**: Proven structures for multi-agent systems
3. **Testing Ground**: Battle-tested code that informed the production implementation
4. **Learning Resource**: Hands-on examples for understanding LangChain/LangGraph

---

## Directory Structure

```
reference_agents/
├── README.md                    # This file
├── app.py                       # Gradio UI reference (134 lines)
├── test_agents.py              # Test suite for all agent modes
├── test_gradio.py              # Gradio UI tests
├── verify_structure.py         # Syntax verification utility
├── core/                       # Abstract interfaces and factory
│   ├── chat_interface.py       # Abstract base class (22 lines)
│   └── factory.py             # Agent factory pattern (120 lines)
├── agents/                     # Agent implementations
│   └── react_multi_agent.py   # Main reference implementation (790 lines)
├── tools/                      # Tool wrappers
│   └── calculator.py          # Safe expression evaluation
└── examples/
    └── final_report.md        # Example research output
```

---

## Key Patterns Demonstrated

### 1. ReAct Multi-Agent Delegation Pattern
**File**: [agents/react_multi_agent.py:745-791](agents/react_multi_agent.py)

Single orchestrator class delegates to specialized sub-agents based on mode:
- `ToolUsingAgent` - Simple ReAct with calculator, datetime, weather tools
- `AgenticRAGAgent` - Iterative RAG with evaluation loop
- `DeepResearchAgent` - Multi-agent research orchestration

### 2. Factory Pattern with Type Safety
**File**: [core/factory.py](core/factory.py)

Centralized agent creation with:
- `AgentType` enum for type-safe agent selection
- Alias mapping for user-friendly names
- Lazy imports and explicit initialization
- Clear error messages

### 3. StateGraph Workflow Orchestration
**File**: [agents/react_multi_agent.py:494-682](agents/react_multi_agent.py)

LangGraph StateGraph pattern for multi-step workflows:
- TypedDict state definitions
- Annotated message sequences
- Conditional routing
- Pydantic models for structured data

### 4. Tool Integration
**File**: [tools/calculator.py](tools/calculator.py)

LangChain `@tool` decorator patterns:
- Type annotations with `Annotated[type, "description"]`
- Safe expression evaluation with regex validation
- Error handling (return strings, not exceptions)
- Clear docstrings with examples

### 5. Gradio UI Patterns
**File**: [app.py](app.py)

Metadata-driven UI with:
- Dynamic configuration from agent metadata
- Chat history management
- Example-based onboarding
- Multi-agent support without code duplication

### 6. Opik Tracing Integration
**File**: [agents/react_multi_agent.py:86-90](agents/react_multi_agent.py)

Observability for agent workflows:
- Per-graph tracer initialization
- Callback integration
- Project-based organization

---

## Pattern Documentation

All patterns from this codebase have been extracted and documented in `/docs/`:

- [**AGENT_PATTERNS.md**](../../docs/AGENT_PATTERNS.md) - ReAct delegation, StateGraph workflows, conditional routing
- [**FACTORY_PATTERN.md**](../../docs/FACTORY_PATTERN.md) - Factory pattern, ChatInterface, agent registration
- [**TOOL_INTEGRATION.md**](../../docs/TOOL_INTEGRATION.md) - LangChain tools, MCP integration, safe evaluation
- [**UI_PATTERNS.md**](../../docs/UI_PATTERNS.md) - Gradio chat interfaces, metadata-driven config
- [**WORKFLOW_ORCHESTRATION.md**](../../docs/WORKFLOW_ORCHESTRATION.md) - StateGraph, routing, error handling

---

## Agent Modes

This reference implementation supports 9 different agent modes:

### LLM Chaining Agents (3 modes)
1. **query_understanding** - Classifies queries and formats responses
2. **basic_tools** - Adds calculator and datetime tools
3. **memory** - Adds conversational memory (full LLM chaining example)

### RAG Agents (3 modes)
4. **web_search** - Live web search with Tavily
5. **document_rag** - Vector store retrieval (OPM docs 2019-2022)
6. **corrective_rag** - Combines document retrieval + web search fallback

### ReAct Agents (3 modes)
7. **tool_using** - Simple ReAct with calculator, datetime, weather
8. **agentic_rag** - Iterative RAG with evaluation and query rewriting
9. **deep_research** - Multi-agent orchestration for comprehensive research

---

## Running the Reference Implementation

**Note**: This is reference code. For production use, see `/code/braze_code_gen/`.

### Setup

```bash
cd /Users/Jacob.Jaffe/code-gen-agent/code
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Launch Gradio UI

```bash
# Launch deep research agent
python run.py react_multi_agent

# Launch web search agent
python run.py rag_web_search

# Launch specific mode
python run.py react_deep_research
```

### Run Tests

```bash
# Test all agent modes
pytest test_agents.py -v

# Test Gradio UI
pytest test_gradio.py -v

# Verify code structure
python verify_structure.py
```

---

## Usage During Development

When building the Braze Code Generator:

### ✅ DO:
- Reference this code for proven patterns
- Copy patterns documented in `/docs/`
- Adapt StateGraph workflows for your needs
- Use factory pattern as template
- Test tool integration approaches here first

### ❌ DON'T:
- Import this code into production (`/code/braze_code_gen/`)
- Modify this code (it's a reference, not a library)
- Depend on this code for production functionality
- Copy-paste without understanding the pattern

---

## Code Quality

This reference implementation:
- ✅ Follows LangChain/LangGraph best practices
- ✅ Includes comprehensive docstrings
- ✅ Has working examples for all patterns
- ✅ Passes all tests
- ✅ Includes Opik tracing for observability
- ✅ Uses type hints throughout
- ✅ Handles errors gracefully

---

## Technical Stack

- **LangChain** 0.3.x - LLM application framework
- **LangGraph** 0.2.x - Workflow orchestration
- **OpenAI** gpt-4o-mini - Primary LLM
- **Gradio** 5.x - Web UI framework
- **Tavily** - Web search tool
- **Opik** - Observability and tracing
- **Pydantic** 2.x - Data validation
- **Python** 3.11+

---

## Future

This directory may be **archived or removed** after:
1. Braze Code Generator is complete and validated
2. All patterns are proven in production
3. Documentation in `/docs/` is comprehensive
4. No longer needed as reference during development

For now, it remains as a valuable resource for pattern reference.

---

## References

- **Production Code**: `/code/braze_code_gen/` (when implemented)
- **Pattern Documentation**: `/docs/`
- **LangChain**: https://python.langchain.com/
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Gradio**: https://www.gradio.app/
- **Opik**: https://www.comet.com/docs/opik/

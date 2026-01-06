# Agent Design Patterns

## Overview

This document extracts and documents proven design patterns from the reference implementation in [/code/reference_agents/](../code/reference_agents/). These patterns are battle-tested approaches for building multi-agent systems with LangChain and LangGraph.

---

## 1. ReAct Multi-Agent Delegation Pattern

### Pattern Description

**Intent**: Single orchestrator class delegates to specialized sub-agents based on task type or mode, avoiding code duplication while supporting multiple agent implementations.

**Structure**:
- Main orchestrator implements ChatInterface
- Mode parameter determines which delegate to instantiate
- Each delegate is a complete, independent agent implementation
- All delegates share the same interface (ChatInterface)

### Implementation Example

From [react_multi_agent.py:745-791](../code/reference_agents/agents/react_multi_agent.py):

```python
class ReActMultiAgent(ChatInterface):
    """ReAct Multi-Agent System with delegation pattern.

    Supports three modes:
    - tool_using: Simple ReAct agent with calculator, datetime, and weather tools
    - agentic_rag: Custom iterative RAG with evaluation loop
    - deep_research: Multi-agent orchestration for comprehensive research
    """

    def __init__(self, mode: Literal["tool_using", "agentic_rag", "deep_research"] = "deep_research"):
        self.mode = mode
        self.delegate = None

    def initialize(self) -> None:
        """Initialize the appropriate delegate based on mode."""
        if self.mode == "tool_using":
            self.delegate = ToolUsingAgent()
        elif self.mode == "agentic_rag":
            self.delegate = AgenticRAGAgent()
        elif self.mode == "deep_research":
            self.delegate = DeepResearchAgent()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

        # Initialize the delegate
        self.delegate.initialize()

    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process a message by delegating to the internal agent."""
        if self.delegate is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return self.delegate.process_message(message, chat_history)
```

### Key Components

1. **Main Orchestrator** (`ReActMultiAgent`)
   - Implements ChatInterface
   - Manages mode selection
   - Delegates to specialized agents

2. **Specialized Agents** (`ToolUsingAgent`, `AgenticRAGAgent`, `DeepResearchAgent`)
   - Each implements ChatInterface independently
   - Complete, self-contained implementations
   - Shared LLM and tools where appropriate

3. **Factory-Based Instantiation**
   - Agents created based on mode string
   - Explicit `initialize()` call pattern
   - Lazy initialization support

### When to Use This Pattern

✅ **Use when:**
- Multiple agent types with shared infrastructure
- Need runtime switching between agent modes
- Want to avoid massive if/else blocks in main code
- Each mode has significantly different logic

❌ **Don't use when:**
- Only one agent type needed
- Agent logic is simple enough for direct implementation
- Delegation overhead outweighs benefits

---

## 2. StateGraph Workflow Pattern

### Pattern Description

**Intent**: Orchestrate multi-step agent workflows with conditional routing and state management using LangGraph's StateGraph.

**Structure**:
- TypedDict defines workflow state
- Nodes are Python functions that update state
- Edges define workflow transitions
- Conditional edges enable dynamic routing

### Implementation Example

From [react_multi_agent.py:494-682](../code/reference_agents/agents/react_multi_agent.py):

```python
class ResearchState(TypedDict):
    """State tracking for the deep research workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    research_plan: Optional[ResearchPlan]
    report: Optional[Report]
    next_step: str

def _create_workflow(self) -> Any:
    """Create the multi-agent deep research workflow."""
    workflow = StateGraph(ResearchState)

    # Define node functions
    def research_manager_node(state: ResearchState):
        """Create the research plan."""
        topic = state["messages"][0].content
        research_plan = self.research_manager.invoke({"topic": topic})

        # Initialize empty report structure
        report = Report(
            detailed_analysis=[
                ReportSection(title=q.title, content=None, sources=[])
                for q in research_plan.questions
            ]
        )

        return {
            "research_plan": research_plan,
            "report": report,
        }

    def evaluator_node(state: ResearchState):
        """Evaluate progress and determine next steps."""
        research_plan = state["research_plan"]
        all_completed = research_plan.current_question_index >= len(research_plan.questions)

        if all_completed:
            return {"next_step": "finalize"}
        else:
            return {"next_step": "research"}

    # Add nodes to the graph
    workflow.add_node("research_manager", research_manager_node)
    workflow.add_node("specialized_research", specialized_research_node)
    workflow.add_node("evaluate", evaluator_node)
    workflow.add_node("finalizer", finalizer_node)

    # Add edges
    workflow.add_edge(START, "research_manager")
    workflow.add_edge("research_manager", "specialized_research")
    workflow.add_edge("specialized_research", "evaluate")

    # Conditional routing from evaluator
    workflow.add_conditional_edges(
        "evaluate",
        lambda x: x["next_step"],
        {
            "research": "specialized_research",
            "finalize": "finalizer"
        }
    )
    workflow.add_edge("finalizer", END)

    return workflow.compile()
```

### Workflow Diagram

```
START
  ↓
research_manager (create plan)
  ↓
specialized_research (research one topic)
  ↓
evaluate (check if done)
  ├─ all_done=False → specialized_research (loop back)
  └─ all_done=True → finalizer
      ↓
     END
```

### State Management Best Practices

1. **Use TypedDict for State**
   ```python
   class MyState(TypedDict):
       messages: Annotated[Sequence[AnyMessage], add_messages]
       counter: int
       data: Optional[SomeModel]
   ```

2. **Annotate Message Lists**
   ```python
   from langgraph.graph.message import add_messages
   messages: Annotated[Sequence[AnyMessage], add_messages]
   ```
   This ensures messages are appended, not replaced.

3. **Return Partial State Updates**
   ```python
   def my_node(state: MyState):
       # Only return fields you want to update
       return {"counter": state["counter"] + 1}
   ```

4. **Use Pydantic for Complex Data**
   ```python
   class ResearchPlan(BaseModel):
       topic: str
       questions: List[ResearchQuestion]
       current_question_index: int = 0
   ```

---

## 3. Tool Integration Pattern

### Pattern Description

**Intent**: Wrap functions as LangChain tools that can be called by agents with proper error handling and type annotations.

### Implementation Example

From [react_multi_agent.py:95-136](../code/reference_agents/agents/react_multi_agent.py):

```python
def _create_tools(self) -> List[Any]:
    """Create and return the list of tools for the agent."""

    @tool
    def calculator(expression: Annotated[str, "The mathematical expression to evaluate"]) -> str:
        """Evaluate a mathematical expression using basic arithmetic operations (+, -, *, /, %, //).
        Examples: '5 + 3', '10 * (2 + 3)', '15 / 3'
        """
        result = Calculator.evaluate_expression(expression)
        if isinstance(result, str) and result.startswith("Error"):
            raise ValueError(result)
        return str(result)

    @tool
    def execute_datetime_code(code: Annotated[str, "Python code to execute for datetime operations"]) -> str:
        """Execute Python code for datetime operations. The code should use datetime or time modules.
        Examples:
        - 'print(datetime.datetime.now().strftime("%Y-%m-%d"))'
        - 'print(datetime.datetime.now().year)'
        """
        output_buffer = io.StringIO()
        code = f"import datetime\nimport time\n{code}"
        try:
            with contextlib.redirect_stdout(output_buffer):
                exec(code)
            return output_buffer.getvalue().strip()
        except Exception as e:
            raise ValueError(f"Error executing datetime code: {str(e)}")

    @tool
    def get_weather(location: Annotated[str, "The location to get weather for (city, country)"]) -> str:
        """Get the current weather for a given location using Tavily search.
        Examples: 'New York, USA', 'London, UK', 'Tokyo, Japan'
        """
        search = TavilySearch(max_results=3)
        query = f"what is the current weather temperature in {location} right now"
        results = search.invoke({"query": query})

        search_results = results.get('results', [])
        if not search_results:
            return f"Could not find weather information for {location}"

        return search_results[0].get("content", f"Could not find weather information for {location}")

    return [calculator, execute_datetime_code, get_weather]
```

### Tool Design Best Practices

1. **Use @tool Decorator**
   ```python
   from langchain_core.tools import tool

   @tool
   def my_function(param: Annotated[str, "Description of param"]) -> str:
       """Function description for LLM."""
       pass
   ```

2. **Provide Type Annotations**
   - Use `Annotated[type, "description"]` for parameters
   - LLM uses these descriptions to understand tool usage

3. **Write Clear Docstrings**
   - First line becomes tool description
   - Include examples of valid inputs
   - LLM uses docstring to decide when to call

4. **Handle Errors Gracefully**
   - Raise `ValueError` for invalid inputs
   - Return error messages as strings when appropriate
   - Don't let exceptions crash the agent

5. **Keep Tools Focused**
   - One tool = one clear purpose
   - Don't combine unrelated functionality
   - Make tools composable

---

## 4. Opik Tracing Integration Pattern

### Pattern Description

**Intent**: Add observability to agent workflows using Opik tracing for debugging and monitoring.

### Implementation Example

From [react_multi_agent.py:86-90, 140-147](../code/reference_agents/agents/react_multi_agent.py):

```python
from opik.integrations.langchain import OpikTracer

class ToolUsingAgent(ChatInterface):
    def initialize(self) -> None:
        # Create the ReAct agent graph
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )

        # Initialize Opik tracer
        self.tracer = OpikTracer(
            graph=self.graph.get_graph(xray=True),
            project_name="react-tool-using"
        )

    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        # Run the graph with tracer in config
        result = self.graph.invoke(
            {"messages": [("user", message)]},
            config={"callbacks": [self.tracer]}
        )

        return result["messages"][-1].content
```

### Tracing Best Practices

1. **Initialize Per Graph**
   - One tracer per workflow graph
   - Pass graph with `xray=True` for detailed traces

2. **Use Project Names**
   - Organize traces by project
   - Makes debugging easier with multiple agents

3. **Pass in Config**
   - Add tracer to `config={"callbacks": [self.tracer]}`
   - Works with any LangChain component

4. **Recursion Limits**
   ```python
   result = self.graph.invoke(
       state,
       config={
           "callbacks": [self.tracer],
           "recursion_limit": 100  # Prevent infinite loops
       }
   )
   ```

---

## 5. Conditional Routing Pattern

### Pattern Description

**Intent**: Route workflow execution based on state conditions using LangGraph conditional edges.

### Implementation Example

From [react_multi_agent.py:349-356](../code/reference_agents/agents/react_multi_agent.py):

```python
def _route_after_eval(self, state: RAGState) -> str:
    """Decide next step after evaluation."""
    if state.get("is_sufficient", False):
        return "synthesize"
    if state.get("iterations", 0) < 3:
        return "rewrite"
    return "synthesize"

# In workflow building:
builder.add_conditional_edges(
    "evaluate",
    self._route_after_eval,
    {
        "rewrite": "rewrite",
        "synthesize": "synthesize",
    },
)
```

### Routing Strategies

1. **Simple Boolean Routing**
   ```python
   def route_fn(state):
       return "success" if state["passed"] else "failure"
   ```

2. **Multi-Way Routing**
   ```python
   def route_fn(state):
       if state["score"] > 0.8:
           return "excellent"
       elif state["score"] > 0.5:
           return "good"
       else:
           return "retry"
   ```

3. **Iteration-Limited Routing**
   ```python
   def route_fn(state):
       if state["is_complete"]:
           return "finalize"
       if state["iterations"] >= MAX_ITERATIONS:
           return "finalize"  # Give up after max tries
       return "retry"
   ```

---

## 6. ReAct Agent Creation Pattern

### Pattern Description

**Intent**: Use LangGraph's `create_react_agent` to build agents that reason and act with tools.

### Implementation Example

From [react_multi_agent.py:80-84, 219-223](../code/reference_agents/agents/react_multi_agent.py):

```python
# Simple ReAct Agent
self.graph = create_react_agent(
    model=self.llm,
    tools=self.tools,
)

# ReAct Agent with System Prompt
self.agent = create_react_agent(
    self.llm,
    tools=self.tools,
    prompt=AGENT_SYSTEM_PROMPT,  # Custom system message
)
```

### ReAct Pattern

**Reasoning + Acting**: Agent alternates between:
1. **Reasoning**: Think about what to do
2. **Acting**: Call a tool
3. **Observing**: Process tool result
4. **Repeat**: Until task is complete

### Benefits of `create_react_agent`

- Built-in reasoning loop
- Automatic tool calling
- Error handling
- Message management
- Stop condition detection

---

## When to Use Each Pattern

| Pattern | Best For | Avoid For |
|---------|----------|-----------|
| **Delegation** | Multiple agent modes, runtime switching | Single agent, simple logic |
| **StateGraph** | Multi-step workflows, conditional logic | Linear chains, simple Q&A |
| **Tool Integration** | External capabilities (search, calc, API) | Pure LLM tasks |
| **Opik Tracing** | Debugging, monitoring, production | Throw-away scripts |
| **Conditional Routing** | Decision points, retry logic | Always-linear flows |
| **ReAct Agent** | Tool-using agents, research tasks | Simple completion tasks |

---

## Complete Example: Agentic RAG Pattern

Combining multiple patterns into a complete agent:

```python
class AgenticRAGAgent(ChatInterface):
    """Custom iterative RAG agent with evaluation loop."""

    def initialize(self):
        # 1. Initialize components
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.tools = self._create_tools()  # Tool Integration Pattern

        # 2. Create ReAct agent
        self.agent = create_react_agent(  # ReAct Pattern
            self.llm,
            tools=self.tools,
            prompt=AGENT_SYSTEM_PROMPT,
        )

        # 3. Build StateGraph workflow
        builder = StateGraph(RAGState)  # StateGraph Pattern
        builder.add_node("agent", self._agent_node)
        builder.add_node("evaluate", self._evaluator_node)
        builder.add_node("rewrite", self._rewriter_node)
        builder.add_node("synthesize", self._synth_node)

        builder.add_edge(START, "agent")
        builder.add_edge("agent", "evaluate")
        builder.add_conditional_edges(  # Conditional Routing Pattern
            "evaluate",
            self._route_after_eval,
            {"rewrite": "rewrite", "synthesize": "synthesize"},
        )
        builder.add_edge("rewrite", "agent")
        builder.add_edge("synthesize", END)

        self.graph = builder.compile()

        # 4. Initialize tracing
        self.tracer = OpikTracer(  # Opik Tracing Pattern
            graph=self.graph.get_graph(xray=True),
            project_name="react-agentic-rag"
        )

    def process_message(self, message: str, chat_history=None) -> str:
        initial_state: RAGState = {
            "messages": [HumanMessage(content=message)],
            "retrieved_docs": [],
            "is_sufficient": None,
            "feedback": "",
            "iterations": 0,
        }

        result = self.graph.invoke(
            initial_state,
            config={"callbacks": [self.tracer]}
        )
        return result["messages"][-1].content
```

---

## References

- **Source Code**: [/code/reference_agents/agents/react_multi_agent.py](../code/reference_agents/agents/react_multi_agent.py)
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangChain Tools**: https://python.langchain.com/docs/modules/tools/
- **Opik Tracing**: https://www.comet.com/docs/opik/

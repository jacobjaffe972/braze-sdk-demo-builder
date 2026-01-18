# Workflow Orchestration with LangGraph

## Overview

This document describes patterns for orchestrating complex multi-step agent workflows using LangGraph's StateGraph, extracted from [/code/reference_agents/agents/react_multi_agent.py](../code/reference_agents/agents/react_multi_agent.py).

**Key Concepts**:
- StateGraph for workflow definition
- TypedDict for state management
- Nodes as Python functions
- Conditional routing
- Message accumulation with Annotated sequences

---

## 1. StateGraph Basics

### Pattern Description

**Intent**: Define multi-step workflows with state management and conditional routing using LangGraph's StateGraph.

### Core Components
1
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, add_messages

# 1. Define State Schema
class MyState(TypedDict):
    """State for workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    counter: int
    data: Optional[dict]

# 2. Create StateGraph
workflow = StateGraph(MyState)

# 3. Define Node Functions
def node_function(state: MyState) -> dict:
    """Process state and return updates."""
    return {"counter": state["counter"] + 1}

# 4. Add Nodes
workflow.add_node("my_node", node_function)

# 5. Add Edges
workflow.add_edge(START, "my_node")
workflow.add_edge("my_node", END)

# 6. Compile Workflow
app = workflow.compile()

# 7. Invoke Workflow
result = app.invoke({"messages": [], "counter": 0, "data": None})
```

---

## 2. State Schema Design Pattern

### Using TypedDict with Annotated

**Source**: [/code/reference_agents/agents/react_multi_agent.py:470-493](../code/reference_agents/agents/react_multi_agent.py)

```python
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

# Pydantic models for structured data
class ResearchQuestion(BaseModel):
    title: str
    description: str
    completed: bool = False

class ResearchPlan(BaseModel):
    topic: str
    questions: list[ResearchQuestion]
    current_question_index: int = 0

class ReportSection(BaseModel):
    title: str
    content: Optional[str]
    sources: list[str]

class Report(BaseModel):
    executive_summary: Optional[str] = None
    key_findings: Optional[str] = None
    detailed_analysis: list[ReportSection]
    limitations: Optional[str] = None

# State schema
class ResearchState(TypedDict):
    """State tracking for the deep research workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    research_plan: Optional[ResearchPlan]
    report: Optional[Report]
    next_step: str
```

### Key Features

1. **TypedDict**: Type-safe state definition
2. **Annotated[Sequence[BaseMessage], add_messages]**: Messages are appended, not replaced
3. **Optional Fields**: Allow gradual state building
4. **Pydantic Models**: Structured data with validation
5. **next_step**: Control field for routing

### Message Accumulation

```python
from langgraph.graph.message import add_messages

# Without add_messages:
messages: List[BaseMessage]  # New messages replace old ones

# With add_messages:
messages: Annotated[Sequence[BaseMessage], add_messages]  # New messages are appended
```

---

## 3. Node Function Pattern

### Pattern Description

**Intent**: Define workflow steps as Python functions that read state and return partial updates.

### Basic Node

```python
def my_node(state: MyState) -> dict:
    """Process state and return updates.

    Args:
        state: Current workflow state

    Returns:
        dict: Partial state updates (only changed fields)
    """
    # Read from state
    counter = state["counter"]
    messages = state["messages"]

    # Process
    result = process_data(counter, messages)

    # Return partial update
    return {"counter": counter + 1}
```

### Node with Agent Invocation

**Source**: [/code/reference_agents/agents/react_multi_agent.py:502-524](../code/reference_agents/agents/react_multi_agent.py)

```python
def research_manager_node(state: ResearchState):
    """Create the research plan."""
    print("\n=== RESEARCH MANAGER NODE ===")

    # Get the topic from the user message
    topic = state["messages"][0].content
    print(f"Planning research for topic: {topic}")

    # Generate research plan using structured output
    research_plan = self.research_manager.invoke({"topic": topic})
    print(f"Created research plan with {len(research_plan.questions)} questions")

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
```

### Node with SubGraph/SubAgent

**Source**: [/code/reference_agents/agents/react_multi_agent.py:527-597](../code/reference_agents/agents/react_multi_agent.py)

```python
def specialized_research_node(state: ResearchState):
    """Conduct research on the current question."""
    print("\n=== SPECIALIZED RESEARCH NODE ===")

    research_plan = state["research_plan"]
    assert research_plan is not None, "Research plan is None"
    current_index = research_plan.current_question_index

    if current_index >= len(research_plan.questions):
        print("All research questions completed")
        return {}

    current_question = research_plan.questions[current_index]
    print(f"Researching question {current_index + 1}/{len(research_plan.questions)}: "
          f"{current_question.title}")

    # Create input for the specialized agent
    research_input = {
        "messages": [
            ("user", f"""Research the following topic thoroughly:

            Topic: {current_question.title}

            Description: {current_question.description}

            Provide a detailed analysis with proper citations to sources.
            """)
        ]
    }

    # Invoke the specialized agent with recursion limit
    result = self.specialized_research_agent.invoke(
        research_input,
        config={"recursion_limit": 50}
    )

    # Extract content from result
    last_message = result["messages"][-1]
    if isinstance(last_message, tuple):
        content = last_message[1]  # Tuple format: (role, content)
    else:
        content = last_message.content  # AIMessage object

    # Parse out sources from the content
    sources = []
    for line in content.split("\n"):
        if "http" in line and "://" in line:
            sources.append(line.strip())

    # Update the research plan
    research_plan.questions[current_index].completed = True

    # Update the report (create new Pydantic instance)
    report = state["report"]
    assert report is not None, "Report is None"
    section = report.detailed_analysis[current_index]
    report.detailed_analysis[current_index] = ReportSection(
        title=section.title,
        content=content,
        sources=sources
    )

    # Move to the next question
    research_plan.current_question_index += 1

    return {
        "research_plan": research_plan,
        "report": report,
    }
```

### Node Best Practices

1. **Read from state**: Extract needed fields at start
2. **Process**: Execute business logic
3. **Return partial updates**: Only return changed fields
4. **Add logging**: Print statements help debugging
5. **Assert invariants**: Check preconditions with assert
6. **Handle empty cases**: Return {} when nothing to update

---

## 4. Conditional Routing Pattern

### Pattern Description

**Intent**: Route workflow execution based on state conditions using conditional edges.

### Simple Router

**Source**: [/code/reference_agents/agents/react_multi_agent.py:600-617](../code/reference_agents/agents/react_multi_agent.py)

```python
def evaluator_node(state: ResearchState):
    """Evaluate the research progress and determine next steps."""
    print("\n=== EVALUATOR NODE ===")

    research_plan = state["research_plan"]
    assert research_plan is not None, "Research plan is None"

    # Check if we've completed all questions
    all_completed = research_plan.current_question_index >= len(research_plan.questions)

    if all_completed:
        print("All research questions have been addressed. Moving to finalizer.")
        return {"next_step": "finalize"}
    else:
        # We have more sections to research
        next_section = research_plan.questions[research_plan.current_question_index].title
        print(f"More research needed. Moving to next section: {next_section}")
        return {"next_step": "research"}
```

### Adding Conditional Edge

**Source**: [/code/reference_agents/agents/react_multi_agent.py:670-678](../code/reference_agents/agents/react_multi_agent.py)

```python
# Add conditional edges from evaluator node
workflow.add_conditional_edges(
    "evaluate",                    # Source node
    lambda x: x["next_step"],      # Router function
    {
        "research": "specialized_research",  # If next_step == "research"
        "finalize": "finalizer"              # If next_step == "finalize"
    }
)
```

### Complex Router with Multiple Conditions

```python
def complex_router(state: MyState) -> str:
    """Route based on multiple conditions."""

    # Condition 1: Check completion
    if state.get("is_complete"):
        return "finalize"

    # Condition 2: Check iteration limit
    if state.get("iterations", 0) >= 3:
        return "give_up"

    # Condition 3: Check quality score
    if state.get("quality_score", 0) > 0.8:
        return "polish"

    # Default: retry
    return "retry"

# Add to workflow
workflow.add_conditional_edges(
    "evaluator",
    complex_router,
    {
        "finalize": "finalizer",
        "give_up": "error_handler",
        "polish": "polisher",
        "retry": "generator",
    }
)
```

---

## 5. Complete Workflow Example

### Deep Research Agent Workflow

**Source**: [/code/reference_agents/agents/react_multi_agent.py:494-682](../code/reference_agents/agents/react_multi_agent.py)

#### Workflow Diagram

```
START
  ↓
research_manager (create plan with N questions)
  ↓
specialized_research (research question 1)
  ↓
evaluate (check progress)
  ├─ more questions → specialized_research (loop back)
  └─ all done → finalizer
      ↓
     END
```

#### Complete Implementation

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

class ResearchState(TypedDict):
    """State tracking for the deep research workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    research_plan: Optional[ResearchPlan]
    report: Optional[Report]
    next_step: str

def _create_workflow(self) -> Any:
    """Create the multi-agent deep research workflow."""
    # Create a state graph
    workflow = StateGraph(ResearchState)

    # Define the nodes

    # Research Manager Node
    def research_manager_node(state: ResearchState):
        """Create the research plan."""
        print("\n=== RESEARCH MANAGER NODE ===")
        topic = state["messages"][0].content
        print(f"Planning research for topic: {topic}")

        # Generate research plan
        research_plan = self.research_manager.invoke({"topic": topic})
        print(f"Created research plan with {len(research_plan.questions)} questions")

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

    # Specialized Research Node
    def specialized_research_node(state: ResearchState):
        """Conduct research on the current question."""
        print("\n=== SPECIALIZED RESEARCH NODE ===")

        research_plan = state["research_plan"]
        current_index = research_plan.current_question_index

        if current_index >= len(research_plan.questions):
            return {}

        current_question = research_plan.questions[current_index]
        print(f"Researching question {current_index + 1}/{len(research_plan.questions)}")

        # Invoke the specialized agent
        result = self.specialized_research_agent.invoke(
            {"messages": [("user", f"Research: {current_question.title}")]},
            config={"recursion_limit": 50}
        )

        # Extract content and update state
        content = result["messages"][-1].content

        # Update report
        report = state["report"]
        report.detailed_analysis[current_index].content = content

        # Move to next question
        research_plan.current_question_index += 1

        return {
            "research_plan": research_plan,
            "report": report,
        }

    # Research Evaluator Node
    def evaluator_node(state: ResearchState):
        """Evaluate the research progress and determine next steps."""
        print("\n=== EVALUATOR NODE ===")

        research_plan = state["research_plan"]
        all_completed = research_plan.current_question_index >= len(research_plan.questions)

        if all_completed:
            print("All research questions completed. Moving to finalizer.")
            return {"next_step": "finalize"}
        else:
            print("More research needed.")
            return {"next_step": "research"}

    # Finalizer Node
    def finalizer_node(state: ResearchState):
        """Finalize the research report."""
        print("\n=== FINALIZER NODE ===")

        report = state["report"]
        research_plan = state["research_plan"]

        # Prepare detailed analysis
        detailed_analysis = "\n\n".join([
            f"## {section.title}\n{section.content}"
            for section in report.detailed_analysis
            if section.content is not None
        ])

        # Generate final sections
        final_sections = self.finalizer.invoke({
            "topic": research_plan.topic,
            "detailed_analysis": detailed_analysis
        })

        # Format final report
        report_message = self._format_report(report)

        return {
            "messages": [report_message],
        }

    # Add nodes to the graph
    workflow.add_node("research_manager", research_manager_node)
    workflow.add_node("specialized_research", specialized_research_node)
    workflow.add_node("evaluate", evaluator_node)
    workflow.add_node("finalizer", finalizer_node)

    # Add edges
    workflow.add_edge(START, "research_manager")
    workflow.add_edge("research_manager", "specialized_research")
    workflow.add_edge("specialized_research", "evaluate")

    # Add conditional edges from evaluator
    workflow.add_conditional_edges(
        "evaluate",
        lambda x: x["next_step"],
        {
            "research": "specialized_research",
            "finalize": "finalizer"
        }
    )
    workflow.add_edge("finalizer", END)

    # Compile the workflow
    return workflow.compile()
```

---

## 6. Workflow Invocation Pattern

### Basic Invocation

```python
# Create initial state
state = {
    "messages": [HumanMessage(content="Research quantum computing")],
    "research_plan": None,
    "report": None,
    "next_step": "research_manager"
}

# Invoke workflow
result = workflow.invoke(state)

# Access result
final_message = result["messages"][-1].content
```

### Invocation with Configuration

**Source**: [/code/reference_agents/agents/react_multi_agent.py:710-739](../code/reference_agents/agents/react_multi_agent.py)

```python
def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Process a message using the deep research system."""
    print("\n=== STARTING DEEP RESEARCH ===")
    print(f"Research Topic: {message}")

    # Create initial state
    state = {
        "messages": [HumanMessage(content=message)],
        "research_plan": None,
        "report": None,
        "next_step": "research_manager"
    }

    # Invoke the workflow with tracer and recursion limit
    result = self.workflow.invoke(state, config={
        "callbacks": [self.tracer],           # Opik tracing
        "recursion_limit": 100                # Allow for loops
    })

    print("\n=== RESEARCH COMPLETED ===")

    # Write the final report to a file
    final_report_path = os.path.expanduser("~/final_report.md")
    with open(final_report_path, "w", encoding="utf-8") as f:
        f.write(result["messages"][-1].content)

    print(f"Final report saved to: {final_report_path}")

    # Return the final report
    return result["messages"][-1].content
```

### Configuration Options

```python
config = {
    "callbacks": [tracer],              # Add callbacks (Opik, LangSmith, etc.)
    "recursion_limit": 100,             # Max workflow iterations
    "configurable": {                   # Custom configuration
        "model": "gpt-4o",
        "temperature": 0.7,
    }
}

result = workflow.invoke(state, config=config)
```

---

## 7. Iterative RAG Workflow Pattern

### Pattern Description

**Intent**: Build iterative retrieval-augmented generation with evaluation and query rewriting.

### Workflow Diagram

```
START
  ↓
agent (retrieve and answer)
  ↓
evaluate (check quality)
  ├─ sufficient=True → synthesize
  ├─ sufficient=False, iterations<3 → rewrite
  └─ iterations>=3 → synthesize (give up)
      ↓
     END
```

### State Schema

```python
class RAGState(TypedDict):
    """State for iterative RAG workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retrieved_docs: list[str]
    is_sufficient: Optional[bool]
    feedback: str
    iterations: int
```

### Router Function

```python
def _route_after_eval(self, state: RAGState) -> str:
    """Decide next step after evaluation."""
    if state.get("is_sufficient", False):
        return "synthesize"
    if state.get("iterations", 0) < 3:
        return "rewrite"
    return "synthesize"  # Give up after 3 tries

# Add conditional edge
builder.add_conditional_edges(
    "evaluate",
    self._route_after_eval,
    {
        "rewrite": "rewrite",
        "synthesize": "synthesize",
    },
)
```

---

## 8. Error Handling in Workflows

### Pattern: Try-Catch in Nodes

```python
def risky_node(state: MyState) -> dict:
    """Node with error handling."""
    try:
        result = process_data(state["data"])
        return {"data": result, "error": None}

    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return {"error": f"Validation failed: {str(e)}"}

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {"error": f"Processing failed: {str(e)}"}
```

### Pattern: Error Recovery Node

```python
def error_handler_node(state: MyState) -> dict:
    """Handle errors and attempt recovery."""
    error = state.get("error")

    if error:
        print(f"Error detected: {error}")

        # Attempt recovery
        if "validation" in error.lower():
            # Retry with default values
            return {"data": DEFAULT_DATA, "error": None}
        else:
            # Critical error, stop workflow
            return {"messages": [AIMessage(content=f"Critical error: {error}")]}

    return {}

# Add error routing
workflow.add_conditional_edges(
    "processor",
    lambda x: "error" if x.get("error") else "continue",
    {
        "error": "error_handler",
        "continue": "next_step"
    }
)
```

---

## 9. Workflow Visualization

### Generate Workflow Graph

```python
from langgraph.graph import StateGraph

workflow = StateGraph(MyState)
# ... add nodes and edges ...
app = workflow.compile()

# Get graph representation
graph = app.get_graph()

# Print ASCII representation
graph.print_ascii()

# Get Mermaid diagram
mermaid_diagram = graph.draw_mermaid()
print(mermaid_diagram)
```

### Opik Tracing Integration

```python
from opik.integrations.langchain import OpikTracer

# Initialize tracer with workflow graph
tracer = OpikTracer(
    graph=self.workflow.get_graph(xray=True),
    project_name="deep-research"
)

# Use tracer in invocation
result = self.workflow.invoke(
    state,
    config={"callbacks": [tracer]}
)
```

---

## 10. Advanced Patterns

### Pattern: Parallel Node Execution

```python
from langgraph.graph import StateGraph

workflow = StateGraph(MyState)

# Add parallel nodes
workflow.add_node("research_1", research_node_1)
workflow.add_node("research_2", research_node_2)
workflow.add_node("research_3", research_node_3)
workflow.add_node("combine", combine_results_node)

# All research nodes run in parallel
workflow.add_edge(START, "research_1")
workflow.add_edge(START, "research_2")
workflow.add_edge(START, "research_3")

# Combine waits for all to finish
workflow.add_edge("research_1", "combine")
workflow.add_edge("research_2", "combine")
workflow.add_edge("research_3", "combine")

workflow.add_edge("combine", END)
```

### Pattern: Subgraph Workflow

```python
# Create subworkflow
subworkflow = StateGraph(SubState)
subworkflow.add_node("step1", step1_node)
subworkflow.add_node("step2", step2_node)
subworkflow.add_edge(START, "step1")
subworkflow.add_edge("step1", "step2")
subworkflow.add_edge("step2", END)
sub_app = subworkflow.compile()

# Use subworkflow in main workflow
def main_node(state: MainState) -> dict:
    """Node that invokes subworkflow."""
    sub_state = {"data": state["data"]}
    result = sub_app.invoke(sub_state)
    return {"result": result["data"]}

main_workflow = StateGraph(MainState)
main_workflow.add_node("main_node", main_node)
```

---

## 11. Testing Workflows

### Unit Test Individual Nodes

```python
import pytest

def test_research_manager_node():
    """Test research manager node."""
    state = {
        "messages": [HumanMessage(content="quantum computing")],
        "research_plan": None,
        "report": None,
    }

    result = research_manager_node(state)

    assert result["research_plan"] is not None
    assert len(result["research_plan"].questions) > 0
    assert result["report"] is not None
```

### Integration Test Workflow

```python
def test_workflow_execution():
    """Test complete workflow execution."""
    workflow = _create_workflow()

    state = {
        "messages": [HumanMessage(content="test topic")],
        "research_plan": None,
        "report": None,
        "next_step": "research_manager"
    }

    result = workflow.invoke(state, config={"recursion_limit": 10})

    assert len(result["messages"]) > 0
    assert result["report"] is not None
    assert result["report"].executive_summary is not None
```

### Test Conditional Routing

```python
def test_evaluator_routing():
    """Test conditional routing logic."""
    # Test "continue" path
    state = {
        "research_plan": ResearchPlan(
            topic="test",
            questions=[ResearchQuestion(title="Q1", description="D1")],
            current_question_index=0
        )
    }
    result = evaluator_node(state)
    assert result["next_step"] == "research"

    # Test "finalize" path
    state["research_plan"].current_question_index = 1
    result = evaluator_node(state)
    assert result["next_step"] == "finalize"
```

---

## 12. Best Practices

### ✅ Do:

1. **Use TypedDict for State**
   - Type-safe state definition
   - IDE autocomplete support

2. **Annotate Message Fields**
   ```python
   messages: Annotated[Sequence[BaseMessage], add_messages]
   ```

3. **Return Partial Updates**
   - Only return changed fields
   - Reduces bugs from accidental overwrites

4. **Add Logging**
   - Print statements in each node
   - Helps debugging workflow execution

5. **Set Recursion Limits**
   - Prevent infinite loops
   - `config={"recursion_limit": 100}`

6. **Use Pydantic for Complex Data**
   - Type validation
   - Clear structure

### ❌ Don't:

1. **Don't Mutate State Directly**
   ```python
   # ❌ Bad
   def node(state):
       state["counter"] += 1  # Mutates state
       return {}

   # ✅ Good
   def node(state):
       return {"counter": state["counter"] + 1}
   ```

2. **Don't Return Full State**
   ```python
   # ❌ Bad
   def node(state):
       return state  # Returns everything

   # ✅ Good
   def node(state):
       return {"counter": state["counter"] + 1}  # Partial update
   ```

3. **Don't Forget Recursion Limits**
   - Workflows can loop forever without limits

---

## Summary: Workflow Orchestration Checklist

When building a LangGraph workflow:

- [ ] Define TypedDict state schema
- [ ] Use Annotated[Sequence[BaseMessage], add_messages] for messages
- [ ] Create node functions that return partial updates
- [ ] Add nodes to StateGraph
- [ ] Connect nodes with add_edge
- [ ] Add conditional routing with add_conditional_edges
- [ ] Compile workflow with compile()
- [ ] Set recursion_limit in config
- [ ] Add Opik tracing for observability
- [ ] Test individual nodes
- [ ] Test complete workflow execution
- [ ] Visualize workflow with get_graph()

---

## References

- **Source Code**: [/code/reference_agents/agents/react_multi_agent.py](../code/reference_agents/agents/react_multi_agent.py)
- **Agent Patterns**: [/docs/AGENT_PATTERNS.md](AGENT_PATTERNS.md)
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **StateGraph Tutorial**: https://langchain-ai.github.io/langgraph/tutorials/introduction/
- **Conditional Edges**: https://langchain-ai.github.io/langgraph/how-tos/branching/

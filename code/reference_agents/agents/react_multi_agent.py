"""ReAct Multi-Agent System - Consolidation of Week 3 Parts 1, 2, and 3.

This implementation provides a unified interface for three different agent patterns:
- Tool-Using Agent: Simple ReAct agent with calculator, datetime, and weather tools
- Agentic RAG: Custom iterative RAG with evaluation loop
- Deep Research: Multi-agent orchestration for comprehensive research

Uses delegation pattern to switch between different agent implementations.
"""

import io
import contextlib
import os
import os.path as osp
from typing import Dict, List, Optional, Any, TypedDict, Annotated, Sequence, Literal

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, AnyMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from opik.integrations.langchain import OpikTracer

from deep_research.core.chat_interface import ChatInterface
from deep_research.tools.calculator import Calculator
from deep_research.prompts.AGENT_PROMPTS import (
    AGENT_SYSTEM_PROMPT,
    DOCUMENT_EVALUATOR_PROMPT,
    DOCUMENT_SYNTHESIZER_PROMPT,
    QUERY_REWRITER_PROMPT,
    RESEARCH_MANAGER_PROMPT,
    RESEARCH_SPECIALIST_PROMPT,
    REPORT_FINALIZER_PROMPT,
    ResearchQuestion,
    ResearchPlan,
    Report,
    ReportSection
)

# Configuration for Agentic RAG - Update these paths as needed
BASE_DIR = "/Users/Jacob.Jaffe/Documents/Maven/RAG Test Docs"
FILE_PATHS = [
    osp.join(BASE_DIR, "2019-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2020-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2021-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2022-annual-performance-report.pdf"),
]
CHROMA_PERSIST_DIRECTORY = "/Users/Jacob.Jaffe/chroma_db"


# Internal Agent Implementations


class ToolUsingAgent(ChatInterface):
    """Simple ReAct agent with calculator, datetime, and weather tools."""

    def __init__(self):
        self.llm = None
        self.tools = []
        self.graph = None
        self.tracer = None

    def initialize(self) -> None:
        """Initialize the tool-using agent with ReAct pattern."""
        # Initialize chat model
        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")

        # Create tools
        self.tools = self._create_tools()

        # Create the ReAct agent graph with the tools
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )

        # Initialize Opik tracer
        self.tracer = OpikTracer(
            graph=self.graph.get_graph(xray=True),
            project_name="react-tool-using"
        )

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

    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process a message using the tool-using agent."""
        # Run the graph with the user's message
        result = self.graph.invoke(
            {"messages": [("user", message)]},
            config={"callbacks": [self.tracer]}
        )

        # Return the last assistant message
        return result["messages"][-1].content if result["messages"] else "No response generated"


class DocumentEvaluation(BaseModel):
    """Evaluation result for retrieved documents."""
    is_sufficient: bool = Field(description="Whether the documents provide sufficient information")
    feedback: str = Field(description="Feedback about the document quality and what's missing")


class RAGState(TypedDict):
    """State for Agentic RAG workflow."""
    messages: Annotated[Sequence[AnyMessage], add_messages]
    retrieved_docs: List[str]
    is_sufficient: Optional[bool]
    feedback: str
    iterations: int


def load_docs(paths: List[str]) -> List[Document]:
    """Load and split PDF documents into chunks."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_docs: List[Document] = []
    for p in paths:
        if not os.path.exists(p):
            print(f"WARNING: missing file {p}")
            continue
        pages = PyPDFLoader(p).load()
        combined = "\n".join(pg.page_content for pg in pages)
        for chunk in splitter.split_text(combined):
            all_docs.append(Document(page_content=chunk, metadata={"source": p}))
    return all_docs


class AgenticRAGAgent(ChatInterface):
    """Custom iterative RAG agent with evaluation loop."""

    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vs = None
        self.tools = []
        self.agent = None
        self.graph = None
        self.tracer = None

    def initialize(self):
        """Initialize the Agentic RAG system."""
        # Models
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # Vector store
        self.vs = Chroma(
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name="opm_documents"
        )

        # Check if vector store has documents
        has_existing_documents = len(self.vs.get(limit=1)['ids']) > 0
        if has_existing_documents:
            print("ChromaDB found - reusing existing documents.")
        else:
            print("No existing ChromaDB found - processing and embedding documents...")
            docs = load_docs(FILE_PATHS)
            if docs:
                self.vs.add_documents(docs)

        # Tools
        self.tools = self._create_tools()

        # Agent (ReAct) with access to tools and a system directive
        self.agent = create_react_agent(
            self.llm,
            tools=self.tools,
            prompt=AGENT_SYSTEM_PROMPT,
        )

        # Build the graph
        builder = StateGraph(RAGState)
        builder.add_node("agent", self._agent_node)
        builder.add_node("evaluate", self._evaluator_node)
        builder.add_node("rewrite", self._rewriter_node)
        builder.add_node("synthesize", self._synth_node)

        builder.add_edge(START, "agent")
        builder.add_edge("agent", "evaluate")
        builder.add_conditional_edges(
            "evaluate",
            self._route_after_eval,
            {
                "rewrite": "rewrite",
                "synthesize": "synthesize",
            },
        )
        builder.add_edge("rewrite", "agent")
        builder.add_edge("synthesize", END)

        self.graph = builder.compile()

        # Initialize Opik tracer
        self.tracer = OpikTracer(
            graph=self.graph.get_graph(xray=True),
            project_name="react-agentic-rag"
        )

    def _create_tools(self):
        """Create tools for document and web search."""

        @tool("search_opm_docs")
        def search_opm_docs(query: str) -> List[str]:
            """Search OPM 2019-2022 documents for passages relevant to the query. Returns a list of short snippets."""
            docs = self.vs.similarity_search(query, k=4)
            snippets: List[str] = []
            for d in docs:
                txt = d.page_content.strip().replace("\n", " ")
                if len(txt) > 500:
                    txt = txt[:500] + " ..."
                src = d.metadata.get("source", "unknown")
                snippets.append(f"[{os.path.basename(src)}] {txt}")
            return snippets

        @tool("web_search")
        def web_search(query: str) -> List[str]:
            """Search the web for recent info. Use this tool to fetch real-time web search information."""
            try:
                results = TavilySearch(max_results=3).invoke(query)
                formatted_results = []
                for result in results['results']:
                    formatted_results.append(f"""
                        Title: {result['title']}
                        URL: {result['url']}
                        Content: {result['content']}
                    """)
                return formatted_results
            except Exception as e:
                return [f"Error: {str(e)}"]

        return [search_opm_docs, web_search]

    def _agent_node(self, state: RAGState):
        """Run the ReAct agent with current messages."""
        result = self.agent.invoke({"messages": state["messages"]})
        new_messages: Sequence[AnyMessage] = result["messages"]

        # Collect tool outputs from appended messages only
        prev_len = len(state["messages"])
        appended = list(new_messages[prev_len:])

        new_snippets: List[str] = []
        for m in appended:
            if isinstance(m, ToolMessage):
                payload = m.content
                if isinstance(payload, list):
                    new_snippets.extend([str(x) for x in payload])
                else:
                    new_snippets.append(str(payload))

        return {
            "messages": new_messages,
            "retrieved_docs": state["retrieved_docs"] + new_snippets,
        }

    def _evaluator_node(self, state: RAGState):
        """Evaluate if retrieved documents are sufficient."""
        user_q = self._first_user_question(state["messages"])

        if not state["retrieved_docs"]:
            return {"is_sufficient": False, "feedback": "No passages retrieved yet. Retrieve first."}

        prompt = DOCUMENT_EVALUATOR_PROMPT.format(
            question=user_q,
            retrieved_docs="\n\n".join(f"- {s}" for s in state["retrieved_docs"]),
        )
        structured_llm = self.llm.with_structured_output(DocumentEvaluation)
        result = structured_llm.invoke(prompt)
        return {"is_sufficient": result.is_sufficient, "feedback": result.feedback}

    def _rewriter_node(self, state: RAGState):
        """Rewrite the question using feedback."""
        user_q = self._first_user_question(state["messages"])
        prompt = QUERY_REWRITER_PROMPT.format(
            question=user_q,
            feedback=state.get("feedback", ""),
            retrieved_docs="\n".join(state.get("retrieved_docs", [])[:5]),
        )
        rewritten = self.llm.invoke(prompt).content.strip()
        return {
            "messages": [HumanMessage(content=rewritten)],
            "iterations": state["iterations"] + 1,
        }

    def _synth_node(self, state: RAGState):
        """Synthesize the final answer from collected snippets."""
        user_q = self._first_user_question(state["messages"])
        prompt = DOCUMENT_SYNTHESIZER_PROMPT.format(
            question=user_q,
            retrieved_docs="\n\n".join(state["retrieved_docs"]),
        )
        ans = self.llm.invoke(prompt).content
        return {"messages": [AIMessage(content=ans)]}

    def _route_after_eval(self, state: RAGState) -> str:
        """Decide next step after evaluation."""
        if state.get("is_sufficient", False):
            return "synthesize"
        if state.get("iterations", 0) < 3:
            return "rewrite"
        return "synthesize"

    @staticmethod
    def _first_user_question(messages: Sequence[AnyMessage]) -> str:
        """Extract the first user question from messages."""
        for m in messages:
            if isinstance(m, HumanMessage):
                return m.content
        return messages[0].content if messages else ""

    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process a message using the Agentic RAG system."""
        initial_state: RAGState = {
            "messages": [HumanMessage(content=message)],
            "retrieved_docs": [],
            "is_sufficient": None,
            "feedback": "",
            "iterations": 0,
        }

        result = self.graph.invoke(initial_state, config={"callbacks": [self.tracer]})
        return result["messages"][-1].content


class ResearchState(TypedDict):
    """State tracking for the deep research workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    research_plan: Optional[ResearchPlan]
    report: Optional[Report]
    next_step: str


class DeepResearchAgent(ChatInterface):
    """Multi-agent orchestration for comprehensive research."""

    def __init__(self):
        self.llm = None
        self.research_manager = None
        self.specialized_research_agent = None
        self.finalizer = None
        self.workflow = None
        self.tavily_search_tool = None
        self.tracer = None

    def initialize(self) -> None:
        """Initialize components for the deep research system."""
        # Initialize LLM model
        self.llm = ChatOpenAI(model="gpt-4o-mini")

        # Create Tavily search tool for agents
        self.tavily_search_tool = TavilySearch(max_results=5)

        # Create components
        self.research_manager = self._create_research_manager()
        self.specialized_research_agent = self._create_specialized_research_agent()
        self.finalizer = self._create_finalizer()

        # Create the workflow graph using these agents
        self.workflow = self._create_workflow()

        # Initialize Opik tracer
        self.tracer = OpikTracer(
            graph=self.workflow.get_graph(xray=True),
            project_name="react-deep-research"
        )

    def _create_research_manager(self) -> Any:
        """Create the research manager agent."""
        research_manager = (
            RESEARCH_MANAGER_PROMPT
            | self.llm.with_structured_output(ResearchPlan)
        )

        return research_manager

    def _create_specialized_research_agent(self) -> Any:
        """Create specialized research agents."""
        # Create search tool for the agent
        @tool("web_search")
        def search_web(query: str) -> str:
            """Search the web for information on the research topic."""
            results = self.tavily_search_tool.invoke(query)
            formatted_results = []

            for i, result in enumerate(results, 1):
                formatted_results.append(f"Result {i}:")
                # Handle both dict and string formats
                if isinstance(result, dict):
                    formatted_results.append(f"Title: {result.get('title', 'N/A')}")
                    formatted_results.append(f"Content: {result.get('content', 'N/A')}")
                    formatted_results.append(f"URL: {result.get('url', 'N/A')}")
                else:
                    # If result is a string, just append it
                    formatted_results.append(f"Content: {result}")
                formatted_results.append("")

            return "\n".join(formatted_results)

        # Create the specialized agent
        tools = [search_web]

        # Define the system message for the specialized research agent
        system_message = """You are a Specialized Research Agent responsible for thoroughly researching a specific topic section.

        Process:
        1. Analyze the research question and description
        2. Generate 1-2 effective search queries to gather information
        3. Use the web_search tool ONCE OR TWICE to find relevant information
        4. After getting search results, IMMEDIATELY synthesize findings into a comprehensive section
        5. DO NOT call the search tool more than 2 times

        IMPORTANT: After you have search results, you MUST provide your final answer without calling any more tools.

        Your response should be:
        - Thorough (at least 300 words)
        - Well-structured with subsections
        - Based on factual information from your search results
        - Include proper citations to sources

        When you're done researching, provide your final analysis immediately.
        """

        # Create the specialized research agent
        specialized_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_message
        )

        return specialized_agent


    def _create_finalizer(self) -> Any:
        """Create the finalizer component."""
        # Create the finalizer
        finalizer = REPORT_FINALIZER_PROMPT | self.llm | StrOutputParser()

        return finalizer

    def _create_workflow(self) -> Any:
        """Create the multi-agent deep research workflow."""
        # Create a state graph
        workflow = StateGraph(ResearchState)

        # Define the nodes

        # Research Manager Node
        def research_manager_node(state: ResearchState):
            """Create the research plan."""
            print("\n=== RESEARCH MANAGER NODE ===")
            # Get the topic from the user message
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

            # Extract content and sources from the result
            last_message = result["messages"][-1]
            if isinstance(last_message, tuple):
                content = last_message[1]  # Tuple format: (role, content)
            else:
                content = last_message.content  # AIMessage object

            # Parse out sources from the content (simplified)
            sources = []
            for line in content.split("\n"):
                if "http" in line and "://" in line:
                    sources.append(line.strip())

            # Update the research plan
            research_plan.questions[current_index].completed = True

            # Update the report
            report = state["report"]
            assert report is not None, "Report is None"
            # Update the ReportSection (Pydantic model) - create a new instance
            section = report.detailed_analysis[current_index]
            report.detailed_analysis[current_index] = ReportSection(
                title=section.title,
                content=content,
                sources=sources
            )

            # Move to the next question
            research_plan.current_question_index += 1

            # Always go to evaluate after each research section
            return {
                "research_plan": research_plan,
                "report": report,
            }

        # Research Evaluator Node
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

        # Finalizer Node
        def finalizer_node(state: ResearchState):
            """Finalize the research report."""
            print("\n=== FINALIZER NODE ===")

            research_plan = state["research_plan"]
            report = state["report"]
            # Both report and research plan should be available at this point:
            assert report is not None, "Report is None"
            assert research_plan is not None, "Research plan is None"

            # Prepare the detailed analysis for the finalizer
            detailed_analysis = "\n\n".join([
                f"## {section.title}\n{section.content}"
                for section in report.detailed_analysis
                if section.content is not None
            ])

            # Generate the final sections
            final_sections = self.finalizer.invoke({
                "topic": research_plan.topic,
                "detailed_analysis": detailed_analysis
            })

            # Parse the final sections (simplified parsing)
            sections = final_sections.split("\n\n")

            # Update the report
            if len(sections) >= 3:  # Very simple parsing, adjust as needed
                report.executive_summary = sections[0].replace("# Executive Summary", "").strip()
                report.key_findings = sections[1].replace("# Key Findings", "").strip()
                report.limitations = sections[2].replace("# Limitations and Further Research", "").strip()

            # Format the final report
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

        # Add conditional edges from evaluator node to research or finalize node:
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

    def _format_report(self, report: Report) -> AIMessage:
        """Format the research report for presentation."""
        sections = [
            "# Research Report\n",

            "## Executive Summary\n" + (report.executive_summary or "N/A"),

            "## Key Findings\n" + (report.key_findings or "N/A"),

            "## Detailed Analysis"
        ]

        # Add detailed analysis sections
        for section in report.detailed_analysis:
            if section.content:
                sections.append(f"### {section.title}\n{section.content}")

                if section.sources:
                    sources = "\n".join([f"- {source}" for source in section.sources])
                    sections.append(f"**Sources:**\n{sources}")

        # Add limitations
        sections.append("## Limitations and Further Research\n" + (report.limitations or "N/A"))

        return AIMessage(content="\n\n".join(sections))

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
            "callbacks": [self.tracer],
            "recursion_limit": 100  # Allow for multiple research iterations
        })

        print("\n=== RESEARCH COMPLETED ===")

        # Write the final report to a file
        final_report_path = os.path.expanduser("~/final_report.md")
        with open(final_report_path, "w", encoding="utf-8") as f:
            f.write(result["messages"][-1].content)

        print(f"Final report saved to: {final_report_path}")

        # Return the final report
        return result["messages"][-1].content


# Main Class with Delegation Pattern


class ReActMultiAgent(ChatInterface):
    """ReAct Multi-Agent System with delegation pattern.

    Supports three modes:
    - tool_using: Simple ReAct agent with calculator, datetime, and weather tools
    - agentic_rag: Custom iterative RAG with evaluation loop
    - deep_research: Multi-agent orchestration for comprehensive research
    """

    def __init__(self, mode: Literal["tool_using", "agentic_rag", "deep_research"] = "deep_research"):
        """Initialize the multi-agent system with specified mode.

        Args:
            mode: The agent mode to use ("tool_using", "agentic_rag", or "deep_research")
        """
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
        """Process a message by delegating to the internal agent.

        Args:
            message: The user's input message
            chat_history: Optional list of previous chat messages

        Returns:
            str: The assistant's response
        """
        if self.delegate is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return self.delegate.process_message(message, chat_history)

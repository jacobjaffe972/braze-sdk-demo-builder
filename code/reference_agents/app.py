import os
import gradio as gr
from typing import List, Tuple
from dotenv import load_dotenv

from deep_research.core.factory import create_agent_by_name, AGENT_ALIASES, AgentType

# Load environment variables
load_dotenv()

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
    AgentType.LLM_CHAINING_MEMORY: {
        "title": "Deep Research AI - Conversational Memory",
        "description": "AI assistant with conversation history and tool usage.",
        "examples": [
            "If I have a dinner bill of $120, what would be a 15% tip?",
            "What about 20%?",
            "What day is it today?",
            "What is the capital of France?",
        ]
    },

    # RAG variants
    AgentType.RAG_WEB_SEARCH: {
        "title": "Deep Research AI - Web Search",
        "description": "AI assistant with live web search capabilities.",
        "examples": [
            "What are the latest developments in quantum computing?",
            "Who is the current CEO of SpaceX?",
        ]
    },
    AgentType.RAG_DOCUMENT: {
        "title": "Deep Research AI - Document RAG",
        "description": "AI assistant for OPM document retrieval (2019-2022).",
        "examples": [
            "What new customer experience improvements did OPM implement in FY 2022?",
            "What were key performance metrics for OPM in 2020?",
        ]
    },
    AgentType.RAG_CORRECTIVE: {
        "title": "Deep Research AI - Corrective RAG",
        "description": "AI assistant combining document retrieval and web search.",
        "examples": [
            "How did OPM's hiring process evolve from 2019-2022?",
            "What strategic goals did OPM outline in 2022?",
        ]
    },

    # ReAct variants
    AgentType.REACT_TOOL_USING: {
        "title": "Deep Research AI - Tool-Using Agent",
        "description": "ReAct agent that autonomously selects tools.",
        "examples": [
            "Calculate 156 * 42",
            "What's the weather in San Francisco?",
        ]
    },
    AgentType.REACT_AGENTIC_RAG: {
        "title": "Deep Research AI - Agentic RAG",
        "description": "Agent that dynamically controls search strategy.",
        "examples": [
            "What strategic goals did OPM outline in 2022?",
            "How did OPM's performance metrics evolve from 2018 to 2022?",
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

"""Factory for creating agent instances.

Provides a unified interface for creating all agent types with proper configuration.
"""

from enum import Enum
from typing import Optional

from deep_research.core.chat_interface import ChatInterface


class AgentType(Enum):
    """Available agent types and their modes."""

    # LLM Chaining agents (Week 1)
    LLM_CHAINING_QUERY = "llm_chaining_query"
    LLM_CHAINING_TOOLS = "llm_chaining_tools"
    LLM_CHAINING_MEMORY = "llm_chaining_memory"

    # RAG agents (Week 2)
    RAG_WEB_SEARCH = "rag_web_search"
    RAG_DOCUMENT = "rag_document"
    RAG_CORRECTIVE = "rag_corrective"

    # ReAct agents (Week 3)
    REACT_TOOL_USING = "react_tool_using"
    REACT_AGENTIC_RAG = "react_agentic_rag"
    REACT_DEEP_RESEARCH = "react_deep_research"


# Convenience aliases for common agent names
AGENT_ALIASES = {
    "llm_chaining": AgentType.LLM_CHAINING_MEMORY,  # Default to full version
    "llm_rag_tools": AgentType.RAG_CORRECTIVE,      # Default to most advanced
    "react_multi_agent": AgentType.REACT_DEEP_RESEARCH,  # Default to deep research
}


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


def create_agent_by_name(name: str) -> ChatInterface:
    """Create agent by friendly name (e.g., 'LLM_Chaining') or specific mode.

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

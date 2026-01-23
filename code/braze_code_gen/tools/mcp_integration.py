"""MCP integration for Braze documentation access.

This module provides LangChain tool interfaces for the official Braze MCP server.
The official server provides comprehensive Braze SDK documentation with semantic
search and structured code examples.
"""

import logging
from typing import Annotated

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ============================================================================
# Official Braze MCP Server Tools
# ============================================================================


@tool
def search_braze_docs(
    query: Annotated[str, "Search query for Braze documentation"]
) -> str:
    """Search Braze documentation using the official Braze MCP server.

    This tool provides comprehensive search across all Braze SDK documentation,
    API references, integration guides, and code examples. Uses semantic search
    for better relevance than simple keyword matching.

    When to use this tool:
    - Finding documentation about specific Braze SDK methods
    - Learning about SDK features and capabilities
    - Discovering integration patterns and best practices
    - Getting overview information before diving into code examples

    Examples:
    - "changeUser method for user identification"
    - "track custom events"
    - "set user attributes"
    - "push notification permissions Web SDK"
    - "initialize Braze Web SDK"

    Args:
        query: What to search for in Braze docs. Be specific but not overly verbose.

    Returns:
        str: Relevant documentation content with page titles, URLs, and snippets
    """
    try:
        from braze_code_gen.tools.mcp_client import run_mcp_search
        result = run_mcp_search(query, limit=5)
        return result
    except Exception as e:
        logger.error(f"Error searching Braze docs: {e}", exc_info=True)
        return f"Error searching documentation: {str(e)}"


@tool
def get_braze_code_examples(
    topic: Annotated[str, "Topic or feature to get code examples for"]
) -> str:
    """Get Braze SDK code examples from the official documentation.

    This tool retrieves working code examples for specific Braze SDK features.
    Returns JavaScript/TypeScript examples for the Web SDK by default.

    When to use this tool:
    - After finding relevant docs, get actual code to implement
    - Learning syntax for specific SDK methods
    - Understanding how to use SDK features in practice
    - Getting implementation patterns for common use cases

    Topic examples:
    - "initialization" - SDK initialization code
    - "user_tracking" - Event tracking examples
    - "push_notifications" - Push notification setup
    - "user_attributes" - Setting user attributes
    - "custom_events" - Logging custom events
    - "content_cards" - Content card implementation

    Args:
        topic: The Braze SDK feature or topic to get examples for.
               Use concise keywords that describe the feature.

    Returns:
        str: Code examples with explanations from Braze documentation
    """
    try:
        from braze_code_gen.tools.mcp_client import run_mcp_get_examples
        result = run_mcp_get_examples(
            topic=topic,
            language="javascript",
            sdk="web",
            limit=5
        )
        return result
    except Exception as e:
        logger.error(f"Error getting code examples: {e}", exc_info=True)
        return f"Error getting code examples: {str(e)}"


@tool
def get_braze_event_schema(
    event_key: Annotated[str, "Event type identifier (e.g., 'custom_event', 'purchase', 'user_attribute')"]
) -> str:
    """Get JSON schema for a Braze event type.

    Returns the expected structure, required fields, and data types for
    sending events to Braze. Useful for ensuring correct API payloads.

    Event keys:
    - "custom_event" - Schema for custom event tracking
    - "purchase" - Schema for purchase events
    - "user_attribute" - Schema for user attributes
    - "push_token" - Schema for push token registration

    Args:
        event_key: The type of Braze event to get schema for

    Returns:
        str: JSON schema with field descriptions and examples
    """
    try:
        from braze_code_gen.tools.mcp_client import run_mcp_get_event_schema
        result = run_mcp_get_event_schema(event_key)
        return result
    except Exception as e:
        logger.error(f"Error getting event schema: {e}", exc_info=True)
        return f"Error getting event schema: {str(e)}"


@tool
def get_braze_setup_checklist(
    environment: Annotated[str, "Target environment: 'dev', 'staging', or 'prod'"] = "dev"
) -> str:
    """Get a structured setup checklist for Braze SDK integration.

    Returns step-by-step instructions for integrating the Braze SDK,
    including prerequisites, configuration steps, and verification.

    Args:
        environment: Target deployment environment (default: 'dev')

    Returns:
        str: Structured checklist with setup steps and time estimates
    """
    try:
        from braze_code_gen.tools.mcp_client import run_mcp_get_setup_checklist
        result = run_mcp_get_setup_checklist(environment)
        return result
    except Exception as e:
        logger.error(f"Error getting setup checklist: {e}", exc_info=True)
        return f"Error getting setup checklist: {str(e)}"


# Export tools for agent use
BRAZE_DOCS_TOOLS = [
    search_braze_docs,
    get_braze_code_examples,
    get_braze_event_schema,
    get_braze_setup_checklist,
]

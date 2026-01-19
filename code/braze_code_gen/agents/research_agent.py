"""Research Agent - Braze documentation research.

This agent searches Braze documentation for implementation guidance.
"""

import logging
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig

from braze_code_gen.core.llm_factory import create_llm
from braze_code_gen.core.models import ResearchResult, BrazeDocumentation, ModelTier
from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.tools.mcp_integration import BRAZE_DOCS_TOOLS
from braze_code_gen.prompts.BRAZE_PROMPTS import RESEARCH_AGENT_PROMPT
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Research agent for Braze documentation."""

    def __init__(
        self,
        model_tier: ModelTier = ModelTier.RESEARCH,
        temperature: float = 0.3
    ):
        """Initialize the research agent.

        Args:
            model_tier: LLM tier to use (primary/research/validation)
            temperature: Temperature for generation
        """
        self.llm = create_llm(tier=model_tier, temperature=temperature)

        # Create ReAct agent with Braze docs tools
        # Note: state_modifier has been deprecated, we'll add system message manually in process()
        self.agent = create_react_agent(
            self.llm,
            tools=BRAZE_DOCS_TOOLS
        )

    def process(self, state: CodeGenerationState, config: RunnableConfig) -> dict:
        """Research Braze documentation for feature implementation.

        Args:
            state: Current workflow state
            config: Optional LangGraph config with callbacks for streaming

        Returns:
            dict: State updates with research results
        """
        logger.info("=== RESEARCH AGENT: Starting documentation research ===")

        feature_plan = state["feature_plan"]
        if not feature_plan:
            logger.error("No feature plan available")
            return {
                "error": "No feature plan available for research",
                "next_step": "error_handler"
            }

        # Format feature plan for research
        feature_plan_text = self._format_feature_plan(feature_plan)

        # Create research query
        research_query = f"""Research Braze SDK documentation for these features:

{feature_plan_text}

For each feature, find:
1. SDK initialization steps
2. Code examples
3. Required methods and parameters
4. Best practices
"""

        # Run ReAct agent
        try:
            # Merge user config with recursion limit for research agent
            research_config = {**(config or {})}
            # Increase recursion limit for research agent (needs more steps for doc search)
            # Using 35 as a balance between thoroughness and speed
            research_config["recursion_limit"] = 35

            # Pass config to agent invoke for token streaming callbacks
            result = self.agent.invoke({
                "messages": [
                    SystemMessage(content=RESEARCH_AGENT_PROMPT),
                    HumanMessage(content=research_query)
                ]
            }, config=research_config)

            # Extract research findings from messages
            total_messages = len(result["messages"])
            logger.info(f"Research agent completed in {total_messages} message exchanges")

            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                content = final_message.content
                # Handle both string and list content formats
                if isinstance(content, list):
                    # Extract text from list of content blocks (e.g., [{'type': 'text', 'text': '...'}])
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and 'text' in block:
                            text_parts.append(block['text'])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    research_summary = '\n'.join(text_parts)
                else:
                    research_summary = str(content)
            else:
                research_summary = str(final_message)

            logger.info(f"Research completed: {len(research_summary)} chars")

            # Create research result
            try:
                implementation_guidance = self._extract_implementation_guidance(research_summary)
                logger.debug(f"Implementation guidance created: {len(implementation_guidance)} chars")
            except Exception as e:
                logger.error(f"Error extracting implementation guidance: {e}")
                implementation_guidance = research_summary  # Fallback

            try:
                research_result = ResearchResult(
                    query=research_query,
                    documentation_pages=[],  # Pages were already processed by tools
                    summary=research_summary,
                    implementation_guidance=implementation_guidance
                )
                logger.debug("ResearchResult object created successfully")
            except Exception as e:
                logger.error(f"Error creating ResearchResult: {e}")
                logger.error(f"query type: {type(research_query)}, value: {research_query}")
                logger.error(f"summary type: {type(research_summary)}, value: {research_summary[:100]}")
                logger.error(f"guidance type: {type(implementation_guidance)}")
                raise

            return {
                "research_results": research_result,
                "next_step": "code_generation"
            }

        except Exception as e:
            logger.error(f"Error during research: {e}", exc_info=True)
            return {
                "error": f"Research failed: {str(e)}",
                "next_step": "code_generation"  # Continue anyway with basic guidance
            }

    def _format_feature_plan(self, feature_plan) -> str:
        """Format feature plan for research query.

        Args:
            feature_plan: SDKFeaturePlan

        Returns:
            str: Formatted feature list
        """
        lines = []
        try:
            for i, feature in enumerate(feature_plan.features, 1):
                lines.append(f"{i}. **{feature.name}**: {feature.description}")

                # Flatten sdk_methods in case of nested lists or mixed types
                methods = feature.sdk_methods
                if methods:
                    # Recursively flatten any nested structures
                    flattened = []
                    for item in methods:
                        if isinstance(item, list):
                            # Nested list - flatten it
                            for subitem in item:
                                flattened.append(str(subitem))
                        else:
                            flattened.append(str(item))
                    methods = flattened

                lines.append(f"   SDK Methods: {', '.join(methods) if methods else 'None'}")
                if feature.implementation_notes:
                    lines.append(f"   Notes: {feature.implementation_notes}")
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting feature plan: {e}")
            logger.error(f"Feature plan data: {feature_plan}")
            # Return a simple string representation as fallback
            return str(feature_plan)

    def _extract_implementation_guidance(self, research_summary: str) -> str:
        """Extract implementation guidance from research summary.

        Args:
            research_summary: Research summary text

        Returns:
            str: Implementation guidance
        """
        # Extract code examples and key points
        lines = []

        # Look for code blocks
        if "```" in research_summary:
            lines.append("**Code Examples Found:**")
            lines.append(research_summary)
        else:
            lines.append("**Implementation Guidance:**")
            lines.append(research_summary)

        return "\n".join(lines)

"""Research Agent - Braze documentation research.

This agent searches Braze documentation for implementation guidance.
"""

import logging
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from braze_code_gen.core.models import ResearchResult, BrazeDocumentation
from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.tools.mcp_integration import BRAZE_DOCS_TOOLS
from braze_code_gen.prompts.BRAZE_PROMPTS import RESEARCH_AGENT_PROMPT
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Research agent for Braze documentation."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3
    ):
        """Initialize the research agent.

        Args:
            model: LLM model to use
            temperature: Temperature for generation
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)

        # Create ReAct agent with Braze docs tools
        self.agent = create_react_agent(
            self.llm,
            tools=BRAZE_DOCS_TOOLS,
            state_modifier=SystemMessage(content=RESEARCH_AGENT_PROMPT)
        )

    def process(self, state: CodeGenerationState) -> dict:
        """Research Braze documentation for feature implementation.

        Args:
            state: Current workflow state

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
            result = self.agent.invoke({
                "messages": [HumanMessage(content=research_query)]
            })

            # Extract research findings from messages
            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                research_summary = final_message.content
            else:
                research_summary = str(final_message)

            logger.info(f"Research completed: {len(research_summary)} chars")

            # Create research result
            research_result = ResearchResult(
                query=research_query,
                documentation_pages=[],  # Pages were already processed by tools
                summary=research_summary,
                implementation_guidance=self._extract_implementation_guidance(research_summary)
            )

            return {
                "research_results": research_result,
                "next_step": "code_generation"
            }

        except Exception as e:
            logger.error(f"Error during research: {e}")
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
        for i, feature in enumerate(feature_plan.features, 1):
            lines.append(f"{i}. **{feature.name}**: {feature.description}")
            lines.append(f"   SDK Methods: {', '.join(feature.sdk_methods)}")
            if feature.implementation_notes:
                lines.append(f"   Notes: {feature.implementation_notes}")
            lines.append("")

        return "\n".join(lines)

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

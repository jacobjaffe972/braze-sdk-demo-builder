"""Code Generation Agent - Generate HTML/CSS/JS with Braze SDK.

This agent generates complete landing pages with customer branding.
"""

import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from braze_code_gen.core.models import GeneratedCode
from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.utils.html_template import generate_base_template
from braze_code_gen.prompts.BRAZE_PROMPTS import CODE_GENERATION_AGENT_PROMPT

logger = logging.getLogger(__name__)


class CodeGenerationAgent:
    """Code generation agent for landing pages."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7
    ):
        """Initialize the code generation agent.

        Args:
            model: LLM model to use (use gpt-4o for better code quality)
            temperature: Temperature for generation
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)

    def process(self, state: CodeGenerationState) -> dict:
        """Generate complete HTML landing page with Braze SDK.

        Args:
            state: Current workflow state

        Returns:
            dict: State updates with generated code
        """
        logger.info("=== CODE GENERATION AGENT: Starting code generation ===")

        feature_plan = state["feature_plan"]
        branding_data = state["branding_data"]
        braze_config = state["braze_api_config"]
        research_results = state.get("research_results")

        if not all([feature_plan, branding_data, braze_config]):
            logger.error("Missing required data for code generation")
            return {
                "error": "Missing feature plan, branding, or API config",
                "next_step": "error_handler"
            }

        # Generate base template
        base_template = generate_base_template(
            branding=branding_data,
            braze_config=braze_config,
            page_title=feature_plan.page_title,
            page_description=feature_plan.page_description
        )

        # Format research summary
        research_summary = ""
        if research_results:
            research_summary = research_results.summary or "No research results available"
        else:
            research_summary = "No research was conducted"

        # Format prompt
        prompt = CODE_GENERATION_AGENT_PROMPT.format(
            feature_plan=self._format_feature_plan(feature_plan),
            research_summary=research_summary,
            primary_color=branding_data.colors.primary,
            accent_color=branding_data.colors.accent,
            primary_font=branding_data.typography.primary_font,
            heading_font=branding_data.typography.heading_font,
            base_template="[Base template with Braze SDK initialization and styling]"
        )

        # Generate code
        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Generate the complete HTML landing page.\n\nBase template:\n{base_template}")
            ]

            response = self.llm.invoke(messages)
            html_content = response.content

            # Clean up response (remove markdown code blocks if present)
            html_content = self._clean_html_response(html_content)

            logger.info(f"Generated HTML: {len(html_content)} characters")

            # Create GeneratedCode object
            generated_code = GeneratedCode(
                html=html_content,
                braze_sdk_initialized=True,  # Base template includes initialization
                features_implemented=[f.name for f in feature_plan.features]
            )

            return {
                "generated_code": generated_code,
                "next_step": "validation"
            }

        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return {
                "error": f"Code generation failed: {str(e)}",
                "next_step": "error_handler"
            }

    def _format_feature_plan(self, feature_plan) -> str:
        """Format feature plan for prompt.

        Args:
            feature_plan: SDKFeaturePlan

        Returns:
            str: Formatted feature plan
        """
        lines = [f"**Page**: {feature_plan.page_title}"]
        lines.append(f"**Description**: {feature_plan.page_description}")
        lines.append("\n**Features to Implement:**\n")

        for i, feature in enumerate(feature_plan.features, 1):
            lines.append(f"{i}. **{feature.name}**")
            lines.append(f"   Description: {feature.description}")
            lines.append(f"   SDK Methods: {', '.join(feature.sdk_methods)}")
            if feature.implementation_notes:
                lines.append(f"   Notes: {feature.implementation_notes}")
            lines.append(f"   Priority: {feature.priority}")
            lines.append("")

        return "\n".join(lines)

    def _clean_html_response(self, html_content: str) -> str:
        """Clean HTML response from LLM.

        Args:
            html_content: Raw HTML from LLM

        Returns:
            str: Cleaned HTML
        """
        # Remove markdown code blocks
        if "```html" in html_content:
            html_content = html_content.split("```html")[1]
            if "```" in html_content:
                html_content = html_content.split("```")[0]

        elif "```" in html_content:
            # Generic code block
            parts = html_content.split("```")
            if len(parts) >= 2:
                html_content = parts[1]

        # Strip whitespace
        html_content = html_content.strip()

        # Ensure starts with DOCTYPE
        if not html_content.upper().startswith("<!DOCTYPE"):
            if html_content.upper().startswith("<HTML"):
                html_content = "<!DOCTYPE html>\n" + html_content

        return html_content

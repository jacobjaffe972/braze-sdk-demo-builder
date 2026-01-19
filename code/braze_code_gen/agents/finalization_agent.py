"""Finalization Agent - Polish and export landing page.

This agent adds final polish and exports the landing page to HTML.
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig

from braze_code_gen.core.llm_factory import create_llm
from braze_code_gen.core.models import GeneratedCode, ModelTier
from braze_code_gen.core.state import CodeGenerationState, mark_complete
from braze_code_gen.utils.exporter import HTMLExporter
from braze_code_gen.utils.html_utils import clean_html_response
from braze_code_gen.prompts.BRAZE_PROMPTS import FINALIZATION_AGENT_PROMPT

logger = logging.getLogger(__name__)


class FinalizationAgent:
    """Finalization agent for polishing and exporting."""

    def __init__(
        self,
        model_tier: ModelTier = ModelTier.PRIMARY,
        temperature: float = 0.3,
        export_dir: str = "/tmp/braze_exports"
    ):
        """Initialize the finalization agent.

        Args:
            model_tier: LLM tier to use (primary/research/validation)
            temperature: Temperature for generation
            export_dir: Directory for exported files
        """
        self.llm = create_llm(tier=model_tier, temperature=temperature)
        self.exporter = HTMLExporter(export_dir=export_dir)

    def process(self, state: CodeGenerationState, config: RunnableConfig) -> dict:
        """Finalize and export landing page.

        Args:
            state: Current workflow state
            config: Optional LangGraph config with callbacks for streaming

        Returns:
            dict: State updates with export path and completion
        """
        logger.info("=== FINALIZATION AGENT: Starting finalization ===")

        generated_code = state["generated_code"]
        validation_report = state.get("validation_report")
        feature_plan = state["feature_plan"]
        branding_data = state["branding_data"]

        if not all([generated_code, feature_plan, branding_data]):
            logger.error("Missing required data for finalization")
            return {
                "error": "Missing generated code, feature plan, or branding",
                "is_complete": True,
                "next_step": "end"
            }

        # Polish the code
        polished_html = self._polish_code(
            generated_code,
            validation_report,
            config=config
        )

        # Export to file
        try:
            export_path = self.exporter.export_landing_page(
                html_content=polished_html,
                branding_data=branding_data,
                feature_plan=feature_plan
            )

            logger.info(f"Exported landing page to: {export_path}")

            # Create success message
            success_message = self._create_success_message(
                export_path,
                feature_plan,
                branding_data,
                validation_report
            )

            # Return completion
            return {
                **mark_complete(str(export_path)),
                "messages": [AIMessage(content=success_message)],
                "generated_code": GeneratedCode(
                    html=polished_html,
                    braze_sdk_initialized=generated_code.braze_sdk_initialized,
                    features_implemented=generated_code.features_implemented
                )
            }

        except Exception as e:
            logger.error(f"Error exporting landing page: {e}")
            return {
                "error": f"Export failed: {str(e)}",
                "is_complete": True,
                "next_step": "end"
            }

    def _polish_code(
        self,
        generated_code: GeneratedCode,
        validation_report,
        config: RunnableConfig
    ) -> str:
        """Polish the generated code.

        Args:
            generated_code: GeneratedCode
            validation_report: ValidationReport (optional)
            config: Optional LangGraph config with callbacks for streaming

        Returns:
            str: Polished HTML
        """
        # Format validation status
        validation_status = "Unknown"
        if validation_report:
            validation_status = "Passed" if validation_report.passed else "Failed (but proceeding)"

        # Format code summary
        final_code_summary = f"""
HTML length: {len(generated_code.html)} characters
Features implemented: {', '.join(generated_code.features_implemented)}
Braze SDK initialized: {generated_code.braze_sdk_initialized}
"""

        # Create polishing prompt
        prompt = FINALIZATION_AGENT_PROMPT.format(
            final_code_summary=final_code_summary,
            validation_status=validation_status
        )

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Polish this HTML for production:\n\n{generated_code.html}")
            ]

            # Pass config to LLM invoke for token streaming callbacks
            response = self.llm.invoke(messages, config=config)
            polished_html = response.content

            # Clean up response
            polished_html = clean_html_response(polished_html)

            logger.info(f"Polished HTML: {len(polished_html)} characters")

            return polished_html

        except Exception as e:
            logger.error(f"Error polishing code: {e}")
            # Return original if polishing fails
            return generated_code.html


    def _create_success_message(
        self,
        export_path,
        feature_plan,
        branding_data,
        validation_report
    ) -> str:
        """Create success message for user.

        Args:
            export_path: Path to exported file
            feature_plan: SDKFeaturePlan
            branding_data: BrandingData
            validation_report: ValidationReport (optional)

        Returns:
            str: Success message
        """
        lines = []

        lines.append("# ✅ Landing Page Generated Successfully!")
        lines.append("")

        # Export info
        lines.append(f"**Exported to**: `{export_path}`")
        lines.append("")

        # Features implemented
        lines.append("## Features Implemented")
        for i, feature in enumerate(feature_plan.features, 1):
            lines.append(f"{i}. **{feature.name}**: {feature.description}")
        lines.append("")

        # Branding info
        lines.append("## Customer Branding Applied")
        if branding_data.extraction_success:
            lines.append(f"- **Website**: {branding_data.website_url}")
            lines.append(f"- **Primary Color**: {branding_data.colors.primary}")
            lines.append(f"- **Accent Color**: {branding_data.colors.accent}")
            lines.append(f"- **Font**: {branding_data.typography.primary_font}")
        else:
            lines.append("- Used default Braze branding (website analysis failed)")
        lines.append("")

        # Validation status
        if validation_report:
            lines.append("## Validation Status")
            if validation_report.passed:
                lines.append("✅ All validation checks passed")
            else:
                lines.append("⚠️ Some validation issues detected (exported anyway)")
                if validation_report.issues:
                    lines.append(f"- {len(validation_report.issues)} issues found")
            lines.append("")

        # Next steps
        lines.append("## Next Steps")
        lines.append("1. Open the exported HTML file in your browser")
        lines.append("2. Test all features and interactions")
        lines.append("3. Verify Braze SDK connection (check status indicator)")
        lines.append("4. Customize further if needed")

        return "\n".join(lines)

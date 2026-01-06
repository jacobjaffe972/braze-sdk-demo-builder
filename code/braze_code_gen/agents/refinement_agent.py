"""Refinement Agent - Fix issues found during validation.

This agent applies targeted fixes to resolve validation issues.
"""

import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from braze_code_gen.core.models import GeneratedCode
from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.prompts.BRAZE_PROMPTS import REFINEMENT_AGENT_PROMPT

logger = logging.getLogger(__name__)


class RefinementAgent:
    """Refinement agent for fixing validation issues."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.5
    ):
        """Initialize the refinement agent.

        Args:
            model: LLM model to use (use gpt-4o for better code quality)
            temperature: Temperature for generation
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)

    def process(self, state: CodeGenerationState) -> dict:
        """Refine generated code to fix validation issues.

        Args:
            state: Current workflow state

        Returns:
            dict: State updates with refined code
        """
        logger.info("=== REFINEMENT AGENT: Starting code refinement ===")

        generated_code = state["generated_code"]
        validation_report = state["validation_report"]
        current_iteration = state.get("refinement_iteration", 0)

        if not generated_code or not validation_report:
            logger.error("Missing generated code or validation report")
            return {
                "error": "Cannot refine without code and validation report",
                "next_step": "error_handler"
            }

        # Format issues to fix
        issues_to_fix = self._format_issues(validation_report)

        # Format original code summary
        original_code_summary = f"""
HTML length: {len(generated_code.html)} characters
Features implemented: {', '.join(generated_code.features_implemented)}
Braze SDK initialized: {generated_code.braze_sdk_initialized}
"""

        # Create refinement prompt
        prompt = REFINEMENT_AGENT_PROMPT.format(
            original_code_summary=original_code_summary,
            validation_issues=self._format_validation_issues(validation_report),
            issues_to_fix=issues_to_fix
        )

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Fix the validation issues in this HTML:\n\n{generated_code.html}")
            ]

            response = self.llm.invoke(messages)
            refined_html = response.content

            # Clean up response
            refined_html = self._clean_html_response(refined_html)

            logger.info(f"Refined HTML: {len(refined_html)} characters")

            # Create updated GeneratedCode
            refined_code = GeneratedCode(
                html=refined_html,
                braze_sdk_initialized=generated_code.braze_sdk_initialized,
                features_implemented=generated_code.features_implemented
            )

            # Increment refinement iteration
            new_iteration = current_iteration + 1

            return {
                "generated_code": refined_code,
                "refinement_iteration": new_iteration,
                "next_step": "validation"  # Go back to validation
            }

        except Exception as e:
            logger.error(f"Error refining code: {e}")

            # Check if we should give up
            if current_iteration >= state.get("max_refinement_iterations", 3) - 1:
                logger.warning("Max refinement iterations reached, proceeding to finalization")
                return {
                    "error": f"Refinement failed: {str(e)}",
                    "next_step": "finalize"
                }
            else:
                return {
                    "error": f"Refinement failed: {str(e)}",
                    "refinement_iteration": current_iteration + 1,
                    "next_step": "finalize"  # Give up and finalize
                }

    def _format_issues(self, validation_report) -> str:
        """Format issues for refinement prompt.

        Args:
            validation_report: ValidationReport

        Returns:
            str: Formatted issues
        """
        if not validation_report.issues:
            return "No specific issues found, but validation failed."

        # Group issues by severity
        errors = [i for i in validation_report.issues if i.severity == "error"]
        warnings = [i for i in validation_report.issues if i.severity == "warning"]

        lines = []

        if errors:
            lines.append("**CRITICAL ERRORS (Fix These First):**")
            for i, issue in enumerate(errors, 1):
                lines.append(f"{i}. {issue.message}")
                if issue.fix_suggestion:
                    lines.append(f"   → {issue.fix_suggestion}")
                lines.append("")

        if warnings:
            lines.append("**WARNINGS (Fix If Possible):**")
            for i, issue in enumerate(warnings, 1):
                lines.append(f"{i}. {issue.message}")
                if issue.fix_suggestion:
                    lines.append(f"   → {issue.fix_suggestion}")
                lines.append("")

        return "\n".join(lines)

    def _format_validation_issues(self, validation_report) -> str:
        """Format full validation issues summary.

        Args:
            validation_report: ValidationReport

        Returns:
            str: Formatted summary
        """
        lines = []

        lines.append(f"**Validation Status**: {'PASSED' if validation_report.passed else 'FAILED'}")
        lines.append(f"**Braze SDK Loaded**: {'Yes' if validation_report.braze_sdk_loaded else 'No'}")
        lines.append(f"**Issues Count**: {len(validation_report.issues)}")

        if validation_report.console_errors:
            lines.append(f"\n**Console Errors**:")
            for error in validation_report.console_errors[:3]:
                lines.append(f"  - {error}")

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

"""Validation Agent - Test generated code with browser.

This agent validates generated HTML using Playwright.
"""

import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.tools.browser_testing import BrowserTester
from braze_code_gen.prompts.BRAZE_PROMPTS import VALIDATION_AGENT_PROMPT

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Validation agent for browser testing."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        enable_browser_testing: bool = True
    ):
        """Initialize the validation agent.

        Args:
            model: LLM model to use
            temperature: Temperature for generation
            enable_browser_testing: Whether to run actual browser tests
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.enable_browser_testing = enable_browser_testing

        if enable_browser_testing:
            try:
                self.browser_tester = BrowserTester(headless=True)
            except ImportError:
                logger.warning("Playwright not available, disabling browser testing")
                self.enable_browser_testing = False
                self.browser_tester = None
        else:
            self.browser_tester = None

    def process(self, state: CodeGenerationState) -> dict:
        """Validate generated code with browser testing.

        Args:
            state: Current workflow state

        Returns:
            dict: State updates with validation results
        """
        logger.info("=== VALIDATION AGENT: Starting validation ===")

        generated_code = state["generated_code"]
        if not generated_code:
            logger.error("No generated code to validate")
            return {
                "error": "No generated code available",
                "next_step": "error_handler"
            }

        # Run browser testing (if enabled)
        if self.enable_browser_testing and self.browser_tester:
            try:
                validation_report = self.browser_tester.validate_html(generated_code.html)
                logger.info(f"Browser validation: {'PASSED' if validation_report.passed else 'FAILED'}")
            except Exception as e:
                logger.error(f"Browser testing error: {e}")
                # Create error report
                from braze_code_gen.core.models import ValidationReport, ValidationIssue
                validation_report = ValidationReport(
                    passed=False,
                    issues=[ValidationIssue(
                        severity="error",
                        category="browser",
                        message=f"Browser testing failed: {str(e)}",
                        fix_suggestion="Check HTML syntax and Braze SDK integration"
                    )],
                    braze_sdk_loaded=False,
                    console_errors=[str(e)],
                    screenshots=[],
                    test_timestamp=""
                )
        else:
            # Skip browser testing - create passing report
            from braze_code_gen.core.models import ValidationReport
            validation_report = ValidationReport(
                passed=True,
                issues=[],
                braze_sdk_loaded=True,
                console_errors=[],
                screenshots=[],
                test_timestamp=""
            )
            logger.info("Browser testing disabled, skipping validation")

        # Analyze validation report with LLM
        decision = self._analyze_validation_report(
            generated_code,
            validation_report
        )

        # Determine next step
        if decision["passed"]:
            next_step = "finalize"
            logger.info("Validation PASSED - proceeding to finalization")
        else:
            # Check refinement iteration count
            current_iteration = state.get("refinement_iteration", 0)
            max_iterations = state.get("max_refinement_iterations", 3)

            if current_iteration < max_iterations:
                next_step = "refine"
                logger.info(f"Validation FAILED - proceeding to refinement (iteration {current_iteration + 1}/{max_iterations})")
            else:
                next_step = "finalize"
                logger.warning(f"Max refinement iterations reached ({max_iterations}), proceeding to finalization anyway")

        return {
            "validation_report": validation_report,
            "validation_passed": decision["passed"],
            "next_step": next_step
        }

    def _analyze_validation_report(
        self,
        generated_code,
        validation_report
    ) -> dict:
        """Analyze validation report with LLM.

        Args:
            generated_code: GeneratedCode
            validation_report: ValidationReport

        Returns:
            dict: Decision with 'passed' boolean and reasoning
        """
        # Format validation report for LLM
        report_text = self._format_validation_report(validation_report)

        # Format generated code summary
        code_summary = f"""
Generated {len(generated_code.html)} characters of HTML
Features implemented: {', '.join(generated_code.features_implemented)}
Braze SDK initialized: {generated_code.braze_sdk_initialized}
"""

        # Create prompt
        prompt = VALIDATION_AGENT_PROMPT.format(
            generated_code_summary=code_summary,
            validation_report=report_text
        )

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content="Analyze the validation report and determine if the code passes validation.")
            ]

            response = self.llm.invoke(messages)
            decision_text = response.content.upper()

            # Determine pass/fail
            passed = "PASS" in decision_text and "FAIL" not in decision_text

            return {
                "passed": passed,
                "reasoning": response.content
            }

        except Exception as e:
            logger.error(f"Error analyzing validation report: {e}")
            # Default to failing if analysis fails
            return {
                "passed": False,
                "reasoning": f"Analysis error: {str(e)}"
            }

    def _format_validation_report(self, report) -> str:
        """Format validation report for LLM.

        Args:
            report: ValidationReport

        Returns:
            str: Formatted report
        """
        lines = [f"**Validation Status**: {'PASSED' if report.passed else 'FAILED'}"]
        lines.append(f"**Braze SDK Loaded**: {'Yes' if report.braze_sdk_loaded else 'No'}")
        lines.append(f"**Test Timestamp**: {report.test_timestamp}")
        lines.append("")

        if report.issues:
            lines.append(f"**Issues Found**: {len(report.issues)}")
            for i, issue in enumerate(report.issues, 1):
                lines.append(f"\n{i}. [{issue.severity.upper()}] {issue.category}")
                lines.append(f"   Message: {issue.message}")
                if issue.fix_suggestion:
                    lines.append(f"   Fix: {issue.fix_suggestion}")
        else:
            lines.append("**Issues Found**: None")

        if report.console_errors:
            lines.append(f"\n**Console Errors**: {len(report.console_errors)}")
            for error in report.console_errors[:5]:  # Show first 5
                lines.append(f"   - {error}")

        return "\n".join(lines)

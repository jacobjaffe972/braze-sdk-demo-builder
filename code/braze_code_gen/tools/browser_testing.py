"""Browser testing tool using Playwright.

This module provides functionality to test generated landing pages in a headless browser.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available. Install with: pip install playwright && playwright install")

from braze_code_gen.core.models import ValidationReport, ValidationIssue

logger = logging.getLogger(__name__)


class BrowserTester:
    """Browser testing tool for validating generated HTML."""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 10000,
        screenshot_dir: Optional[str] = None
    ):
        """Initialize browser tester.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
            screenshot_dir: Directory for screenshots (optional)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required. Install with: pip install playwright && playwright install")

        self.headless = headless
        self.timeout = timeout
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else None

        if self.screenshot_dir:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def validate_html(self, html_content: str) -> ValidationReport:
        """Validate HTML content in browser.

        Args:
            html_content: HTML content to validate

        Returns:
            ValidationReport: Validation results

        Example:
            >>> tester = BrowserTester()
            >>> report = tester.validate_html("<html>...</html>")
            >>> if report.passed:
            ...     print("Validation passed!")
        """
        logger.info("Starting browser validation...")
        issues: List[ValidationIssue] = []
        console_errors: List[str] = []
        screenshots: List[str] = []
        braze_sdk_loaded = False

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(ignore_https_errors=True)

            # Set up console listener
            def handle_console(msg):
                if msg.type in ['error', 'warning']:
                    console_errors.append(f"[{msg.type}] {msg.text}")
                    logger.debug(f"Console {msg.type}: {msg.text}")

            page.on('console', handle_console)

            try:
                # Write HTML to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(html_content)
                    temp_file = f.name

                # Load page
                page.goto(f'file://{temp_file}', timeout=self.timeout)

                # Wait for page to load
                page.wait_for_load_state('networkidle', timeout=self.timeout)

                # Check for Braze SDK
                braze_sdk_loaded = self._check_braze_sdk(page)

                # Validate HTML structure
                html_issues = self._validate_html_structure(page)
                issues.extend(html_issues)

                # Validate Braze SDK initialization
                if braze_sdk_loaded:
                    sdk_issues = self._validate_braze_sdk_init(page)
                    issues.extend(sdk_issues)
                else:
                    issues.append(ValidationIssue(
                        severity="error",
                        category="braze_sdk",
                        message="Braze SDK not detected on page",
                        fix_suggestion="Ensure Braze SDK script is included and initialized"
                    ))

                # Take screenshot
                if self.screenshot_dir:
                    screenshot_path = self._take_screenshot(page)
                    if screenshot_path:
                        screenshots.append(screenshot_path)

                # Clean up temp file
                Path(temp_file).unlink()

            except Exception as e:
                logger.error(f"Browser validation error: {str(e)}")
                issues.append(ValidationIssue(
                    severity="error",
                    category="browser",
                    message=f"Browser error: {str(e)}",
                    fix_suggestion="Check HTML syntax and JavaScript errors"
                ))

            finally:
                browser.close()

        # Determine if validation passed
        has_errors = any(issue.severity == "error" for issue in issues)
        passed = not has_errors and braze_sdk_loaded

        return ValidationReport(
            passed=passed,
            issues=issues,
            braze_sdk_loaded=braze_sdk_loaded,
            console_errors=console_errors,
            screenshots=screenshots,
            test_timestamp=datetime.now().isoformat()
        )

    def _check_braze_sdk(self, page: Page) -> bool:
        """Check if Braze SDK is loaded.

        Args:
            page: Playwright page

        Returns:
            bool: Whether Braze SDK is loaded
        """
        try:
            # Check for braze global object
            result = page.evaluate("typeof window.braze !== 'undefined'")
            return bool(result)
        except Exception as e:
            logger.warning(f"Error checking Braze SDK: {e}")
            return False

    def _validate_html_structure(self, page: Page) -> List[ValidationIssue]:
        """Validate HTML structure.

        Args:
            page: Playwright page

        Returns:
            List[ValidationIssue]: List of issues found
        """
        issues = []

        try:
            # Check for required elements
            has_title = page.locator('title').count() > 0
            if not has_title:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="html",
                    message="Missing <title> tag",
                    fix_suggestion="Add <title> tag to <head>"
                ))

            # Check for viewport meta tag (important for mobile)
            has_viewport = page.locator('meta[name="viewport"]').count() > 0
            if not has_viewport:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="html",
                    message="Missing viewport meta tag",
                    fix_suggestion='Add <meta name="viewport" content="width=device-width, initial-scale=1"> to <head>'
                ))

            # Check for forms
            form_count = page.locator('form').count()
            if form_count > 0:
                # Validate forms have submit handlers
                for i in range(form_count):
                    form = page.locator('form').nth(i)
                    has_action = form.get_attribute('action') is not None
                    has_submit_button = form.locator('button[type="submit"], input[type="submit"]').count() > 0

                    if not has_action and not has_submit_button:
                        issues.append(ValidationIssue(
                            severity="info",
                            category="html",
                            message=f"Form {i+1} may not have proper submission handling",
                            fix_suggestion="Add onsubmit handler or action attribute to form"
                        ))

        except Exception as e:
            logger.error(f"Error validating HTML structure: {e}")

        return issues

    def _validate_braze_sdk_init(self, page: Page) -> List[ValidationIssue]:
        """Validate Braze SDK initialization.

        Args:
            page: Playwright page

        Returns:
            List[ValidationIssue]: List of issues found
        """
        issues = []

        try:
            # Check if Braze is initialized
            is_initialized = page.evaluate("""
                window.braze &&
                typeof window.braze.initialize === 'function' &&
                typeof window.braze.openSession === 'function'
            """)

            if not is_initialized:
                issues.append(ValidationIssue(
                    severity="error",
                    category="braze_sdk",
                    message="Braze SDK not properly initialized",
                    fix_suggestion="Call braze.initialize() with API key and SDK endpoint"
                ))

            # Check if session is opened
            try:
                session_opened = page.evaluate("window.braze.isSessionOpen && window.braze.isSessionOpen()")
                if not session_opened:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="braze_sdk",
                        message="Braze session not opened",
                        fix_suggestion="Call braze.openSession() after initialization"
                    ))
            except:
                # isSessionOpen might not exist in all SDK versions
                pass

        except Exception as e:
            logger.error(f"Error validating Braze SDK: {e}")
            issues.append(ValidationIssue(
                severity="error",
                category="braze_sdk",
                message=f"Error checking Braze SDK: {str(e)}",
                fix_suggestion="Verify Braze SDK is loaded and initialized correctly"
            ))

        return issues

    def _take_screenshot(self, page: Page) -> Optional[str]:
        """Take screenshot of page.

        Args:
            page: Playwright page

        Returns:
            Optional[str]: Path to screenshot file
        """
        if not self.screenshot_dir:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshot_dir / f"validation_{timestamp}.png"
            page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None

    def test_interactions(self, html_content: str, interactions: List[str]) -> ValidationReport:
        """Test specific user interactions.

        Args:
            html_content: HTML content
            interactions: List of CSS selectors to click

        Returns:
            ValidationReport: Validation results with interaction testing

        Example:
            >>> tester = BrowserTester()
            >>> report = tester.test_interactions(
            ...     html_content,
            ...     interactions=["#subscribe-btn", ".push-permission-btn"]
            ... )
        """
        issues = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(ignore_https_errors=True)

            try:
                # Load page
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(html_content)
                    temp_file = f.name

                page.goto(f'file://{temp_file}', timeout=self.timeout)
                page.wait_for_load_state('networkidle', timeout=self.timeout)

                # Test interactions
                for selector in interactions:
                    try:
                        element = page.locator(selector)
                        if element.count() == 0:
                            issues.append(ValidationIssue(
                                severity="error",
                                category="interaction",
                                message=f"Element not found: {selector}",
                                fix_suggestion=f"Ensure element with selector '{selector}' exists"
                            ))
                            continue

                        # Click element
                        element.click()
                        page.wait_for_timeout(500)  # Wait for any animations

                        logger.info(f"Successfully clicked: {selector}")

                    except Exception as e:
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="interaction",
                            message=f"Error clicking {selector}: {str(e)}",
                            fix_suggestion="Check if element is visible and clickable"
                        ))

                # Clean up
                Path(temp_file).unlink()

            finally:
                browser.close()

        return ValidationReport(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            braze_sdk_loaded=True,  # Assume checked elsewhere
            console_errors=[],
            screenshots=[],
            test_timestamp=datetime.now().isoformat()
        )

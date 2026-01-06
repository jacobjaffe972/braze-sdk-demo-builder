"""Lead Agent - Feature planning and branding extraction.

This agent analyzes user requests, extracts website URLs, and creates feature plans.
"""

import re
import logging
from typing import Optional, Dict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from braze_code_gen.core.models import (
    SDKFeaturePlan,
    SDKFeature,
    BrandingData,
)
from braze_code_gen.core.state import CodeGenerationState
from braze_code_gen.tools.website_analyzer import WebsiteAnalyzer
from braze_code_gen.prompts.BRAZE_PROMPTS import format_lead_agent_prompt

logger = logging.getLogger(__name__)


class LeadAgent:
    """Lead agent for feature planning and branding extraction."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ):
        """Initialize the lead agent.

        Args:
            model: LLM model to use
            temperature: Temperature for generation
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.website_analyzer = WebsiteAnalyzer()

    def process(self, state: CodeGenerationState) -> dict:
        """Process user input to create feature plan with branding.

        Args:
            state: Current workflow state

        Returns:
            dict: State updates with feature plan and branding data
        """
        logger.info("=== LEAD AGENT: Starting feature planning ===")

        # Get user message
        user_message = state["messages"][-1].content

        # Extract website URL from message (if not already provided)
        customer_website_url = state.get("customer_website_url")
        if not customer_website_url:
            customer_website_url = self._extract_url_from_message(user_message)
            logger.info(f"Extracted URL from message: {customer_website_url}")

        # Analyze website for branding (if URL provided)
        branding_data = None
        if customer_website_url:
            try:
                branding_data = self.website_analyzer.analyze_website(customer_website_url)
                logger.info(f"Branding extraction: {'Success' if branding_data.extraction_success else 'Failed (using defaults)'}")
            except Exception as e:
                logger.error(f"Error analyzing website: {e}")
                branding_data = None

        # Create feature plan using LLM
        feature_plan = self._create_feature_plan(
            user_message,
            customer_website_url,
            branding_data
        )

        logger.info(f"Created feature plan with {len(feature_plan.features)} features")

        # Return state updates
        return {
            "customer_website_url": customer_website_url,
            "branding_data": branding_data,
            "feature_plan": feature_plan,
            "next_step": "research"
        }

    def _extract_url_from_message(self, message: str) -> Optional[str]:
        """Extract website URL from user message.

        Args:
            message: User message

        Returns:
            Optional[str]: Extracted URL or None
        """
        # Pattern for URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, message)

        if urls:
            return urls[0]

        # Try to find domain-like patterns
        domain_pattern = r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
        domains = re.findall(domain_pattern, message)

        if domains:
            # Filter out common non-domain words
            filtered = [d for d in domains if d not in ['example.com', 'test.com']]
            if filtered:
                return f"https://{filtered[0]}"

        return None

    def _create_feature_plan(
        self,
        user_request: str,
        customer_website_url: Optional[str],
        branding_data: Optional[BrandingData]
    ) -> SDKFeaturePlan:
        """Create feature plan using LLM.

        Args:
            user_request: User's feature request
            customer_website_url: Customer website URL
            branding_data: Extracted branding data

        Returns:
            SDKFeaturePlan: Feature plan
        """
        # Prepare branding data for prompt
        branding_dict = None
        if branding_data:
            branding_dict = {
                'primary_color': branding_data.colors.primary,
                'secondary_color': branding_data.colors.secondary,
                'accent_color': branding_data.colors.accent,
                'background_color': branding_data.colors.background,
                'text_color': branding_data.colors.text,
                'primary_font': branding_data.typography.primary_font,
                'heading_font': branding_data.typography.heading_font,
                'extraction_success': branding_data.extraction_success
            }

        # Format prompt
        prompt = format_lead_agent_prompt(
            user_request=user_request,
            customer_website_url=customer_website_url or "Not provided",
            branding_data=branding_dict
        )

        # Call LLM with structured output
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content="Create the feature plan based on the user request.")
        ]

        try:
            # Use structured output (Pydantic model)
            response = self.llm.with_structured_output(SDKFeaturePlan).invoke(messages)
            return response

        except Exception as e:
            logger.error(f"Error creating feature plan: {e}")
            # Return default plan
            return self._create_default_plan(user_request, customer_website_url)

    def _create_default_plan(
        self,
        user_request: str,
        customer_website_url: Optional[str]
    ) -> SDKFeaturePlan:
        """Create a default feature plan as fallback.

        Args:
            user_request: User's request
            customer_website_url: Website URL

        Returns:
            SDKFeaturePlan: Default feature plan
        """
        # Extract domain name for title
        domain = "Customer"
        if customer_website_url:
            from urllib.parse import urlparse
            parsed = urlparse(customer_website_url)
            domain = parsed.netloc.replace('www.', '').split('.')[0].capitalize()

        return SDKFeaturePlan(
            features=[
                SDKFeature(
                    name="User Tracking",
                    description="Track custom events for user interactions",
                    sdk_methods=["braze.logCustomEvent()"],
                    implementation_notes="Add event tracking to buttons and form submissions",
                    priority=1
                ),
                SDKFeature(
                    name="User Attributes",
                    description="Collect and set user attributes",
                    sdk_methods=["braze.getUser().setEmail()", "braze.getUser().setFirstName()"],
                    implementation_notes="Create a form to collect user information",
                    priority=1
                )
            ],
            page_title=f"Braze SDK Demo - {domain}",
            page_description=f"Interactive Braze SDK demonstration for {domain}",
            branding_constraints="Use customer branding colors and fonts" if customer_website_url else None
        )

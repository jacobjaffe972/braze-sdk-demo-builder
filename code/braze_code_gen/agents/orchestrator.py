"""Main orchestrator for Braze SDK Landing Page Code Generator.

This is the primary entry point for the code generation workflow, implementing
the ChatInterface for compatibility with the reference agent framework.
"""

import logging
from typing import List, Dict, Optional, Generator, Any

from langchain_openai import ChatOpenAI
from opik.integrations.langchain import OpikTracer

from braze_code_gen.core.state import CodeGenerationState, create_initial_state
from braze_code_gen.core.models import BrazeAPIConfig
from braze_code_gen.core.workflow import create_workflow
from braze_code_gen.agents.planning_agent import PlanningAgent
from braze_code_gen.agents.research_agent import ResearchAgent
from braze_code_gen.agents.code_generation_agent import CodeGenerationAgent
from braze_code_gen.agents.validation_agent import ValidationAgent
from braze_code_gen.agents.refinement_agent import RefinementAgent
from braze_code_gen.agents.finalization_agent import FinalizationAgent
from braze_code_gen.tools.website_analyzer import WebsiteAnalyzer
from braze_code_gen.tools.browser_testing import BrowserTester
from braze_code_gen.utils.exporter import HTMLExporter

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for Braze SDK landing page generation.

    This class coordinates the 6-agent workflow:
    1. Planning Agent - Feature planning and branding extraction
    2. Research Agent - Braze documentation queries
    3. Code Generation Agent - HTML/CSS/JS generation
    4. Validation Agent - Browser testing
    5. Refinement Agent - Fix validation issues (up to 3 iterations)
    6. Finalization Agent - Polish and export
    """

    def __init__(
        self,
        braze_api_config: Optional[BrazeAPIConfig] = None,
        enable_browser_testing: bool = True,
        export_dir: str = "/tmp/braze_exports",
        opik_project_name: str = "braze-code-gen"
    ):
        """Initialize the Braze Code Generator.

        Args:
            braze_api_config: Braze API configuration (optional, can be set later)
            enable_browser_testing: Whether to run Playwright browser tests
            export_dir: Directory for exported HTML files
            opik_project_name: Opik project name for tracing
        """
        self.braze_api_config = braze_api_config
        self.enable_browser_testing = enable_browser_testing
        self.export_dir = export_dir
        self.opik_project_name = opik_project_name

        # Browser tester (optional)
        self.browser_tester = None
        if enable_browser_testing:
            try:
                self.browser_tester = BrowserTester(headless=True)
                logger.info("Browser testing enabled")
            except ImportError:
                logger.warning("Playwright not available, disabling browser testing")
                self.enable_browser_testing = False

        # Initialize agents
        self._initialize_agents()

        # Build workflow
        self.workflow = create_workflow(
            planning_agent=self.planning_agent,
            research_agent=self.research_agent,
            code_generation_agent=self.code_generation_agent,
            validation_agent=self.validation_agent,
            refinement_agent=self.refinement_agent,
            finalization_agent=self.finalization_agent
        )

        # Initialize Opik tracer
        self.tracer = None
        try:
            self.tracer = OpikTracer(
                graph=self.workflow.graph.get_graph(xray=True),
                project_name=opik_project_name
            )
            logger.info(f"Opik tracing enabled for project: {opik_project_name}")
        except Exception as e:
            logger.warning(f"Could not initialize Opik tracing: {e}")

        logger.info("Orchestrator initialized successfully")

    def _initialize_agents(self):
        """Initialize all agent instances."""
        from braze_code_gen.core.models import ModelTier

        self.planning_agent = PlanningAgent(
            model_tier=ModelTier.PRIMARY,
            temperature=0.3
        )

        self.research_agent = ResearchAgent(
            model_tier=ModelTier.RESEARCH,
            temperature=0.3
        )

        self.code_generation_agent = CodeGenerationAgent(
            model_tier=ModelTier.PRIMARY,
            temperature=0.7
        )

        self.validation_agent = ValidationAgent(
            model_tier=ModelTier.VALIDATION,
            temperature=0.3,
            enable_browser_testing=self.enable_browser_testing
        )

        self.refinement_agent = RefinementAgent(
            model_tier=ModelTier.PRIMARY,
            temperature=0.5
        )

        self.finalization_agent = FinalizationAgent(
            model_tier=ModelTier.PRIMARY,
            temperature=0.3,
            export_dir=self.export_dir
        )

    def set_braze_api_config(self, api_config: BrazeAPIConfig):
        """Set Braze API configuration.

        Args:
            api_config: Validated Braze API configuration
        """
        self.braze_api_config = api_config
        logger.info("Braze API configuration updated")

    def generate(
        self,
        user_message: str,
        website_url: Optional[str] = None,
        max_refinement_iterations: int = 3
    ) -> Dict[str, Any]:
        """Generate landing page with blocking execution.

        Args:
            user_message: User's feature request
            website_url: Optional customer website URL for branding
            max_refinement_iterations: Maximum refinement attempts

        Returns:
            dict: Final workflow state with generated code and export path
        """
        if not self.braze_api_config:
            raise ValueError("Braze API configuration not set. Call set_braze_api_config() first.")

        logger.info(f"Starting landing page generation: {user_message[:100]}...")

        # Create initial state
        state = create_initial_state(
            user_message=user_message,
            braze_api_config=self.braze_api_config,
            customer_website_url=website_url,
            max_refinement_iterations=max_refinement_iterations
        )

        # Execute workflow
        config = {}
        if self.tracer:
            config["callbacks"] = [self.tracer]

        result = self.workflow.invoke(state, config=config)

        logger.info("Landing page generation complete")
        return result

    def generate_streaming(
        self,
        user_message: str,
        website_url: Optional[str] = None,
        max_refinement_iterations: int = 3
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate landing page with streaming updates.

        This method streams intermediate progress updates as each agent completes,
        providing real-time visibility into the workflow.

        Args:
            user_message: User's feature request
            website_url: Optional customer website URL for branding
            max_refinement_iterations: Maximum refinement attempts

        Yields:
            dict: Update dictionaries:
                - {"type": "node_complete", "node": str, "status": str}
                - {"type": "message", "content": str}
                - {"type": "error", "message": str}
                - {"type": "final_state", "state": dict}
        """
        if not self.braze_api_config:
            yield {
                "type": "error",
                "message": "Braze API configuration not set. Please configure API first."
            }
            return

        logger.info(f"Starting streaming generation: {user_message[:100]}...")

        # Create initial state
        state = create_initial_state(
            user_message=user_message,
            braze_api_config=self.braze_api_config,
            customer_website_url=website_url,
            max_refinement_iterations=max_refinement_iterations
        )

        # Stream workflow updates
        config = {}
        if self.tracer:
            config["callbacks"] = [self.tracer]

        final_state = None
        for update in self.workflow.stream_workflow(state, config=config):
            yield update

            # Track final state
            if update.get("type") == "node_complete" and update.get("node") == "finalization":
                # Workflow is complete, we'll get final state on next iteration
                pass

        # Yield final state for downstream processing
        # Note: In streaming mode, we collect final state from the last chunk
        # For now, we rely on the finalization node's success message
        logger.info("Streaming generation complete")

    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process message using blocking execution (ChatInterface compatibility).

        Args:
            message: User's message
            chat_history: Optional chat history (not used in current implementation)

        Returns:
            str: Success message with export path
        """
        try:
            # Extract website URL from message if present
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, message)
            website_url = urls[0] if urls else None

            # Generate landing page
            result = self.generate(
                user_message=message,
                website_url=website_url
            )

            # Extract export path from result
            export_path = result.get("export_file_path", "Unknown path")

            # Return success message
            return f"""
✅ Landing page generated successfully!

**Export Path**: {export_path}

**Features Implemented**:
{self._format_features(result)}

**Branding**:
{self._format_branding(result)}

Open the HTML file in your browser to test the landing page.
"""

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"

    def _format_features(self, result: Dict[str, Any]) -> str:
        """Format implemented features for display."""
        generated_code = result.get("generated_code")
        if generated_code and generated_code.features_implemented:
            return "\n".join(f"- {f}" for f in generated_code.features_implemented)
        return "- No features listed"

    def _format_branding(self, result: Dict[str, Any]) -> str:
        """Format branding information for display."""
        branding = result.get("branding_data")
        if not branding:
            return "- Default Braze branding used"

        lines = []
        if branding.website_url:
            lines.append(f"- Website: {branding.website_url}")
        if branding.colors:
            lines.append(f"- Primary Color: {branding.colors.primary}")
            lines.append(f"- Accent Color: {branding.colors.accent}")
        if branding.fallback_used:
            lines.append("- (Fallback to default branding - website blocked scraping)")

        return "\n".join(lines) if lines else "- Default Braze branding used"

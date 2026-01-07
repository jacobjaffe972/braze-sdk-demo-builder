"""Workflow orchestration with LangGraph StateGraph.

This module defines the workflow for the Braze Code Generator using
LangGraph's StateGraph pattern with conditional routing and streaming support.
"""

import logging
from typing import Dict, Any, Generator

from langgraph.graph import StateGraph, START, END

from braze_code_gen.core.state import CodeGenerationState

logger = logging.getLogger(__name__)


class BrazeCodeGeneratorWorkflow:
    """Workflow orchestrator for Braze landing page generation."""

    def __init__(
        self,
        lead_agent,
        research_agent,
        code_generation_agent,
        validation_agent,
        refinement_agent,
        finalization_agent
    ):
        """Initialize workflow with agent instances.

        Args:
            lead_agent: LeadAgent instance
            research_agent: ResearchAgent instance
            code_generation_agent: CodeGenerationAgent instance
            validation_agent: ValidationAgent instance
            refinement_agent: RefinementAgent instance
            finalization_agent: FinalizationAgent instance
        """
        self.lead_agent = lead_agent
        self.research_agent = research_agent
        self.code_generation_agent = code_generation_agent
        self.validation_agent = validation_agent
        self.refinement_agent = refinement_agent
        self.finalization_agent = finalization_agent

        # Build the workflow graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph StateGraph workflow.

        Returns:
            Compiled StateGraph
        """
        # Create workflow
        workflow = StateGraph(CodeGenerationState)

        # Add nodes for each agent
        workflow.add_node("lead", self._lead_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("code_generation", self._code_generation_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("refinement", self._refinement_node)
        workflow.add_node("finalization", self._finalization_node)

        # Linear edges for main flow
        workflow.add_edge(START, "lead")
        workflow.add_edge("lead", "research")
        workflow.add_edge("research", "code_generation")
        workflow.add_edge("code_generation", "validation")

        # Conditional routing after validation
        workflow.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {
                "refine": "refinement",
                "finalize": "finalization"
            }
        )

        # Refinement loop back to validation
        workflow.add_edge("refinement", "validation")

        # Finalization ends workflow
        workflow.add_edge("finalization", END)

        return workflow.compile()

    # Node wrapper functions

    def _lead_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Lead agent node - feature planning and branding extraction."""
        logger.info("Executing lead agent node")
        return self.lead_agent.process(state)

    def _research_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Research agent node - Braze documentation research."""
        logger.info("Executing research agent node")
        return self.research_agent.process(state)

    def _code_generation_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Code generation agent node - HTML/CSS/JS generation."""
        logger.info("Executing code generation agent node")
        return self.code_generation_agent.process(state)

    def _validation_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Validation agent node - browser testing."""
        logger.info("Executing validation agent node")
        return self.validation_agent.process(state)

    def _refinement_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Refinement agent node - fix validation issues."""
        logger.info("Executing refinement agent node")
        return self.refinement_agent.process(state)

    def _finalization_node(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Finalization agent node - polish and export."""
        logger.info("Executing finalization agent node")
        return self.finalization_agent.process(state)

    # Router function

    def _route_after_validation(self, state: CodeGenerationState) -> str:
        """Route after validation based on test results.

        Args:
            state: Current workflow state

        Returns:
            str: Next node name ("refine" or "finalize")
        """
        validation_passed = state.get("validation_passed", False)
        current_iteration = state.get("refinement_iteration", 0)
        max_iterations = state.get("max_refinement_iterations", 3)

        if validation_passed:
            logger.info("Validation passed - routing to finalization")
            return "finalize"

        if current_iteration >= max_iterations:
            logger.warning(
                f"Max refinement iterations ({max_iterations}) reached - "
                "routing to finalization anyway"
            )
            return "finalize"

        logger.info(
            f"Validation failed - routing to refinement "
            f"(iteration {current_iteration + 1}/{max_iterations})"
        )
        return "refine"

    # Execution methods

    def invoke(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Execute workflow with blocking invocation.

        Args:
            state: Initial workflow state

        Returns:
            dict: Final state after workflow completion
        """
        logger.info("Invoking workflow (blocking)")
        return self.graph.invoke(state)

    def stream_workflow(self, state: CodeGenerationState) -> Generator[Dict[str, Any], None, None]:
        """Stream workflow execution with intermediate updates.

        This method streams state updates as each node completes, providing
        real-time progress updates for the UI.

        Args:
            state: Initial workflow state

        Yields:
            dict: Update dictionaries with type and content:
                - {"type": "node_complete", "node": str, "status": str}
                - {"type": "message", "content": str}
                - {"type": "error", "message": str}
        """
        logger.info("Streaming workflow execution")

        try:
            for chunk in self.graph.stream(state):
                # chunk is dict with node name as key
                if not chunk:
                    continue

                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]

                # Yield status update
                yield {
                    "type": "node_complete",
                    "node": node_name,
                    "status": self._format_node_status(node_name, node_output)
                }

                # If there's an error, yield it
                if "error" in node_output and node_output["error"]:
                    yield {
                        "type": "error",
                        "message": node_output["error"]
                    }

                # If there's a message, yield it
                if "messages" in node_output and node_output["messages"]:
                    last_message = node_output["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        yield {
                            "type": "message",
                            "content": last_message.content
                        }

        except Exception as e:
            logger.error(f"Error during workflow streaming: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": f"Workflow error: {str(e)}"
            }

    def _format_node_status(self, node_name: str, output: Dict[str, Any]) -> str:
        """Format node completion status for UI display.

        Args:
            node_name: Name of the completed node
            output: Node output state updates

        Returns:
            str: Formatted status message
        """
        status_messages = {
            "lead": "✓ Feature plan created with customer branding",
            "research": "✓ Braze documentation research complete",
            "code_generation": "✓ Landing page code generated",
            "validation": (
                "✓ Browser validation complete"
                if output.get("validation_passed")
                else "⚠ Validation issues detected, starting refinement"
            ),
            "refinement": f"✓ Code refined (iteration {output.get('refinement_iteration', 0)})",
            "finalization": "✓ Landing page finalized and exported"
        }

        status = status_messages.get(node_name, f"✓ {node_name} complete")

        # Add error context if present
        if "error" in output and output["error"]:
            status += f" (with warnings)"

        return status


def create_workflow(
    lead_agent,
    research_agent,
    code_generation_agent,
    validation_agent,
    refinement_agent,
    finalization_agent
) -> BrazeCodeGeneratorWorkflow:
    """Factory function to create workflow instance.

    Args:
        lead_agent: LeadAgent instance
        research_agent: ResearchAgent instance
        code_generation_agent: CodeGenerationAgent instance
        validation_agent: ValidationAgent instance
        refinement_agent: RefinementAgent instance
        finalization_agent: FinalizationAgent instance

    Returns:
        BrazeCodeGeneratorWorkflow: Configured workflow instance
    """
    return BrazeCodeGeneratorWorkflow(
        lead_agent=lead_agent,
        research_agent=research_agent,
        code_generation_agent=code_generation_agent,
        validation_agent=validation_agent,
        refinement_agent=refinement_agent,
        finalization_agent=finalization_agent
    )

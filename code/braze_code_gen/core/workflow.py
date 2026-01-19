"""Workflow orchestration with LangGraph StateGraph.

This module defines the workflow for the Braze Code Generator using
LangGraph's StateGraph pattern with conditional routing and streaming support.
"""

import logging
from typing import Dict, Any, Generator, Optional

from langgraph.graph import StateGraph, START, END

from braze_code_gen.core.state import CodeGenerationState

logger = logging.getLogger(__name__)


class BrazeCodeGeneratorWorkflow:
    """Workflow orchestrator for Braze landing page generation."""

    def __init__(
        self,
        planning_agent,
        research_agent,
        code_generation_agent,
        validation_agent,
        refinement_agent,
        finalization_agent
    ):
        """Initialize workflow with agent instances.

        Args:
            planning_agent: PlanningAgent instance
            research_agent: ResearchAgent instance
            code_generation_agent: CodeGenerationAgent instance
            validation_agent: ValidationAgent instance
            refinement_agent: RefinementAgent instance
            finalization_agent: FinalizationAgent instance
        """
        self.planning_agent = planning_agent
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

        # Add nodes for each agent (using lambdas to ensure RunnableConfig is properly passed)
        workflow.add_node("planning", lambda state, config: self.planning_agent.process(state, config))
        workflow.add_node("research", lambda state, config: self.research_agent.process(state, config))
        workflow.add_node("code_generation", lambda state, config: self.code_generation_agent.process(state, config))
        workflow.add_node("validation", lambda state, config: self.validation_agent.process(state, config))
        workflow.add_node("refinement", lambda state, config: self.refinement_agent.process(state, config))
        workflow.add_node("finalization", lambda state, config: self.finalization_agent.process(state, config))

        # Linear edges for main flow
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "research")
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

    def invoke(self, state: CodeGenerationState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute workflow with blocking invocation.

        Args:
            state: Initial workflow state
            config: Optional LangGraph config (e.g., callbacks for tracing)

        Returns:
            dict: Final state after workflow completion
        """
        logger.info("Invoking workflow (blocking)")
        return self.graph.invoke(state, config=config)

    def stream_workflow(self, state: CodeGenerationState, config: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """Stream workflow execution with intermediate updates.

        This method streams state updates as each node completes, providing
        real-time progress updates for the UI.

        Args:
            state: Initial workflow state
            config: Optional LangGraph config (e.g., callbacks for tracing)

        Yields:
            dict: Update dictionaries with type and content:
                - {"type": "node_complete", "node": str, "status": str}
                - {"type": "message", "content": str}
                - {"type": "error", "message": str}
        """
        logger.info("Streaming workflow execution")

        final_state = None
        try:
            for chunk in self.graph.stream(state, config=config):
                # chunk is dict with node name as key
                if not chunk:
                    continue

                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]

                # NEW: Yield node_start event BEFORE processing
                yield {
                    "type": "node_start",
                    "node": node_name,
                    "status": f"Starting {node_name}..."
                }

                # Store the latest state
                final_state = node_output

                # Yield status update (existing)
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

            # Yield final state with export path
            if final_state and "export_file_path" in final_state:
                logger.info(f"Yielding complete event with export path: {final_state['export_file_path']}")
                yield {
                    "type": "complete",
                    "export_file_path": final_state["export_file_path"],
                    "branding_data": final_state.get("branding_data"),
                    "generated_code": final_state.get("generated_code")
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
            "planning": "✓ Feature plan created with customer branding",
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
    planning_agent,
    research_agent,
    code_generation_agent,
    validation_agent,
    refinement_agent,
    finalization_agent
) -> BrazeCodeGeneratorWorkflow:
    """Factory function to create workflow instance.

    Args:
        planning_agent: PlanningAgent instance
        research_agent: ResearchAgent instance
        code_generation_agent: CodeGenerationAgent instance
        validation_agent: ValidationAgent instance
        refinement_agent: RefinementAgent instance
        finalization_agent: FinalizationAgent instance

    Returns:
        BrazeCodeGeneratorWorkflow: Configured workflow instance
    """
    return BrazeCodeGeneratorWorkflow(
        planning_agent=planning_agent,
        research_agent=research_agent,
        code_generation_agent=code_generation_agent,
        validation_agent=validation_agent,
        refinement_agent=refinement_agent,
        finalization_agent=finalization_agent
    )

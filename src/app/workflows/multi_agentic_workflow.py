"""Multi-agent workflow for HeliosCommand using LangGraph.

Implements a LangGraph workflow that orchestrates multiple healthcare agents
in a coordinated manner for hospital lookup, medical shop search, and email sending.
"""
import json
import os
from typing import Any, Dict, List, Optional

try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.state import CompiledStateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from app.agents.orchestrator_agent import OrchestratorAgent
from app.workflows.state import HeliosState, get_initial_state


class MultiAgentWorkflow:
    """LangGraph workflow with multi-agent integration for healthcare queries.

    Architecture:
        User Message
             |
             v
        Orchestrator (routes to appropriate agent)
             |
             v
        Tool Result (Hospital / Medical Shop / Email)
             |
             v
        User Response
    """

    def __init__(
        self,
        orchestrator: Optional[OrchestratorAgent] = None,
        conversation_id: Optional[str] = None,
        use_langgraph: bool = True,
    ) -> None:
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.conversation_id = conversation_id or f"helios_{hash(str(os.urandom(8)))}"
        self.use_langgraph = use_langgraph and LANGGRAPH_AVAILABLE
        self.history: List[Dict[str, Any]] = []
        self._state: Optional[HeliosState] = None

        if self.use_langgraph:
            self.memory = MemorySaver()
            self.workflow = self._create_workflow()
            self.thread_id = self.conversation_id
            self.config = {"configurable": {"thread_id": self.thread_id}}

    def _create_workflow(self) -> CompiledStateGraph:
        """Create and compile the LangGraph workflow."""
        workflow = StateGraph(HeliosState)

        # Add orchestrator node
        workflow.add_node("orchestrator", self._orchestrator_node)

        # Add edges
        workflow.add_edge(START, "orchestrator")
        workflow.add_edge("orchestrator", END)

        return workflow.compile(checkpointer=self.memory)

    def _orchestrator_node(self, state: HeliosState) -> HeliosState:
        """Process query through orchestrator agent."""
        user_query = state.get("user_query", "")
        result = self.orchestrator.process_query(user_query)
        
        state["orchestrator_result"] = json.dumps(result, default=str)
        state["turn_count"] = state.get("turn_count", 0) + 1
        
        return state

    def _get_current_state(self) -> HeliosState:
        """Get the current state or initialize a new one."""
        if self._state is None:
            self._state = get_initial_state()
        return self._state

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """Process a query through the workflow."""
        try:
            state = self._get_current_state()

            # Add user message
            state["messages"] = list(state.get("messages", [])) + [
                HumanMessage(content=user_message) if LANGGRAPH_AVAILABLE else {"role": "user", "content": user_message}
            ]
            state["user_query"] = user_message

            if self.use_langgraph:
                final_state = self.workflow.invoke(state, self.config)
            else:
                # Fallback to simple orchestrator call
                result = self.orchestrator.process_query(user_message)
                final_state = state
                final_state["orchestrator_result"] = json.dumps(result, default=str)
                final_state["turn_count"] = state.get("turn_count", 0) + 1

            self._state = dict(final_state)

            # Extract response for display
            response = self._format_response(final_state.get("orchestrator_result", ""))

            # Store in history
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": response})

            return {
                "success": True,
                "response": response,
                "state": final_state,
            }

        except Exception as e:
            return {
                "success": False,
                "response": f"Error: {str(e)}",
                "error": str(e),
            }

    def _format_response(self, result: str) -> str:
        """Format orchestrator result for display."""
        try:
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            if isinstance(data, dict):
                # Extract orchestrator_result nested dict
                if "orchestrator_result" in data:
                    inner = data["orchestrator_result"]
                    if isinstance(inner, dict):
                        if inner.get("success"):
                            nearest = inner.get("nearest")
                            if nearest:
                                return f"Found: {nearest.get('Hospital Name', 'Hospital')} | Distance: {inner.get('distance_km')} km | ETA: {inner.get('eta_minutes')} min"
                            places = inner.get("places", [])
                            if places:
                                return f"Found {len(places)} nearby places. First: {places[0].get('displayName', {}).get('text', 'Place')}"
                            return str(inner.get("error", "Completed"))
                return str(data)
        except Exception:
            pass
        return str(result)

    def chat(self, user_message: str) -> str:
        """Simple chat interface that returns just the response string."""
        result = self.process_query(user_message)
        return result.get("response", "")

    def get_greeting(self) -> str:
        """Get initial greeting."""
        return "Welcome to HeliosCommand! Tell me your location or what you need: nearest hospital, pharmacy nearby, or send an email."

    def reset(self) -> None:
        """Reset the conversation state and start a new one."""
        self._state = None
        self.conversation_id = f"helios_{hash(str(os.urandom(8)))}"
        if self.use_langgraph:
            self.thread_id = self.conversation_id
            self.config = {"configurable": {"thread_id": self.thread_id}}
        self.history = []

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.history

    def get_state(self) -> Optional[HeliosState]:
        """Get the current workflow state."""
        return self._state

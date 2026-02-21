"""Multi-agent workflow for HeliosCommand using LangGraph.

Implements a LangGraph workflow that orchestrates multiple healthcare agents
in a coordinated manner using create_react_agent pattern.
"""

import os
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.nodes.orchestrator_node import OrchestratorNode
from app.utils import get_conversation_store
from app.workflows.state import HeliosState, get_initial_state

logger = structlog.get_logger(__name__)


class MultiAgentWorkflow:
    """LangGraph workflow with multi-agent integration for healthcare queries.

    Architecture:
        User Message
             |
             v
        OrchestratorNode (create_react_agent routes to appropriate agent tool)
             |
             v
        User Response
    """

    def __init__(
        self,
        orchestrator_node: OrchestratorNode,
        conversation_id: Optional[str] = None,
        persist_conversations: bool = True,
    ) -> None:
        self.orchestrator_node = orchestrator_node
        self.conversation_store = get_conversation_store() if persist_conversations else None
        self.persist_conversations = persist_conversations

        self.memory = MemorySaver()
        self.workflow = self._create_workflow()
        self.conversation_id = conversation_id or f"helios_{hash(str(os.urandom(8)))}"
        self.thread_id = self.conversation_id
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self._state: Optional[HeliosState] = None

        self._load_conversation_history()

        logger.info("MultiAgentWorkflow initialized", conversation_id=self.conversation_id)

    def _create_workflow(self) -> CompiledStateGraph:
        """Create and compile the LangGraph workflow."""
        workflow = StateGraph(HeliosState)

        workflow.add_node("orchestrator", self.orchestrator_node.process)

        workflow.add_edge(START, "orchestrator")
        workflow.add_edge("orchestrator", END)

        return workflow.compile(checkpointer=self.memory)

    def _load_conversation_history(self) -> None:
        """Load conversation history from file storage."""
        if not self.conversation_store:
            return
        stored_messages = self.conversation_store.get_messages(self.conversation_id)
        if stored_messages:
            self._state = get_initial_state()
            messages = []
            for msg in stored_messages:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
            self._state["messages"] = messages

            conversation_data = self.conversation_store.load_conversation(self.conversation_id)
            if conversation_data and conversation_data.get("metadata"):
                metadata = conversation_data["metadata"]
                self._state["user_intent"] = metadata.get("user_intent", "unknown")
                self._state["turn_count"] = metadata.get("turn_count", 0)

            logger.info("Loaded conversation history", conversation_id=self.conversation_id, message_count=len(messages))

    def _save_conversation(self) -> None:
        """Save current conversation to file storage."""
        if self._state is None or not self.conversation_store:
            return

        messages: List[Dict[str, Any]] = []
        for msg in self._state.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                if not getattr(msg, "tool_calls", None):
                    messages.append({"role": "assistant", "content": msg.content})

        metadata = {
            "user_intent": self._state.get("user_intent", "unknown"),
            "turn_count": self._state.get("turn_count", 0),
        }

        self.conversation_store.save_conversation(
            self.conversation_id,
            messages,
            metadata,
        )

    def _get_current_state(self) -> HeliosState:
        """Get the current state or initialize a new one."""
        if self._state is None:
            self._state = get_initial_state()
        return self._state

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """Process a query synchronously through the workflow."""
        try:
            logger.info("Processing user message", message=user_message)
            state = self._get_current_state()

            state["messages"] = list(state.get("messages", [])) + [
                HumanMessage(content=user_message)
            ]
            state["user_query"] = user_message

            final_state = self.workflow.invoke(state, self.config)

            self._state = dict(final_state)

            self._save_conversation()

            response = final_state.get("orchestrator_result", "How can I help you today?")

            return {
                "success": True,
                "response": response,
                "state": final_state,
            }

        except Exception as e:
            logger.error("Workflow processing failed", error=str(e))
            return {
                "success": False,
                "response": f"Error: {str(e)}",
                "error": str(e),
            }

    def chat(self, user_message: str) -> str:
        """Simple chat interface that returns just the response string."""
        result = self.process_query(user_message)
        return result.get("response", "How can I help you today?")

    def get_greeting(self) -> str:
        """Get initial greeting from the orchestrator."""
        try:
            model = self.orchestrator_node.orchestrator_agent.model

            response = model.invoke(
                "You are a supportive healthcare assistant called HeliosCommand. "
                "Generate a brief, welcoming greeting for a new user. "
                "Mention you can help find hospitals, pharmacies, or send emails. "
                "Keep it to 1-2 sentences."
            )

            if response and response.content:
                return response.content

            return "Welcome to HeliosCommand! I can help you find nearby hospitals, pharmacies, or send emails."

        except Exception as e:
            logger.error("Failed to get greeting", error=str(e))
            return "Welcome to HeliosCommand! I can help you find nearby hospitals, pharmacies, or send emails."

    def reset(self) -> None:
        """Reset the conversation state and start a new one."""
        self._state = None
        self.conversation_id = f"helios_{hash(str(os.urandom(8)))}"
        self.thread_id = self.conversation_id
        self.config = {"configurable": {"thread_id": self.thread_id}}
        logger.info("Workflow state reset", new_conversation_id=self.conversation_id)

    def get_state(self) -> Optional[HeliosState]:
        """Get the current conversation state."""
        return self._state

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history from state messages."""
        if self._state is None:
            return []
        messages = []
        for msg in self._state.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                if not getattr(msg, "tool_calls", None):
                    messages.append({"role": "assistant", "content": msg.content})
        return messages

"""
Orchestrator Node for the HeliosCommand Workflow.

Wraps the OrchestratorAgent in a LangGraph node that uses create_react_agent
to route user queries to the appropriate agent tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import structlog
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.tools.agent_tools import get_agent_tools, set_current_messages
from app.workflows.state import HeliosState

if TYPE_CHECKING:
    from app.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


def _detect_intent(message: str) -> str:
    """Simple keyword-based intent detection for fast routing."""
    q = message.lower()
    if any(k in q for k in ["hospital", "beds", "icu", "nearest hospital", "admission", "emergency"]):
        return "hospital"
    if any(k in q for k in ["medical shop", "pharmacy", "medical store", "medicines", "drugstore"]):
        return "pharmacy"
    if any(k in q for k in ["email", "send email", "mail"]):
        return "email"
    return "unknown"


def _detect_confirmation(message: str) -> str:
    """Detect if message is a confirmation response.
    
    Returns:
        "yes", "no", or None
    """
    q = message.lower().strip()
    yes_keywords = ["yes", "yeah", "yep", "ok", "okay", "sure", "go ahead", "proceed"]
    no_keywords = ["no", "nope", "not interested", "don't want", "no thanks", "don't"]
    
    if any(q.startswith(k) for k in yes_keywords):
        return "yes"
    if any(q.startswith(k) for k in no_keywords):
        return "no"
    return None


class OrchestratorNode:
    """Node for processing conversations through the orchestrator agent."""

    def __init__(self, orchestrator_agent: BaseAgent) -> None:
        self.orchestrator_agent = orchestrator_agent

    @staticmethod
    def _extract_text(content) -> str:
        """Extract text from content that may be a string or a list of content blocks."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)
        return str(content)

    def process(self, state: HeliosState) -> Dict[str, Any]:
        """Process the current state through the orchestrator using create_react_agent."""
        try:
            # Extract latest user message
            user_msg = ""
            for msg in reversed(state.get("messages", [])):
                if isinstance(msg, HumanMessage):
                    user_msg = msg.content
                    break

            # Check for confirmation responses first
            confirmation = _detect_confirmation(user_msg)
            if confirmation == "yes":
                logger.info("User confirmed, returning acknowledgment")
                return {
                    "messages": state.get("messages", []) + [
                        AIMessage(content="Thanks for confirming. Take care and get well soon!")
                    ],
                    "user_intent": state.get("user_intent", "unknown"),
                    "orchestrator_result": "Thanks for confirming. Take care and get well soon!",
                }
            
            if confirmation == "no":
                logger.info("User declined, routing to email agent")
                # User said no, route to send_email tool
                current_intent = state.get("user_intent", "unknown")
                tools = get_agent_tools()
                prompt = self.orchestrator_agent.get_prompt(state)

                set_current_messages(state.get("messages", []))
                agent = create_react_agent(
                    self.orchestrator_agent.model,
                    tools,
                    prompt=prompt,
                )
                
                result = agent.invoke({"messages": state.get("messages", [])})
                
                orchestrator_response = ""
                ai_message = ""
                
                for msg in reversed(result.get("messages", [])):
                    if isinstance(msg, ToolMessage) and msg.content:
                        orchestrator_response = msg.content
                        break
                    if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                        ai_message = self._extract_text(msg.content)
                
                if orchestrator_response == "":
                    orchestrator_response = ai_message
                
                return {
                    "messages": result.get("messages", []),
                    "user_intent": current_intent,
                    "orchestrator_result": orchestrator_response,
                }

            # Detect intent
            current_intent = state.get("user_intent", "unknown")
            if current_intent == "unknown" and user_msg:
                current_intent = _detect_intent(user_msg)

            # Get tools and prompt from the orchestrator agent
            tools = get_agent_tools()
            prompt = self.orchestrator_agent.get_prompt(state)

            # Make conversation messages available to agent tools
            set_current_messages(state.get("messages", []))

            # Create and invoke the ReAct agent
            agent = create_react_agent(
                self.orchestrator_agent.model,
                tools,
                prompt=prompt,
            )

            result = agent.invoke({"messages": state.get("messages", [])})

            # Extract response from messages
            orchestrator_response = ""
            ai_message = ""

            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, ToolMessage) and msg.content:
                    orchestrator_response = msg.content
                    break
                if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                    ai_message = self._extract_text(msg.content)

            if orchestrator_response == "":
                orchestrator_response = ai_message

            return {
                "messages": result.get("messages", []),
                "user_intent": current_intent,
                "orchestrator_result": orchestrator_response,
            }

        except Exception as e:
            error_msg = f"Orchestrator node failed: {str(e)}"
            logger.error("Orchestrator node failed", error=str(e))
            return {
                "orchestrator_result": None,
                "error": [error_msg],
            }

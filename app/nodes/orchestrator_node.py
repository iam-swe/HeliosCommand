"""
Orchestrator Node for the HeliosCommand Workflow.

Wraps the OrchestratorAgent in a LangGraph node that uses create_react_agent
to route user queries to the appropriate agent tools.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict

import structlog
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.tools.agent_tools import get_agent_tools, set_current_messages
from app.utils.geo import geocode_address, google_earth_link
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

    def _geocode_from_messages(self, state: HeliosState) -> Dict[str, Any]:
        """Extract address from conversation and geocode it.

        Returns dict with user_address, user_latitude, user_longitude, google_earth_link
        (values may be None if geocoding fails).
        """
        # Already geocoded in this session
        if state.get("user_latitude") is not None and state.get("user_longitude") is not None:
            return {
                "user_address": state.get("user_address"),
                "user_latitude": state["user_latitude"],
                "user_longitude": state["user_longitude"],
                "google_earth_link": state.get("google_earth_link"),
            }

        # Collect all human messages to find an address
        all_text = []
        for msg in state.get("messages", []):
            if isinstance(msg, HumanMessage):
                all_text.append(msg.content)

        if not all_text:
            return {"user_address": None, "user_latitude": None, "user_longitude": None, "google_earth_link": None}

        # Use the LLM to extract an address from conversation
        conversation = "\n".join(all_text)
        extract_prompt = (
            "From the following conversation messages extract only the physical "
            "address or location mentioned by the user. Return ONLY the address "
            "string, nothing else. If no address is found return NONE.\n\n"
            f"{conversation}"
        )

        try:
            resp = self.orchestrator_agent.model.invoke(extract_prompt)
            address = resp.content.strip()
            if not address or address.upper() == "NONE":
                logger.info("No address found in conversation")
                return {"user_address": None, "user_latitude": None, "user_longitude": None, "google_earth_link": None}

            logger.info("Extracted address for geocoding", address=address)
            api_key = os.environ.get("GOOGLE_MAPS_KEY", "")
            coords = geocode_address(address, api_key)

            if coords is None:
                logger.warning("Geocoding failed for address", address=address)
                return {"user_address": address, "user_latitude": None, "user_longitude": None, "google_earth_link": None}

            lat, lng = coords
            earth_link = google_earth_link(lat, lng)
            logger.info("Geocoded successfully", lat=lat, lng=lng, earth_link=earth_link)
            return {
                "user_address": address,
                "user_latitude": lat,
                "user_longitude": lng,
                "google_earth_link": earth_link,
            }
        except Exception as e:
            logger.error("Address extraction / geocoding failed", error=str(e))
            return {"user_address": None, "user_latitude": None, "user_longitude": None, "google_earth_link": None}

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
                    "user_address": state.get("user_address"),
                    "user_latitude": state.get("user_latitude"),
                    "user_longitude": state.get("user_longitude"),
                    "google_earth_link": state.get("google_earth_link"),
                }
            
            if confirmation == "no":
                logger.info("User declined, routing to email agent")
                # User said no, route to send_email tool
                current_intent = state.get("user_intent", "unknown")

                # Geocode address before delegating
                geo_data = self._geocode_from_messages(state)
                state["user_address"] = geo_data["user_address"]
                state["user_latitude"] = geo_data["user_latitude"]
                state["user_longitude"] = geo_data["user_longitude"]
                state["google_earth_link"] = geo_data["google_earth_link"]

                tools = get_agent_tools()
                prompt = self.orchestrator_agent.get_prompt(state)

                set_current_messages(state.get("messages", []), state)
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
                    "user_address": state.get("user_address"),
                    "user_latitude": state.get("user_latitude"),
                    "user_longitude": state.get("user_longitude"),
                    "google_earth_link": state.get("google_earth_link"),
                }

            # Detect intent
            current_intent = state.get("user_intent", "unknown")
            if current_intent == "unknown" and user_msg:
                current_intent = _detect_intent(user_msg)

            # Geocode the user's address and store in state
            geo_data = self._geocode_from_messages(state)
            state["user_address"] = geo_data["user_address"]
            state["user_latitude"] = geo_data["user_latitude"]
            state["user_longitude"] = geo_data["user_longitude"]
            state["google_earth_link"] = geo_data["google_earth_link"]

            # Get tools and prompt from the orchestrator agent
            tools = get_agent_tools()
            prompt = self.orchestrator_agent.get_prompt(state)

            # Make conversation messages available to agent tools
            set_current_messages(state.get("messages", []), state)

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
                "user_address": state.get("user_address"),
                "user_latitude": state.get("user_latitude"),
                "user_longitude": state.get("user_longitude"),
                "google_earth_link": state.get("google_earth_link"),
            }

        except Exception as e:
            error_msg = f"Orchestrator node failed: {str(e)}"
            logger.error("Orchestrator node failed", error=str(e))
            return {
                "orchestrator_result": None,
                "error": [error_msg],
            }

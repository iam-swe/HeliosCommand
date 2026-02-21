"""
Agent tools for the HeliosCommand multi-agent system.

These tools wrap the actual agent instances so the orchestrator
delegates to them via create_react_agent rather than duplicating agent logic inline.
"""

import asyncio
from typing import List

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field


class HeliosInput(BaseModel):
    """Input schema for agent tools."""

    message: str = Field(description="The user's message to respond to")
    context: str = Field(description="Conversation context/summary", default="")


_agent_cache = {}

# Module-level storage for current workflow messages and state.
# Set by OrchestratorNode before invoking the react agent so that
# agent tools have access to the full conversation history.
_current_messages: list = []
_current_state: dict = {}


def set_current_messages(messages: list, state: dict | None = None) -> None:
    """Store the current workflow messages and state for agent tools to access."""
    global _current_messages, _current_state
    _current_messages = list(messages)
    _current_state = dict(state) if state else {}


def _get_agent(agent_class):
    """Lazily instantiate and cache agent instances."""
    name = agent_class.__name__
    if name not in _agent_cache:
        _agent_cache[name] = agent_class()
    return _agent_cache[name]


def _create_agent_tool_fn(agent_class):
    """Create a tool function that delegates to an actual agent instance."""

    def agent_tool_fn(message: str, context: str = "") -> str:
        agent = _get_agent(agent_class)
        state = {
            "messages": _current_messages,
            "user_address": _current_state.get("user_address"),
            "user_latitude": _current_state.get("user_latitude"),
            "user_longitude": _current_state.get("user_longitude"),
            "google_earth_link": _current_state.get("google_earth_link"),
        }

        result = asyncio.run(agent.process_query(message, state))

        return result.get(agent.get_result_key(), "")

    return agent_tool_fn


def _build_tools() -> List[BaseTool]:
    """Build all agent tools. Imports are deferred to avoid circular imports."""
    from app.agents.hospital_agent import HospitalAnalyserAgent
    from app.agents.medical_shop_agent import MedicalShopAgent
    from app.agents.email_agent import EmailAgent

    hospital = StructuredTool.from_function(
        func=_create_agent_tool_fn(HospitalAnalyserAgent),
        name="hospital_analyser",
        description="Use when user needs to find the nearest hospital, needs a bed, mentions ICU, emergency, or hospital admission.",
        args_schema=HeliosInput,
    )

    medical_shops = StructuredTool.from_function(
        func=_create_agent_tool_fn(MedicalShopAgent),
        name="medical_shops",
        description="Use when user needs to find a pharmacy, medical shop, or medical store nearby.",
        args_schema=HeliosInput,
    )

    email = StructuredTool.from_function(
        func=_create_agent_tool_fn(EmailAgent),
        name="send_email",
        description="Use when user declines a hospital/pharmacy option or explicitly asks to send an email. Composes and sends email with patient details.",
        args_schema=HeliosInput,
    )

    tools: List[BaseTool] = [hospital, medical_shops, email]

    return tools


def get_agent_tools() -> List[BaseTool]:
    """Get all agent-backed tools for the orchestrator."""
    return _build_tools()

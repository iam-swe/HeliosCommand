"""Hospital analyser agent implementation using LangGraph BaseAgent pattern."""

import os
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel

from app.agents.agent_types import HOSPITAL_AGENT_NAME
from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels
from app.tools.hospital_tools import find_nearest_hospital
from app.workflows.state import HeliosState

logger = structlog.get_logger(__name__)


HOSPITAL_AGENT_PROMPT = """You are a Hospital Analyser Agent for HeliosCommand — a healthcare assistant.

YOUR RESPONSIBILITIES:
1. Help users find the nearest hospital based on their location
2. Present hospital details (name, distance, ETA) clearly
3. Ask for user confirmation before proceeding
4. If the user declines, offer alternatives or send their details via email

You receive hospital lookup results and format them for the user.
Keep responses concise and helpful.

CURRENT STATE:
- Intent: {intent}
"""


class HospitalResponse(BaseModel):
    """Response format for the hospital agent."""
    message: str
    hospital_name: Optional[str] = None
    distance_km: Optional[float] = None
    eta_minutes: Optional[int] = None


class HospitalAnalyserAgent(BaseAgent):
    """Agent for finding and recommending nearby hospitals."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name=HOSPITAL_AGENT_NAME,
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state: Optional[HeliosState] = None) -> str:
        intent = state.get("user_intent", "unknown") if state else "unknown"
        return HOSPITAL_AGENT_PROMPT.format(intent=intent)

    def get_response_format(self) -> type[BaseModel]:
        return HospitalResponse

    def get_result_key(self) -> str:
        return "hospital_analyser_result"

    async def process_query(
        self,
        query: str,
        state: Optional[HeliosState] = None,
    ) -> Dict[str, Any]:
        """Process a hospital lookup query."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        logger.info(
            "HospitalAnalyserAgent.process_query called",
            query=query,
            state_keys=list(state.keys()) if state else None,
        )

        # Perform hospital lookup
        logger.info("Performing hospital lookup", query=query)
        result = find_nearest_hospital(query, api_key)

        if not result.get("success"):
            logger.warning("Hospital lookup failed", result=result)
            error_msg = result.get("error", "Could not find nearby hospitals")
            return {
                "success": False,
                self.get_result_key(): f"Sorry, I couldn't find hospitals near that location: {error_msg}",
                "error": [str(error_msg)],
            }

        nearest = result.get("nearest") or {}
        distance = result.get("distance_km")
        eta = result.get("eta_minutes")
        name = nearest.get("Name") or nearest.get("name") or "Nearest Hospital"

        message = (
            f"I found a hospital near you!\n\n"
            f"**{name}**\n"
            f"- Distance: {distance} km\n"
            f"- ETA: {eta} min\n\n"
            f"Would you like to proceed with this hospital?"
        )

        logger.info("Found nearest hospital", name=name, distance=distance, eta=eta)
        return {
            "success": True,
            self.get_result_key(): message,
            "error": [],
        }

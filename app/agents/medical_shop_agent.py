"""Medical shop search agent implementation using LangGraph BaseAgent pattern."""

import os
import math
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel

from app.agents.agent_types import MEDICAL_SHOP_AGENT_NAME
from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels
from app.tools.hospital_tools import search_medical_shops_nearby
from app.workflows.state import HeliosState

logger = structlog.get_logger(__name__)


MEDICAL_SHOP_PROMPT = """You are a Medical Shop Finder Agent for HeliosCommand — a healthcare assistant.

YOUR RESPONSIBILITIES:
1. Help users find the CLOSEST nearby medical shop or pharmacy
2. Present only the single best result (closest match)
3. Include the name and location clearly
4. Keep response concise and helpful

CURRENT STATE:
- Intent: {intent}
"""


class MedicalShopResponse(BaseModel):
    """Response format for the medical shop agent."""
    message: str
    places_count: int = 0


class MedicalShopAgent(BaseAgent):
    """Agent for finding nearby medical shops and pharmacies."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name=MEDICAL_SHOP_AGENT_NAME,
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state: Optional[HeliosState] = None) -> str:
        intent = state.get("user_intent", "unknown") if state else "unknown"
        return MEDICAL_SHOP_PROMPT.format(intent=intent)

    def get_response_format(self) -> type[BaseModel]:
        return MedicalShopResponse

    def get_result_key(self) -> str:
        return "medical_shops_result"

    @staticmethod
    def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula (in km)."""
        R = 6371.0  # Earth radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def process_query(
        self,
        query: str,
        state: Optional[HeliosState] = None,
    ) -> Dict[str, Any]:
        """Process a medical shop search query."""
        api_key = os.environ.get("GOOGLE_MAPS_KEY")
        logger.info("MedicalShopAgent.process_query called", query=query, api_key_available=bool(api_key))

        # Get pre-computed address and coordinates from state (set by orchestrator)
        address = (state.get("user_address") if state else None) or query
        user_lat = state.get("user_latitude") if state else None
        user_lng = state.get("user_longitude") if state else None

        logger.debug("Calling search_medical_shops_nearby", address=address, user_lat=user_lat, user_lng=user_lng)
        result = search_medical_shops_nearby(address, api_key, user_lat=user_lat, user_lng=user_lng)
        
        logger.debug("search_medical_shops_nearby returned", result_keys=list(result.keys()), success=result.get("success"))

        if not result.get("success"):
            error_msg = result.get("error", "Could not find nearby medical shops")
            logger.warning("Medical shop search failed", error=error_msg, full_result=result)
            return {
                "success": False,
                self.get_result_key(): f"Sorry, I couldn't find medical shops near that location: {error_msg}",
                "error": [str(error_msg)],
            }

        places = result.get("places") or []
        
        if not places:
            logger.info("No places returned from API")
            return {
                "success": True,
                self.get_result_key(): "No medical shops found nearby. Try a different location.",
                "error": [],
            }

        # Get user coordinates
        user_lat = result.get("user_coords", {}).get("lat")
        user_lng = result.get("user_coords", {}).get("lng")
        
        # Calculate distances for all places
        distances = []
        for place in places:
            location = place.get("location", {})
            place_lat = location.get("latitude")
            place_lng = location.get("longitude")
            
            if place_lat and place_lng and user_lat and user_lng:
                distance = self._calculate_distance(user_lat, user_lng, place_lat, place_lng)
                distances.append({
                    "name": place.get("displayName", {}).get("text", "Unknown"),
                    "distance_km": round(distance, 2),
                    "place": place
                })
        
        # Log all distances
        for i, d in enumerate(distances, 1):
            logger.info(f"Place {i} distance", name=d["name"], distance_km=d["distance_km"])
        
        # Get only the closest/first result
        closest_place = places[0]
        closest_distance = distances[0]["distance_km"] if distances else "N/A"
        logger.info("Selected closest place", selected=distances[0]["name"] if distances else "Unknown", distance_km=closest_distance)
        logger.debug("Selected closest place", place_keys=list(closest_place.keys()) if isinstance(closest_place, dict) else "not_dict")
        
        display_name = None
        if isinstance(closest_place.get("displayName"), dict):
            display_name = closest_place["displayName"].get("text")
            logger.debug("Extracted displayName from dict", display_name=display_name)
        
        display_name = display_name or closest_place.get("name") or closest_place.get("vicinity") or "Unknown"
        
        # Get formatted address if available
        formatted_address = closest_place.get("formattedAddress", "")
        
        # Log opening hours if available
        opening_hours = closest_place.get("currentOpeningHours", {})
        logger.info("Place opening hours", opening_hours=opening_hours)
        
        if formatted_address:
            message = f"I found a medical shop near you!\n\n**{display_name}**\n- Address: {formatted_address}\n\nWould you like to proceed?"
        else:
            message = f"I found a medical shop near you!\n\n**{display_name}**\n\nWould you like to proceed?"
        
        logger.info("Medical shop search completed successfully", 
                   selected_place=display_name,
                   message_length=len(message))
        logger.debug("Final message", message=message)
        return {
            "success": True,
            self.get_result_key(): message,
            "error": [],
        }

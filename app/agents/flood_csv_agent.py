"""Flood CSV Analyst Agent.

Reads the flood_detection_data.csv file and analyses it to identify
places with the highest flood risk based on water level, rainfall,
river flow rate, soil moisture, and historical alert status.
"""

import os
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel

from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels

logger = structlog.get_logger(__name__)

# Resolve CSV path relative to this file (sits in app/agents/)
_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # app/
    "flood_detection_data.csv",
)

FLOOD_CSV_AGENT_PROMPT = """You are an expert Flood Risk Analyst.

You will be given time-series sensor data from multiple locations.
Each row contains: timestamp, water_level_m, rainfall_mm_per_hr,
river_flow_rate_m3s, soil_moisture_percent, temperature_celsius,
humidity_percent, alert_status, place, latitude, longitude.

YOUR TASK:
1. Quickly scan the data to identify the places that face the MAXIMUM flood risk.
2. Rank the places from most to least severe based on high water level, rainfall,
   river flow, and "Danger" readings.
3. CRITICAL: Do NOT output step-by-step calculations or list every location.
   ONLY output the final top 5 most severe places to save time.
4. For the top 5 most severe places, provide:
   - Place name
   - Latitude, Longitude
   - Peak water level (m), Peak rainfall (mm/hr)
   - Number of Flood/Danger readings
   - Overall severity: CRITICAL / HIGH / MODERATE
5. Return the analysis in a short, structured format. Keep it extremely brief.

IMPORTANT: Be precise with numbers. Do not fabricate data.

DATA:
{csv_data}
"""


class FloodCSVResponse(BaseModel):
    analysis: str


class FloodCSVAgent(BaseAgent):
    """Analyses flood sensor CSV data to identify high-risk locations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name="flood_csv_agent",
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state=None) -> str:
        csv_data = self._read_csv()
        return FLOOD_CSV_AGENT_PROMPT.format(csv_data=csv_data)

    def get_response_format(self) -> type[BaseModel]:
        return FloodCSVResponse

    def get_result_key(self) -> str:
        return "csv_analysis_result"

    @staticmethod
    def _read_csv() -> str:
        """Read the CSV file and return its contents as a string."""
        try:
            with open(_CSV_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("Flood detection CSV not found", path=_CSV_PATH)
            return "ERROR: flood_detection_data.csv not found."

    async def process_query(
        self,
        query: str = "Analyse flood risk",
        state=None,
    ) -> Dict[str, Any]:
        """Run LLM analysis over the CSV data."""
        try:
            from langchain_core.messages import HumanMessage

            prompt = self.get_prompt(state)
            response = self.model.invoke([
                HumanMessage(content=prompt),
            ])

            result_text = response.content if response else "No analysis produced."
            logger.info("CSV analysis complete", length=len(result_text))

            return {
                "success": True,
                self.get_result_key(): result_text,
                "error": [],
            }
        except Exception as e:
            logger.error("Flood CSV agent failed", error=str(e))
            return {
                "success": False,
                self.get_result_key(): f"CSV analysis failed: {str(e)}",
                "error": [str(e)],
            }

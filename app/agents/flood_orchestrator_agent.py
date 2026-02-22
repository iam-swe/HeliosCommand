"""Flood Alert Orchestrator Agent.

Receives the combined output from both parallel agents (CSV analyst
and web scraper), analyses the data, and decides whether to trigger
a detailed email alert for severe flood situations.
"""

from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels

logger = structlog.get_logger(__name__)


FLOOD_ORCHESTRATOR_PROMPT = """You are the Flood Alert Orchestrator for HeliosCommand.

You have received TWO intelligence reports about flood-prone areas:

--- REPORT 1: CSV SENSOR DATA ANALYSIS (Weight: {csv_weight_pct}%) ---
{csv_analysis}

--- REPORT 2: WEB & SOCIAL MEDIA INTELLIGENCE (Weight: {web_weight_pct}%) ---
{web_scraper}

YOUR TASK:

1. CROSS-REFERENCE both reports according to their Weights:
   - If there is a conflict between the CSV sensor data and Web intelligence,
     give higher priority to the report with the higher weight.
   - For example, if CSV weight is 80%, trust the CSV sensor data over the web news.

2. For each location, assign a FINAL SEVERITY:
   - CRITICAL: Appears in both reports with Flood/Danger status AND active warnings.
   - HIGH: Flood/Danger in sensor data OR active web warnings.
   - MODERATE: Watch/Warning status with no active web reports.
   - LOW: Normal status, no web warnings.
   (Adjust severity boundaries if the higher-weighted report indicates otherwise).

3. COMPILE a final consolidated flood risk report with:
   - Location name, Lat/Long
   - Severity rating (CRITICAL / HIGH / MODERATE / LOW)
   - Evidence summary (from which source)
   - Recommended actions

4. DECISION - SEND EMAIL ALERT:
   If ANY location is rated CRITICAL or HIGH, call the
   send_flood_alert_email tool EXACTLY ONCE.

   IMPORTANT EMAIL RULES:
   a) Call send_flood_alert_email EXACTLY ONCE. Never call it more than once.
   b) The "subject" should be SHORT, e.g.: "FLOOD ALERT: 3 Critical Locations in Chennai"
   c) The "body" must be PLAIN TEXT. Do NOT use markdown (no ** or *).
      Write it as a clean professional letter addressed to
      "Dear Emergency Services and Local Authorities".
   d) List each CRITICAL and HIGH location as a numbered item with:
      name, coordinates, peak water level, peak rainfall, and recommended action.
   e) After the tool returns, provide a brief text summary. Do NOT call the tool again.

   If no location is CRITICAL or HIGH, do NOT call the tool at all.
   Just provide your analysis as text.

5. After finishing (whether or not you sent an email), provide a final
   summary of your findings as plain text. Do NOT call any tool after
   the first email send.

Be thorough and precise. Lives may depend on this analysis.
"""


class FloodOrchestratorResponse(BaseModel):
    """Response format for the flood orchestrator."""
    analysis: str = Field(description="Consolidated flood risk analysis")
    email_triggered: bool = Field(description="Whether an email alert was sent")


class FloodOrchestratorAgent(BaseAgent):
    """Orchestrator that analyses combined flood data and triggers alerts."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name="flood_orchestrator_agent",
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state=None) -> str:
        csv_analysis = ""
        web_scraper = ""
        csv_weight_pct = 50
        web_weight_pct = 50

        if state:
            csv_analysis = state.get("csv_analysis_result", "No CSV analysis available.")
            web_scraper = state.get("web_scraper_result", "No web scraper data available.")
            csv_w = state.get("csv_weight", 0.5)
            web_w = state.get("web_weight", 0.5)
            csv_weight_pct = int(csv_w * 100)
            web_weight_pct = int(web_w * 100)

        return FLOOD_ORCHESTRATOR_PROMPT.format(
            csv_analysis=csv_analysis,
            web_scraper=web_scraper,
            csv_weight_pct=csv_weight_pct,
            web_weight_pct=web_weight_pct,
        )

    def get_response_format(self) -> type[BaseModel]:
        return FloodOrchestratorResponse

    def get_result_key(self) -> str:
        return "orchestrator_result"

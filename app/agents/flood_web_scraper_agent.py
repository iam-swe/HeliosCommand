"""Flood Web Scraper Agent.

Uses Firecrawl to scrape REAL-TIME flood news from established news
websites only. Does NOT read historical data, blogs, social media, or
government archives — only current news articles.

Inspired by the learner_agent scraping pattern in SVCE-Workshop-AI-Agents.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel

from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels

logger = structlog.get_logger(__name__)

# Current date injected into the prompt so the LLM searches for today's news
_TODAY = datetime.now().strftime("%B %d, %Y")  # e.g. "February 22, 2026"
_YEAR = datetime.now().strftime("%Y")

FLOOD_SCRAPER_PROMPT = f"""You are a Real-Time Flood News Analyst.

You have access to a web search tool (firecrawl_flood_search).
Use it to find ONLY current, real-time flood news from established
news websites.

TODAY'S DATE: {_TODAY}

STRICT RULES:
- Search ONLY for news from TODAY or the last 24-48 hours.
- ONLY use reputable NEWS sources. Acceptable sources include:
    * NDTV, The Hindu, Times of India, India Today, Hindustan Times
    * Reuters, BBC, CNN, The Indian Express, News18
    * ANI, PTI, IANS (news agencies)
    * weather.com, AccuWeather, IMD (India Meteorological Department)
- Do NOT use: LinkedIn, Twitter/X, Facebook, blogs, Wikipedia,
  government archives, research papers, or historical databases.
- REJECT any page that contains old/historical flood data.
  Only extract information about floods happening NOW or imminent.

YOUR TASK:
1. Search for real-time flood news using the queries below.
   Call the tool 2-3 times with different queries.
2. From ONLY news articles, extract for each flood-affected location:
   - Place / Area name
   - Latitude and Longitude (estimate from place name if not stated)
   - News source name and URL
   - Current flood severity or alert level
   - Key details: current water level, rainfall, evacuations, deaths, etc.
3. Compile a structured report of locations currently affected by flooding.
4. If no current flood news is found, say so clearly. Do NOT make up data.

SEARCH QUERIES TO USE:
- "flood warning today {_YEAR} India news"
- "Chennai Tamil Nadu flood alert today {_YEAR}"
- "India flood news today latest"

IMPORTANT:
- Extract ACTUAL data from the news articles. Do NOT fabricate anything.
- If a scraped page is not a news article or contains old data, SKIP it.
- Always include source URLs for traceability.
- Focus on the Tamil Nadu / Chennai region but include other areas too
  if there are active flood events.

Return a structured report with ONLY currently affected locations.
"""


class FloodScraperResponse(BaseModel):
    report: str


class FloodWebScraperAgent(BaseAgent):
    """Scrapes news websites for real-time flood intelligence."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name="flood_web_scraper_agent",
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state=None) -> str:
        return FLOOD_SCRAPER_PROMPT

    def get_response_format(self) -> type[BaseModel]:
        return FloodScraperResponse

    def get_result_key(self) -> str:
        return "web_scraper_result"

    async def process_query(
        self,
        query: str = "Find current real-time flood news from today",
        state=None,
    ) -> Dict[str, Any]:
        """Use a ReAct agent with Firecrawl tool to gather flood news."""
        try:
            from langchain_core.messages import HumanMessage
            from langgraph.prebuilt import create_react_agent

            from app.tools.flood_scraper_tool import get_flood_scraper_tools

            prompt = self.get_prompt(state)
            tools = get_flood_scraper_tools()

            agent = create_react_agent(
                self.model,
                tools,
                prompt=prompt,
            )

            result = agent.invoke(
                {"messages": [HumanMessage(content=query)]},
                {"recursion_limit": 15},
            )

            # Extract the final AI response
            from langchain_core.messages import AIMessage, ToolMessage

            final_text = ""
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                    final_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            if not final_text:
                # Fallback: grab last ToolMessage
                for msg in reversed(result.get("messages", [])):
                    if isinstance(msg, ToolMessage) and msg.content:
                        final_text = msg.content
                        break

            logger.info("Web scraping complete", length=len(final_text))

            return {
                "success": True,
                self.get_result_key(): final_text or "No current flood news found from web sources.",
                "error": [],
            }
        except Exception as e:
            logger.error("Flood web scraper agent failed", error=str(e))
            return {
                "success": False,
                self.get_result_key(): f"Web scraping failed: {str(e)}",
                "error": [str(e)],
            }

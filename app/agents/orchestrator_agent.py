"""
Orchestrator Agent for the HeliosCommand System.

Routes conversations to appropriate agent based on user requirement
using LangGraph's create_react_agent pattern.
"""

from typing import Any, Dict, List, Optional

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.agents.agent_types import ORCHESTRATOR_NAME
from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels
from app.tools.agent_tools import get_agent_tools
from app.workflows.state import HeliosState

logger = structlog.get_logger(__name__)


class OrchestratorResponse(BaseModel):
    """Response format for the orchestrator agent."""

    selected_agent: str = Field(description="The agent selected to handle this query")
    reasoning: str = Field(description="Why this agent was selected")


ORCHESTRATOR_PROMPT = """You are the ORCHESTRATOR of HeliosCommand — a Healthcare Assistant System.

YOUR PRIMARY RESPONSIBILITIES:
1. Understand the user's healthcare need and location
2. Identify their intent (hospital lookup, pharmacy search, or email)
3. Decide which tool agent to delegate to
4. Maintain context across follow-up questions (like confirmations)
5. Keep your own responses brief — let agents handle details

AVAILABLE TOOL AGENTS:

1) hospital_analyser
   - Finds the nearest hospital based on user location
   - Provides distance and ETA information
   - Use when user mentions: hospital, beds, ICU, nearest hospital, admission, emergency

2) medical_shops
   - Finds nearby medical shops and pharmacies
   - Use when user mentions: pharmacy, medical shop, medical store, medicines, drugstore

3) send_email
   - Sends an email on behalf of the user
   - Use when user explicitly asks to send an email
   - Requires: to_address, subject, and body

DECISION RULES:

If the user:
- Mentions hospital, beds, ICU, emergency, admission, or a hospital name → delegate to hospital_analyser
- Mentions pharmacy, medical shop, medicines, drugstore → delegate to medical_shops
- Asks to send an email → delegate to send_email
- Says "yes", "okay", "sure" (confirmation) → just acknowledge: "Thanks for confirming. Take care!"
- Says "no", "not interested", "don't want" → delegate to send_email to notify about alternative options
- If unclear → ask: "Would you like help finding a hospital, pharmacy, or sending an email?"

CONVERSATION FLOW:

1. First interaction:
   - Ask the user to provide thei name, phone number and address
   - Understand the user's need and location
   - Delegate immediately to the correct agent

2. Follow-ups:
   - If "yes" → simple acknowledgment (no delegation needed)
   - If "no" → delegate to send_email with context about their original request

IMPORTANT:
- Do NOT provide hospital/pharmacy information yourself — always delegate to the appropriate tool
- Always delegate once intent is clear
- Keep responses short and directive
- Focus on routing, not answering directly

CURRENT STATE:
- Intent: {intent}
"""


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent for routing healthcare conversations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name=ORCHESTRATOR_NAME,
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_tools(self) -> List[BaseTool]:
        """Get agent-backed tools for the orchestrator."""
        return get_agent_tools()

    def get_result_key(self) -> str:
        return "orchestrator_result"

    def get_prompt(self, state: Optional[HeliosState] = None) -> str:
        intent = state.get("user_intent", "unknown") if state else "unknown"
        return ORCHESTRATOR_PROMPT.format(intent=intent)

    def get_response_format(self) -> type[BaseModel]:
        return OrchestratorResponse

    async def process_query(
        self,
        query: str,
        state: Optional[HeliosState] = None,
    ) -> Dict[str, Any]:
        """Process a query through the orchestrator using create_react_agent."""
        try:
            from langgraph.prebuilt import create_react_agent

            tools = self.get_tools()
            prompt = self.get_prompt(state)

            agent = create_react_agent(self.model, tools, prompt=prompt)

            result = agent.invoke({"messages": state.get("messages", []) if state else []})

            return {
                "success": True,
                "orchestrator_result": result,
                "messages": result.get("messages", []),
                "error": [],
            }
        except Exception as e:
            logger.error("Orchestrator processing failed", error=str(e))
            return {
                "success": False,
                "orchestrator_result": None,
                "error": [str(e)],
            }


__all__ = ["OrchestratorAgent"]

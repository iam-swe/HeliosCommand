"""
Base agent functionality for all HeliosCommand agents.
Uses Google Gemini 2.5 Flash as the LLM provider.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.agents.llm_models import LLMModels
from app.workflows.state import HeliosState

logger = structlog.get_logger(__name__)


class BaseLLM(ABC):
    """Abstract base class for all agents with Gemini LLM functionality."""

    def __init__(
        self,
        agent_name: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        self.agent_name = agent_name
        self.temperature = temperature
        self.model_name = model_name
        self.model: Any = None

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY in .env file.")

        self._setup_model()

        logger.info(
            f"Initialized {self.__class__.__name__}",
            agent_name=agent_name,
            temperature=temperature,
            model_name=model_name,
        )

    def _setup_model(self) -> None:
        try:
            self.model = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=self.temperature,
            )
            logger.debug("Gemini model initialized", agent_name=self.agent_name)
        except Exception as e:
            logger.error("Failed to initialize model", error=str(e), agent_name=self.agent_name)
            raise

    @abstractmethod
    def get_prompt(self, state: Optional[HeliosState] = None) -> str:
        """Get the system prompt for this agent."""
        pass

    @abstractmethod
    def get_response_format(self) -> type[BaseModel]:
        """Get the expected response format for this agent."""
        pass


class BaseAgent(BaseLLM):
    """Base class for agents that process queries."""

    def __init__(
        self,
        agent_name: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name=agent_name,
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to this agent. Override in subclasses."""
        return []

    @abstractmethod
    def get_result_key(self) -> str:
        """Get the key used to store this agent's result in state."""
        pass

    async def process_query(
        self,
        query: str,
        state: Optional[HeliosState] = None,
    ) -> Dict[str, Any]:
        """Process a query and return results."""
        try:
            prompt = self.get_prompt(state)
            messages: List[BaseMessage] = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ]

            response = await self.model.ainvoke(messages)

            return {
                "success": True,
                self.get_result_key(): response.content,
                "error": [],
            }
        except Exception as e:
            logger.error("Agent processing failed", error=str(e), agent_name=self.agent_name)
            return {
                "success": False,
                self.get_result_key(): None,
                "error": [str(e)],
            }

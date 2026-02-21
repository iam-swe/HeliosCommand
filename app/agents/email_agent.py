"""Email agent implementation using LangGraph BaseAgent pattern."""

import os
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel

from app.agents.agent_types import ORCHESTRATOR_NAME
from app.agents.base_agent import BaseAgent
from app.agents.llm_models import LLMModels
from app.tools.email_tool import send_email
from app.workflows.state import HeliosState

logger = structlog.get_logger(__name__)


EMAIL_AGENT_PROMPT = """You are an Email Composer Agent for HeliosCommand — a healthcare assistant.

YOUR RESPONSIBILITIES:
1. Compose urgent healthcare emails on behalf of patients
2. Extract patient address and requirements from conversation history
3. Convey urgency appropriately based on the need

CURRENT STATE:
- Intent: {intent}

URGENCY RULES:
- If the patient needs hospital beds/ICU/admission/emergency → convey that they need IMMEDIATE EMERGENCY help for beds
- If the patient needs medicines/pharmacy/medical shop → convey that they seek medications as soon as possible

EMAIL RULES:
- Extract patient address/location from conversation — include it in the email
- Do NOT include patient name or regards/sign-off name — just the address is enough
- Be direct and urgent
- Format: Return ONLY this format: SUBJECT|BODY (separated by |)

Example:
URGENT: Emergency Hospital Bed Required|Dear Healthcare Administrator,

This is an urgent request for immediate emergency assistance with hospital bed availability.

Patient Address: Shivasunder hospital area, Shastri Nagar, Adyar, Chennai
Requirement: 1 hospital bed — immediate emergency help needed

Please respond at the earliest with available options in this area.
"""


class EmailResponse(BaseModel):
    """Response format for the email agent."""
    message: str
    email_sent: bool = False


class EmailAgent(BaseAgent):
    """Agent for composing and sending healthcare emails."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        model_name: str = LLMModels.DEFAULT,
    ) -> None:
        super().__init__(
            agent_name="email_agent",
            api_key=api_key,
            temperature=temperature,
            model_name=model_name,
        )

    def get_prompt(self, state: Optional[HeliosState] = None) -> str:
        intent = state.get("user_intent", "unknown") if state else "unknown"
        return EMAIL_AGENT_PROMPT.format(intent=intent)

    def get_response_format(self) -> type[BaseModel]:
        return EmailResponse

    def get_result_key(self) -> str:
        return "email_agent_result"

    def _extract_conversation_context(self, state: Optional[HeliosState]) -> str:
        """Extract full conversation from state."""
        if not state or "messages" not in state:
            return ""
        
        context_parts = []
        from langchain_core.messages import HumanMessage, AIMessage
        
        for msg in state.get("messages", []):
            if isinstance(msg, HumanMessage):
                context_parts.append(f"Patient: {msg.content}")
            elif isinstance(msg, AIMessage):
                context_parts.append(f"Assistant: {msg.content}")
        
        return "\n".join(context_parts)

    async def process_query(
        self,
        query: str,
        state: Optional[HeliosState] = None,
    ) -> Dict[str, Any]:
        """Generate and send an email based on conversation context."""
        logger.info(
            "EmailAgent.process_query called",
            query=query,
            state_keys=list(state.keys()) if state else None,
        )

        # Extract full conversation context from state
        conversation_context = self._extract_conversation_context(state)
        
        if not conversation_context:
            logger.warning("No conversation context available")
            return {
                "success": False,
                self.get_result_key(): "No conversation history available to compose email",
                "error": ["No conversation context"],
            }
        
        # Create a message for the LLM with full conversation
        llm_prompt = f"""Based on this conversation, compose an urgent email requesting alternative healthcare options.

CONVERSATION:
{conversation_context}

RULES:
- Extract the patient's address/location from the conversation
- If they need hospital beds/ICU/emergency → state they need IMMEDIATE EMERGENCY help for beds
- If they need medicines/pharmacy → state they seek medications as soon as possible
- Do NOT include any patient name or regards/sign-off name — just the patient address
- Be direct and convey urgency

IMPORTANT: Return ONLY in this exact format with no additional text:
SUBJECT|BODY

Example:
URGENT: Emergency Hospital Bed Required|Dear Healthcare Administrator,

This is an urgent request for immediate emergency assistance with hospital bed availability.

Patient Address: Shivasunder hospital area, Shastri Nagar, Adyar, Chennai
Requirement: 1 hospital bed — immediate emergency help needed

Please respond at the earliest with available options in this area."""

        try:
            # Call the LLM to generate the email
            from langchain_core.messages import HumanMessage
            response = self.model.invoke([HumanMessage(content=llm_prompt)])
            
            email_content = response.content.strip()
            logger.info("Generated email content", content=email_content[:150])
            
            # Parse the email content
            if "|" not in email_content:
                logger.warning("Invalid email format from LLM", content=email_content[:100])
                return {
                    "success": False,
                    self.get_result_key(): "Failed to generate email in proper format",
                    "error": ["Invalid email format generated"],
                }
            
            parts = email_content.split("|", 1)
            subject = parts[0].strip()
            body = parts[1].strip()
            
            # Validate that we have meaningful content
            if not subject or not body or len(subject) < 5 or len(body) < 20:
                logger.warning("Generated email content too short", subject_len=len(subject), body_len=len(body))
                return {
                    "success": False,
                    self.get_result_key(): "Generated email content was incomplete",
                    "error": ["Email content validation failed"],
                }
            
            # Get recipient email from environment
            user_email = os.environ.get("USER_EMAIL", "")
            if not user_email or "@" not in user_email:
                logger.warning("USER_EMAIL not set in environment")
                return {
                    "success": False,
                    self.get_result_key(): "USER_EMAIL not configured",
                    "error": ["USER_EMAIL environment variable not set"],
                }
            
            # Send the email
            logger.info("Sending email", to=user_email, subject=subject)
            result = send_email(user_email, subject, body)
            
            if result.get("success"):
                message = f"Email sent successfully with your healthcare request details."
                logger.info("Email sent successfully", to=user_email)
                return {
                    "success": True,
                    self.get_result_key(): message,
                    "email_sent": True,
                    "error": [],
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning("Email sending failed", error=error_msg)
                return {
                    "success": False,
                    self.get_result_key(): f"Failed to send email: {error_msg}",
                    "email_sent": False,
                    "error": [str(error_msg)],
                }
                
        except Exception as e:
            error_msg = f"Email generation failed: {str(e)}"
            logger.error("Email generation error", error=str(e))
            return {
                "success": False,
                self.get_result_key(): error_msg,
                "email_sent": False,
                "error": [error_msg],
            }

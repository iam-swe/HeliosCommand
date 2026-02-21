"""Orchestrator agent for HeliosCommand (app-level implementation).

Routes user requests to available agent-tools registered in `app.tools.tool_registry`.
"""
from typing import Optional, Dict, Any
import os

from app.agents.base_agent import BaseAgent
from app.tools.tool_registry import initialize_tools, get_tool


class OrchestratorAgent(BaseAgent):
	def __init__(self):
		super().__init__(agent_name="orchestrator")
		initialize_tools()

	def _decide(self, query: str) -> str:
		q = query.lower()
		if any(k in q for k in ["hospital", "beds", "icu", "nearest hospital"]):
			return "hospital_analyser"
		if any(k in q for k in ["medical shop", "pharmacy", "medical store", "nearby medical"]):
			return "medical_shops"
		if any(k in q for k in ["email", "send email", "mail"]):
			return "send_email"
		return "hospital_analyser"

	def process_query(self, query: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		selected = self._decide(query)
		tool = get_tool(selected)
		if not tool:
			return {"success": False, "error": "No tool registered for selected action"}

		# For email, expect pipe separated: to|subject|body
		if selected == "send_email":
			parts = query.split("|")
			if len(parts) < 3:
				return {"success": False, "error": "Bad email format. Use to|subject|body"}
			to = parts[0].strip()
			subject = parts[1].strip()
			body = "|".join(parts[2:]).strip()
			# send_email is registered as a callable that accepts (to, subject, body)
			res = tool(to, subject, body)
			return {"success": True, self.get_result_key(): res}

		# hospital_analyser & medical_shops tools accept a single query string
		res = tool(query)
		return {"success": True, self.get_result_key(): res}


__all__ = ["OrchestratorAgent"]

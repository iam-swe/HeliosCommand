"""Hospital analyser agent implementation."""
import os
from typing import Optional, Dict, Any

from app.agents.base_agent import BaseAgent
from app.tools.hospital_tools import find_nearest_hospital


class HospitalAnalyserAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="hospital_analyser")

    def process_query(self, query: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        api_key = os.environ.get("GOOGLE_API_KEY")
        result = find_nearest_hospital(query, api_key)
        return {"success": True, self.get_result_key(): result}

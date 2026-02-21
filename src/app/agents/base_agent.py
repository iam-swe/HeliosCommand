from typing import Optional, Dict, Any


class BaseAgent:
    """Minimal base agent used by HeliosCommand agents."""

    def __init__(self, agent_name: str = "base_agent") -> None:
        self.agent_name = agent_name

    def get_result_key(self) -> str:
        return f"{self.agent_name}_result"

    def process_query(self, query: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError()

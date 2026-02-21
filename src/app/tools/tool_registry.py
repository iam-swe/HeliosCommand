from typing import Callable, Dict

from app.tools.agent_tools import get_agent_tools


TOOL_REGISTRY: Dict[str, Callable] = {}


def register_tool(name: str, fn: Callable) -> None:
	TOOL_REGISTRY[name] = fn


def get_tool(name: str):
	return TOOL_REGISTRY.get(name)


def initialize_tools() -> None:
	tools = get_agent_tools()
	for name, fn in tools.items():
		register_tool(name, fn)

	# also register non-agent tools
	try:
		from app.tools.email_tool import send_email
		register_tool("send_email", send_email)
	except Exception:
		pass


def get_all_tools() -> Dict[str, Callable]:
	return TOOL_REGISTRY

__all__ = ["initialize_tools", "get_tool", "get_all_tools", "register_tool"]

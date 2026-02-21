"""Tool registry for HeliosCommand.

With the move to create_react_agent + StructuredTool, the orchestrator
gets tools directly via get_agent_tools(). This registry is kept for
backward compatibility and direct tool access if needed.
"""

from typing import Callable, Dict, Optional

from app.tools.agent_tools import get_agent_tools


TOOL_REGISTRY: Dict[str, Callable] = {}
_initialized: bool = False


def register_tool(name: str, fn: Callable) -> None:
    TOOL_REGISTRY[name] = fn


def get_tool(name: str) -> Optional[Callable]:
    if not _initialized:
        initialize_tools()
    return TOOL_REGISTRY.get(name)


def initialize_tools() -> None:
    global _initialized
    if _initialized:
        return

    # Register non-agent tools (email)
    try:
        from app.tools.email_tool import send_email
        register_tool("send_email", send_email)
    except Exception:
        pass

    _initialized = True


def get_all_tools() -> Dict[str, Callable]:
    if not _initialized:
        initialize_tools()
    return TOOL_REGISTRY


__all__ = ["initialize_tools", "get_tool", "get_all_tools", "register_tool"]

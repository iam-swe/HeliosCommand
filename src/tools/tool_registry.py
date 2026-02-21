"""Compatibility wrapper re-exporting app.tools.tool_registry API."""
from app.tools.tool_registry import initialize_tools, register_tool, get_tool, get_all_tools

__all__ = ["initialize_tools", "register_tool", "get_tool", "get_all_tools"]

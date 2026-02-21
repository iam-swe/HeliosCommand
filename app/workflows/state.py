"""State definitions for HeliosCommand workflow."""

from typing import Annotated, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class HeliosState(TypedDict):
    """State shared across all nodes in the HeliosCommand workflow."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    user_intent: str
    turn_count: int
    current_response: Optional[str]
    error: List[str]
    orchestrator_result: Optional[str]


def get_conversation_context(state: HeliosState, max_messages: int = 6) -> str:
    """Build conversation context from message history."""
    context_parts: List[str] = []
    messages = state.get("messages", [])[-max_messages:]

    for msg in messages:
        if isinstance(msg, HumanMessage):
            context_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage) and msg.content:
            if not getattr(msg, "tool_calls", None):
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                context_parts.append(f"HeliosCommand: {content}")

    return "\n".join(context_parts)


def get_initial_state() -> HeliosState:
    """Get the initial HeliosCommand state."""
    return HeliosState(
        messages=[],
        user_query="",
        user_intent="unknown",
        turn_count=0,
        current_response=None,
        error=[],
        orchestrator_result=None,
    )

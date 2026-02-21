"""State definitions for HeliosCommand workflow."""
from typing import Any, Dict, List, Optional, TypedDict


class HeliosState(TypedDict, total=False):
    """Workflow state for HeliosCommand."""
    messages: List[Any]
    user_query: str
    orchestrator_result: str
    turn_count: int
    user_intent: str


def get_initial_state() -> HeliosState:
    """Initialize a new workflow state."""
    return {
        "messages": [],
        "user_query": "",
        "orchestrator_result": "",
        "turn_count": 0,
        "user_intent": "unknown",
    }

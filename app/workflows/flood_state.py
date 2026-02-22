"""State definitions for the Flood Alert workflow."""

import operator
from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class FloodAlertState(TypedDict):
    """State shared across all nodes in the Flood Alert workflow."""

    messages: Annotated[List[BaseMessage], add_messages]

    # Weights configured by user (e.g. 0.7 vs 0.3)
    csv_weight: float
    web_weight: float

    # Results from parallel agents
    csv_analysis_result: Optional[str]
    web_scraper_result: Optional[str]

    # Orchestrator final output
    orchestrator_result: Optional[str]
    email_sent: bool

    # operator.add concatenates lists from parallel nodes
    error: Annotated[List[str], operator.add]


def get_initial_flood_state(csv_weight: float = 0.5) -> FloodAlertState:
    """Return a blank flood-alert state with configured weights."""
    return FloodAlertState(
        messages=[],
        csv_weight=csv_weight,
        web_weight=max(0.0, 1.0 - csv_weight),
        csv_analysis_result=None,
        web_scraper_result=None,
        orchestrator_result=None,
        email_sent=False,
        error=[],
    )

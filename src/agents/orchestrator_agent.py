"""Compatibility wrapper re-exporting app-level orchestrator.

This thin wrapper prevents import breakage where modules import
`src.agents.orchestrator_agent` directly. Implementation lives in
`app.agents.orchestrator_agent`.
"""
from app.agents.orchestrator_agent import OrchestratorAgent

__all__ = ["OrchestratorAgent"]

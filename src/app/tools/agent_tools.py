"""Wrap agent instances as callable tools for the orchestrator."""
from typing import Callable, Dict
import asyncio

from app.agents.hospital_agent import HospitalAnalyserAgent
from app.agents.medical_shop_agent import MedicalShopAgent


_AGENT_CACHE: Dict[str, object] = {}


def _get_agent(agent_cls):
    name = agent_cls.__name__
    if name not in _AGENT_CACHE:
        _AGENT_CACHE[name] = agent_cls()
    return _AGENT_CACHE[name]


def get_agent_tools() -> Dict[str, Callable[[str], dict]]:
    """Return a mapping of tool name -> callable(query) that delegates to agents.

    The callable returns the agent result dict.
    """
    hospital = _get_agent(HospitalAnalyserAgent)
    medical = _get_agent(MedicalShopAgent)

    def hospital_tool(query: str):
        return hospital.process_query(query)

    def medical_tool(query: str):
        return medical.process_query(query)

    return {"hospital_analyser": hospital_tool, "medical_shops": medical_tool}

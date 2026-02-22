"""Nodes for the Flood Alert LangGraph workflow.

Defines three nodes:
  1. csv_analyst_node  — runs the FloodCSVAgent
  2. web_scraper_node  — runs the FloodWebScraperAgent
  3. flood_orchestrator_node — runs the FloodOrchestratorAgent with email tool

Nodes 1 and 2 run in PARALLEL; node 3 runs AFTER both complete.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

import structlog
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.workflows.flood_state import FloodAlertState

logger = structlog.get_logger(__name__)


def _log_step(icon: str, step: str, detail: str = "") -> None:
    """Print a formatted progress step to both logger and console."""
    msg = f"{icon}  [{step}] {detail}" if detail else f"{icon}  [{step}]"
    logger.info(msg)
    print(msg)


# ─── Node 1: CSV Analyst ───────────────────────────────────────────

def csv_analyst_node(state: FloodAlertState) -> Dict[str, Any]:
    """Run the FloodCSVAgent and store results in state."""
    from app.agents.flood_csv_agent import FloodCSVAgent

    _log_step("📊", "CSV ANALYST", "Starting — reading flood_detection_data.csv …")
    t0 = time.time()

    _log_step("📊", "CSV ANALYST", "Initialising FloodCSVAgent (Gemini LLM) …")
    agent = FloodCSVAgent()

    _log_step("📊", "CSV ANALYST", "Loading CSV data from disk …")
    csv_data = agent._read_csv()
    line_count = csv_data.count("\n")
    _log_step("📊", "CSV ANALYST", f"CSV loaded — {line_count} rows of sensor data")

    _log_step("📊", "CSV ANALYST", "Sending data to LLM for flood risk analysis …")
    result = asyncio.run(agent.process_query())

    csv_result = result.get("csv_analysis_result", "No analysis produced.")
    errors = result.get("error", [])
    elapsed = round(time.time() - t0, 1)

    if errors:
        _log_step("❌", "CSV ANALYST", f"Completed with errors in {elapsed}s: {errors}")
    else:
        _log_step("✅", "CSV ANALYST", f"Analysis complete in {elapsed}s — {len(csv_result)} chars of risk report generated")

    return {
        "csv_analysis_result": csv_result,
        "error": errors,
    }


# ─── Node 2: Web Scraper ───────────────────────────────────────────

def web_scraper_node(state: FloodAlertState) -> Dict[str, Any]:
    """Run the FloodWebScraperAgent and store results in state."""
    from app.agents.flood_web_scraper_agent import FloodWebScraperAgent

    _log_step("🌐", "WEB SCRAPER", "Starting — will search web & social media for flood intel …")
    t0 = time.time()

    _log_step("🌐", "WEB SCRAPER", "Initialising FloodWebScraperAgent (Gemini + Firecrawl) …")
    agent = FloodWebScraperAgent()

    _log_step("🌐", "WEB SCRAPER", "Launching ReAct agent with Firecrawl search tool …")
    result = asyncio.run(agent.process_query())

    web_result = result.get("web_scraper_result", "No web data found.")
    errors = result.get("error", [])
    elapsed = round(time.time() - t0, 1)

    if errors:
        _log_step("❌", "WEB SCRAPER", f"Completed with errors in {elapsed}s: {errors}")
    else:
        _log_step("✅", "WEB SCRAPER", f"Scraping complete in {elapsed}s — {len(web_result)} chars of intel gathered")

    return {
        "web_scraper_result": web_result,
        "error": errors,
    }


# ─── Node 3: Flood Orchestrator ────────────────────────────────────

def _extract_text(content) -> str:
    """Extract text from content that may be a string or list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def flood_orchestrator_node(state: FloodAlertState) -> Dict[str, Any]:
    """Analyse combined data and optionally send email alert.

    Uses create_react_agent with the send_flood_alert_email tool so
    the LLM can decide autonomously whether to fire an alert.
    """
    from app.agents.flood_orchestrator_agent import FloodOrchestratorAgent
    from app.tools.flood_email_tool import get_flood_email_tools
    from app.tools.flood_sms_tool import get_flood_sms_tools

    _log_step("🧠", "ORCHESTRATOR", "Starting — both parallel agents have completed")
    t0 = time.time()

    # Log what we received from the parallel agents
    csv_len = len(state.get("csv_analysis_result", "") or "")
    web_len = len(state.get("web_scraper_result", "") or "")
    _log_step("🧠", "ORCHESTRATOR", f"Received CSV analysis: {csv_len} chars")
    _log_step("🧠", "ORCHESTRATOR", f"Received Web intelligence: {web_len} chars")

    _log_step("🧠", "ORCHESTRATOR", "Initialising FloodOrchestratorAgent …")
    agent_instance = FloodOrchestratorAgent()

    _log_step("🧠", "ORCHESTRATOR", "Building prompt with combined data from both agents …")
    prompt = agent_instance.get_prompt(state)
    tools = get_flood_email_tools() + get_flood_sms_tools()

    _log_step("🧠", "ORCHESTRATOR", "Creating ReAct agent with email and SMS alert tools (max 10 steps) …")
    react_agent = create_react_agent(
        agent_instance.model,
        tools,
        prompt=prompt,
    )

    _log_step("🧠", "ORCHESTRATOR", "Invoking LLM to cross-reference data and assess severity …")
    result = react_agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Analyse the flood data from both sources and produce "
                        "a consolidated flood risk report. If any location is "
                        "CRITICAL or HIGH severity, call BOTH send_flood_alert_email "
                        "and send_flood_alert_sms exactly ONCE each. "
                        "After sending, do NOT call the tools again — just provide "
                        "a brief summary of what was sent."
                    )
                ),
            ],
        },
        {"recursion_limit": 10},
    )

    # Extract the final response
    orchestrator_response = ""
    email_sent = False
    sms_sent = False

    _log_step("🧠", "ORCHESTRATOR", "Parsing agent response messages …")

    # Check for tool calls (email and SMS)
    for msg in result.get("messages", []):
        if isinstance(msg, ToolMessage) and msg.content:
            if msg.name == "send_flood_alert_email":
                if "successfully" in msg.content:
                    email_sent = True
                    _log_step("📧", "ORCHESTRATOR", f"Email tool returned: {msg.content}")
                else:
                    _log_step("⚠️", "ORCHESTRATOR", f"Email tool error: {msg.content}")
            elif msg.name == "send_flood_alert_sms":
                if "successfully" in msg.content:
                    sms_sent = True
                    _log_step("📱", "ORCHESTRATOR", f"SMS tool returned: {msg.content}")
                else:
                    _log_step("⚠️", "ORCHESTRATOR", f"SMS tool error: {msg.content}")

    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            orchestrator_response = _extract_text(msg.content)
            break

    if not orchestrator_response:
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, ToolMessage) and msg.content:
                orchestrator_response = msg.content
                break

    elapsed = round(time.time() - t0, 1)

    if email_sent or sms_sent:
        _log_step("🚨", "ORCHESTRATOR", f"ALERTS SENT — severe flood locations detected! ({elapsed}s)")
    else:
        _log_step("✅", "ORCHESTRATOR", f"Analysis complete in {elapsed}s — no severe alerts triggered")

    _log_step("✅", "ORCHESTRATOR", f"Final report: {len(orchestrator_response)} chars")

    return {
        "orchestrator_result": orchestrator_response,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "messages": result.get("messages", []),
    }

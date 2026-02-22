"""Flood Alert Workflow — Parallel Multi-Agent LangGraph Pipeline.

Architecture:
                    ┌──────────────────┐
                    │      START       │
                    └──────┬───────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼─────────┐   ┌──────────▼──────────┐
     │   CSV Analyst     │   │   Web Scraper        │
     │   (sensor data)   │   │   (Firecrawl)        │
     └────────┬─────────┘   └──────────┬──────────┘
              │                         │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Flood Orchestrator     │
              │  (analyse + email?)     │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │     END      │
                    └──────────────┘

The CSV Analyst and Web Scraper nodes run IN PARALLEL.
The Orchestrator waits for both to complete, then analyses the
combined data and decides whether to trigger an email alert.
"""

import time

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.nodes.flood_alert_nodes import (
    csv_analyst_node,
    flood_orchestrator_node,
    web_scraper_node,
)
from app.workflows.flood_state import FloodAlertState, get_initial_flood_state

logger = structlog.get_logger(__name__)


def _banner(msg: str, char: str = "═", width: int = 60) -> None:
    """Print a formatted banner to console and log."""
    line = char * width
    print(f"\n{line}")
    print(f"  {msg}")
    print(f"{line}\n")
    logger.info(msg)


class FloodAlertWorkflow:
    """LangGraph workflow that runs two agents in parallel, then orchestrates."""

    def __init__(self) -> None:
        print("\n⚙️  [INIT] Building LangGraph workflow …")
        print("    Nodes: csv_analyst, web_scraper, flood_orchestrator")
        print("    Edges: START → csv_analyst ─┐")
        print("           START → web_scraper  ─┤→ flood_orchestrator → END")
        self.workflow = self._create_workflow()
        print("✅  [INIT] Workflow graph compiled successfully\n")
        logger.info("FloodAlertWorkflow initialized")

    def _create_workflow(self) -> CompiledStateGraph:
        """Build the LangGraph with parallel fan-out → fan-in pattern."""

        graph = StateGraph(FloodAlertState)

        # ── Add nodes ──────────────────────────────────────────
        graph.add_node("csv_analyst", csv_analyst_node)
        graph.add_node("web_scraper", web_scraper_node)
        graph.add_node("flood_orchestrator", flood_orchestrator_node)

        # ── Fan-out: START → both agents in parallel ───────────
        graph.add_edge(START, "csv_analyst")
        graph.add_edge(START, "web_scraper")

        # ── Fan-in: both agents → orchestrator ─────────────────
        graph.add_edge("csv_analyst", "flood_orchestrator")
        graph.add_edge("web_scraper", "flood_orchestrator")

        # ── Orchestrator → END ─────────────────────────────────
        graph.add_edge("flood_orchestrator", END)

        return graph.compile()

    def run(self, csv_weight: float = 0.5) -> dict:
        """Execute the full flood alert workflow.

        Args:
            csv_weight: Weight given to CSV sensor data (e.g., 0.8 for 80%).

        Returns:
            dict with keys: orchestrator_result, email_sent, error
        """
        _banner("🌊  FLOOD ALERT WORKFLOW — STARTING")

        print(f"📌  Step 1/3: Launching PARALLEL agents (CSV weight: {csv_weight * 100:.0f}%) …")
        print("     ├── 📊 CSV Analyst   → analyses flood_detection_data.csv")
        print("     └── 🌐 Web Scraper   → scrapes web & social media")
        print()

        t_start = time.time()

        initial_state = get_initial_flood_state(csv_weight=csv_weight)

        final_state = self.workflow.invoke(initial_state)

        t_total = round(time.time() - t_start, 1)

        report = final_state.get("orchestrator_result", "No report generated.")
        email_sent = final_state.get("email_sent", False)
        sms_sent = final_state.get("sms_sent", False)
        errors = final_state.get("error", [])

        # ── Summary ────────────────────────────────────────────
        _banner("🌊  FLOOD ALERT WORKFLOW — COMPLETE")

        print(f"⏱️   Total execution time: {t_total}s")
        print(f"📊  CSV analysis:   {len(final_state.get('csv_analysis_result', '') or '')} chars")
        print(f"🌐  Web intel:      {len(final_state.get('web_scraper_result', '') or '')} chars")
        print(f"🧠  Final report:   {len(report)} chars")
        print(f"📧  Email sent:     {'✅ Yes' if email_sent else '❌ No'}")
        print(f"📱  SMS sent:       {'✅ Yes' if sms_sent else '❌ No'}")
        if errors:
            print(f"⚠️   Errors:        {errors}")
        print()

        return {
            "report": report,
            "email_sent": email_sent,
            "sms_sent": sms_sent,
            "csv_analysis": final_state.get("csv_analysis_result", ""),
            "web_intelligence": final_state.get("web_scraper_result", ""),
            "errors": errors,
        }


def run_flood_alert(csv_weight: float = 0.5) -> dict:
    """Convenience function to create and run the workflow."""
    workflow = FloodAlertWorkflow()
    return workflow.run(csv_weight=csv_weight)

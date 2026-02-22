"""Main entry point for HeliosCommand — Healthcare Assistant.

This CLI demonstrates two multi-agentic workflows:

1. Healthcare Assistant (interactive):
   - Hospital finder (HospitalAnalyserAgent)
   - Medical shop locator (MedicalShopAgent)
   - Email sender (via Gmail API)
   All routed by the OrchestratorAgent using LangGraph's create_react_agent.

2. Flood Alert System (--flood-alert):
   - CSV Analyst Agent — analyses flood_detection_data.csv in parallel
   - Web Scraper Agent — scrapes flood intel from web & social media in parallel
   - Flood Orchestrator — combines results & sends email alert if severe
"""

import os

import structlog

# Configure structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        int(os.environ.get("HELIOS_LOG_LEVEL_NUM", "20"))  # INFO=20
    ),
)

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value

from app.agents.orchestrator_agent import OrchestratorAgent
from app.nodes.orchestrator_node import OrchestratorNode
from app.workflows import MultiAgentWorkflow
from app.workflows.flood_alert_workflow import run_flood_alert


def create_app(conversation_id=None):
    """Create and initialize the workflow with LangGraph agents."""
    orchestrator_agent = OrchestratorAgent()
    orchestrator_node = OrchestratorNode(orchestrator_agent)
    return MultiAgentWorkflow(
        orchestrator_node=orchestrator_node,
        conversation_id=conversation_id,
    )


def run(query: str, conversation_id=None) -> str:
    """Run a single query through the workflow."""
    workflow = create_app(conversation_id)
    result = workflow.chat(query)
    return result


def run_interactive(conversation_id=None) -> None:
    """Run an interactive chat session."""
    print("\n" + "=" * 70)
    print("HeliosCommand — Healthcare Assistant")
    print("=" * 70)
    print("Multi-agent workflow for hospital/pharmacy/email services")
    print("Type 'quit', 'exit', or 'bye' to end the session")
    print("-" * 70)

    workflow = create_app(conversation_id)

    # Show conversation info
    print(f"Conversation ID: {workflow.conversation_id}")
    print(f"Saving to: data/conversations/{workflow.conversation_id}.json")
    print("-" * 70 + "\n")

    # Print initial greeting
    greeting = workflow.get_greeting()
    print(f"Assistant: {greeting}\n")

    # Main conversation loop
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                print("\nAssistant: Thank you for using HeliosCommand. Stay healthy! Goodbye.\n")
                break

            response = workflow.chat(user_input)
            print(f"Assistant: {response}\n")

        except KeyboardInterrupt:
            print("\n\nAssistant: Session interrupted. Stay healthy! Goodbye.\n")
            break
        except EOFError:
            print("\n\nAssistant: End of input. Goodbye.\n")
            break
        except Exception as e:
            print(f"Error: {str(e)}\n")


def start_session(conversation_id=None) -> None:
    """Alias for run_interactive."""
    run_interactive(conversation_id)


def run_flood_alert_workflow(csv_weight: float = 0.5) -> None:
    """Run the Flood Alert parallel multi-agent workflow.

    Two agents run in parallel:
      1. CSV Analyst — analyses flood sensor data
      2. Web Scraper — scrapes flood intel from web & social media

    Their outputs feed into the Flood Orchestrator which
    cross-references the data and sends an email alert if
    any location is rated CRITICAL or HIGH severity.
    """
    print("\n" + "═" * 70)
    print("  🌊  HeliosCommand — FLOOD ALERT SYSTEM")
    print("═" * 70)
    print()
    print("  Running TWO agents in PARALLEL:")
    print(f"  📊 Agent 1: CSV Sensor Data Analyst (Weight: {csv_weight * 100:.0f}%)")
    web_weight = max(0.0, 1.0 - csv_weight)
    print(f"  🌐 Agent 2: Web News Scraper          (Weight: {web_weight * 100:.0f}%)")
    print()
    print("  Both feed into the Flood Orchestrator which")
    print("  analyses severity and sends email alerts if needed.")
    print()
    print("─" * 70)
    print()

    result = run_flood_alert(csv_weight=csv_weight)

    # ── Display results ──────────────────────────────────────
    print("\n" + "═" * 70)
    print("  📋  FINAL FLOOD RISK REPORT")
    print("═" * 70)
    print()

    print("─── CSV Analysis Summary ───")
    csv_summary = result.get("csv_analysis", "N/A")
    if len(csv_summary) > 500:
        print(csv_summary[:500] + "…\n(truncated for display)")
    else:
        print(csv_summary)

    print()
    print("─── Web Intelligence Summary ───")
    web_summary = result.get("web_intelligence", "N/A")
    if len(web_summary) > 500:
        print(web_summary[:500] + "…\n(truncated for display)")
    else:
        print(web_summary)

    print()
    print("═" * 70)
    print("  🧠  ORCHESTRATOR ANALYSIS")
    print("═" * 70)
    print()
    print(result.get("report", "No report generated."))

    print()
    print("─" * 70)
    if result.get("email_sent"):
        print("  📧  EMAIL ALERT: ✅ Sent successfully")
    else:
        print("  📧  EMAIL ALERT: ❌ Not triggered (no CRITICAL/HIGH severity)")

    if result.get("errors"):
        print(f"  ⚠️  Errors: {result['errors']}")

    print("─" * 70)
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HeliosCommand — Healthcare Assistant & Flood Alert System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main
    Start interactive healthcare session

  python -m app.main "nearest hospital in Adyar"
    Query hospital finder

  python -m app.main "pharmacies near Velachery"
    Query medical shop locator

  python -m app.main --flood-alert
    Run the parallel flood alert analysis workflow

  python -m app.main --flood-alert --csv-weight 0.8
    Run flood alert giving 80% weight to CSV sensor data
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Single query to process (if omitted, starts interactive session)",
    )
    parser.add_argument(
        "--conversation-id",
        help="Resume existing conversation by ID",
    )
    parser.add_argument(
        "--flood-alert",
        action="store_true",
        help="Run the Flood Alert parallel multi-agent workflow",
    )
    parser.add_argument(
        "--csv-weight",
        type=float,
        default=0.5,
        help="Weight to assign to CSV data (0.0 to 1.0). Default is 0.5 (equal weight).",
    )

    args = parser.parse_args()

    if args.flood_alert:
        run_flood_alert_workflow(csv_weight=args.csv_weight)
    elif args.query:
        result = run(args.query, conversation_id=args.conversation_id)
        print(f"\nAssistant: {result}\n")
    else:
        run_interactive(conversation_id=args.conversation_id)

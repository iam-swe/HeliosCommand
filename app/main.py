"""Main entry point for HeliosCommand — Healthcare Assistant.

This CLI demonstrates the multi-agentic workflow that coordinates:
  - Hospital finder (HospitalAnalyserAgent)
  - Medical shop locator (MedicalShopAgent)
  - Email sender (via Gmail API)

All routed by the OrchestratorAgent using LangGraph's create_react_agent.
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HeliosCommand — Healthcare Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main
    Start interactive session

  python -m app.main "nearest hospital in Adyar"
    Query hospital finder

  python -m app.main "pharmacies near Velachery"
    Query medical shop locator
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

    args = parser.parse_args()

    if args.query:
        result = run(args.query, conversation_id=args.conversation_id)
        print(f"\nAssistant: {result}\n")
    else:
        run_interactive(conversation_id=args.conversation_id)

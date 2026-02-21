"""Main entry point for HeliosCommand — Healthcare Assistant.

This CLI demonstrates the multi-agentic workflow that coordinates:
  • Hospital finder (HospitalAnalyserAgent)
  • Medical shop locator (MedicalShopAgent)  
  • Email sender (via Gmail API)

All routed by the OrchestratorAgent.
"""
import sys
import os

from app.workflows import MultiAgentWorkflow


def create_app(conversation_id=None, use_langgraph=True):
    """Create and initialize the workflow."""
    return MultiAgentWorkflow(conversation_id=conversation_id, use_langgraph=use_langgraph)


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
    print("-" * 70 + "\n")

    workflow = create_app(conversation_id)
    
    # Print initial greeting
    greeting = workflow.get_greeting()
    print(f"Assistant: {greeting}\n")

    # Main conversation loop
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                print("\nAssistant: Thank you for using HeliosCommand. Stay healthy! Goodbye.\n")
                break

            # Process query through workflow
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
    """Alias for run_interactive_session."""
    run_interactive(conversation_id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HeliosCommand — Healthcare Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main
    Start interactive session

  python -m src.main "nearest hospital in Adyar"
    Query hospital finder

  python -m src.main "pharmacies near Velachery"
    Query medical shop locator
        """,
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Single query to process (if omitted, starts interactive session)",
    )
    parser.add_argument(
        "--no-langgraph",
        action="store_true",
        help="Disable LangGraph and use simple fallback mode",
    )
    parser.add_argument(
        "--conversation-id",
        help="Resume existing conversation by ID",
    )

    args = parser.parse_args()

    if args.query:
        # Single query mode
        result = run(args.query, conversation_id=args.conversation_id)
        print(f"\nAssistant: {result}\n")
    else:
        # Interactive mode
        run_interactive(conversation_id=args.conversation_id)


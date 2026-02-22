"""Entry point for the Flood Alert Workflow.

Usage:
    uv run python -m app.flood_alert

This triggers the parallel multi-agent flood analysis pipeline:
  1. CSV Analyst agent — analyses sensor data from flood_detection_data.csv
  2. Web Scraper agent — scrapes flood intel from web & social media
  3. Flood Orchestrator — combines results & sends email if severe
"""

import os
import sys

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

from app.workflows.flood_alert_workflow import run_flood_alert


def main():
    """Run the flood alert workflow and display the results."""

    print("\n" + "═" * 70)
    print("  🌊  HeliosCommand — FLOOD ALERT SYSTEM")
    print("═" * 70)
    print()
    print("  This system runs TWO agents in PARALLEL:")
    print("  📊 Agent 1: CSV Sensor Data Analyst")
    print("  🌐 Agent 2: Web & Social Media Scraper")
    print()
    print("  Both feed into the Flood Orchestrator which")
    print("  analyses severity and sends email alerts if needed.")
    print()
    print("─" * 70)
    print()

    result = run_flood_alert()

    # Display results
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
    main()

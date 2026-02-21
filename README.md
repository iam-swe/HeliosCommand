HeliosCommand — Healthcare Assistant
=====================================

A **multi-agentic LangGraph workflow** that orchestrates healthcare agents for hospital lookup, medical shop search, and email sending using Google APIs and Gmail.

## Quick Start

```bash
# Set environment variables
export GOOGLE_API_KEY="<your-maps-api-key>"
export GMAIL_BEARER_TOKEN="<your-oauth2-token>"

# Install dependencies
pip install requests langchain-core langgraph

# Run interactive session
python -m src.main

# Or single query
python -m src.main "nearest hospital in Adyar, Chennai"
```

## Architecture

The system uses **LangGraph StateGraph** to coordinate multi-agent workflow:

```
src/
├── app/                                # Main implementation package
│   ├── agents/
│   │   ├── base_agent.py                  # BaseAgent class
│   │   ├── orchestrator_agent.py          # Routes queries to agents
│   │   ├── hospital_agent.py              # Finds nearest hospitals
│   │   └── medical_shop_agent.py          # Searches nearby medical shops
│   ├── tools/
│   │   ├── hospital_tools.py              # Geocoding & distance logic
│   │   ├── email_tool.py                  # Gmail API helper
│   │   ├── agent_tools.py                 # Wraps agents as tool callables
│   │   └── tool_registry.py               # Tool registration
│   └── workflows/
│       ├── state.py                       # HeliosState (TypedDict)
│       └── multi_agentic_workflow.py      # LangGraph workflow
├── agents/ & tools/                    # Thin wrappers (backward compatibility)
├── main.py                             # CLI entrypoint
└── chennai_hospitals_dshm.csv          # Hospital dataset
```

## Multi-Agentic Workflow

### LangGraph Integration

The **MultiAgentWorkflow** uses LangGraph with:
- **HeliosState**: Messages, user_query, orchestrator_result, turn_count, user_intent
- **Single Orchestrator Node**: Routes queries to specialized agents
- **Memory Checkpointer**: Maintains conversation state
- **Graceful Fallback**: Works without LangGraph if unavailable

### Execution Flow

```
User Input
    ↓
[HeliosState initialized/updated]
    ↓
orchestrator_node (processes state)
    ↓
OrchestratorAgent (keyword-based routing)
    ↓
Specialized Agent (hospital_analyser | medical_shops | send_email)
    ↓
Tool Execution (Google APIs)
    ↓
Formatted Response
    ↓
Chat Output + History Storage
```

## Agent Details

| Agent | Routes on | Delegates to | Returns |
|-------|-----------|--------------|---------|
| **OrchestratorAgent** | All queries | HospitalAnalyser, MedicalShop, or Gmail | Result from agent tool |
| **HospitalAnalyserAgent** | hospital/beds/icu keywords | find_nearest_hospital() | Hospital name, distance km, ETA min |
| **MedicalShopAgent** | pharmacy/shop keywords | search_medical_shops_nearby() | List of Places API results |

## Requirements

- Python 3.8+
- `requests` library

```bash
pip install requests
```

## Environment Variables

Create a `.env` file in the root or export:

```bash
export GOOGLE_API_KEY="<your-google-maps-places-api-key>"
export GMAIL_BEARER_TOKEN="<your-oauth2-bearer-token>"
export GMAIL_USER_ID="me"  # Optional, defaults to 'me'
```

**Getting credentials:**
1. **GOOGLE_API_KEY**: Enable Maps & Places API in [Google Cloud Console](https://console.cloud.google.com)
2. **GMAIL_BEARER_TOKEN**: Use [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground) to get a bearer token for Gmail API

## Quick Start

```bash
cd /Users/swethaa/Desktop/HeliosCommand
python -m src.main
```

## Example Interactions

**Find nearest hospital:**
```bash
$ python -m src.main "nearest hospital in Adyar, Chennai"
Assistant: Found: Fortis Malar Hospital, Adyar | Distance: 1.234 km | ETA: 2 min
```

**Search medical shops:**
```bash
$ python -m src.main "pharmacies near Velachery, Chennai"
Assistant: Found 3 nearby places. First: MedPlus Pharmacy
```

**Interactive mode:**
```bash
$ python -m src.main
Assistant: Welcome to HeliosCommand! Tell me your location or what you need: nearest hospital, pharmacy nearby, or send an email.

You: nearest hospital in Adyar
Assistant: Found: Fortis Malar Hospital, Adyar | Distance: 1.234 km | ETA: 2 min

You: quit
Assistant: Thank you for using HeliosCommand. Stay healthy! Goodbye.
```

## Python API

```python
from app.workflows import MultiAgentWorkflow

# Initialize workflow
workflow = MultiAgentWorkflow()

# Get greeting
print(workflow.get_greeting())

# Single query
response = workflow.chat("nearest hospital in Adyar, Chennai")
print(response)

# Access conversation history
history = workflow.get_conversation_history()

# Get current state
state = workflow.get_state()
print(f"Turn count: {state['turn_count']}")
print(f"Messages: {len(state['messages'])}")

# Reset conversation
workflow.reset()
```

## Command-Line Options

```bash
python -m src.main --help

# Run with specific conversation ID (for resuming)
python -m src.main --conversation-id "helios_12345"

# Disable LangGraph (use fallback mode)
python -m src.main --no-langgraph
```

## API Endpoints Used

| Service | Endpoint | Method | Purpose |
|---------|----------|--------|---------|
| Google Maps | `maps.googleapis.com/maps/api/geocode/json` | GET | Address → Latitude/Longitude |
| Google Places | `places.googleapis.com/v1/places:searchNearby` | POST | Find nearby medical shops |
| Gmail | `gmail.googleapis.com/gmail/v1/users/{userId}/messages/send` | POST | Send email |

## Workflow Documentation

For detailed architecture, see [WORKFLOW_ARCHITECTURE.md](WORKFLOW_ARCHITECTURE.md)

Key features:
- **LangGraph Integration**: StateGraph with HeliosState (TypedDict)
- **Conversation History**: In-memory storage of all messages
- **Graceful Degradation**: Falls back to simple mode if LangGraph unavailable
- **Extensible Design**: Add new agents and tools easily

## Troubleshooting

### Missing GOOGLE_API_KEY

```
Error: GOOGLE_API_KEY is required
```

Set the environment variable:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### Gmail API Error

```
Error: Gmail API error: 401 Unauthorized
```

Ensure `GMAIL_BEARER_TOKEN` is a valid OAuth2 access token (not an API key):
```bash
export GMAIL_BEARER_TOKEN="ya29.your-valid-token"
```

### LangGraph Not Available

If LangGraph is not installed, the workflow automatically uses fallback mode:
```bash
pip install langchain-core langgraph
```

## Notes

- **ETA Estimation**: Uses crude 30 km/h average speed. For real routing, use `computeRouteMatrix` API
- **Places API**: Requires appropriate pricing tier; check quotas in Google Cloud Console
- **Gmail OAuth**: Tokens expire; use refresh tokens for production deployments
- **Dataset**: Hospital data is limited to Chennai; can be extended with other regions

## Future Enhancements

1. Add async/await support for long-running operations
2. Implement file-based conversation persistence
3. Add ML-based intent classifier (vs keyword-based)
4. Support multiple cities/regions
5. Add user confirmation workflow (before taking action)
6. Integrate with real hospital management systems

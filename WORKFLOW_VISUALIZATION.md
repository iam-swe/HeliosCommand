HeliosCommand — Multi-Agentic Workflow Visualization
========================================================

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        User Interaction Layer                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐         ┌──────────────────┐                   │
│  │   CLI Entry     │         │   Python API     │                   │
│  │  (src/main.py)  │         │  (import & use)  │                   │
│  └────────┬────────┘         └────────┬─────────┘                   │
│           │                           │                              │
│           └───────────────┬───────────┘                              │
│                           ▼                                          │
│               ┌─────────────────────────┐                            │
│               │ MultiAgentWorkflow.chat │                           │
│               └────────────┬────────────┘                            │
│                            │                                         │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Workflow Layer (LangGraph)                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  process_query(user_message)                                         │
│       │                                                              │
│       ├─► Initialize/Update HeliosState                              │
│       │   ├─ messages: [ HumanMessage(content) ]                     │
│       │   ├─ user_query: "nearest hospital in Adyar"                 │
│       │   ├─ turn_count: increment                                   │
│       │   └─ user_intent: (empty)                                    │
│       │                                                              │
│       └─► StateGraph.invoke(state, config)                           │
│           ▼                                                          │
│           ┌──────────────────────────────────┐                       │
│           │      orchestrator_node()         │                       │
│           │                                  │                       │
│           │  1. Extract user_query from state│                       │
│           │  2. Call OrchestratorAgent       │                       │
│           │  3. Store result in state        │                       │
│           │  4. Increment turn_count         │                       │
│           │  5. Return updated state         │                       │
│           └───────────────┬──────────────────┘                       │
│                           │                                         │
│                           ▼                                         │
│           ┌──────────────────────────────────┐                       │
│           │   Final State with results       │                       │
│           └───────────────┬──────────────────┘                       │
│                           │                                         │
│       ┌───────────────────┘                                          │
│       │                                                              │
│       ├─► Format Response                                           │
│       ├─► Store in History                                          │
│       └─► Return to User                                            │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Agent Routing Layer                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  OrchestratorAgent._decide(query)                                     │
│       │                                                              │
│       ├─► Keyword Detection                                         │
│       │   ├─ "hospital|beds|icu" ──► HospitalAnalyserAgent          │
│       │   ├─ "pharmacy|shop" ──────► MedicalShopAgent               │
│       │   ├─ "email|send" ─────────► send_email()                   │
│       │   └─ (default) ────────────► HospitalAnalyserAgent          │
│       │                                                              │
│       └─► Get Tool from Registry                                    │
│           └─► Call tool(query)                                      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
   ┌────────────┐    ┌────────────┐    ┌────────────┐
   │  Hospital  │    │   Medical  │    │   Gmail    │
   │  Analyser  │    │    Shop    │    │    Send    │
   │   Agent    │    │   Agent    │    │   Helper   │
   └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
         │                 │                  │
         ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│            Tool Execution Layer (Google APIs)           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────┐  ┌────────────────┐               │
│  │   Geocoding    │  │    Hospital    │               │
│  │   API (GET)    │  │   CSV Dataset  │               │
│  │                │  │  (Haversine)   │               │
│  │ Address        │  │                │               │
│  │ ↓              │  │ Distance       │               │
│  │ Lat/Lng        │  │ ↓              │               │
│  └────────────────┘  │ Hospital Info  │               │
│                      └────────────────┘               │
│                                                         │
│  ┌────────────────┐  ┌────────────────┐               │
│  │   Geocoding    │  │   Places API   │               │
│  │   API (GET)    │  │   (POST)       │               │
│  │                │  │                │               │
│  │ Address        │  │ Nearby Shops   │               │
│  │ ↓              │  │ ↓              │               │
│  │ Lat/Lng        │  │ Places List    │               │
│  └────────────────┘  └────────────────┘               │
│                                                         │
│  ┌─────────────────────────────────────────────┐      │
│  │            Gmail API (POST)                  │      │
│  │                                              │      │
│  │  Email Message → Base64 Encode              │      │
│  │  ↓                                           │      │
│  │  Send via /messages/send endpoint           │      │
│  │  ↓                                           │      │
│  │  Confirmation                               │      │
│  └─────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │   Result     │
                  │   JSON       │
                  └──────┬───────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
      ┌─────────┐   ┌──────────┐   ┌──────────┐
      │Hospital │   │  Places  │   │  Email   │
      │Details  │   │  List    │   │   Sent   │
      └─────────┘   └──────────┘   └──────────┘
          │              │              │
          └──────────────┼──────────────┘
                         ▼
          ┌──────────────────────────┐
          │  Format Response String  │
          │                          │
          │ "Found: X | Distance: Y  │
          │ km | ETA: Z min"         │
          └──────────┬───────────────┘
                     │
                     ▼
          ┌──────────────────────────┐
          │    Display to User       │
          └──────────────────────────┘
```

## State Flow Diagram

```
┌────────────────────────────────────────────────────────────┐
│  Initial State (get_initial_state())                       │
├────────────────────────────────────────────────────────────┤
│ {                                                           │
│   "messages": [],                                           │
│   "user_query": "",                                         │
│   "orchestrator_result": "",                                │
│   "turn_count": 0,                                          │
│   "user_intent": "unknown"                                  │
│ }                                                           │
└────────────────────┬───────────────────────────────────────┘
                     │
        User Input: "nearest hospital"
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  State After process_query() - Turn 1                       │
├────────────────────────────────────────────────────────────┤
│ {                                                           │
│   "messages": [                                             │
│     HumanMessage("nearest hospital")                        │
│   ],                                                        │
│   "user_query": "nearest hospital",                         │
│   "orchestrator_result": "",  ← Will be filled by node     │
│   "turn_count": 0,            ← Will be incremented        │
│   "user_intent": "unknown"                                  │
│ }                                                           │
└────────────────────┬───────────────────────────────────────┘
                     │
          orchestrator_node processes
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  State After orchestrator_node Execution                   │
├────────────────────────────────────────────────────────────┤
│ {                                                           │
│   "messages": [                                             │
│     HumanMessage("nearest hospital")                        │
│   ],                                                        │
│   "user_query": "nearest hospital",                         │
│   "orchestrator_result": "{                                │
│       \"success\": true,                                    │
│       \"orchestrator_result\": {                            │
│         \"nearest\": {...},                                 │
│         \"distance_km\": 2.341,                             │
│         \"eta_minutes\": 5                                  │
│       }                                                     │
│     }",                                                     │
│   "turn_count": 1,                                          │
│   "user_intent": "unknown"  ← Can be populated later      │
│ }                                                           │
└────────────────────┬───────────────────────────────────────┘
                     │
        Format & Return to User
                     │
                     ▼
          ┌────────────────────┐
          │ "Found: Hospital   │
          │ Distance: 2.341 km │
          │ ETA: 5 min"        │
          └────────────────────┘
```

## Message Flow Diagram

```
USER
  │
  ├─ (Text Input) ─────────────┐
  │                             │
  │                             ▼
  │                    CLI (src/main.py)
  │                             │
  │                             ▼
  │                   MultiAgentWorkflow()
  │                             │
  │                             ├─► chat(query)
  │                             │      ↓
  │                             │  process_query()
  │                             │      ↓
  │                             │  StateGraph.invoke()
  │                             │      ↓
  │                             │  orchestrator_node()
  │                             │      ↓
  │                             │  OrchestratorAgent
  │                             │      ↓
  │                             │  [agent_tool called]
  │                             │      ↓
  │                             │  Google API
  │                             │      ↓
  │                             │  Result JSON
  │                             │      ↓
  │                             │  Format Response
  │                             │      ↓
  │                             │  Store in History
  │                             │      ↓
  └─────────────────────────────┘  Return Response
                                        │
                                        ▼
                                      USER
                            (Formatted Text Output)
```

## Component Interaction Matrix

```
┌─────────────────────┬─────────────────┬──────────────────┐
│ Component A         │ Component B     │ Interaction      │
├─────────────────────┼─────────────────┼──────────────────┤
│ MultiAgentWorkflow  │ OrchestratorAgt │ Calls process_q  │
│ OrchestratorAgt     │ Tool Registry   │ Gets tool func   │
│ Tool Registry       │ Agent Tools     │ Returns callable │
│ Agent Tools         │ Specialized Agt │ Calls agent      │
│ HospitalAnalyser    │ hospital_tools  │ Calls geocode    │
│ MedicalShop         │ hospital_tools  │ Calls search     │
│ hospital_tools      │ Google APIs     │ HTTP requests    │
│ email_tool          │ Gmail API       │ POST /send       │
│ Workflows/State     │ MultiAgentWF    │ Provides HeliosS │
│ LangGraph           │ StateGraph      │ Orchestrates     │
└─────────────────────┴─────────────────┴──────────────────┘
```

## Data Flow End-to-End

```
INPUT: "nearest hospital in Adyar, Chennai"
   │
   ├─► CLI (src/main.py)
   │   └─► MultiAgentWorkflow.chat()
   │       └─► process_query()
   │           ├─► Create/Update HeliosState
   │           │
   │           ├─► StateGraph.invoke()
   │           │   └─► orchestrator_node()
   │           │       ├─► Extract user_query
   │           │       ├─► OrchestratorAgent.process_query()
   │           │       │   ├─► Detect keyword: "hospital"
   │           │       │   ├─► Get tool: hospital_analyser
   │           │       │   └─► Call tool(query)
   │           │       │       └─► HospitalAnalyserAgent
   │           │       │           └─► find_nearest_hospital()
   │           │       │               ├─► _geocode_address()
   │           │       │               │   └─► Google Geocoding API
   │           │       │               │       └─► Lat: 13.0067, Lng: 80.2565
   │           │       │               │
   │           │       │               ├─► _load_hospitals()
   │           │       │               │   └─► Read CSV
   │           │       │               │
   │           │       │               ├─► Find nearest (Haversine)
   │           │       │               │   └─► Fortis Malar Hospital
   │           │       │               │
   │           │       │               └─► Return:
   │           │       │                   {
   │           │       │                     "distance_km": 0.567,
   │           │       │                     "eta_minutes": 1,
   │           │       │                     "nearest": {...}
   │           │       │                   }
   │           │       │
   │           │       └─► Store in orchestrator_result
   │           │           └─► Return updated state
   │           │
   │           ├─► _format_response()
   │           │   └─► Extract & prettify result
   │           │
   │           ├─► Store in history
   │           │   ├─ {"role": "user", "content": "..."}
   │           │   └─ {"role": "assistant", "content": "..."}
   │           │
   │           └─► Return formatted response
   │
   └─► Display to User
       └─► "Found: Fortis Malar Hospital, Adyar | Distance: 0.567 km | ETA: 1 min"

OUTPUT: User receives formatted hospital information
```

---

This visualization shows:
1. **Architecture Layers**: User → Workflow → Agents → Tools → APIs
2. **State Evolution**: How HeliosState changes through execution
3. **Message Flow**: Complete request-response cycle
4. **Component Interactions**: Which modules talk to which
5. **Data Flow**: End-to-end information transformation

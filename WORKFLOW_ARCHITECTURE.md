"""
HeliosCommand Multi-Agentic Workflow Architecture
===================================================

This document describes the multi-agentic workflow that coordinates multiple
healthcare agents for hospital lookup, medical shop search, and email sending.

## Architecture Overview

The workflow follows a LangGraph-based multi-agent pattern:

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│  HeliosState (TypedDict)        │
│  - messages                     │
│  - user_query                   │
│  - orchestrator_result          │
│  - turn_count                   │
│  - user_intent                  │
└────────┬────────────────────────┘
         │
         v
┌──────────────────────────────────────────┐
│  LangGraph StateGraph                    │
│  ┌──────────────────────────────────┐   │
│  │  orchestrator_node               │   │
│  │  (routes to agents)              │   │
│  └──────────────────────────────────┘   │
└────────┬─────────────────────────────────┘
         │
         v
┌──────────────────────────────────────────┐
│  OrchestratorAgent                       │
│  ┌─────────────────────────────────────┐ │
│  │ Keyword-based routing               │ │
│  │  • hospital → HospitalAnalyser      │ │
│  │  • pharmacy → MedicalShop           │ │
│  │  • email → SendEmail                │ │
│  └─────────────────────────────────────┘ │
└────────┬─────────────────────────────────┘
         │
         v
┌──────────────────────────────────────────────┐
│  Specialized Agents                          │
│  ┌──────────────────┐ ┌──────────────────┐  │
│  │ HospitalAnalyser │ │ MedicalShop      │  │
│  │ - Geocodes addr  │ │ - Geocodes addr  │  │
│  │ - Finds nearest  │ │ - Places API     │  │
│  │ - Distance + ETA │ │ - Returns list   │  │
│  └──────────────────┘ └──────────────────┘  │
└──────────────────────────────────────────────┘
         │
         v
┌──────────────────────────────────┐
│  Formatted Response              │
│  Ready for display               │
└──────────────────────────────────┘
```

## State Management

### HeliosState (TypedDict)

```python
class HeliosState(TypedDict, total=False):
    messages: List[Any]           # Message history
    user_query: str              # Current user input
    orchestrator_result: str     # JSON result from orchestrator
    turn_count: int              # Conversation turn counter
    user_intent: str             # Detected intent (hospital/pharmacy/email)
```

## Workflow Components

### MultiAgentWorkflow

Main class that:
- Initializes LangGraph StateGraph with HeliosState
- Creates and manages orchestrator_node
- Stores conversation history
- Provides chat interface (like SVCE's MultiAgentWorkflow)
- Falls back to simple mode if LangGraph unavailable

**Key methods:**
- `process_query(user_message)` - Process message through workflow
- `chat(user_message)` - Simple chat interface
- `get_greeting()` - Greeting message
- `reset()` - Reset conversation
- `get_conversation_history()` - Access message history
- `get_state()` - Current workflow state

### Orchestrator Node

Function: `_orchestrator_node(state: HeliosState) -> HeliosState`

Responsibilities:
1. Extract user_query from state
2. Call OrchestratorAgent.process_query()
3. Store result in orchestrator_result (JSON serialized)
4. Increment turn_count
5. Return updated state

### Message Handling

- Messages can be langchain `HumanMessage`/`AIMessage` (if LangGraph available)
- Fallback to dict format: `{"role": "user"|"assistant", "content": "..."}` 
- All messages stored in conversation history

## LangGraph Integration

### Graph Structure
- **START** → **orchestrator** → **END**

### Node Execution
- Single orchestrator node processes all queries
- State passed through node and updated
- Message history automatically maintained by StateGraph

### Fallback Mode

If LangGraph not available:
- Workflow still functions with simple orchestrator call
- No state graph compilation
- Manual state management
- Same public API

## Conversation History

- Each turn: user message + assistant response stored
- Accessible via `get_conversation_history()`
- Format: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`

## Response Formatting

`_format_response(result: str) -> str` extracts meaningful info from orchestrator results:
- Hospital found: "Found: X | Distance: Y km | ETA: Z min"
- Medical shops found: "Found N nearby places. First: Name"
- Errors: Error message from tool

## Example Usage

```python
from app.workflows import MultiAgentWorkflow

# Initialize
workflow = MultiAgentWorkflow()
print(workflow.get_greeting())

# Chat loop
while True:
    user_input = input("You: ")
    response = workflow.chat(user_input)
    print(f"Assistant: {response}")

# Access history
history = workflow.get_conversation_history()

# Reset conversation
workflow.reset()
```

## Comparison with SVCE

| Feature | SVCE | HeliosCommand |
|---------|------|--------------|
| Graph Type | Multi-node (orchestrator + specialized nodes) | Single orchestrator node |
| State Management | ExamHelperState | HeliosState |
| Agents | LLM-based (Gemini, LangChain) | Rule-based router |
| Tools | LangChain tools (structured) | Direct agent callables |
| Conversation Store | File-based (JSON) | In-memory list |
| LangGraph | Required | Optional (graceful fallback) |
| Async Support | Full async/await | Sync only (can add) |

## Future Enhancements

1. **Async Support**: Add `aprocess_query_async()` for async node processing
2. **Persistence**: Add file-based conversation storage (like SVCE)
3. **More Nodes**: Split orchestrator into routing + confirmation nodes
4. **State Transitions**: Add user confirmation workflow ("Is this OK?")
5. **Better Intent Detection**: Rule-based → ML-based intent classifier
6. **Tool Execution Tracking**: Record which tools were called and their outputs
"""

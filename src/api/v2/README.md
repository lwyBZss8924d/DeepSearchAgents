# DeepSearchAgents Web API v2

A simplified, real-time API for interaction with DeepSearchAgents through WebSocket streaming. This API processes agent execution events and streams them with metadata-driven component routing for the frontend.

## Overview

The Web API v2 is designed with simplicity and reliability in mind:

- **Real-time streaming** via WebSocket with event-driven architecture
- **Metadata-driven routing** for frontend component selection
- **Session management** for multi-turn conversations
- **Direct event processing** from smolagents with minimal transformation
- **Support for streaming** with initial → delta → final message pattern

## Architecture

```
┌─────────────┐        WebSocket         ┌──────────────┐
│   Web UI    │ ◄───────────────────────► │ WebSocket    │
│  (Frontend) │                           │ Endpoint     │
└─────────────┘                           └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   Session    │
                                          │  Manager     │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   web_ui     │
                                          │  Processor   │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │ Agent Events │
                                          │(smolagents)  │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │    Agent     │
                                          │(React/CodeAct)│
                                          └──────────────┘
```

## Design Principles

The v2 API follows these core principles:

1. **Event-Driven Processing**: Directly processes smolagents events (PlanningStep, ActionStep, etc.)
2. **Metadata-Based Routing**: Each message includes metadata for frontend component selection
3. **Minimal Transformation**: Events are enhanced with routing metadata, not transformed
4. **Streaming Support**: Handles both streaming and non-streaming agent configurations
5. **Session Isolation**: Each WebSocket connection maintains its own agent session

## Quick Start

### 1. Start the API Server

The v2 API is integrated into the main FastAPI application:

```bash
# Start the main server (includes v2 endpoints)
python -m src.main --port 8000

# The v2 endpoints will be available at:
# - WebSocket: ws://localhost:8000/api/v2/ws/{session_id}
# - REST: http://localhost:8000/api/v2/*
```

### 2. Connect via WebSocket

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v2/ws/my-session?agent_type=codact');

// Handle incoming messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
  
  // Route based on metadata
  if (message.metadata?.component === 'chat') {
    // Display in chat
  } else if (message.metadata?.component === 'webide') {
    // Show in code editor
  } else if (message.metadata?.component === 'terminal') {
    // Display in terminal
  }
};

// Send a query
ws.send(JSON.stringify({
  type: 'query',
  query: 'What is the capital of France?'
}));
```

## Message Format

### DSAgentRunMessage

All messages follow this structure:

```typescript
interface DSAgentRunMessage {
  // Core fields
  role: 'user' | 'assistant';
  content: string;
  message_id: string;
  timestamp: string;
  
  // Metadata for routing and display
  metadata: {
    // Component routing
    component?: 'chat' | 'webide' | 'terminal';
    
    // Message type identification
    message_type?: 'planning_header' | 'planning_content' | 'action_thought' | 
                   'tool_call' | 'final_answer' | 'error' | etc.;
    
    // Step information
    step_type?: 'planning' | 'action' | 'final_answer';
    step_number?: number;
    
    // Planning specific
    planning_type?: 'initial' | 'update';
    
    // Action specific
    tool_name?: string;
    thoughts_content?: string;  // First 60 chars of thinking
    
    // Final answer specific
    has_structured_data?: boolean;
    answer_title?: string;
    answer_content?: string;
    answer_sources?: string[];
    
    // Streaming state
    streaming?: boolean;
    is_delta?: boolean;
    stream_id?: string;
    
    // Status
    status?: 'streaming' | 'done';
    error?: boolean;
  };
  
  // Context
  session_id?: string;
  step_number?: number;
}
```

## WebSocket Protocol

### Client → Server

```json
// Submit a query
{
  "type": "query",
  "query": "Your question here"
}

// Ping (keepalive)
{
  "type": "ping"
}

// Get session messages
{
  "type": "get_messages",
  "limit": 100
}

// Get session state
{
  "type": "get_state"
}
```

### Server → Client

The server streams various message types:

#### Planning Messages
```json
// Planning header (badge)
{
  "role": "assistant",
  "content": "",
  "metadata": {
    "component": "chat",
    "message_type": "planning_header",
    "planning_type": "initial",
    "status": "done"
  }
}

// Planning content
{
  "role": "assistant",
  "content": "I'll help you find information about...",
  "metadata": {
    "component": "chat",
    "message_type": "planning_content",
    "planning_type": "initial"
  }
}
```

#### Action Messages
```json
// Action thought
{
  "role": "assistant",
  "content": "Let me search for that information...",
  "metadata": {
    "component": "chat",
    "message_type": "action_thought",
    "thoughts_content": "Let me search for that inf...",
    "status": "done"
  }
}

// Tool call
{
  "role": "assistant",
  "content": "",
  "metadata": {
    "component": "chat",
    "message_type": "tool_call",
    "tool_name": "search",
    "tool_args_summary": "query=capital of France"
  }
}
```

#### Streaming Messages
```json
// Initial streaming message
{
  "role": "assistant",
  "content": "",
  "metadata": {
    "streaming": true,
    "is_initial_stream": true,
    "stream_id": "msg-1-planning_content-stream"
  }
}

// Delta updates
{
  "role": "assistant",
  "content": "The capital of France is ",
  "metadata": {
    "streaming": true,
    "is_delta": true,
    "stream_id": "msg-1-planning_content-stream"
  }
}
```

## REST Endpoints

### Session Management

- `POST /api/v2/sessions` - Create a new session
  ```json
  {
    "agent_type": "codact",
    "max_steps": 30
  }
  ```

- `GET /api/v2/sessions` - List active sessions
- `GET /api/v2/sessions/{session_id}` - Get session info
- `DELETE /api/v2/sessions/{session_id}` - Delete session
- `GET /api/v2/sessions/{session_id}/messages` - Get session messages

### Health Check

- `GET /api/v2/health` - API health status

## Session Management

Sessions provide conversation isolation and state management:

- **Unique session ID** per conversation
- **Agent instance** per session (React or CodeAct)
- **Message history** with configurable limit (default 10,000)
- **Automatic cleanup** of expired sessions (1 hour timeout)
- **Session states**: idle, processing, completed, error, expired

## Configuration

### Agent Configuration

Sessions can be configured with:
- `agent_type`: "react" or "codact" (default: "codact")
- `max_steps`: Maximum agent steps (default: 25)

### Streaming Configuration

Streaming is controlled by agent configuration in `config.toml`:

```toml
[agents.codact]
enable_streaming = true
```

## Implementation Details

### web_ui.py Processing

The core processing happens in `web_ui.py`:

1. **Event Processing**: Handles PlanningStep, ActionStep, FinalAnswerStep, ChatMessageStreamDelta
2. **Metadata Enrichment**: Adds component routing and UI-specific metadata
3. **Content Formatting**: Handles code blocks, truncation, structured data
4. **Streaming Context**: Maintains state across streaming messages

### Message Type Mapping

- **PlanningStep** → planning_header, planning_content, planning_footer
- **ActionStep** → action_header, action_thought, tool_call, tool_invocation, execution_logs
- **FinalAnswerStep** → final_answer (with structured data support)
- **ChatMessageStreamDelta** → streaming deltas with appropriate message_type

### Component Routing Logic

Messages are routed to frontend components based on metadata:

- **Chat Component** (`component: "chat"`):
  - Planning messages
  - Action thoughts
  - Tool call badges
  - Final answers
  - General messages

- **Code Editor** (`component: "webide"`):
  - Python code execution
  - Code with syntax highlighting

- **Terminal** (`component: "terminal"`):
  - Execution logs
  - Command outputs
  - Error traces

## Error Handling

Errors are returned as DSAgentRunMessage with error metadata:

```json
{
  "role": "assistant",
  "content": "Error: Failed to execute query",
  "metadata": {
    "component": "chat",
    "message_type": "error",
    "error": true,
    "error_type": "RuntimeError",
    "status": "done"
  }
}
```

## Frontend Integration

The v2 API is designed for the DeepSearchAgents frontend which:

1. Connects via WebSocket
2. Routes messages based on metadata.component
3. Handles streaming with message accumulation
4. Displays UI elements based on message_type:
   - Planning badges for planning_header
   - Action thought cards for action_thought
   - Structured cards for final_answer
   - Code editor for webide components
   - Terminal output for terminal components

## Streaming Architecture

### Message Flow
1. **Initial Message**: Empty content with `streaming: true`
2. **Delta Messages**: Incremental updates with `is_delta: true`
3. **Final Message**: Complete content with `streaming: false`

### Frontend Handling
- Accumulate deltas by stream_id
- Replace with final message when streaming completes
- Handle both streaming and non-streaming modes

## Best Practices

1. **Session Management**: Create a new session for each conversation
2. **Error Handling**: Always handle WebSocket disconnections gracefully
3. **Message Routing**: Use metadata.component for UI routing decisions
4. **Streaming**: Accumulate delta messages by stream_id
5. **Keepalive**: Send periodic ping messages to maintain connection

## Migration from v1

Key differences from v1 API:

1. **Simplified Architecture**: Direct event processing instead of complex transformations
2. **Metadata Routing**: Component selection via metadata instead of content parsing
3. **Better Streaming**: Proper delta message handling with stream_id
4. **Session-Based**: Each conversation has its own session and agent instance

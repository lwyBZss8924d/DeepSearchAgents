# DeepSearchAgents Web API v2

A simplified, real-time API for interaction with DeepSearchAgents through WebSocket streaming. This API provides direct pass-through of agent execution messages using the proven `smolagents.gradio_ui` interface.

## Overview

The Web API v2 is designed with simplicity and reliability in mind:

- **Real-time streaming** via WebSocket with direct message pass-through
- **Simple message format** based on Gradio ChatMessage structure
- **Session management** for multi-turn conversations
- **Minimal transformation** - leverages smolagents' battle-tested streaming
- **Clean architecture** with straightforward data flow

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
                                          │   Gradio     │
                                          │ Passthrough  │
                                          │  Processor   │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │stream_to_gradio│
                                          │ (smolagents) │
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

1. **Direct Pass-through**: Messages from `smolagents.gradio_ui.stream_to_gradio` are passed through with minimal transformation
2. **Field Renaming Only**: Gradio ChatMessage fields are renamed to DS-specific names (DSAgentRunMessage)
3. **No Complex Event Parsing**: Avoids fragile regex-based parsing of message content
4. **Leverage Proven Code**: Uses smolagents' well-tested streaming infrastructure
5. **Simple Maintenance**: Minimal custom code means fewer bugs and easier updates

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
  console.log(`${message.role}: ${message.content}`);
};

// Send a query
ws.send(JSON.stringify({
  type: 'query',
  query: 'What is 2 + 2?'
}));
```

## Message Format

### DSAgentRunMessage

All messages follow this simple structure:

```typescript
interface DSAgentRunMessage {
  role: 'user' | 'assistant';
  content: string;
  metadata: Record<string, any>;
  message_id: string;
  timestamp: string;
  session_id?: string;
  step_number?: number;
}
```

This is a direct mapping from Gradio's ChatMessage with DS-specific field names.

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
```

### Server → Client

The server streams DSAgentRunMessage objects as the agent executes:

```json
{
  "role": "assistant",
  "content": "Let me search for that information...",
  "metadata": {"streaming": true},
  "message_id": "msg_abc123",
  "timestamp": "2024-01-20T10:30:00Z",
  "session_id": "my-session",
  "step_number": 1
}
```

## REST Endpoints

### Core Endpoints

- `POST /api/v2/session/create` - Create a new session
- `GET /api/v2/session/{session_id}` - Get session info
- `DELETE /api/v2/session/{session_id}` - Delete session
- `GET /api/v2/sessions` - List active sessions
- `GET /api/v2/health` - Health check

## Session Management

Sessions provide conversation isolation:

- Unique session ID per conversation
- Each session maintains its own agent instance
- Sessions expire after 1 hour of inactivity
- Automatic cleanup of expired sessions

## Implementation Details

### GradioPassthroughProcessor

The core of the v2 API is the `GradioPassthroughProcessor` which:

1. Receives agent and query
2. Calls `smolagents.gradio_ui.stream_to_gradio`
3. Converts Gradio ChatMessages to DSAgentRunMessages
4. Yields messages through async generator

### Why a Separate main.py?

The v2 API has its own `main.py` for:

1. **Development Isolation**: Can be developed/tested independently
2. **Future Flexibility**: Easy to deploy as a separate microservice
3. **Clear Boundaries**: Explicit separation from v1 API
4. **Simplified Testing**: Can be tested without the full application

However, in production, v2 endpoints are mounted into the main FastAPI application.

## Error Handling

Errors are returned as standard messages:

```json
{
  "type": "error",
  "message": "Detailed error message"
}
```

## Examples

See the `src/api/v2/examples/` directory for:

- `test_debug.py` - Direct processor testing
- `test_simple_agent.py` - Agent integration example
- `test_stream_to_gradio.py` - Understanding stream_to_gradio

## Migration from Gradio UI

For users migrating from the legacy Gradio UI:

1. The v2 API provides similar real-time updates
2. Message format is simpler and more predictable
3. No need to run a separate Gradio server
4. Better integration with modern web frameworks

## Future Enhancements

Planned improvements while maintaining simplicity:

1. Message compression for large responses
2. Batch message delivery option
3. GraphQL endpoint for flexible queries
4. WebRTC support for lower latency
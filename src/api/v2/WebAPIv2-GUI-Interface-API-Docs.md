# WebAPIv2-GUI-Interface-API-Docs

## 📋 API Overview
This OpenAPI specification defines a real-time streaming API for interacting with DeepSearchAgents, focusing on direct message pass-through via WebSockets. It includes endpoints for session management, health checks, and WebSocket communication for agent interaction.

### 🌐 Major Endpoints
- **POST /api/v2/sessions** - Creates a new agent session.
- **GET /api/v2/sessions/{session_id}** - Retrieves session information.
- **DELETE /api/v2/sessions/{session_id}** - Deletes a session.
- **GET /api/v2/sessions** - Lists active sessions.
- **GET /api/v2/sessions/{session_id}/messages** - Retrieves messages from a session with pagination.
- **GET /api/v2/health** - Provides a health check for the API.
- **GET /api/v2/ws/{session_id}** - WebSocket endpoint for real-time agent interaction.

### 🤖 Schema Models
- **CreateSessionRequest** - Defines the request body for creating a new session, including agent type and maximum steps.
- **CreateSessionResponse** - Defines the response body for session creation, including session ID, agent type, and WebSocket URL.
- **HealthResponse** - Defines the response body for the health check endpoint, including status, timestamp, active sessions, and version.
- **DSAgentRunMessage** - Represents a message exchanged during an agent run, including role, content, metadata (with streaming, status, title fields), and session information.
- **QueryRequest** - Defines the structure for sending queries to the agent via WebSocket.
- **PingMessage** - Defines the structure for sending ping messages to the agent via WebSocket.
- **PongMessage** - Defines the structure for receiving pong messages from the agent via WebSocket.
- **GetMessagesRequest** - Defines the structure for retrieving message history via WebSocket (with optional limit).
- **GetStateRequest** - Defines the structure for getting session state via WebSocket.
- **StateResponse** - Defines the structure for state response via WebSocket.
- **ErrorMessage** - Defines the structure for error messages sent via WebSocket.
- **SessionState** - Defines the structure for session state information (includes states: idle, processing, completed, error, expired).

### 🔌 WebSocket Protocol
The WebSocket endpoint supports the following message types:

**Client → Server Messages:**
- `{"type": "query", "query": "..."}` - Submit a query for processing
- `{"type": "ping"}` - Keepalive ping
- `{"type": "get_messages", "limit": 100}` - Retrieve message history (limit optional, default: 100)
- `{"type": "get_state"}` - Get current session state

**Server → Client Messages:**
- `DSAgentRunMessage` objects - Streamed during query processing
- `{"type": "pong"}` - Response to ping
- `{"type": "state", "state": {...}}` - Session state response
- `{"type": "error", "message": "...", "error_code": "..."}` - Error messages

### ✨ Special Features & Considerations

- **Real-time Streaming**: Uses WebSockets for real-time communication with the agent.
- **Session Management**: Manages agent sessions, including creation, retrieval, and deletion.
- **Health Check**: Provides an endpoint for monitoring the health of the API.
- **Pagination**: Implements pagination for retrieving messages from a session.
- **Agent Types**: Supports different agent types (e.g., react, codact).
- **Error Handling**: Provides error messages via WebSocket for handling issues during agent interaction.
- **Message Metadata**: Includes streaming status, execution status, and tool information in metadata field.

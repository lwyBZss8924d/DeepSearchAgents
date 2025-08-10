# DeepSearchAgents Frontend - Technical Documentation

This document provides comprehensive technical documentation for the DeepSearchAgents web frontend, including architecture details, message flow, and implementation insights gained from the v0.3.3.dev integration.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Integration](#backend-integration)
3. [Frontend Components](#frontend-components)
4. [Message Protocol](#message-protocol)
5. [Streaming Architecture](#streaming-architecture)
6. [UI Features](#ui-features)
7. [Development Guide](#development-guide)
8. [Debugging Experience](#debugging-experience)

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DeepSearchAgents System                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Backend (Python)                    Frontend (Next.js)      │
│  ┌─────────────────┐               ┌────────────────────┐   │
│  │   Agent Core    │               │   React Frontend   │   │
│  │  ┌───────────┐  │               │  ┌──────────────┐  │   │
│  │  │  CodeAct-DeepSearchAgent  │  │               │  │  AgentChat   │  │   │
│  │  └─────┬─────┘  │               │  └──────┬───────┘  │   │
│  │        │        │               │         │          │   │
│  │  ┌─────▼─────┐  │               │  ┌──────▼───────┐  │   │
│  │  │  web_ui   │  │  WebSocket    │  │  WebSocket   │  │   │
│  │  │ Processor │◄─┼───────────────┼─►│    Hook      │  │   │
│  │  └─────┬─────┘  │               │  └──────┬───────┘  │   │
│  │        │        │               │         │          │   │
│  │  ┌─────▼─────┐  │               │  ┌──────▼───────┐  │   │
│  │  │  Session  │  │               │  │  Component   │  │   │
│  │  │  Manager  │  │               │  │   Router     │  │   │
│  │  └───────────┘  │               │  └──────────────┘  │   │
│  └─────────────────┘               └────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Metadata-Driven Rendering**: UI components are selected based on message metadata, not content parsing
2. **Direct Pass-Through**: Backend uses smolagents' Gradio messages with minimal transformation
3. **Streaming First**: Built for real-time streaming with delta message support
4. **Component Isolation**: Each UI component operates independently based on routing

## Backend Integration

### Web API v2 Structure

```
src/api/v2/
├── endpoints.py         # WebSocket and REST endpoints
├── session.py          # Session management with cleanup
├── web_ui.py           # Agent event processing
├── ds_agent_message_processor.py  # Message processor wrapper
└── models.py           # Pydantic models
```

### Message Processing Pipeline

1. **Agent Events**: smolagents generates events (PlanningStep, ActionStep, FinalAnswerStep)
2. **web_ui.py**: Processes events into DSAgentRunMessage objects with routing metadata
3. **Session Manager**: Maintains conversation state and message history
4. **WebSocket**: Streams messages to frontend in real-time

### Key Backend Components

#### web_ui.py
- Handles all agent event types
- Adds component routing metadata
- Manages streaming vs non-streaming modes
- Enriches messages with UI-specific fields

#### session.py
- Manages WebSocket sessions
- Handles agent lifecycle
- Provides message history
- Automatic cleanup of expired sessions

## Frontend Components

### Component Hierarchy

```
app/page.tsx
└── Home (components/home.tsx)
    └── HomeContent (components/home-content.tsx)
        └── AgentChat (components/agent-chat.tsx)
            ├── ActionThoughtCard
            ├── PlanningCard
            ├── FinalAnswerDisplay
            └── Markdown (default)
```

### Core Components

#### AgentChat (`components/agent-chat.tsx`)
Main chat interface that:
- Receives all messages from WebSocket
- Routes messages based on metadata
- Handles message grouping by step
- Manages scroll behavior

#### ActionThoughtCard (`components/action-thought-card.tsx`)
Displays agent thinking with:
- Truncated content (60 chars)
- Specific format: "Thinking🤔...{content}...and Action Running[Terminal]..."
- Expandable card UI
- Purple color scheme

#### PlanningCard (`components/planning-card.tsx`)
Shows planning steps with:
- Badge display (Initial Plan/Updated Plan)
- Full markdown rendering
- Custom styling for planning content
- Step number tracking

#### FinalAnswerDisplay (`components/final-answer-display.tsx`)
Renders structured final answers:
- Title extraction from metadata
- Markdown content rendering
- Source citations
- Green success styling

### Component Routing Logic

```typescript
// Metadata-based routing in AgentChat
if (message.metadata?.component !== 'chat') {
  return null; // Skip non-chat messages
}

// Message type detection
if (message.metadata?.message_type === 'planning_header') {
  // Render planning badge
} else if (message.metadata?.message_type === 'action_thought') {
  // Render ActionThoughtCard
} else if (message.metadata?.has_structured_data) {
  // Render FinalAnswerDisplay
} else {
  // Render default Markdown
}
```

## Message Protocol

### DSAgentRunMessage Structure

```typescript
interface DSAgentRunMessage {
  // Core fields
  message_id: string;
  role: "user" | "assistant";
  content: string;
  
  // Metadata for routing and rendering
  metadata: {
    // Component routing
    component?: "chat" | "webide" | "terminal";
    
    // Message type identification
    message_type?: string;
    step_type?: "planning" | "action" | "final_answer";
    
    // Planning specific
    planning_type?: "initial" | "update";
    
    // Streaming state
    streaming?: boolean;
    is_delta?: boolean;
    stream_id?: string;
    
    // Action thought specific
    thoughts_content?: string;  // First 60 chars
    is_raw_thought?: boolean;
    
    // Final answer specific
    has_structured_data?: boolean;
    answer_title?: string;
    answer_content?: string;
    answer_sources?: string[];
    
    // Tool execution
    tool_name?: string;
    tool_args?: Record<string, any>;
    
    // Status
    status?: "streaming" | "done";
    error?: boolean;
  };
  
  // Context
  session_id?: string;
  step_number?: number;
  timestamp?: string;
}
```

### Message Types

1. **Planning Messages**
   - `planning_header`: Badge display only
   - `planning_content`: Full planning text
   - `planning_footer`: Timing and token info

2. **Action Messages**
   - `action_thought`: Thinking process
   - `tool_call`: Tool execution details
   - `observation`: Tool results

3. **Final Answer**
   - Detected by `has_structured_data` or content patterns
   - Contains title, content, and sources

## Streaming Architecture

### Streaming Flow

```
1. Initial Message (streaming: true, content: "")
   ↓
2. Delta Updates (is_delta: true, incremental content)
   ↓
3. Final Message (streaming: false, complete content)
```

### WebSocket Hook (`hooks/use-websocket.tsx`)

Key features:
- Automatic reconnection
- Message accumulation for streaming
- Ping/pong keepalive
- Session management
- Debug logging

### Streaming Message Handling

```typescript
// Identify streaming messages by step-type key
const streamKey = `${step_number}-${message_type}`;

// Accumulate delta messages
if (metadata.is_delta) {
  const existing = streamingMessages.get(streamKey);
  const accumulated = existing ? 
    existing.content + content : content;
  
  streamingMessages.set(streamKey, {
    ...message,
    content: accumulated
  });
}

// Replace with final message when streaming ends
if (!metadata.streaming && streamingMessages.has(streamKey)) {
  streamingMessages.delete(streamKey);
}
```

## UI Features

### 1. Planning Badges

Visual indicators for planning steps:
- **Initial Plan**: Blue badge with calendar icon
- **Updated Plan**: Purple badge with refresh icon
- Displayed above planning content
- Step number tracking

### 2. Action Thoughts

Agent thinking visualization:
- Truncated to 60 characters
- Fixed format with emoji and terminal icon
- Expandable card interface
- Purple color scheme for visibility

### 3. Final Answers

Structured response display:
- Green success card styling
- Title extraction from metadata
- Full markdown rendering
- Source citations when available

### 4. Step Separation

Visual organization by execution step:
- Horizontal dividers between steps
- Step number labels
- Grouped message display

## Development Guide

### Setup

1. **Environment Variables** (.env.local):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

2. **Dependencies**:
```bash
npm install
```

3. **Development Server**:
```bash
npm run dev
```

### Key Development Patterns

1. **Metadata-First Development**
   - Always check metadata before content
   - Use metadata fields for routing decisions
   - Avoid content parsing when possible

2. **Type Safety**
   - Use TypeScript interfaces from `typings/dsagent.ts`
   - Avoid `any` types in metadata
   - Maintain proper type guards

3. **Component Isolation**
   - Each component handles its own rendering
   - No cross-component dependencies
   - Clear separation of concerns

### Testing Approach

1. **WebSocket Testing**:
   - Use debug scripts from `debug-archive/scripts/`
   - Test both ReAct and CodeAct agents
   - Verify streaming behavior

2. **Component Testing**:
   - Test with various metadata combinations
   - Verify proper routing
   - Check edge cases (empty content, missing metadata)

## Debugging Experience

### Key Discoveries

1. **Component Usage**: App uses `AgentChat`, not `ChatMessage`
2. **Field Naming**: Backend sends `message_type`, not `event_type`
3. **Streaming Complexity**: Delta messages require careful accumulation
4. **Metadata Reliability**: Metadata fields are more reliable than content parsing

### Common Issues and Solutions

1. **Action Thoughts Not Displaying**
   - Issue: Checking wrong metadata field
   - Solution: Use `message_type` instead of `event_type`

2. **Final Answers as Raw JSON**
   - Issue: Missing `has_structured_data` check
   - Solution: Check metadata before rendering

3. **Planning Badges Missing**
   - Issue: Not handling `planning_header` messages
   - Solution: Add specific handler for header messages

### Debug Tools

1. **Enable Debug Logging**:
```typescript
const DEBUG_PLANNING = true; // in use-websocket.tsx
```

2. **WebSocket Message Inspection**:
```typescript
console.log('📨 WebSocket message:', {
  metadata: data.metadata,
  contentLength: data.content?.length,
  step: data.step_number
});
```

3. **Test Scripts** (in debug-archive/):
- `test_websocket_e2e.py`: End-to-end testing
- `test_frontend_ui_fixes.py`: UI feature validation
- `test_action_thought_e2e.py`: Action thought testing

## Best Practices

1. **Always Trust Metadata**: Backend metadata is authoritative for routing
2. **Handle Streaming Gracefully**: Support both streaming and non-streaming modes
3. **Provide Fallbacks**: Always have default rendering for unknown message types
4. **Log Strategically**: Add debug logs for new features but clean up after
5. **Test Both Agents**: Features should work with both ReAct and CodeAct

## Future Enhancements

1. **Component Preloading**: Load code editor/terminal before first use
2. **Message Persistence**: Save conversation history locally
3. **Offline Support**: Queue messages when disconnected
4. **Theme Customization**: Support for custom color schemes
5. **Performance Monitoring**: Track rendering performance metrics

---

*Last Updated: July 2025 (v0.3.2.rc2)*
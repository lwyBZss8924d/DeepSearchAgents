# StreamEvent Flow in DeepSearchAgents v2 API

This document explains how StreamEvents flow through the system from smolagents to the frontend components.

## Architecture Overview

```
Agent (React/CodeAct)
    ↓ (generates events)
stream_agent_messages() in web_ui.py
    ↓ (processes events)
DSAgentMessageProcessor
    ↓ (wraps messages)
WebSocket Endpoint
    ↓ (streams JSON)
Frontend Components
```

The key insight is that the v2 API processes agent events directly in `web_ui.py`, not through a Gradio passthrough processor. Each agent event is transformed into one or more DSAgentRunMessage objects with metadata that drives frontend component routing.

## StreamEvent Types

The v2 API processes 4 main event types from smolagents:

1. **PlanningStep**: Planning phase with strategy and approach
2. **ActionStep**: Action execution including thoughts, tool calls, and results
3. **FinalAnswerStep**: Final answer delivery with structured data support
4. **ChatMessageStreamDelta**: Streaming text chunks during model generation (when streaming is enabled)

### smolagents StreamEvent [`somlagents.agent`]

1. **ChatMessageStreamDelta**: Streaming text chunks during model generation
2. **ChatMessageToolCall**: Tool call metadata from the model
3. **ActionOutput**: Result of an action (can be final answer)
4. **ToolCall**: Actual tool invocation
5. **ToolOutput**: Result from tool execution
6. **PlanningStep**: Planning phase information
7. **ActionStep**: Complete action step with all details
8. **FinalAnswerStep**: Final answer delivery

## Event Flow Sequence

### 1. Agent Execution Flow

```
User Query
    ↓
PlanningStep → ActionStep(s) → FinalAnswerStep
    ↓              ↓                ↓
[streaming]    [streaming]      Final Result
  deltas         deltas
```

When streaming is enabled:
- PlanningStep content arrives via ChatMessageStreamDelta events
- ActionStep thoughts arrive via ChatMessageStreamDelta events
- Non-streaming mode sends complete content immediately

### 2. web_ui.py Processing

The `web_ui.py` module processes these events into DSAgentRunMessage objects:

- **Step events** (PlanningStep, ActionStep, FinalAnswerStep):
  - Each step generates multiple messages with specific metadata
  - Messages include headers, content, footers, and separators
  - Metadata drives frontend component routing

- **Streaming events** (ChatMessageStreamDelta):
  - Accumulated into complete messages
  - Sent as delta updates with `is_delta: true`
  - Include stream_id for frontend message correlation

### 3. Frontend Component Routing

The `web_ui.py` processor adds component routing metadata:

#### Chat Component (`component: "chat"`)
- Planning messages (headers, content, footers)
- Action thoughts (truncated to 60 chars)
- Tool call badges
- Final answers (with structured data support)
- User messages
- General assistant messages

#### Web IDE Component (`component: "webide"`)
- Python code execution
- Code blocks with syntax highlighting
- Python tool outputs

#### Terminal Component (`component: "terminal"`)
- Non-Python tool execution (search, readurl, etc.)
- Execution logs and outputs
- Command results
- Error messages

## Message Metadata Structure

Each DSAgentRunMessage includes metadata for frontend routing and rendering:

```python
{
    # Component routing
    "component": "chat" | "webide" | "terminal",
    
    # Message type identification
    "message_type": "planning_header" | "planning_content" | "action_thought" | 
                    "tool_call" | "final_answer" | "error" | etc.,
    
    # Step information
    "step_type": "planning" | "action" | "final_answer",
    "step_number": 1,
    
    # Planning specific
    "planning_type": "initial" | "update",
    
    # Action specific
    "tool_name": "search" | "python_interpreter" | etc.,
    "thoughts_content": "First 60 chars of thinking...",
    
    # Final answer specific
    "has_structured_data": true,
    "answer_title": "Title text",
    "answer_content": "Answer markdown",
    "answer_sources": ["source1", "source2"],
    
    # Streaming state
    "streaming": true | false,
    "is_delta": true | false,
    "stream_id": "msg-1-planning_content-stream",
    
    # Status
    "status": "streaming" | "done",
    "error": true | false
}
```

## Example Event Sequences

### Planning Phase
1. **PlanningStep** event received
2. Generates messages:
   - planning_header (badge only)
   - planning_content (full text or streaming)
   - planning_footer (timing/token info)
   - separator

### Action Phase (Python Code)
1. **ActionStep** event received
2. Generates messages:
   - action_header ("Step N")
   - action_thought (agent reasoning)
   - tool_call (with tool_name="python_interpreter")
   - tool_invocation (code block → webide)
   - observation (execution result → terminal)
   - action_footer (timing/token info)
   - separator

### Action Phase (Web Search)
1. **ActionStep** event received
2. Generates messages:
   - action_header ("Step N")
   - action_thought (reasoning)
   - tool_call (with tool_name="search")
   - tool_invocation (query details)
   - observation (search results)
   - action_footer (timing/token info)
   - separator

### Final Answer
1. **FinalAnswerStep** event received
2. Generates message:
   - final_answer with structured data or markdown content

## Implementation Details

### Message Processing Pipeline

1. **Event Reception**: Agent generates events during execution
2. **web_ui Processing**: 
   - `process_planning_step()`: Handles PlanningStep events
   - `process_action_step()`: Handles ActionStep events  
   - `process_final_answer_step()`: Handles FinalAnswerStep events
   - Each processor generates multiple DSAgentRunMessage objects

3. **Metadata Enrichment**:
   - Component routing based on content type
   - Message type identification
   - Streaming context (stream_id, is_delta)
   - UI-specific fields (thoughts_content, has_structured_data)

### Streaming Architecture

1. **Initial Message**: Empty content with `streaming: true, is_initial_stream: true`
2. **Delta Messages**: Incremental updates with `is_delta: true, stream_id: "..."`
3. **Final Message**: Complete content with `streaming: false`

### Message Type Details

#### Planning Messages
- **planning_header**: Empty content, triggers badge display
- **planning_content**: Markdown text with plan details
- **planning_footer**: Timing and token usage info

#### Action Messages
- **action_header**: Step number indicator
- **action_thought**: Agent reasoning (truncated for UI)
- **tool_call**: Tool execution badge
- **tool_invocation**: Tool input details
- **observation**: Tool execution results
- **action_footer**: Step timing and tokens

#### Final Answer
- Supports both structured JSON and plain text
- Extracts title, content, and sources when available
- Falls back to markdown rendering

### Component Routing Logic

```python
# Chat component (default)
if tool_name == "python_interpreter" and "```python" in content:
    component = "webide"
elif message_type == "observation" and tool_name != "python_interpreter":
    component = "terminal"
else:
    component = "chat"
```

### Error Handling

Errors are wrapped in DSAgentRunMessage with:
- `message_type: "error"`
- `error: true`
- `error_type: "ExceptionName"`
- `component: "chat"`

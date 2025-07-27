# StreamEvent Flow in DeepSearchAgents v2 API

This document explains how StreamEvents flow through the system from smolagents to the frontend components.

## StreamEvent Types

The smolagents library defines 8 StreamEvent types (from `agents.py:219`):

1. **ChatMessageStreamDelta**: Streaming text chunks during model generation
2. **ChatMessageToolCall**: Tool call metadata from the model
3. **ActionOutput**: Result of an action (can be final answer)
4. **ToolCall**: Actual tool invocation
5. **ToolOutput**: Result from tool execution
6. **PlanningStep**: Planning phase information
7. **ActionStep**: Complete action step with all details
8. **FinalAnswerStep**: Final answer delivery

## Event Flow Sequence

### 1. Agent Execution Flow (`_run_stream`)

```
Start → PlanningStep (optional) → ActionStep loop → FinalAnswerStep
         ↓                         ↓
         ChatMessageStreamDelta    ├─ ChatMessageStreamDelta (model thinking)
         (planning text)           ├─ ToolCall (tool invocation)
                                  ├─ ToolOutput (tool result)
                                  └─ ActionOutput (step result)
```

### 2. stream_to_gradio Processing

The `stream_to_gradio` function processes these events:

- **Streaming events** (ChatMessageStreamDelta): 
  - Accumulated and yielded as text strings
  - Represents partial model output during generation

- **Step events** (ActionStep, PlanningStep, FinalAnswerStep):
  - Passed to `pull_messages_from_step`
  - Yields multiple `gr.ChatMessage` objects with metadata

### 3. Frontend Component Routing

Our `gradio_passthrough_processor.py` adds component routing metadata:

#### Chat Component
- Model reasoning and planning
- Final answers
- General assistant messages
- User queries

#### Web IDE Component  
- Python code execution (`python_interpreter` tool)
- Code blocks with ```python
- Python-related outputs

#### Terminal Component
- Non-Python tool execution (search, wolfram, etc.)
- Execution logs
- Error messages
- System outputs

## Message Metadata Structure

Each DSAgentRunMessage includes metadata to help frontend routing:

```python
{
    "component": "chat" | "webide" | "terminal",
    "event_type": "tool_call" | "tool_invocation" | "tool_output" | "action_output",
    "tool_name": "python_interpreter" | "search" | etc.,
    "streaming": true | false,
    "is_final_answer": true | false,
    "status": "pending" | "done",
    "title": "🛠️ Used tool X" | "📝 Execution Logs" | etc.
}
```

## Example Event Sequences

### Python Code Execution
1. ChatMessageStreamDelta: "I'll write Python code to solve this..."
2. ToolCall: {name: "python_interpreter", arguments: {code: "..."}}
3. ToolOutput: {observation: "Execution logs:\n..."}
4. ActionOutput: {output: result, is_final_answer: false}

### Web Search
1. ChatMessageStreamDelta: "Let me search for information..."
2. ToolCall: {name: "search", arguments: {query: "..."}}
3. ToolOutput: {observation: "Search results:\n..."}
4. ActionOutput: {output: processed_results}

### Final Answer
1. ActionOutput: {output: "The answer is...", is_final_answer: true}
2. FinalAnswerStep: {output: "The answer is..."}

## Implementation Notes

1. **Accumulation**: ChatMessageStreamDelta events are accumulated until a complete message is formed
2. **Step Numbers**: Extracted from "**Step N**" patterns in content
3. **Component Detection**: Based on tool names, metadata titles, and content patterns
4. **Streaming Support**: Text updates are marked with `streaming: true` metadata
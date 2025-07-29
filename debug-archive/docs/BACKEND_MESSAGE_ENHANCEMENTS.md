# Backend Message Processing Enhancements

## Overview

This document summarizes the comprehensive enhancements made to the backend message processing in `src/api/v2/web_ui.py` to provide rich metadata for frontend UI components.

## Enhancements Implemented

### 1. Planning Messages

#### Planning Header
- Added `is_update_plan` boolean for clarity
- Added `planning_step_number` (distinct from ActionStep number)
- Added error information extraction
- Empty content allows frontend to render badges based on metadata

#### Planning Content
- Added `thoughts_content`: First 60 characters of planning content
- Added `content_length`: Total length of planning content
- Added structured token usage and timing via `get_step_metadata()`
- Preserved existing planning type indicators

#### Planning Footer
- Added structured metadata instead of just HTML
- Included `footer_label` for display
- Added token usage and timing information
- Added error information if present

### 2. Action Messages

#### NEW: Tool Call Messages
- Created new message type `tool_call` for tool invocations
- Displays tool name as a badge
- Includes tool ID and arguments summary
- Special handling for final_answer tool to show title
- `is_python_interpreter` flag for UI styling

#### Action Thought Messages
- Added `thoughts_content`: First 60 characters for truncated display
- Added `full_thought_length`: Total length of original thought
- Added error information extraction
- Fixed streaming type assignment bug (now correctly uses phase tracking)

#### Code Action (WebIDE) Messages
- Added `code_lines`: Count of lines in the code
- Added `has_imports`: Boolean indicating if imports are present
- Improved code cleaning to remove trailing tags
- Preserved existing code editor metadata

#### Terminal (Execution Logs) Messages
- Added `output_lines`: Count of output lines
- Added `has_error`: Boolean based on error pattern detection
- Added `execution_duration` from timing information
- Enhanced error detection regex

### 3. Final Answer Messages
- Preserved existing JSON parsing and metadata extraction
- Maintained structured data fields (title, content, sources)
- Added consistent error handling

### 4. Utility Functions

#### `get_step_metadata()`
New function to extract structured metadata from step logs:
- Token usage (input, output, total)
- Timing information (duration)
- Error information (message, type)

#### `get_step_footnote_content()`
Preserved for backward compatibility while adding structured alternatives

## Frontend Integration

### New Components Created

#### ToolCallBadge Component
```tsx
<ToolCallBadge
  toolName={metadata.tool_name}
  toolId={metadata.tool_id}
  argsSummary={metadata.tool_args_summary}
  isPythonInterpreter={metadata.is_python_interpreter}
/>
```

### Updated Components

#### ChatMessage Component
- Added handling for `tool_call` message type
- Integrated ToolCallBadge component
- Preserved all existing message type handling

## Message Flow Example

```
1. Planning Header (empty content, metadata indicates badge type)
2. Planning Content (with thoughts_content truncated to 60 chars)
3. Planning Footer (with structured token/timing data)
4. Action Header
5. Action Thought (with thoughts_content for special display)
6. Tool Call Badge (shows which tool is being invoked)
7. Tool Invocation (actual code/content)
8. Execution Logs (with line count and error detection)
9. Action Footer (with structured metadata)
10. Final Answer (with structured JSON data)
```

## Benefits

1. **Rich Metadata**: Frontend components receive all necessary data for proper rendering
2. **Consistent Structure**: All message types follow similar metadata patterns
3. **Error Tracking**: Comprehensive error extraction across all step types
4. **Performance Metrics**: Token usage and timing available in structured format
5. **Backward Compatible**: Existing frontend code continues to work
6. **Type Safety**: Clear message type indicators for component routing

## Testing

Created `test_enhanced_messages.py` to verify:
- All message types are sent with correct metadata
- Tool call badges appear for tool invocations
- Thought messages include truncated content
- Footer messages include structured metadata
- Error information is properly extracted

## Migration Notes

Frontend components can gradually adopt the new metadata fields:
- Existing code using content parsing can continue to work
- New features can use structured metadata directly
- Tool call badges are opt-in (only shown when frontend handles them)
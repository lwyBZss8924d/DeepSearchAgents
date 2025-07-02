# DeepSearchAgents CLI v0.2.9 Upgrade Plan
## Smolagents Framework v1.19.0 Compliance & Feature Enhancement

### Overview
This document outlines the implementation plan for upgrading DeepSearchAgents CLI to fully support smolagents v1.19.0 features, focusing on enabling streaming support and updating token counting to use the new TokenUsage API.

### Version Information
- **Current State**: v0.2.9.dev with partial smolagents v1.19.0 support
- **Target State**: Full v1.19.0 compliance with streaming and proper token counting
- **Key Focus**: CLI streaming capability and TokenUsage API integration

---

## Current Status Analysis

### ✅ Already Implemented Features
1. **Managed Agents Support** - Full hierarchical agent management
2. **Context Managers** - Proper cleanup with __enter__/__exit__ methods
3. **RunResult Objects** - Complete implementation with metadata
4. **Structured Generation** - CodeAgent supports structured outputs
5. **Parallel Tool Calls** - ReactAgent supports multi-threaded execution
6. **Streaming Infrastructure** - StreamAggregator follows v1.19.0 patterns

### ❌ Missing/Incomplete Features
1. **CLI Streaming Support** - Infrastructure exists but not connected
2. **Token Counting** - Still using deprecated attributes
3. **Code Tag Format** - Using markdown instead of XML format
4. **Streaming Configuration** - Settings referenced but not defined

---

## Implementation Plan

## Phase 1: Enable Streaming Support in CLI

### Task 1.1: Add Streaming Configuration
**File**: `src/core/config/settings.py`

Add the following configuration options:
```python
# Streaming configuration
REACT_ENABLE_STREAMING: bool = Field(
    default=False,
    description="Enable streaming output for React agent"
)
CODACT_ENABLE_STREAMING: bool = Field(
    default=False, 
    description="Enable streaming output for CodeAct agent"
)
CLI_STREAMING_ENABLED: bool = Field(
    default=False,
    description="Global toggle for CLI streaming display"
)
```

### Task 1.2: Update Runtime to Use Streaming Settings
**File**: `src/agents/runtime.py`

Update agent initialization:
- Line 385: Change to `stream_outputs=settings.REACT_ENABLE_STREAMING`
- Line 455: Change to `stream_outputs=settings.CODACT_ENABLE_STREAMING`

### Task 1.3: Implement Streaming in process_query_async
**File**: `src/cli.py`

Modify the `process_query_async` function to:
1. Check if streaming is enabled via settings
2. Pass `stream=True` to agent.run() when enabled
3. Handle async iteration over streaming responses
4. Display partial results as they arrive

### Task 1.4: Create StreamingConsoleFormatter
**New File**: `src/agents/ui_common/streaming_formatter.py`

Create a new formatter class:
```python
class StreamingConsoleFormatter(ConsoleFormatter):
    def on_stream_chunk(self, chunk: str):
        """Display streaming chunk in real-time"""
        pass
    
    def on_stream_start(self):
        """Initialize streaming display"""
        pass
    
    def on_stream_end(self):
        """Finalize streaming display"""
        pass
```

---

## Phase 2: Update Token Counting to smolagents v1.19.0 API

### Task 2.1: Import and Use TokenUsage Class
**Files to Update**:
- `src/agents/base_agent.py`
- `src/agents/ui_common/agent_step_callback.py`
- `src/agents/run_result.py`

Add import:
```python
from smolagents.types import TokenUsage
```

### Task 2.2: Fix AgentStepCallback Token Extraction
**File**: `src/agents/ui_common/agent_step_callback.py`

Replace the `_extract_token_stats` method to:
1. Remove checks for deprecated attributes
2. Use `step.token_usage` from ActionStep/PlanningStep
3. Aggregate using TokenUsage objects

### Task 2.3: Update RunResult Implementation
**File**: `src/agents/run_result.py`

Change token_usage to use TokenUsage class:
```python
token_usage: Optional[TokenUsage] = None
```

### Task 2.4: Fix CLI Token Display
**File**: `src/cli.py`

Update lines 467-485 and 698-713 to:
1. Use TokenUsage object attributes
2. Remove TODO comments about token stats
3. Display tokens using the new API format

---

## Phase 3: Additional v1.19.0 Compliance Updates

### Task 3.1: Update Code Tag Format
**File**: `src/agents/prompt_templates/codact_prompts.py`

Update prompts to use XML format:
- Change from: "Write Python code enclosed in `<code>...</code>`"
- Change to: "Write Python code enclosed in `<execute_python>...</execute_python>`"

### Task 3.2: Enable Structured Outputs by Default
**File**: `src/core/config/settings.py`

Change default value:
```python
CODACT_USE_STRUCTURED_OUTPUTS: bool = Field(
    default=True,  # Changed from False
    description="Use structured outputs for CodeAct agent"
)
```

---

## Phase 4: Testing and Documentation

### Task 4.1: Test Streaming Functionality
1. Test React agent with streaming enabled
2. Test CodeAct agent with streaming enabled
3. Verify token counting accuracy
4. Test fallback when streaming fails

### Task 4.2: Update Documentation
**File**: `CLAUDE.md`

Add section on streaming configuration:
```markdown
### Streaming Configuration
Streaming output is now available but disabled by default due to stability considerations.
To enable streaming:
- Set `REACT_ENABLE_STREAMING=true` for React agent
- Set `CODACT_ENABLE_STREAMING=true` for CodeAct agent
- Set `CLI_STREAMING_ENABLED=true` for CLI display
```

---

## Implementation Order

1. **Day 1 Morning**: 
   - Task 1.1: Add streaming configuration (30 min)
   - Task 1.2: Update runtime settings (15 min)
   - Task 2.1: Import TokenUsage class (30 min)
   - Task 2.2: Fix token extraction (1 hour)

2. **Day 1 Afternoon**:
   - Task 1.3: Implement streaming in CLI (2 hours)
   - Task 1.4: Create streaming formatter (1.5 hours)
   - Task 2.3: Update RunResult (30 min)

3. **Day 1 Evening**:
   - Task 2.4: Fix CLI token display (1 hour)
   - Task 3.1: Update code tag format (30 min)
   - Task 3.2: Enable structured outputs (15 min)
   - Task 4.1: Test all features (1 hour)

4. **Day 2 Morning**:
   - Task 4.2: Update documentation (30 min)
   - Final testing and bug fixes (1.5 hours)

---

## Success Criteria

1. **Streaming Works**: CLI displays real-time output when enabled
2. **Token Counting Accurate**: Uses new TokenUsage API correctly
3. **No Deprecation Warnings**: All deprecated attributes removed
4. **Backward Compatible**: Existing functionality preserved
5. **Tests Pass**: All existing tests continue to pass
6. **Documentation Complete**: All changes documented

---

## Risk Mitigation

1. **Streaming Stability**: Keep streaming disabled by default
2. **Token Counting Fallback**: Gracefully handle missing token data
3. **Performance Impact**: Monitor streaming overhead
4. **Testing Coverage**: Add specific tests for new features

---

## Notes

- The streaming infrastructure already exists and follows v1.19.0 patterns
- Token counting requires careful migration to avoid breaking existing functionality
- XML format for code tags is a minor but important compliance update
- Structured outputs are stable in v1.19.0 and should be enabled by default

---

### Document Version
- **Created**: 2025-01-02
- **Author**: DeepSearchAgents Team
- **Status**: Ready for Implementation
- **Target Completion**: 2 days
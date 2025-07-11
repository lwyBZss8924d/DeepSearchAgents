# Smolagents v0.2.9 Upgrade Implementation Plan

## Executive Summary
DeepSearchAgents is already using smolagents v1.19.0 (as per pyproject.toml) but hasn't implemented the new features. This plan details the implementation of v1.19.0 features and breaking changes.

## Current State Analysis

### ✅ Already Implemented
- **Dependency**: smolagents>=1.19.0 in pyproject.toml
- **Basic Agent Structure**: CodeAct and ReAct agents using smolagents
- **Multi-Model Router**: Custom implementation for routing between models
- **Tool System**: Working tool integration with smolagents

### ❌ Not Yet Implemented (Breaking Changes)
1. **Code Tag Format**: Still using markdown ```python``` instead of XML
2. **Streaming Refactor**: Streaming aggregation still in MultiModelRouter
3. **RunResult Objects**: Agents return strings, not RunResult objects
4. **Context Managers**: No __enter__/__exit__ implementation
5. **Managed Agents**: No hierarchical agent support
6. **Parallel Tool Execution**: Sequential tool execution only

## Implementation Tasks

### Task 1: Code Tag Format Migration (High Priority)
**File**: `src/agents/prompt_templates/codact_prompts.py`

**Current State** (Line 37):
```python
"Write Code:** Write a Python code snippet enclosed in ```python ... ```"
```

**Required Changes**:
1. Update CODACT_SYSTEM_EXTENSION to use XML format:
   ```python
   # Old: ```python\ncode here\n```
   # New: <code>\ncode here\n</code>
   ```
2. Update code parsing logic in agents to handle XML tags
3. Add compatibility layer for gradual migration

**Impact**: High - Affects all CodeAct agent interactions

### Task 2: Streaming Architecture Refactor (High Priority)
**File**: `src/agents/base_agent.py`

**Current State**: 
- MultiModelRouter contains streaming logic (lines 145-258)
- Token counting mixed with streaming

**Required Changes**:
1. Extract streaming logic from MultiModelRouter
2. Create new StreamAggregator class:
   ```python
   class StreamAggregator:
       def aggregate_stream(self, stream_generator):
           # Handle stream aggregation outside model
   ```
3. Update generate_stream to use new architecture
4. Separate token counting from streaming

**Impact**: Medium - Internal architecture change

### Task 3: RunResult Integration (High Priority)
**Files**: Multiple agent files

**Current State**: 
- Agents return strings directly
- No metadata about execution

**Required Changes**:
1. Create RunResult dataclass:
   ```python
   @dataclass
   class RunResult:
       final_answer: str
       steps: List[Dict]
       token_usage: Dict[str, int]
       execution_time: float
       error: Optional[str]
   ```
2. Update BaseAgent.run() return type
3. Maintain backward compatibility with string returns
4. Update all callers to handle RunResult

**Impact**: High - API breaking change

### Task 4: Context Manager Support (Medium Priority)
**File**: `src/agents/base_agent.py`

**Required Changes**:
1. Add context manager methods:
   ```python
   async def __aenter__(self):
       # Initialize resources
       return self
   
   async def __aexit__(self, exc_type, exc_val, exc_tb):
       # Cleanup tools, memory, executors
   ```
2. Update AgentRuntime to use context managers
3. Ensure proper resource cleanup

**Impact**: Low - Enhancement, backward compatible

### Task 5: Parallel Tool Execution (Medium Priority)
**File**: `src/agents/react_agent.py`

**Current State**: 
- ToolCallingAgent used but no parallel execution

**Required Changes**:
1. Enable parallel tool calls in ToolCallingAgent
2. Update tool execution logic to handle concurrent calls
3. Add configuration for parallel execution limits

**Impact**: Medium - Performance improvement

### Task 6: Managed Agents Support (Low Priority)
**Files**: `src/agents/react_agent.py`, prompt templates

**Required Changes**:
1. Add managed_agents parameter to agent initialization
2. Update prompt templates to include team member section
3. Implement agent delegation logic
4. Add configuration for agent hierarchies

**Impact**: Low - New feature, optional

## Implementation Order

### Phase 1: Critical Breaking Changes (Day 1)
1. **Code Tag Format** (2-3 hours)
   - Update prompts
   - Update parsing logic
   - Test with both formats
   
2. **RunResult Integration** (3-4 hours)
   - Create RunResult class
   - Update agent.run() methods
   - Add compatibility layer
   
3. **Streaming Refactor** (2-3 hours)
   - Extract streaming logic
   - Create StreamAggregator
   - Update MultiModelRouter

### Phase 2: Enhancements (Day 1-2)
4. **Context Managers** (1-2 hours)
   - Add __enter__/__exit__
   - Update runtime usage
   
5. **Parallel Tool Execution** (2-3 hours)
   - Enable in ToolCallingAgent
   - Add concurrency controls
   
6. **Managed Agents** (2-3 hours)
   - Add support infrastructure
   - Update prompts

### Phase 3: Testing & Documentation (Day 2)
7. **Testing** (3-4 hours)
   - Unit tests for all changes
   - Integration tests
   - Backward compatibility tests
   
8. **Documentation** (2 hours)
   - Update README
   - Create migration guide
   - Update API docs

## Risk Mitigation

### Backward Compatibility
- Maintain string return option alongside RunResult
- Support both markdown and XML code tags temporarily
- Version flag for old vs new behavior

### Performance Risks
- Benchmark streaming changes
- Monitor memory usage with new architecture
- Profile parallel tool execution

### Security Considerations
- Apply LocalPythonExecutor security fixes
- Validate XML parsing for code injection
- Sandbox parallel tool execution

## Success Metrics
1. All tests pass with new smolagents features
2. No regression in existing functionality
3. Improved streaming performance (target: 20% reduction in latency)
4. Successful parallel tool execution
5. Clean resource management with context managers

## Migration Guide for Users

### Code Tag Format
```python
# Old format
"""```python
code here
```"""

# New format
"""<code>
code here
</code>"""
```

### RunResult Usage
```python
# Old usage
response = agent.run(query)
print(response)

# New usage
result = agent.run(query)
if isinstance(result, RunResult):
    print(result.final_answer)
    print(f"Tokens used: {result.token_usage}")
else:
    # Backward compatibility
    print(result)
```

### Context Manager Usage
```python
# New recommended usage
async with AgentRuntime.create_agent() as agent:
    result = await agent.run(query)
    # Resources automatically cleaned up
```

## Next Steps
1. Review and approve this plan
2. Create feature branch `feature/smolagents-v1.19-upgrade`
3. Implement Phase 1 changes
4. Test thoroughly before proceeding to Phase 2
5. Document all changes in CHANGELOG.md
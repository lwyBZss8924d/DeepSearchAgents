# DeepSearchAgents v0.2.9 Development Plan
## Smolagents Framework Upgrade v1.16.1 → v1.19.0

### Overview
This document outlines the development plan for upgrading DeepSearchAgents from smolagents v1.16.1 to v1.19.0, incorporating new framework features and optimizing the system based on the latest capabilities.

### Version Information
- **Current Version**: v0.2.8.dev (smolagents v1.16.1)
- **Target Version**: v0.2.9.dev (smolagents v1.19.0)
- **Branch**: Dev → v0.2.9.dev

---

## 1. Framework Upgrade Analysis

### 1.1 Critical Breaking Changes
- **Streaming Refactor** (v1.19.0 #1449): Streaming aggregation moved off Model class
- **Code Tag Format** (v1.19.0 #1442): Changed from markdown to XML format
- **Final Answer Checks** (v1.19.0 #1448): Refactored final answer validation logic

### 1.2 New Features to Integrate
- **Multiple Parallel Tool Calls** (v1.18.0 #1412): ToolCallingAgent parallel execution
- **Streaming for ToolCallingAgent** (v1.18.0 #1409): Native streaming support
- **Managed Agents Support** (v1.19.0 #1456): Hierarchical agent management
- **Context Managers** (v1.19.0 #1422): Proper cleanup lifecycle
- **RunResult Objects** (v1.17.0 #1337): Rich metadata from agent.run()
- **Structured Generation** (v1.17.0 #1346): Optional structured outputs in CodeAgent
- (There are currently more advanced and powerful web search tools available, so this feature is temporarily not needed. However, the source code of the web search tool can be referenced to analyze whether it can be used to optimize various web search tools in the current system) **API Web Search Tool** (v1.18.0 #1400): Native web search integration

### 1.3 Bug Fixes to Apply
- Planning logic fixes (v1.19.0 #1417, #1454)
- Memory message handling improvements
- Multiline final answer support in remote executors (v1.19.0 #1444)
- Tool decorator fixes for remote executors (v1.18.0 #1334)

---

## 2. Development Tasks

### Phase 1: Core Framework Upgrade (Day 1)

#### Task 1.1: Update Dependencies
```toml
# pyproject.toml changes
smolagents>=1.19.0  # Update from 1.16.1
version = "0.2.9.dev"  # Update project version
```

#### Task 1.2: Streaming Architecture Refactor
**Files to Update**:
- `src/agents/base_agent.py` - MultiModelRouter streaming
- `src/agents/runtime.py` - Stream handling logic

**Changes Required**:
1. Move streaming aggregation logic out of MultiModelRouter
2. Implement new streaming pattern per v1.19.0 (#1449)
3. Update token counting during streaming
4. Fix live streaming during planning steps (#1348)

#### Task 1.3: Code Tag Format Migration
**Files to Update**:
- `src/agents/prompt_templates/codact_prompts.py`
- `src/agents/prompt_templates/react_prompts.py`

**Changes Required**:
1. Update code blocks from markdown (```) to XML format
2. Update parsing logic for XML tags
3. Test prompt compatibility

### Phase 2: Agent Enhancements (Day 1)

#### Task 2.1: Parallel Tool Execution for ReactAgent
**Files to Update**:
- `src/agents/react_agent.py`

**Implementation**:
```python
# Support multiple tool calls in parallel
# Leverage v1.18.0 ToolCallingAgent improvements
```

#### Task 2.2: Managed Agents Support
**New Feature**: Enable hierarchical agent management
1. Update ReactAgent to support managed sub-agents
2. Implement agent coordination logic
3. Add configuration for agent hierarchies

#### Task 2.3: Context Manager Implementation
**Files to Update**:
- `src/agents/base_agent.py`
- `src/agents/runtime.py`

**Implementation**:
```python
# Add context manager support for proper cleanup
async def __aenter__(self):
    # Initialize resources
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    # Cleanup resources
    pass
```

#### Task 2.4: RunResult Integration
**Files to Update**:
- All agent run() methods
- `src/agents/runtime.py`

**Changes**:
1. Return RunResult objects with metadata
2. Maintain backward compatibility
3. Expose execution metrics

### Phase 3: New Features Integration (Day 1)

#### Task 3.1: Structured Generation for CodeAgent
**Files to Update**:
- `src/agents/codact_agent.py`
- `src/core/config/settings.py`

**Implementation**:
```python
# Add configuration option
use_structured_outputs_internally: bool = False

# Implement structured generation logic
```

#### Task 3.2: Enhanced Memory Management
**Features**:
1. Implement reset_agent_memory support
2. Fix memory handling during planning
3. Add memory persistence options

#### Task 3.3: Web Search Tool Optimization Analysis
**Approach**: Reference smolagents ApiWebSearchTool for optimization ideas

**Analysis Tasks**:
1. Study ApiWebSearchTool implementation for best practices
2. Compare with current search engines (Serper, XCom)
3. Identify optimization opportunities:
   - Response caching strategies
   - Request batching patterns
   - Error handling improvements
   - Result parsing optimizations

**Note**: DeepSearchAgents already has more advanced search capabilities than the native smolagents tool, so this is purely for reference and potential optimization insights.

### Phase 4: Optimization & Testing (Day 1)

#### Task 4.1: Performance Optimizations
1. **Parallel Tool Execution**: Optimize for concurrent operations
2. **Streaming Performance**: Reduce latency with new architecture
3. **Token Usage**: Improve token counting accuracy

#### Task 4.2: Security Enhancements
1. Apply LocalPythonExecutor security fixes
2. Implement safer code execution patterns
3. Add execution sandboxing options

#### Task 4.3: Comprehensive Testing
1. Unit tests for all updated components
2. Integration tests for new features
3. Performance benchmarks
4. Backward compatibility tests

---

## 3. Feature Enhancement Plan (Day 2)

### 3.1 Advanced Agent Orchestration
**Goal**: Leverage managed agents for complex workflows

**Implementation**:
1. Create `OrchestratorAgent` class extending ToolCallingAgent
2. Implement agent delegation patterns
3. Add configuration for agent specialization

### 3.2 Enhanced Streaming Experience
**Goal**: Real-time visibility with minimal latency

**Implementation**:
1. Optimize streaming for both CLI and Web UI
2. Add streaming progress indicators
3. Implement streaming for parallel tool calls

### 3.3 Intelligent Tool Selection
**Goal**: Automatic tool selection based on query analysis

**Implementation**:
1. Leverage structured generation for tool planning
2. Implement tool recommendation system
3. Add tool usage analytics

### 3.4 Improved Error Recovery
**Goal**: Graceful handling of failures

**Implementation**:
1. Implement retry logic with exponential backoff
2. Add fallback strategies for tool failures
3. Enhanced error messages with recovery suggestions

---

## 4. Migration Guide

### 4.1 For Developers
1. Update local environment to smolagents v1.19.0
2. Run migration scripts for code tag updates
3. Update custom tool implementations
4. Test streaming functionality

### 4.2 For Users
1. Configuration changes required:
   - Enable new streaming architecture
   - Configure parallel tool execution
   - Set structured generation preferences

### 4.3 Breaking Changes
1. Streaming API changes
2. Code tag format in prompts
3. RunResult return type from agent.run()

---

## 5. Timeline & Milestones

### Day 1: Core Framework Upgrade
- [ ] Update dependencies to smolagents v1.19.0
- [ ] Refactor streaming architecture
- [ ] Migrate code tag formats
- [ ] Initial testing suite

### Day 1: Agent Enhancements
- [ ] Implement parallel tool execution
- [ ] Add managed agents support
- [ ] Integrate context managers
- [ ] RunResult implementation

### Day 1: New Features
- [ ] Structured generation for CodeAgent
- [ ] Enhanced memory management
- [ ] Web search optimization analysis
- [ ] Performance optimizations

### Day 2: Testing & Release
- [ ] Comprehensive testing
- [ ] Documentation updates
- [ ] Migration guide completion
- [ ] v0.2.9.dev release

---

## 6. Risk Mitigation

### 6.1 Compatibility Risks
- Maintain backward compatibility layer
- Provide migration tools
- Extensive testing on existing workflows

### 6.2 Performance Risks
- Benchmark all changes
- Profile memory usage
- Monitor streaming latency

### 6.3 Security Risks
- Apply all security patches from v1.17.0-v1.19.0
- Additional security audit
- Sandboxed execution testing

---

## 7. Success Metrics

1. **Performance**: 20% improvement in streaming latency
2. **Reliability**: 99% backward compatibility
3. **Features**: All v1.19.0 features integrated
4. **Quality**: Zero regression in existing functionality
5. **Security**: Pass security audit with no critical issues

---

## 8. Next Steps

1. Create feature branch `v0.2.9.dev` from `Dev`
2. Update `pyproject.toml` with new version
3. Begin Phase 1 implementation
4. Set up CI/CD for new version
5. Communicate upgrade plan to team

---

### Document Version
- **Created**: 2025-06-30
- **Author**: DeepSearchAgents Team
- **Status**: Planning
- **Target Release**: v0.2.9.dev
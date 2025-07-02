# DeepSearchAgents v0.2.9 Test Fix Plan

## Overview
This document outlines the iterative test and debug plan for fixing test failures after the smolagents v1.19.0 upgrade.

## Current Status
- Unit Tests: 39/66 passed (59%)
- Integration Tests: 9/26 passed (35%)
- Compatibility Tests: 12/19 passed (63%)
- Overall Coverage: ~25%

## Phase 1: Unit Test Fixes (Priority: High)

### 1.1 Fix BaseAgent MockAgent Issues
**File**: `tests/unit/test_base_agent.py`
- [ ] Fix MockAgent state initialization to use deepcopy properly
- [ ] Fix planning_interval assertion (expects 3 but gets 4)
- [ ] Ensure MockAgent attributes match BaseAgent interface

### 1.2 Fix ManagerAgent Tests
**Files**: 
- `src/agents/manager_agent.py`
- `tests/unit/test_manager_agent.py`
- [ ] Remove managed_agents from ToolCallingAgent initialization
- [ ] Pass managed agents through tools parameter
- [ ] Update test expectations

### 1.3 Fix MultiModelRouter Tests
**File**: `tests/unit/test_multi_model_router.py`
- [ ] Correct assertion for aggregated content (line 44)
- [ ] Update streaming error handling tests

### 1.4 Fix ReactAgent Tests
**File**: `tests/unit/test_react_agent.py`
- [ ] Fix undefined variable 'react_agent' (line 248)
- [ ] Update ToolCallingAgent parameter expectations

## Phase 2: Integration Test Fixes (Priority: High)

### 2.1 Fix Streaming Tests
**File**: `tests/integration/test_streaming.py`
- [ ] Update StreamAggregator test assertions (line 44)
- [ ] Fix ChatMessageStreamDelta initialization parameters
- [ ] Correct expected aggregated content

### 2.2 Fix Structured Generation Tests
**File**: `tests/integration/test_structured_generation.py`
- [ ] Update LocalPythonExecutor parameters for v1.19.0
- [ ] Fix executor_kwargs passing

### 2.3 Fix Parallel Tools Tests
**File**: `tests/integration/test_parallel_tools.py`
- [ ] Ensure proper tool initialization
- [ ] Update async tool compatibility

## Phase 3: Compatibility Test Fixes (Priority: Medium)

### 3.1 Fix Backward Compatibility
**Files**:
- `src/agents/base_agent.py`
- `tests/compatibility/test_backward_compatibility.py`
- [ ] Add state format conversion (list to set)
- [ ] Update legacy state handling

### 3.2 Fix Config Loading
**File**: `src/agents/runtime.py`
- [ ] Fix default_agent configuration loading
- [ ] Update streaming parameter handling

## Phase 4: LiteLLM Integration Tests (Priority: High)

### 4.1 Configure Timeouts
- [ ] Apply @pytest.mark.timeout(1200) to LLM tests
- [ ] Ensure pytest-timeout is properly configured

### 4.2 Run Integration Tests
- [ ] Verify LiteLLM API integration works
- [ ] Test with proper timeouts

## Execution Strategy

1. **Run tests for each phase after fixes**
   ```bash
   # Phase 1 - Unit tests
   pytest tests/unit/test_base_agent.py -xvs
   pytest tests/unit/test_manager_agent.py -xvs
   pytest tests/unit/test_multi_model_router.py -xvs
   pytest tests/unit/test_react_agent.py -xvs
   
   # Phase 2 - Integration tests
   pytest tests/integration/test_streaming.py -xvs
   pytest tests/integration/test_structured_generation.py -xvs
   pytest tests/integration/test_parallel_tools.py -xvs
   
   # Phase 3 - Compatibility tests
   pytest tests/compatibility/test_backward_compatibility.py -xvs
   
   # Phase 4 - Full suite
   python run_tests.py integration -v
   ```

2. **Use verbose mode with stop on first failure**
3. **Document each fix applied**
4. **Track test progress in test-report.md**

## Key Issues to Address

### smolagents API Changes
- v1.19.0 has changed several parameter names and initialization patterns
- Need to update all test expectations to match new API

### Streaming Architecture
- New StreamAggregator pattern needs consistent implementation
- ChatMessageStreamDelta initialization has changed

### Parameter Passing
- Many tests assume old parameter names that have changed
- Need systematic update of all parameter references

### State Management
- Legacy state format conversion needs explicit handling
- Memory management has been updated in v1.19.0

## Success Criteria
- All unit tests passing (66/66)
- All integration tests passing (26/26)
- All compatibility tests passing (19/19)
- No regression in existing functionality
- Clean test output with no warnings
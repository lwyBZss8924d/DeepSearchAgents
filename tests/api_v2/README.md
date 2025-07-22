# DeepSearchAgents Web API v2 Tests

This directory contains comprehensive test suites for the DeepSearchAgents Web API v2, which uses a simplified Gradio message pass-through architecture.

## Test Structure

- **`conftest.py`** - Shared pytest fixtures and configuration
- **`utils.py`** - Helper utilities for WebSocket testing
- **`test_websocket_streaming.py`** - Main WebSocket streaming tests
- **`test_agent_steps.py`** - Tests for agent steps streaming (ActionStep, PlanningStep, etc.)
- **`test_final_answer.py`** - Tests for final answer message format and behavior

## Key Test Cases

### 1. Agent Steps Test (`test_agent_steps.py`)
- **Query**: "Search about New LLM: Qwen [Qwen3-235B-A22B] model info, and summarize it into a nice table for me."
- **Timeout**: 2000 seconds (33 minutes)
- **Validates**: 
  - Streaming of ActionStep messages
  - PlanningStep messages
  - Tool execution updates
  - Progress indicators
  - Final answer with table format

### 2. Final Answer Test (`test_final_answer.py`)
- **Query**: "Calculate 50 * 3 + 25 and show your work"
- **Timeout**: 1000 seconds (16 minutes)
- **Validates**:
  - Streaming of intermediate steps
  - Final answer format
  - Metadata fields
  - Completion status
  - Mathematical correctness

## Running the Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Make sure the API server is NOT running
# (tests will start their own server instances)
```

### Run All API v2 Tests

```bash
# From project root
pytest tests/api_v2/ -v

# With coverage
pytest tests/api_v2/ --cov=src/api/v2 --cov-report=html
```

### Run Specific Test Files

```bash
# WebSocket streaming tests
pytest tests/api_v2/test_websocket_streaming.py -v

# Agent steps tests (slow, integration tests)
pytest tests/api_v2/test_agent_steps.py -v -m integration

# Final answer tests
pytest tests/api_v2/test_final_answer.py -v
```

### Run Specific Test Cases

```bash
# Run the LLM research test
pytest tests/api_v2/test_agent_steps.py::TestAgentSteps::test_llm_research_steps -v -s

# Run the calculation test
pytest tests/api_v2/test_final_answer.py::TestFinalAnswer::test_calculation_final_answer -v
```

### Skip Slow Tests

```bash
# Skip tests marked as slow
pytest tests/api_v2/ -v -m "not slow"

# Skip integration tests
pytest tests/api_v2/ -v -m "not integration"
```

## Test Markers

- **`@pytest.mark.slow`** - Long-running tests (>1 minute)
- **`@pytest.mark.integration`** - Integration tests that use real agents
- **`@pytest.mark.asyncio`** - Async tests (required for all WebSocket tests)

## Understanding Test Output

The tests validate the DSAgentRunMessage format:

```python
{
    "role": "user" | "assistant",
    "content": "message content",
    "metadata": {
        "status": "thinking" | "running" | "complete",
        "title": "Step title",
        ...
    },
    "message_id": "msg_xxx",
    "timestamp": "ISO timestamp",
    "session_id": "session UUID",
    "step_number": 1
}
```

## Debugging Tests

### Enable Verbose Output

```bash
# Show print statements and logging
pytest tests/api_v2/ -v -s

# Set logging level
pytest tests/api_v2/ -v -s --log-cli-level=DEBUG
```

### Run Single Test with Debugging

```python
# Add breakpoint in test
import pdb; pdb.set_trace()

# Or use pytest debugging
pytest tests/api_v2/test_file.py -v -s --pdb
```

### Check WebSocket Messages

The tests collect all WebSocket messages in `MessageCollector`. To debug:

```python
# In test code
for msg in manager.collector.messages:
    print(f"Message: {msg}")
```

## Common Issues

### 1. Timeout Errors
- Increase timeout values in test cases
- Check if agent is actually running
- Verify model API keys are configured

### 2. WebSocket Connection Errors
- Ensure no other process is using the port
- Check FastAPI server startup logs
- Verify WebSocket URL format

### 3. Missing Final Answer
- Agent may be taking longer than expected
- Check for errors in agent execution
- Verify query complexity matches timeout

## Writing New Tests

1. Use `websocket_session` context manager:
```python
async with websocket_session(test_client, websocket_url) as manager:
    await manager.send_query("Your query")
    final_answer = await manager.wait_for_final_answer(timeout=60)
```

2. Always validate message format:
```python
assert_message_format(message)
```

3. Use appropriate timeouts for complex queries:
```python
# Simple queries: 30-60 seconds
# Complex queries: 120-300 seconds
# Research queries: 1000-2000 seconds
```

## CI/CD Integration

For CI/CD pipelines, consider:

1. Running only fast tests by default
2. Setting shorter timeouts for CI
3. Mocking external API calls
4. Using test-specific model configurations

Example GitHub Actions configuration:

```yaml
- name: Run API v2 Tests
  run: |
    pytest tests/api_v2/ -v -m "not slow and not integration"
  timeout-minutes: 10
```
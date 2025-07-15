# DeepSearchAgents Test Suite

This directory contains the comprehensive test suite for DeepSearchAgents v0.2.9, covering all new features and ensuring backward compatibility with v0.2.8.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_base_agent.py
│   ├── test_react_agent.py
│   ├── test_codact_agent.py
│   ├── test_manager_agent.py
│   ├── test_multi_model_router.py
│   └── test_run_result.py
├── integration/             # Integration tests for component interactions
│   ├── test_managed_agents.py
│   ├── test_parallel_tools.py
│   ├── test_streaming.py
│   └── test_structured_generation.py
├── performance/            # Performance benchmarks
│   ├── test_token_usage.py
│   └── test_execution_time.py
├── compatibility/          # Backward compatibility tests
│   ├── test_backward_compatibility.py
│   └── test_migration.py
└── conftest.py            # Pytest configuration and fixtures
```

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run unit tests only
python run_tests.py unit

# Run with coverage
python run_tests.py -c

# Run quick smoke tests (no API calls)
python run_tests.py --smoke
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_base_agent.py

# Run tests by marker
pytest -m unit
pytest -m "not requires_llm"  # Skip tests requiring LLM API

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Markers

- `unit` - Unit tests for individual components
- `integration` - Integration tests requiring multiple components
- `performance` - Performance benchmarks
- `compatibility` - Backward compatibility tests
- `requires_llm` - Tests requiring LLM API access
- `requires_search` - Tests requiring search API access
- `slow` - Tests that take more than 5 seconds

## Environment Setup

### Required Environment Variables

For full test suite:
```bash
export LITELLM_MASTER_KEY="your-key"
export SERPER_API_KEY="your-key"
export JINA_API_KEY="your-key"
export WOLFRAM_ALPHA_APP_ID="your-app-id"
export XAI_API_KEY="your-key"
```

For smoke tests (no API keys needed):
```bash
python run_tests.py --smoke
```

### Test Configuration

Tests use reduced limits for faster execution:
- `MAX_STEPS`: 5 (reduced from default)
- `PLANNING_INTERVAL`: 2 (reduced from default)
- `ENABLE_STREAMING`: False (for consistent testing)

## Key Test Coverage

### 1. Core Framework (Unit Tests)

- **MultiModelRouter**: Model selection, token counting, streaming
- **BaseAgent**: Initialization, callable interface, context managers
- **ReactAgent**: Parallel tools, managed agents, configuration
- **CodeActAgent**: Structured generation, security, authorized imports
- **ManagerAgent**: Delegation, task analysis, orchestration
- **RunResult**: Metadata collection, serialization

### 2. New Features (Integration Tests)

- **Managed Agents**: Hierarchical agent management, delegation
- **Parallel Tools**: Concurrent execution, thread configuration
- **Streaming**: New architecture, error handling
- **Structured Generation**: JSON output format, prompt loading

### 3. Performance Tests

- **Token Usage**: Accuracy, overhead, aggregation
- **Execution Time**: Measurement accuracy, initialization, cleanup

### 4. Compatibility Tests

- **Backward Compatibility**: Legacy APIs, state formats, error handling
- **Migration**: Settings, new components, security enhancements

## Writing New Tests

### Test Template

```python
import pytest
from src.agents.runtime import AgentRuntime

class TestNewFeature:
    """Test new feature functionality."""
    
    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime
    
    @pytest.mark.unit
    def test_feature_behavior(self, runtime):
        """Test specific behavior."""
        # Test implementation
        assert True
```

### Best Practices

1. **Use fixtures** for common setup
2. **Mark tests appropriately** (unit, integration, etc.)
3. **Skip tests** when dependencies unavailable
4. **Clean up resources** using cleanup_agents fixture
5. **Test both success and error cases**
6. **Avoid mocking core functionality** - test real behavior

## CI/CD Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run unit tests
  run: python run_tests.py unit -v

- name: Run integration tests
  if: github.event_name == 'push'
  run: python run_tests.py integration -v
  
- name: Generate coverage
  run: python run_tests.py all -c
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Set environment variables or run smoke tests
2. **Import Errors**: Ensure `uv pip install -e ".[dev,test]"` was run
3. **Slow Tests**: Use markers to skip slow tests: `pytest -m "not slow"`
4. **Flaky Tests**: May be due to API rate limits or network issues

### Debug Mode

```bash
# Run with detailed output
pytest -vvs tests/unit/test_base_agent.py::TestBaseAgent::test_initialization

# Run with pdb on failure
pytest --pdb tests/unit/test_multi_model_router.py
```

## Contributing

When adding new features:
1. Write unit tests first
2. Add integration tests for component interactions
3. Include performance tests if relevant
4. Ensure backward compatibility
5. Update this README with new test information
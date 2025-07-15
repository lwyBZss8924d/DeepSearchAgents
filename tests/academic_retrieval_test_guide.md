# AcademicRetrieval Tool Test Guide

This guide explains how to test the AcademicRetrieval tool in DeepSearchAgents.

## Prerequisites

1. **FutureHouse API Key**: You must have a valid FutureHouse API key to run these tests.
   ```bash
   export FUTUREHOUSE_API_KEY='your-api-key-here'
   ```

2. **Environment Setup**: Ensure all dependencies are installed:
   ```bash
   uv pip install -e ".[dev,test,cli]"
   ```

## Test Files

- `tests/integration/test_academic_retrieval_integration.py` - Direct tool testing
- `tests/integration/test_academic_retrieval_cli.py` - CLI agent integration testing
- `tests/test_case_codact.md` - Example test queries for manual testing

## Running Tests

### Using the Test Runner

The easiest way to run tests is using the test runner script:

```bash
# Run all tests
python tests/run_academic_tests.py

# Run only integration tests
python tests/run_academic_tests.py integration

# Run only CLI tests
python tests/run_academic_tests.py cli

# Run a specific test
python tests/run_academic_tests.py test_search_operation_react_papers

# Run manual CLI test
python tests/run_academic_tests.py manual
```

### Using pytest directly

```bash
# Run all academic retrieval tests
pytest tests/integration/test_academic_retrieval_*.py -xvs

# Run a specific test file
pytest tests/integration/test_academic_retrieval_integration.py -xvs

# Run a specific test function
pytest tests/integration/test_academic_retrieval_integration.py::TestAcademicRetrievalIntegration::test_search_operation_react_papers -xvs
```

### Manual CLI Testing

You can test the tool directly through the CLI:

```bash
# Test with React agent
python -m src.cli --agent-type react --query "Use the academic_retrieval tool to search for papers about 'transformer architecture'"

# Test with CodeAct agent
python -m src.cli --agent-type codact --query "Use academic_retrieval with operation='research' to analyze the HiRA framework paper"
```

## Test Cases

### 1. Search Operation Test
Tests the basic paper search functionality:
- Searches for AI-LLM Agent papers about ReAct methodology
- Verifies response structure and content
- Checks metadata and result formatting

### 2. Research Operation Test
Tests the deep research functionality:
- Researches the HiRA framework paper
- Verifies comprehensive report generation
- Checks Chinese language output

### 3. CLI Integration Tests
Tests the tool integration with different agents:
- React agent paper search workflow
- CodeAct agent research workflow
- Manager agent team research
- Error handling and edge cases

## Expected Outputs

### Search Operation
```json
{
  "operation": "search",
  "query": "your search query",
  "results": [
    {
      "title": "Paper Title",
      "url": "paper://url",
      "description": "Paper abstract...",
      "snippets": ["relevant snippet..."]
    }
  ],
  "total_results": 20,
  "meta": {
    "source": "futurehouse_crow",
    "timeout": 600,
    "verbose": true
  }
}
```

### Research Operation
```json
{
  "operation": "research",
  "query": "your research query",
  "content": "Comprehensive research report...",
  "meta": {
    "source": "futurehouse_falcon",
    "timeout": 1200,
    "verbose": true
  }
}
```

## Troubleshooting

1. **API Key Issues**
   - Ensure `FUTUREHOUSE_API_KEY` is set correctly
   - Check if the key has proper permissions

2. **Timeout Issues**
   - Research operations may take 10-20 minutes
   - Adjust timeout values if needed

3. **Rate Limiting**
   - Tests include delays to avoid rate limiting
   - Run tests sequentially, not in parallel

4. **Network Issues**
   - Ensure stable internet connection
   - Check if FutureHouse API is accessible

## Notes

- The research operation is resource-intensive and may take significant time
- Chinese output is expected for certain test cases
- Some tests are marked as `@pytest.mark.slow` due to long execution times
# Academic Toolkit Tests

This directory contains comprehensive tests for the academic paper retrieval system. All tests are designed to work WITHOUT mocking, testing real behavior.

## Test Structure

```
tests/
├── test_arxiv_client.py          # Unit tests for ArXiv search functionality
├── test_paper_reader.py          # Unit tests for PDF/HTML parsing
├── test_paper_retriever.py       # Unit tests for orchestration layer
├── test_integration_workflow.py  # Integration tests for complete workflows
├── test_integration_apis.py      # Integration tests for external APIs
├── test_metadata_merger.py       # Unit tests for metadata merging (existing)
└── run_academic_tests.py         # Test runner script
```

## Running Tests

### Quick Start

```bash
# Run all tests
python tests/run_academic_tests.py

# Run specific user examples
python tests/run_academic_tests.py --examples

# Run individual test files
pytest tests/test_arxiv_client.py -v
pytest tests/test_paper_reader.py -v
pytest tests/test_paper_retriever.py -v
```

### Test Categories

1. **Unit Tests** - Test individual components
   - No API keys required
   - Use real ArXiv API (with rate limiting)
   - Fast execution

2. **Integration Tests** - Test complete workflows
   - May require API keys for full functionality
   - Test real-world scenarios
   - Slower execution

### API Configuration

Some tests require API keys for full functionality:

```bash
# Optional - for PDF parsing
export MISTRAL_API_KEY="your-key-here"

# Optional - for HTML parsing
export JINA_API_KEY="your-key-here"
```

Tests will automatically skip API-dependent functionality if keys are not configured.

## Test Examples

The tests cover the specific examples provided:

### Example 1: Search for AI-LLM Agent Papers
```python
# Searches for "AI LLM Agent papers about ReAct agent methodology"
# Tests search, deduplication, and batch reading
pytest tests/test_integration_workflow.py::test_search_ai_llm_agent_papers -v
```

### Example 2: Read Specific Paper
```python
# Reads the ReAct paper (arXiv:2210.03629)
# Tests paper retrieval by ID and content extraction
pytest tests/test_integration_workflow.py::test_read_specific_paper -v
```

### Example 3: HTML Availability Detection
```python
# Tests HTML availability detection with two papers:
# - ReAct (2210.03629): No HTML version, should use PDF
# - CodeAct (2402.01030): Has HTML version, should prefer HTML
pytest tests/test_paper_reader.py::test_html_availability_detection -v

# Integration test for CodeAct paper with HTML
pytest tests/test_integration_workflow.py::test_codeact_paper_html_version -v
```

## Key Test Features

### No Mocking Policy
- All tests use real implementations
- External APIs are called directly
- Rate limiting is respected (3-second delays for ArXiv)

### Comprehensive Coverage
- Search functionality with various parameters
- PDF and HTML parsing
- Metadata merging
- Error handling
- Concurrent operations
- Rate limiting compliance

### Real-World Testing
- Tests use actual ArXiv papers
- Verifies content extraction quality
- Tests error recovery
- Measures performance

## Test Data

Common test papers used:
- **ReAct Paper**: arXiv:2210.03629
- **GPT-4 Paper**: arXiv:2303.08774
- **Attention Paper**: arXiv:1706.03762
- **BERT Paper**: arXiv:1810.04805

## Running Specific Test Types

```bash
# Unit tests only
pytest -m unit tests/

# Integration tests only
pytest -m integration tests/

# Tests requiring Mistral API
pytest -m requires_mistral tests/

# Tests requiring Jina API
pytest -m requires_jina tests/

# Slow tests (> 5 seconds)
pytest -m slow tests/
```

## Debugging Tests

```bash
# Run with verbose output
pytest tests/test_arxiv_client.py -v -s

# Run specific test method
pytest tests/test_arxiv_client.py::TestArxivClient::test_search_react_papers -v

# Run with coverage
pytest --cov=src.core.academic_tookit tests/
```

## Expected Test Results

### Without API Keys
- ArXiv search tests: ✓ Pass
- Basic retriever tests: ✓ Pass
- Format selection tests: ✓ Pass
- PDF/HTML parsing tests: ⚠️ Skip

### With API Keys
- All tests: ✓ Pass
- Full content extraction: ✓ Available
- Metadata merging: ✓ Verified

## Troubleshooting

1. **Rate Limit Errors**: Tests include 3-second delays between ArXiv requests
2. **Connection Errors**: Check internet connectivity
3. **API Key Errors**: Verify keys are correctly set in environment
4. **Import Errors**: Run from project root directory

## Performance Expectations

- Unit tests: < 30 seconds total
- Integration tests: 2-5 minutes (with API calls)
- Rate-limited tests: ~6 seconds per 3 requests

## Future Enhancements

Currently pending tasks:
- Optimize PDF parser to skip redundant extraction (when search metadata available)
- Optimize HTML parser to skip redundant extraction
- Add more edge case testing
- Performance benchmarking suite
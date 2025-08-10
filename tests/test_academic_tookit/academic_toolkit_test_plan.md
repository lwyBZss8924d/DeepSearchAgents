# Academic Toolkit Test Plan

## Overview
This document outlines the comprehensive test plan for the academic paper retrieval system in DeepSearchAgents. The tests are designed to verify functionality WITHOUT using mocks, testing real behavior while managing external dependencies.

## Test Strategy
- **Unit Tests**: Test individual components with controlled inputs
- **Integration Tests**: Test component interactions and real API calls
- **No Mocking Policy**: Use real implementations, control behavior through configuration and test data

## 1. Unit Tests

### 1.1 ArxivClient Tests (`tests/test_arxiv_client.py`)

#### Test Scenarios:

1. **Basic Search Functionality**
   ```python
   # Test 1: Search for "ReAct agent methodology" papers
   async def test_search_react_papers():
       """Test searching for ReAct agent papers returns relevant results."""
       client = ArxivClient()
       params = SearchParams(
           query="ReAct agent methodology",
           max_results=5
       )
       papers = await client.search(params)
       assert len(papers) > 0
       assert any("react" in p.title.lower() for p in papers)
   ```

2. **Advanced Search with Categories**
   ```python
   # Test 2: Search AI papers in specific categories
   async def test_search_with_categories():
       """Test category-filtered search."""
       client = ArxivClient()
       params = SearchParams(
           query="language models",
           categories=["cs.AI", "cs.CL"],
           max_results=10
       )
       papers = await client.search(params)
       assert all(any(cat in p.categories for cat in ["cs.AI", "cs.CL"]) for p in papers)
   ```

3. **Get Paper by ID**
   ```python
   # Test 3: Retrieve specific paper by arXiv ID
   async def test_get_paper_by_id():
       """Test retrieving the ReAct paper by its ID."""
       client = ArxivClient()
       paper = await client.get_paper("2210.03629")  # ReAct paper
       assert paper is not None
       assert "ReAct" in paper.title
       assert paper.paper_id == "2210.03629"
   ```

4. **Natural Language Query Processing**
   ```python
   # Test 4: Test NLP query interpretation
   async def test_natural_language_query():
       """Test that natural language queries work correctly."""
       client = ArxivClient()
       params = SearchParams(
           query="papers about ReAct agent more methodology in 2024-2025",
           max_results=10
       )
       papers = await client.search(params)
       assert len(papers) > 0
       # Verify date filter worked
       for paper in papers:
           assert paper.published_date.year >= 2023 and paper.published_date.year <= 2026
   ```

5. **Error Handling**
   ```python
   # Test 5: Handle invalid paper IDs gracefully
   async def test_invalid_paper_id():
       """Test error handling for non-existent papers."""
       client = ArxivClient()
       paper = await client.get_paper("invalid.id.12345")
       assert paper is None
   ```

### 1.2 PaperReader Tests (`tests/test_paper_reader.py`)

#### Test Scenarios:

1. **PDF Reading from URL**
   ```python
   # Test 1: Read a known PDF paper
   async def test_read_pdf_from_url():
       """Test reading PDF content from a URL."""
       reader = PaperReader()
       paper = Paper(
           paper_id="2210.03629",
           title="ReAct: Synergizing Reasoning and Acting in Language Models",
           pdf_url="https://arxiv.org/pdf/2210.03629.pdf",
           source="arxiv"
       )
       
       result = await reader.read_paper(paper, force_format="pdf")
       assert result["content_format"] == "pdf"
       assert len(result["full_text"]) > 1000
       assert len(result["sections"]) > 0
   ```

2. **HTML Reading (if available)**
   ```python
   # Test 2: Read HTML version when available
   async def test_read_html_when_available():
       """Test preferring HTML format when available."""
       reader = PaperReader()
       # Use a paper with known HTML version
       paper = Paper(
           paper_id="test_html",
           title="Test Paper",
           html_url="https://ar5iv.labs.arxiv.org/html/2210.03629",
           pdf_url="https://arxiv.org/pdf/2210.03629.pdf",
           source="arxiv"
       )
       
       result = await reader.read_paper(paper)
       assert result["content_format"] == "html"
   ```

3. **Format Selection Logic**
   ```python
   # Test 3: Verify format selection priority
   async def test_format_selection_priority():
       """Test that HTML is preferred over PDF when both available."""
       reader = PaperReader()
       paper = Paper(
           paper_id="test",
           title="Test",
           html_url="https://example.com/paper.html",
           pdf_url="https://example.com/paper.pdf",
           source="test"
       )
       
       # Should choose HTML by default
       format_chosen = reader._select_format(paper, force_format=None)
       assert format_chosen == "html"
   ```

4. **Metadata Merging**
   ```python
   # Test 4: Verify metadata merger integration
   async def test_metadata_merging_in_reader():
       """Test that search metadata is preserved during reading."""
       reader = PaperReader()
       paper = Paper(
           paper_id="2210.03629",
           title="ReAct: Synergizing Reasoning and Acting in Language Models",
           authors=["Shunyu Yao", "Jeffrey Zhao", "Dian Yu"],
           doi="10.48550/arXiv.2210.03629",
           pdf_url="https://arxiv.org/pdf/2210.03629.pdf",
           source="arxiv"
       )
       
       result = await reader.read_paper(paper)
       # Verify search metadata is preserved
       assert result["metadata"]["authors"] == paper.authors
       assert result["metadata"]["doi"] == paper.doi
   ```

### 1.3 PaperRetriever Tests (`tests/test_paper_retriever.py`)

#### Test Scenarios:

1. **Basic Search and Retrieval**
   ```python
   # Test 1: Search for papers
   async def test_basic_search():
       """Test basic paper search functionality."""
       retriever = PaperRetriever()
       papers = await retriever.search(
           query="ReAct agent methodology",
           max_results=5
       )
       assert len(papers) <= 5
       assert all(isinstance(p, Paper) for p in papers)
   ```

2. **Search and Read Workflow**
   ```python
   # Test 2: Complete search and read workflow
   async def test_search_and_read():
       """Test searching and reading papers in one operation."""
       retriever = PaperRetriever()
       results = await retriever.search_and_read(
           query="ReAct: Synergizing Reasoning and Acting",
           max_papers=1
       )
       
       assert len(results) == 1
       result = results[0]
       assert "full_text" in result
       assert "sections" in result
       assert "harmonized_metadata" in result
       assert result["harmonized_metadata"]["title"] is not None
   ```

3. **Batch Reading**
   ```python
   # Test 3: Read multiple papers concurrently
   async def test_batch_reading():
       """Test concurrent paper reading with rate limiting."""
       retriever = PaperRetriever()
       papers = await retriever.search(
           query="transformer models",
           max_results=3
       )
       
       content_dict = await retriever.read_papers_batch(
           papers,
           max_concurrent=2
       )
       
       assert len(content_dict) == len(papers)
       for paper_id, content in content_dict.items():
           if "error" not in content:
               assert "full_text" in content
   ```

4. **Deduplication**
   ```python
   # Test 4: Verify deduplication works
   async def test_deduplication():
       """Test that duplicate papers are removed."""
       retriever = PaperRetriever()
       # Search with overlapping terms that might return duplicates
       papers = await retriever.search(
           query="ReAct reasoning acting",
           max_results=20,
           deduplicate=True
       )
       
       # Check no duplicate paper IDs
       paper_ids = [p.paper_id for p in papers]
       assert len(paper_ids) == len(set(paper_ids))
   ```

## 2. Integration Tests

### 2.1 Full Workflow Tests (`tests/test_integration_workflow.py`)

1. **Example 1: Search AI-LLM Agent Papers**
   ```python
   async def test_search_ai_llm_agent_papers():
       """Integration test for Example 1 from user."""
       retriever = PaperRetriever()
       
       # Search for ReAct papers and derived methods
       results = await retriever.search_and_read(
           query="AI LLM Agent papers ReAct agent methodology derived methods",
           max_papers=20,
           deduplicate=True
       )
       
       # Verify we got relevant papers
       assert len(results) > 0
       
       # Check for ReAct paper specifically
       react_found = any(
           "2210.03629" in r.get("harmonized_metadata", {}).get("paper_id", "")
           for r in results
       )
       assert react_found, "ReAct paper should be in results"
       
       # Verify full content extraction
       for result in results[:5]:  # Check first 5
           assert result["full_text"] is not None
           assert len(result["sections"]) > 0
   ```

2. **Example 2: Read Specific Paper**
   ```python
   async def test_read_specific_paper():
       """Integration test for Example 2 from user."""
       retriever = PaperRetriever()
       
       # Get the ReAct paper by ID
       paper = await retriever.get_paper("2210.03629", "arxiv")
       assert paper is not None
       
       # Read the paper
       content = await retriever.read_paper(paper)
       
       # Verify content
       assert content["harmonized_metadata"]["title"] == "ReAct: Synergizing Reasoning and Acting in Language Models"
       assert "Shunyu Yao" in str(content["harmonized_metadata"]["authors"])
       assert len(content["full_text"]) > 10000  # Substantial content
       assert any("reasoning" in s.get("title", "").lower() for s in content["sections"])
   ```

### 2.2 API Integration Tests (`tests/test_integration_apis.py`)

1. **ArXiv API Rate Limiting**
   ```python
   async def test_arxiv_rate_limiting():
       """Test that rate limiting is respected."""
       client = ArxivClient()
       
       # Make multiple rapid requests
       start_time = time.time()
       for i in range(3):
           params = SearchParams(query=f"test query {i}", max_results=1)
           await client.search(params)
       
       elapsed = time.time() - start_time
       # Should take at least 6 seconds (3 requests * 2 second delay)
       assert elapsed >= 6.0
   ```

2. **PDF Parsing with Mistral (if API key available)**
   ```python
   async def test_mistral_pdf_parsing():
       """Test real Mistral OCR API if configured."""
       if not os.getenv("MISTRAL_API_KEY"):
           pytest.skip("MISTRAL_API_KEY not configured")
       
       from src.core.academic_tookit.paper_reader.paper_parser_pdf import parse_pdf_with_ocr
       
       # Use a small test PDF
       metadata, text, sections, figures, tables = await parse_pdf_with_ocr(
           "https://arxiv.org/pdf/2210.03629.pdf"
       )
       
       assert metadata["title"] is not None
       assert len(text) > 1000
       assert len(sections) > 0
   ```

3. **HTML Parsing with Jina (if API key available)**
   ```python
   async def test_jina_html_parsing():
       """Test real Jina Reader API if configured."""
       if not os.getenv("JINA_API_KEY"):
           pytest.skip("JINA_API_KEY not configured")
       
       from src.core.academic_tookit.paper_reader.paper_parser_html import parse_html_with_jina
       
       metadata, text, sections = await parse_html_with_jina(
           "https://ar5iv.labs.arxiv.org/html/2210.03629"
       )
       
       assert metadata["title"] is not None
       assert len(text) > 1000
   ```

## 3. Performance Tests

### 3.1 Concurrency Tests (`tests/test_performance.py`)

```python
async def test_concurrent_search_performance():
    """Test that concurrent searches work efficiently."""
    retriever = PaperRetriever()
    
    queries = [
        "transformer models",
        "reinforcement learning",
        "computer vision",
        "natural language processing"
    ]
    
    start_time = time.time()
    
    # Search all queries concurrently
    tasks = [retriever.search(q, max_results=5) for q in queries]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    # Should complete faster than sequential (4 * 3 seconds = 12 seconds)
    assert elapsed < 10.0
    assert all(len(r) > 0 for r in results)
```

## 4. Error Handling Tests

### 4.1 Network Failures (`tests/test_error_handling.py`)

```python
async def test_network_timeout_handling():
    """Test handling of network timeouts."""
    retriever = PaperRetriever()
    
    # Use a paper with unreachable URL
    paper = Paper(
        paper_id="timeout_test",
        title="Test",
        pdf_url="https://invalid-domain-12345.com/paper.pdf",
        source="test"
    )
    
    result = await retriever.read_paper(paper)
    # Should handle gracefully, not crash
    assert "error" in result or result is None
```

## 5. Test Execution Strategy

### Running Tests

```bash
# Run all unit tests
pytest tests/test_arxiv_client.py -v
pytest tests/test_paper_reader.py -v
pytest tests/test_paper_retriever.py -v

# Run integration tests (slower, requires network)
pytest tests/test_integration_workflow.py -v -s

# Run API integration tests (requires API keys)
MISTRAL_API_KEY=xxx JINA_API_KEY=yyy pytest tests/test_integration_apis.py -v

# Run with coverage
pytest --cov=src.core.academic_tookit tests/ -v
```

### Test Configuration

Create `tests/conftest.py`:
```python
import pytest
import asyncio
import os

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def skip_if_no_api_key():
    """Skip test if API keys not configured."""
    def _skip(api_name):
        key_name = f"{api_name.upper()}_API_KEY"
        if not os.getenv(key_name):
            pytest.skip(f"{key_name} not configured")
    return _skip
```

## 6. Expected Results

### Success Criteria
1. All unit tests pass without external API calls
2. Integration tests successfully retrieve and read real papers
3. Error handling tests demonstrate graceful failure
4. Performance tests show concurrent operations work correctly
5. No mocking required - all tests use real implementations

### Key Metrics
- Unit test execution time: < 30 seconds
- Integration test execution time: < 5 minutes
- Code coverage: > 80% for core modules
- API rate limits respected
- Concurrent operations properly managed
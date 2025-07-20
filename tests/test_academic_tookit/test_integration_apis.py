#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_integration_apis.py

"""
Integration tests for real API interactions.
These tests require API keys and make real API calls.
"""

import pytest
import asyncio
import os
import time

from src.core.academic_tookit.paper_search.arxiv import ArxivClient
from src.core.academic_tookit.models import SearchParams


@pytest.mark.integration
class TestArxivAPIIntegration:
    """Test real ArXiv API interactions."""
    
    @pytest.mark.asyncio
    async def test_arxiv_rate_limiting(self, arxiv_client):
        """Test that rate limiting is properly enforced."""
        client = arxiv_client
        
        # Make 3 rapid requests
        start_time = time.time()
        
        for i in range(3):
            params = SearchParams(query=f"test query {i}", max_results=1)
            await client.search(params)
        
        elapsed = time.time() - start_time
        
        # Should take at least 6 seconds (3 requests * 3 second delay)
        # Allow some margin for execution time
        assert elapsed >= 5.5, f"Rate limiting not enforced: {elapsed:.2f}s"
        
        print(f"\nRate limiting test: {elapsed:.2f}s for 3 requests")
    
    @pytest.mark.asyncio
    async def test_arxiv_connection_validation(self, arxiv_client):
        """Test ArXiv connection validation."""
        client = arxiv_client
        
        is_valid = await client.validate_connection()
        
        assert is_valid is True
        print("\nArXiv connection validated successfully")
    
    @pytest.mark.asyncio
    async def test_arxiv_large_result_handling(self, arxiv_client,
                                               rate_limit_delay):
        """Test handling of large result sets."""
        client = arxiv_client
        
        params = SearchParams(
            query="machine learning",
            max_results=100  # Large request
        )
        
        papers = await client.search(params)
        
        assert len(papers) > 50  # Should get many results
        assert len(papers) <= 100
        
        # Verify all papers have required fields
        for paper in papers[:10]:  # Check first 10
            assert paper.paper_id is not None
            assert paper.title is not None
            assert paper.authors is not None
            assert paper.abstract is not None
            assert paper.pdf_url is not None
        
        print(f"\nLarge result test: Retrieved {len(papers)} papers")
        
        await asyncio.sleep(rate_limit_delay)


@pytest.mark.integration
@pytest.mark.requires_mistral
class TestMistralAPIIntegration:
    """Test real Mistral OCR API interactions."""
    
    @pytest.mark.asyncio
    async def test_mistral_pdf_parsing(self, skip_if_no_api_key):
        """Test real Mistral OCR API if configured."""
        skip_if_no_api_key("mistral")
        
        from src.core.academic_tookit.paper_reader.paper_parser_pdf import (
            parse_pdf_with_ocr
        )
        
        # Use the ReAct paper as test
        pdf_url = "https://arxiv.org/pdf/2210.03629.pdf"
        
        print("\nTesting Mistral PDF parsing...")
        start_time = time.time()
        
        result = await parse_pdf_with_ocr(pdf_url)
        
        elapsed = time.time() - start_time
        print(f"PDF parsing completed in {elapsed:.2f}s")
        
        # Unpack the 5-element tuple
        metadata, text, sections, figures, tables = result
        
        # Verify extraction quality
        assert metadata is not None
        assert metadata.get("title") is not None
        assert "ReAct" in metadata["title"]
        
        assert len(text) > 10000  # Substantial content
        assert len(sections) >= 5  # Multiple sections
        
        # Check section quality
        section_titles = [s.get("title", "").lower() for s in sections]
        assert any("introduction" in t for t in section_titles)
        assert any("conclusion" in t for t in section_titles)
        
        print(f"Extracted {len(sections)} sections, {len(text)} chars")
        print(f"Found {len(figures)} figures, {len(tables)} tables")
    
    @pytest.mark.asyncio
    async def test_mistral_error_handling(self, skip_if_no_api_key):
        """Test Mistral API error handling."""
        skip_if_no_api_key("mistral")
        
        from src.core.academic_tookit.paper_reader.paper_parser_pdf import (
            parse_pdf_with_ocr
        )
        
        # Try to parse invalid URL
        with pytest.raises(Exception):
            await parse_pdf_with_ocr("https://invalid-url-12345.com/fake.pdf")


@pytest.mark.integration
@pytest.mark.requires_jina
class TestJinaAPIIntegration:
    """Test real Jina Reader API interactions."""
    
    @pytest.mark.asyncio
    async def test_jina_html_parsing(self, skip_if_no_api_key):
        """Test real Jina Reader API if configured."""
        skip_if_no_api_key("jina")
        
        from src.core.academic_tookit.paper_reader.paper_parser_html import (
            parse_html_with_jina
        )
        
        # Use ar5iv HTML version of a paper
        html_url = "https://ar5iv.labs.arxiv.org/html/2210.03629"
        
        print("\nTesting Jina HTML parsing...")
        start_time = time.time()
        
        metadata, text, sections = await parse_html_with_jina(html_url)
        
        elapsed = time.time() - start_time
        print(f"HTML parsing completed in {elapsed:.2f}s")
        
        # Verify extraction quality
        assert metadata is not None
        assert len(text) > 5000  # Substantial content
        assert len(sections) > 0
        
        # Check metadata
        if metadata.get("title"):
            assert "ReAct" in metadata["title"] or len(metadata["title"]) > 10
        
        print(f"Extracted {len(sections)} sections, {len(text)} chars")
    
    @pytest.mark.asyncio
    async def test_jina_rate_limiting(self, skip_if_no_api_key):
        """Test Jina API rate limiting behavior."""
        skip_if_no_api_key("jina")
        
        from src.core.academic_tookit.paper_reader.paper_parser_html import (
            parse_html_with_jina
        )
        
        # Make multiple requests
        urls = [
            "https://ar5iv.labs.arxiv.org/html/1706.03762",  # Attention
            "https://ar5iv.labs.arxiv.org/html/1810.04805",  # BERT
        ]
        
        start_time = time.time()
        
        for url in urls:
            try:
                await parse_html_with_jina(url)
                await asyncio.sleep(1)  # Polite delay
            except Exception as e:
                print(f"Request failed: {e}")
        
        elapsed = time.time() - start_time
        print(f"\nJina rate limit test: {elapsed:.2f}s for {len(urls)} requests")


@pytest.mark.integration
class TestEndToEndAPIWorkflow:
    """Test complete end-to-end workflows with all APIs."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_paper_processing(self, paper_retriever,
                                             skip_if_no_api_key):
        """Test complete workflow: search, retrieve, and parse with all APIs."""
        skip_if_no_api_key("mistral")  # Requires at least Mistral for PDF
        
        retriever = paper_retriever
        
        print("\n=== Starting complete paper processing test ===")
        
        # Step 1: Search for a specific paper
        print("Step 1: Searching for papers...")
        papers = await retriever.search(
            query="attention is all you need transformer",
            max_results=1
        )
        
        assert len(papers) > 0
        paper = papers[0]
        print(f"Found paper: {paper.title}")
        
        # Step 2: Read the paper (will use available APIs)
        print("Step 2: Reading paper content...")
        start_time = time.time()
        
        content = await retriever.read_paper(paper)
        
        elapsed = time.time() - start_time
        print(f"Paper read in {elapsed:.2f}s using {content['content_format']}")
        
        # Step 3: Verify complete extraction
        assert content is not None
        assert "error" not in content
        assert len(content["full_text"]) > 5000
        assert len(content["sections"]) > 3
        
        # Step 4: Check metadata merging worked
        meta = content["harmonized_metadata"]
        assert meta["title"] == paper.title
        assert meta["authors"] == paper.authors
        assert meta["paper_id"] == paper.paper_id
        
        print(f"\nExtraction summary:")
        print(f"- Format: {content['content_format']}")
        print(f"- Sections: {len(content['sections'])}")
        print(f"- Text length: {len(content['full_text'])} chars")
        print(f"- References: {len(content.get('references', []))}")
        print(f"- Figures: {len(content.get('figures', []))}")
        print(f"- Tables: {len(content.get('tables', []))}")
        
        print("\n=== Complete paper processing test finished ===")


@pytest.mark.integration
class TestPerformanceMetrics:
    """Test and measure API performance metrics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, paper_retriever):
        """Test concurrent search performance."""
        retriever = paper_retriever
        
        queries = [
            "deep learning",
            "natural language processing",
            "computer vision",
            "reinforcement learning"
        ]
        
        print("\n=== Testing concurrent search performance ===")
        start_time = time.time()
        
        # Search all queries concurrently
        tasks = [retriever.search(q, max_results=5) for q in queries]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # Verify results
        assert all(len(r) > 0 for r in results)
        
        total_papers = sum(len(r) for r in results)
        print(f"Concurrent search completed in {elapsed:.2f}s")
        print(f"Retrieved {total_papers} papers across {len(queries)} queries")
        print(f"Average time per query: {elapsed/len(queries):.2f}s")
        
        # Should be faster than sequential (which would take ~12s with delays)
        assert elapsed < 10.0
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_batch_processing_performance(self, paper_retriever,
                                                skip_if_no_api_key):
        """Test batch paper reading performance."""
        skip_if_no_api_key("mistral")
        
        retriever = paper_retriever
        
        # Get multiple papers
        papers = await retriever.search(
            query="machine learning",
            max_results=3
        )
        
        print(f"\n=== Testing batch reading of {len(papers)} papers ===")
        start_time = time.time()
        
        content_dict = await retriever.read_papers_batch(
            papers,
            max_concurrent=2
        )
        
        elapsed = time.time() - start_time
        
        successful = sum(1 for c in content_dict.values() if "error" not in c)
        
        print(f"Batch reading completed in {elapsed:.2f}s")
        print(f"Successfully read {successful}/{len(papers)} papers")
        print(f"Average time per paper: {elapsed/len(papers):.2f}s")
        
        assert successful > 0
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_paper_retriever.py

"""
Unit tests for PaperRetriever - orchestration and integration testing.
"""

import pytest
import asyncio
from datetime import datetime

from src.core.academic_tookit.models import Paper, SearchParams, PaperSource
from src.core.academic_tookit.paper_retrievaler import PaperRetriever


@pytest.mark.unit
class TestPaperRetriever:
    """Test PaperRetriever functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self, paper_retriever, academic_search_queries,
                                rate_limit_delay):
        """Test basic paper search functionality."""
        retriever = paper_retriever
        
        papers = await retriever.search(
            query=academic_search_queries["react"],
            max_results=5
        )
        
        assert len(papers) <= 5
        assert all(isinstance(p, Paper) for p in papers)
        assert all(p.source == PaperSource.ARXIV for p in papers)
        
        # Check relevance
        assert any("react" in p.title.lower() or
                   "reasoning" in p.abstract.lower()[:200]
                   for p in papers)
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_search_with_categories(self, paper_retriever,
                                          rate_limit_delay):
        """Test search with category filtering."""
        retriever = paper_retriever
        
        papers = await retriever.search(
            query="transformer models",
            max_results=10,
            categories=["cs.CL", "cs.LG"]
        )
        
        assert len(papers) > 0
        assert len(papers) <= 10
        
        # Verify categories
        for paper in papers:
            assert any(cat in paper.categories 
                       for cat in ["cs.CL", "cs.LG"])
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_and_read(self, paper_retriever, rate_limit_delay,
                                   skip_if_no_api_key):
        """Test complete search and read workflow."""
        skip_if_no_api_key("mistral")  # Need API for reading
        
        retriever = paper_retriever
        
        results = await retriever.search_and_read(
            query="ReAct: Synergizing Reasoning and Acting",
            max_papers=1
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Verify structure
        assert "full_text" in result
        assert "sections" in result
        assert "harmonized_metadata" in result
        assert "metadata" in result
        assert "content_format" in result
        
        # Verify harmonized metadata
        meta = result["harmonized_metadata"]
        assert meta["title"] is not None
        assert "ReAct" in meta["title"]
        assert len(meta["authors"]) > 0
        assert meta["source"] == PaperSource.ARXIV
        
        # Verify extraction info
        assert "extraction_info" in meta
        assert meta["extraction_info"]["format"] in ["pdf", "html"]
        assert meta["extraction_info"]["sections_count"] >= 0
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_batch_reading(self, paper_retriever, rate_limit_delay):
        """Test concurrent paper reading with rate limiting."""
        retriever = paper_retriever
        
        # First get some papers
        papers = await retriever.search(
            query="machine learning",
            max_results=3
        )
        
        assert len(papers) >= 1
        papers_to_read = papers[:min(3, len(papers))]
        
        # Test batch reading
        content_dict = await retriever.read_papers_batch(
            papers_to_read,
            max_concurrent=2
        )
        
        assert len(content_dict) == len(papers_to_read)
        assert all(paper_id in content_dict 
                   for paper_id in [p.paper_id for p in papers_to_read])
        
        # Check content structure (may have errors without API keys)
        for paper_id, content in content_dict.items():
            assert isinstance(content, dict)
            if "error" not in content:
                assert "full_text" in content or "error" in content
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_deduplication(self, paper_retriever, rate_limit_delay):
        """Test that duplicate papers are removed."""
        retriever = paper_retriever
        
        # Search with broad terms that might return duplicates
        papers = await retriever.search(
            query="ReAct reasoning acting language models",
            max_results=20,
            deduplicate=True
        )
        
        # Check no duplicate paper IDs
        paper_ids = [p.paper_id for p in papers]
        assert len(paper_ids) == len(set(paper_ids))
        
        # Also check no duplicate DOIs (where present)
        dois = [p.doi for p in papers if p.doi]
        assert len(dois) == len(set(dois))
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_get_paper_by_id(self, paper_retriever,
                                    arxiv_test_paper_ids, rate_limit_delay):
        """Test retrieving specific paper by ID."""
        retriever = paper_retriever
        
        paper = await retriever.get_paper(
            paper_id=arxiv_test_paper_ids["react"],
            source=PaperSource.ARXIV
        )
        
        assert paper is not None
        assert paper.paper_id == arxiv_test_paper_ids["react"]
        assert "ReAct" in paper.title
        assert paper.source == PaperSource.ARXIV
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_get_paper_by_doi(self, paper_retriever, rate_limit_delay):
        """Test retrieving paper by DOI."""
        retriever = paper_retriever
        
        # ReAct paper DOI
        doi = "10.48550/arXiv.2210.03629"
        
        paper = await retriever.get_paper_by_doi(doi)
        
        assert paper is not None
        assert paper.doi == doi
        assert "ReAct" in paper.title
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_find_related_papers(self, paper_retriever, sample_paper,
                                       rate_limit_delay):
        """Test finding papers related to a reference paper."""
        retriever = paper_retriever
        
        related = await retriever.find_related_papers(
            reference_paper=sample_paper,
            max_results=5
        )
        
        assert len(related) > 0
        assert len(related) <= 5
        
        # Related papers should be about similar topics
        for paper in related[:3]:
            # Check for topic relevance
            relevant = (
                any(cat in paper.categories for cat in sample_paper.categories) or
                any(keyword in paper.title.lower() 
                    for keyword in ["agent", "reasoning", "language model"])
            )
            assert relevant
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_error_handling_no_sources(self, paper_retriever):
        """Test error when no sources are available."""
        retriever = paper_retriever
        
        # Request non-existent source
        with pytest.raises(ValueError) as exc_info:
            await retriever.search(
                query="test",
                sources=["nonexistent_source"]
            )
        
        assert "No available sources found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_parameters(self, paper_retriever, rate_limit_delay):
        """Test various search parameter combinations."""
        retriever = paper_retriever
        
        # Test with date range
        from datetime import datetime, timedelta
        start_date = datetime.now() - timedelta(days=365)
        
        papers = await retriever.search(
            query="deep learning",
            max_results=5,
            start_date=start_date,
            sort_by="submitted_date"
        )
        
        assert len(papers) > 0
        assert all(p.published_date >= start_date.date() for p in papers)
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_available_sources(self, paper_retriever):
        """Test getting available sources."""
        retriever = paper_retriever
        
        sources = retriever.get_available_sources()
        
        assert isinstance(sources, list)
        assert PaperSource.ARXIV in sources
        # Future sources would be added here
    
    @pytest.mark.asyncio
    async def test_validate_sources(self, paper_retriever):
        """Test source connectivity validation."""
        retriever = paper_retriever
        
        validation_results = await retriever.validate_sources()
        
        assert isinstance(validation_results, dict)
        assert PaperSource.ARXIV in validation_results
        assert validation_results[PaperSource.ARXIV] is True
    
    @pytest.mark.asyncio
    async def test_read_paper_with_metadata_enhancement(
            self, paper_retriever, arxiv_test_paper_ids,
            rate_limit_delay, skip_if_no_api_key):
        """Test that read_paper enhances results with paper metadata."""
        skip_if_no_api_key("mistral")
        
        retriever = paper_retriever
        
        # Get a specific paper
        paper = await retriever.get_paper(
            arxiv_test_paper_ids["react"],
            PaperSource.ARXIV
        )
        
        # Read it
        result = await retriever.read_paper(paper)
        
        # Verify metadata enhancement
        assert result["metadata"]["paper_id"] == paper.paper_id
        assert result["metadata"]["source"] == paper.source
        assert result["metadata"]["url"] == paper.url
        
        # Verify fallback metadata population
        if not result["metadata"].get("title"):
            assert result["metadata"]["title"] == paper.title
        if not result["metadata"].get("authors"):
            assert result["metadata"]["authors"] == paper.authors
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_search_and_read_harmonized_metadata(
            self, paper_retriever, rate_limit_delay):
        """Test harmonized metadata in search_and_read results."""
        retriever = paper_retriever
        
        results = await retriever.search_and_read(
            query="transformer architecture",
            max_papers=2
        )
        
        for result in results:
            if "error" not in result:
                # Check harmonized metadata structure
                meta = result["harmonized_metadata"]
                
                assert "paper_id" in meta
                assert "title" in meta
                assert "authors" in meta
                assert "source" in meta
                assert "urls" in meta
                assert "extraction_info" in meta
                assert "search_info" in meta
                
                # Verify search info
                assert meta["search_info"]["query"] == "transformer architecture"
                assert meta["search_info"]["relevance_rank"] > 0
                
                # Verify URLs structure
                assert "main" in meta["urls"]
                assert meta["urls"]["main"] is not None
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_empty_search_results(self, paper_retriever,
                                        rate_limit_delay):
        """Test handling of searches with no results."""
        retriever = paper_retriever
        
        # Very specific query unlikely to match
        results = await retriever.search_and_read(
            query="xyzabc123nonexistentpaper quantum blockchain AI",
            max_papers=5
        )
        
        assert isinstance(results, list)
        assert len(results) == 0
        
        await asyncio.sleep(rate_limit_delay)


@pytest.mark.unit  
class TestPaperRetrieverInit:
    """Test PaperRetriever initialization and configuration."""
    
    @pytest.mark.asyncio
    async def test_default_initialization(self):
        """Test default initialization."""
        retriever = PaperRetriever()
        
        assert PaperSource.ARXIV in retriever.sources
        assert retriever.deduplicator is not None
        assert retriever.paper_reader is not None
    
    @pytest.mark.asyncio
    async def test_custom_reader_config(self):
        """Test initialization with custom reader config."""
        from src.core.academic_tookit.paper_reader import PaperReaderConfig
        
        config = PaperReaderConfig(
            prefer_html=False,
            max_pdf_size_mb=5
        )
        
        retriever = PaperRetriever(reader_config=config)
        
        assert retriever.paper_reader.config.prefer_html is False
        assert retriever.paper_reader.config.max_pdf_size_mb == 5
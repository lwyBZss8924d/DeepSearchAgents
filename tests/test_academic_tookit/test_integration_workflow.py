#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_integration_workflow.py

"""
Integration tests for complete academic paper search and read workflows.
Tests the examples provided by the user.
"""

import pytest
import asyncio

from src.core.academic_tookit.paper_retrievaler import PaperRetriever
from src.core.academic_tookit.models import PaperSource


@pytest.mark.integration
@pytest.mark.slow
class TestAcademicWorkflows:
    """Test complete workflows from user examples."""
    
    @pytest.mark.asyncio
    async def test_search_ai_llm_agent_papers(self, paper_retriever,
                                              rate_limit_delay):
        """
        Integration test for Example 1 from user:
        'Search AI-LLM Agent papers about [ReAct] agent methodology 
        and the Top 20 papers on derived methods'
        """
        retriever = paper_retriever
        
        # Search for ReAct papers and derived methods
        results = await retriever.search_and_read(
            query=("AI LLM Agent papers ReAct agent methodology "
                   "derived methods"),
            max_papers=20,
            deduplicate=True
        )
        
        # Verify we got results
        assert len(results) > 0, "Should find papers about ReAct methodology"
        
        # Check for ReAct paper specifically (2210.03629)
        react_found = any(
            "2210.03629" in r.get("harmonized_metadata", {}).get(
                "paper_id", ""
            )
            for r in results if "error" not in r
        )
        
        # The ReAct paper should be in results for this specific query
        assert react_found, "ReAct paper (2210.03629) should be in results"
        
        # Verify content extraction for successful reads
        successful_reads = [r for r in results if "error" not in r]
        
        for result in successful_reads[:5]:  # Check first 5
            # Verify complete structure
            assert "full_text" in result
            assert "sections" in result
            assert "harmonized_metadata" in result
            
            # Verify metadata quality
            meta = result["harmonized_metadata"]
            assert meta["title"] is not None
            assert len(meta["authors"]) > 0
            assert meta["paper_id"] is not None
            assert meta["source"] == PaperSource.ARXIV
            
            # Verify content quality
            assert len(result["full_text"]) > 1000
            assert len(result["sections"]) > 0
            
            # Verify search context
            assert meta["search_info"]["query"] == (
                "AI LLM Agent papers ReAct agent methodology derived methods"
            )
            assert meta["search_info"]["relevance_rank"] <= 20
        
        # Log summary
        print(f"\nFound {len(results)} papers total")
        print(f"Successfully read {len(successful_reads)} papers")
        
        # Add delay for rate limiting
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    @pytest.mark.requires_mistral
    async def test_read_specific_paper(self, paper_retriever, rate_limit_delay,
                                       skip_if_no_api_key):
        """
        Integration test for Example 2 from user:
        '[ReAct: Synergizing Reasoning and Acting in Language Models]
        [`arXiv:2210.03629`]'
        """
        skip_if_no_api_key("mistral")
        
        retriever = paper_retriever
        
        # Get the ReAct paper by ID
        paper = await retriever.get_paper("2210.03629", PaperSource.ARXIV)
        
        assert paper is not None, "Should find ReAct paper by ID"
        assert paper.paper_id == "2210.03629"
        assert "ReAct" in paper.title
        assert "Synergizing Reasoning and Acting" in paper.title
        
        # Read the paper
        content = await retriever.read_paper(paper)
        
        # Verify content extraction
        assert content is not None
        assert "error" not in content
        
        # Verify metadata
        meta = content["harmonized_metadata"]
        assert meta["title"] == (
            "ReAct: Synergizing Reasoning and Acting in Language Models"
        )
        assert "Shunyu Yao" in str(meta["authors"])
        assert meta["paper_id"] == "2210.03629"
        
        # Verify content quality
        assert len(content["full_text"]) > 10000  # Substantial content
        assert len(content["sections"]) >= 5  # Multiple sections
        
        # Check for expected sections
        section_titles = [s.get("title", "").lower() 
                          for s in content["sections"]]
        
        # Should have sections about reasoning/acting
        assert any("introduction" in title for title in section_titles)
        assert any("reasoning" in title or "react" in title 
                   for title in section_titles)
        
        # Verify extraction info
        assert content["content_format"] in ["pdf", "html"]
        assert meta["extraction_info"]["sections_count"] == len(
            content["sections"]
        )
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_search_and_filter_by_year(self, paper_retriever,
                                             rate_limit_delay):
        """Test searching with year filtering."""
        retriever = paper_retriever
        
        from datetime import datetime, timedelta
        
        # Search for recent papers (last 2 years)
        start_date = datetime.now() - timedelta(days=730)
        
        results = await retriever.search_and_read(
            query="transformer models attention mechanisms",
            max_papers=5,
            start_date=start_date
        )
        
        # Verify date filtering
        for result in results:
            if "error" not in result:
                meta = result["harmonized_metadata"]
                # Check published date is recent
                if meta.get("published_date"):
                    # Parse ISO format date
                    pub_date = datetime.fromisoformat(
                        meta["published_date"].replace("Z", "+00:00")
                    )
                    assert pub_date >= start_date
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_find_and_read_related_papers(self, paper_retriever,
                                                rate_limit_delay):
        """Test finding related papers workflow."""
        retriever = paper_retriever
        
        # First get a reference paper
        papers = await retriever.search(
            query="attention is all you need",
            max_results=1
        )
        
        assert len(papers) > 0
        reference_paper = papers[0]
        
        # Find related papers
        related = await retriever.find_related_papers(
            reference_paper=reference_paper,
            max_results=5
        )
        
        assert len(related) > 0
        
        # Read the related papers
        content_dict = await retriever.read_papers_batch(
            related[:2],  # Just read first 2
            max_concurrent=2
        )
        
        # Verify we got content
        assert len(content_dict) == min(2, len(related))
        
        # Check content quality
        for paper_id, content in content_dict.items():
            if "error" not in content:
                assert "full_text" in content
                assert len(content["sections"]) > 0
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_category_specific_search(self, paper_retriever,
                                            rate_limit_delay):
        """Test searching within specific arXiv categories."""
        retriever = paper_retriever
        
        # Search only in AI and CL categories
        results = await retriever.search_and_read(
            query="neural networks",
            categories=["cs.AI", "cs.CL"],
            max_papers=3
        )
        
        # Verify category filtering
        for result in results:
            if "error" not in result:
                paper_categories = result["harmonized_metadata"]["categories"]
                assert any(cat in paper_categories 
                           for cat in ["cs.AI", "cs.CL"])
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_author_based_search(self, paper_retriever, rate_limit_delay):
        """Test searching for papers by specific authors."""
        retriever = paper_retriever
        
        # Search for papers by Yao (ReAct author)
        results = await retriever.search_and_read(
            query="author:Yao author:Zhao ReAct",
            max_papers=5
        )
        
        # Should find papers by these authors
        if len(results) > 0:
            # Check at least one paper has expected authors
            yao_found = any(
                any("Yao" in author 
                    for author in r["harmonized_metadata"]["authors"])
                for r in results if "error" not in r
            )
            assert yao_found, "Should find papers by author Yao"
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_comprehensive_search_workflow(self, paper_retriever,
                                                 rate_limit_delay):
        """Test a comprehensive search, filter, and read workflow."""
        retriever = paper_retriever
        
        # Step 1: Initial broad search
        papers = await retriever.search(
            query="language models reasoning",
            max_results=30,
            deduplicate=True
        )
        
        assert len(papers) > 10, "Should find many papers"
        
        # Step 2: Filter by relevance (papers with "reasoning" in title)
        relevant_papers = [
            p for p in papers 
            if "reasoning" in p.title.lower() or "react" in p.title.lower()
        ]
        
        assert len(relevant_papers) > 0, "Should find relevant papers"
        
        # Step 3: Read top relevant papers
        papers_to_read = relevant_papers[:3]
        content_dict = await retriever.read_papers_batch(papers_to_read)
        
        # Step 4: Verify complete workflow results
        successful_reads = [
            content for content in content_dict.values()
            if "error" not in content
        ]
        
        assert len(successful_reads) > 0, "Should successfully read some papers"
        
        # Verify quality of results
        for content in successful_reads:
            assert len(content["full_text"]) > 1000
            assert len(content["sections"]) > 0
            assert content["harmonized_metadata"]["title"] is not None
        
        await asyncio.sleep(rate_limit_delay)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, paper_retriever):
        """Test workflow handles errors gracefully."""
        retriever = paper_retriever
        
        # Search with a query that might have mixed results
        results = await retriever.search_and_read(
            query="quantum computing applications",
            max_papers=5
        )
        
        # Even if some papers fail to read, should handle gracefully
        assert isinstance(results, list)
        
        # Check error handling
        for result in results:
            if "error" in result:
                # Error results should still have basic info
                assert "paper_id" in result
                assert "title" in result
            else:
                # Successful results should have full content
                assert "full_text" in result
                assert "harmonized_metadata" in result
    
    @pytest.mark.asyncio
    @pytest.mark.requires_jina
    async def test_codeact_paper_html_version(self, paper_retriever,
                                              rate_limit_delay,
                                              skip_if_no_api_key):
        """
        Test reading the CodeAct paper which has both PDF and HTML versions.
        Paper: 'Executable Code Actions Elicit Better LLM Agents'
        arXiv: 2402.01030
        """
        skip_if_no_api_key("jina")  # HTML parsing needs Jina
        
        retriever = paper_retriever
        
        # Get the CodeAct paper specifically
        paper = await retriever.get_paper("2402.01030", PaperSource.ARXIV)
        
        assert paper is not None
        assert "Executable Code Actions" in paper.title
        assert "Xingyao Wang" in str(paper.authors)
        
        # Read the paper - should prefer HTML since it's available
        content = await retriever.read_paper(paper)
        
        assert content is not None
        assert "error" not in content
        
        # Log which format was used
        print(f"\nCodeAct paper format used: {content['content_format']}")
        print(f"Paper has HTML URL: {paper.html_url}")
        print(f"Paper has PDF URL: {paper.pdf_url}")
        
        # Verify content quality
        assert len(content["full_text"]) > 5000
        assert len(content["sections"]) > 3
        
        # Check for CodeAct-specific content
        full_text_lower = content["full_text"].lower()
        assert "codeact" in full_text_lower
        assert "python" in full_text_lower
        assert "llm agent" in full_text_lower
        
        # Verify metadata
        meta = content["harmonized_metadata"]
        assert meta["title"] == paper.title
        assert meta["paper_id"] == "2402.01030"
        assert "cs.CL" in meta["categories"]
        assert "cs.AI" in meta["categories"]
        
        await asyncio.sleep(rate_limit_delay)
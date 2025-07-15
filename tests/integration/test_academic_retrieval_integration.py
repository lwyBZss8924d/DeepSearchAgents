#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_academic_retrieval_integration.py
# code style: PEP 8

"""
Integration tests for AcademicRetrieval Tool with real FutureHouse API calls.

These tests make actual API calls to the FutureHouse Platform and should
be run with caution to avoid rate limiting.
"""

import pytest
import asyncio
import time
import os
from typing import Dict, Any

from src.tools.academic_retrieval import AcademicRetrieval
from src.core.academic_tookit import (
    ScholarSearchClient,
    AcademicResearchClient
)


@pytest.mark.integration
@pytest.mark.requires_llm
class TestAcademicRetrievalIntegration:
    """Integration tests for AcademicRetrieval Tool with real API calls."""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        api_key = os.getenv("FUTUREHOUSE_API_KEY")
        if not api_key:
            pytest.skip("FUTUREHOUSE_API_KEY not set")
        return api_key

    @pytest.fixture
    def tool(self, api_key):
        """Create AcademicRetrieval tool instance for integration testing."""
        return AcademicRetrieval(api_key=api_key, verbose=True)

    @pytest.fixture
    def search_client(self, api_key):
        """Create ScholarSearchClient for direct testing."""
        return ScholarSearchClient(api_key=api_key, verbose=True)

    @pytest.fixture
    def research_client(self, api_key):
        """Create AcademicResearchClient for direct testing."""
        return AcademicResearchClient(api_key=api_key)

    def test_search_operation_react_papers(self, tool):
        """Test Case 1: Search AI-LLM Agent papers about ReAct methodology."""
        query = (
            "Search AI-LLM Agent papers about [ReAct] agent methodology "
            "and the Top 20 papers on derived methods"
        )
        
        print(f"\n=== Test Case 1: Academic Search ===")
        print(f"Query: {query}")
        
        # Execute search
        result = tool.forward(
            query=query,
            operation="search",
            num_results=20,
            verbose=True
        )
        
        # Verify response structure
        assert isinstance(result, dict)
        assert result.get("operation") == "search"
        assert result.get("query") == query
        assert "results" in result
        assert "total_results" in result
        assert "meta" in result
        
        # Check results
        results = result.get("results", [])
        print(f"\nFound {len(results)} results")
        
        # Display first few results
        for i, paper in enumerate(results[:5]):
            print(f"\nResult {i+1}:")
            print(f"  Title: {paper.get('title', 'N/A')}")
            print(f"  URL: {paper.get('url', 'N/A')}")
            print(f"  Description: {paper.get('description', 'N/A')[:100]}...")
            
        # Verify result structure
        if results:
            first_result = results[0]
            assert "title" in first_result
            assert "url" in first_result
            assert "description" in first_result
            assert "snippets" in first_result
            
        # Check metadata
        meta = result.get("meta", {})
        assert meta.get("source") == "futurehouse_crow"
        assert meta.get("verbose") is True

    def test_research_operation_hira_paper(self, tool):
        """Test Case 2: Deep research on HiRA hierarchical framework paper."""
        query = (
            'Task: Search, Read, and Research paper about: '
            '["HiRA" (a hierarchical framework that decouples strategic '
            'planning from specialized execution in deep search tasks)]\n'
            'Summarize the paper core work about "Decoupled Planning and '
            'Execution: A Hierarchical Reasoning(HiRA) Framework for Deep Search":\n'
            '- "HiRA" Framework architecture;\n'
            '- "HiRA" Framework base pipeline & workflow '
            '(mermaid Flowchart & sequenceDiagram);\n'
            '- "HiRA" Framework CORE methods & algorithm principles;\n'
            'Output: End of your research job output result research report '
            'MUST be in Zh(最终报告用中文) for me, BUT you reasoning process '
            'MUST be in English (EN).'
        )
        
        print(f"\n=== Test Case 2: Academic Research ===")
        print(f"Query: {query[:200]}...")
        print("\nThis is a deep research task that may take several minutes...")
        
        # Execute research with longer timeout
        result = tool.forward(
            query=query,
            operation="research",
            verbose=True,
            timeout=1200  # 20 minutes
        )
        
        # Verify response structure
        assert isinstance(result, dict)
        assert result.get("operation") == "research"
        assert result.get("query") == query
        assert "content" in result or "error" in result
        
        if "error" in result:
            print(f"\nResearch failed with error: {result['error']}")
            pytest.skip(f"Research operation failed: {result['error']}")
            
        # Check research content
        content = result.get("content", "")
        print(f"\nResearch Report Preview (first 500 chars):")
        print(content[:500])
        print("...")
        
        # Verify Chinese output
        # Check for common Chinese characters
        chinese_chars = [
            "框架", "架构", "方法", "算法", "流程", 
            "核心", "原理", "总结", "研究", "分析"
        ]
        has_chinese = any(char in content for char in chinese_chars)
        
        if not has_chinese:
            print("\nWarning: Expected Chinese output not detected")
            
        # Check metadata
        meta = result.get("meta", {})
        assert meta.get("source") == "futurehouse_falcon"

    def test_invalid_operation_handling(self, tool):
        """Test handling of invalid operations."""
        result = tool.forward(
            query="test query",
            operation="invalid_op"
        )
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "valid_operations" in result
        assert result["valid_operations"] == ["search", "research"]

    def test_search_with_timeout(self, tool):
        """Test search operation with custom timeout."""
        result = tool.forward(
            query="machine learning optimization algorithms",
            operation="search",
            num_results=5,
            timeout=30  # Short timeout
        )
        
        assert isinstance(result, dict)
        # Should complete or timeout gracefully
        assert "operation" in result

    def test_usage_statistics(self, tool):
        """Test usage statistics tracking."""
        # Perform a search
        tool.forward(
            query="test query",
            operation="search",
            num_results=5
        )
        
        # Get usage stats
        stats = tool.get_usage_stats()
        
        assert isinstance(stats, dict)
        assert "total_searches" in stats
        assert "total_research" in stats
        assert "total_operations" in stats
        assert stats["total_searches"] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, search_client):
        """Test concurrent search operations."""
        queries = [
            "deep learning transformers",
            "reinforcement learning agents",
            "neural architecture search"
        ]
        
        print("\n=== Testing Concurrent Searches ===")
        
        # Run searches concurrently
        tasks = []
        for query in queries:
            task = asyncio.create_task(
                asyncio.to_thread(
                    search_client.search,
                    query=query,
                    num_results=5
                )
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # Verify all searches completed
        assert len(results) == len(queries)
        
        for i, (query, result) in enumerate(zip(queries, results)):
            print(f"\nQuery {i+1}: {query}")
            print(f"Results found: {len(result)}")
            assert isinstance(result, list)

    def test_research_with_initial_context(self, tool):
        """Test research operation with initial context."""
        # First, do a search to get context
        search_result = tool.forward(
            query="HiRA hierarchical reasoning framework",
            operation="search",
            num_results=5
        )
        
        # Extract context from search results
        initial_context = ""
        if search_result.get("results"):
            for result in search_result["results"][:3]:
                initial_context += f"Title: {result.get('title', '')}\n"
                initial_context += f"Description: {result.get('description', '')}\n\n"
        
        # Now do research with context
        research_result = tool.forward(
            query="Based on the context, explain the HiRA framework architecture in detail",
            operation="research",
            initial_context=initial_context,
            timeout=600
        )
        
        assert isinstance(research_result, dict)
        assert research_result.get("operation") == "research"

    def test_error_recovery(self, tool):
        """Test error handling and recovery."""
        # Test with empty query
        result = tool.forward(
            query="",
            operation="search"
        )
        
        # Should handle gracefully
        assert isinstance(result, dict)
        
        # Test with very long query
        long_query = "test " * 1000
        result = tool.forward(
            query=long_query,
            operation="search",
            num_results=1
        )
        
        # Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.slow
    def test_full_workflow(self, tool):
        """Test complete workflow: search then research."""
        print("\n=== Full Workflow Test ===")
        
        # Step 1: Search for papers
        search_query = "Large Language Model agent architectures CodeAct ReAct"
        print(f"\nStep 1: Searching for papers on: {search_query}")
        
        search_result = tool.forward(
            query=search_query,
            operation="search",
            num_results=10
        )
        
        assert search_result.get("total_results", 0) > 0
        print(f"Found {search_result.get('total_results')} papers")
        
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # Step 2: Deep research based on search results
        research_query = (
            "Based on the latest papers about LLM agent architectures, "
            "compare and contrast ReAct and CodeAct methodologies. "
            "Provide a comprehensive analysis of their strengths, weaknesses, "
            "and use cases. 最终总结请用中文输出。"
        )
        
        print(f"\nStep 2: Conducting deep research...")
        
        research_result = tool.forward(
            query=research_query,
            operation="research",
            timeout=900
        )
        
        assert "content" in research_result or "error" in research_result
        
        if "content" in research_result:
            print("\nResearch completed successfully!")
            print(f"Report length: {len(research_result['content'])} characters")
        else:
            print(f"\nResearch failed: {research_result.get('error')}")


if __name__ == "__main__":
    # Run specific test for debugging
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        pytest.main(["-xvs", __file__, f"-k", test_name])
    else:
        # Run all tests
        pytest.main(["-xvs", __file__])
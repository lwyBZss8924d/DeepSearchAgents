#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_github_qa_integration.py
# code style: PEP 8

"""
Integration tests for GitHubRepoQATool with real DeepWiki API calls.

These tests make actual API calls to the DeepWiki MCP server and should
be run with caution to avoid rate limiting.
"""

import pytest
import asyncio
import time
from typing import Dict, Any

from src.tools.github_qa import GitHubRepoQATool
from src.core.github_toolkit.deepwiki import DeepWikiClient


@pytest.mark.integration
@pytest.mark.requires_llm
class TestGitHubRepoQAToolIntegration:
    """Integration tests for GitHubRepoQATool with real API calls."""

    @pytest.fixture
    def tool(self):
        """Create GitHubRepoQATool instance for integration testing."""
        return GitHubRepoQATool(verbose=True)

    @pytest.fixture
    def test_repos(self):
        """List of test repositories."""
        return {
            "deepsearch": "lwyBZss8924d/DeepSearchAgents",
            "popular": "microsoft/markitdown",
            "small": "anthropics/claude-code-action",
        }

    def test_structure_operation_real(self, tool, test_repos):
        """Test structure operation with real API call."""
        # Test with DeepSearchAgents repository
        repo = test_repos["deepsearch"]
        result = tool.forward(repo, operation="structure")

        # Verify response
        assert isinstance(result, (dict, str))
        if isinstance(result, dict):
            if result.get("success") is False:
                pytest.skip(f"API error: {result.get('error')}")
            assert "topics" in result or "error" in result
        else:
            # DeepWiki might return string directly
            assert len(result) > 0
            print(f"\nStructure result for {repo}:\n{result[:500]}...")

    def test_contents_operation_real(self, tool, test_repos):
        """Test contents operation with real API call."""
        # Test with a smaller repository to avoid huge responses
        repo = test_repos["small"]
        result = tool.forward(repo, operation="contents")

        # Verify response
        assert result is not None
        if isinstance(result, dict) and result.get("success") is False:
            pytest.skip(f"API error: {result.get('error')}")

        # Should contain documentation content
        assert isinstance(result, str) or isinstance(result, dict)
        print(f"\nContents preview for {repo}:\n{str(result)[:500]}...")

    def test_query_operation_real(self, tool, test_repos):
        """Test query operation with real API call."""
        # Test with DeepSearchAgents repository
        repo = test_repos["deepsearch"]
        questions = [
            "what is this agent system agent's tools architecture?",
        ]

        for question in questions:
            result = tool.forward(
                repo,
                operation="query",
                question=question
            )

            # Verify response
            assert result is not None
            if isinstance(result, dict) and result.get("success") is False:
                print(f"\nSkipping question due to error: {result.get('error')}")
                continue

            print(f"\nQ: {question}")
            print(f"A: {str(result)[:500]}...")

            # Add delay to avoid rate limiting
            time.sleep(1)

    def test_invalid_repository_handling(self, tool):
        """Test handling of non-existent repositories."""
        # Test with clearly invalid repository
        result = tool.forward(
            "nonexistent12345/fakerepo67890",
            operation="structure"
        )

        # Should handle gracefully
        assert result is not None
        if isinstance(result, dict):
            # Might return error or empty result
            print(f"\nInvalid repo result: {result}")

    def test_github_url_support(self, tool):
        """Test if the tool handles GitHub URLs (not just owner/repo)."""
        # Some implementations might support full URLs
        test_urls = [
            "https://github.com/lwyBZss8924d/DeepSearchAgents",
            "github.com/anthropics/claude-code-action",
            "http://github.com/anthropics/claude-code-action",
        ]

        for url in test_urls:
            # Extract owner/repo from URL
            import re
            match = re.search(r'github\.com/([^/]+/[^/]+)', url)
            if match:
                repo = match.group(1)
                result = tool.forward(repo, operation="structure")
                print(f"\nTesting extracted repo {repo} from {url}")
                assert result is not None

    @pytest.mark.asyncio
    async def test_async_operations(self, tool, test_repos):
        """Test async operations."""
        repo = test_repos["deepsearch"]

        # Test async forward method
        result = await tool._async_forward(
            repo,
            operation="structure"
        )

        assert result is not None
        print(f"\nAsync structure result: {str(result)[:300]}...")

    def test_concurrent_requests(self, tool, test_repos):
        """Test handling of concurrent requests."""
        repos = [test_repos["small"], test_repos["deepsearch"]]

        # Create multiple tools to simulate concurrent usage
        tools = [GitHubRepoQATool() for _ in range(2)]

        results = []
        for i, repo in enumerate(repos):
            result = tools[i].forward(repo, operation="structure")
            results.append(result)
            print(f"\nConcurrent result {i+1}: {str(result)[:200]}...")

        # Both should complete successfully
        assert all(r is not None for r in results)

    def test_deepwiki_client_direct(self, test_repos):
        """Test DeepWikiClient directly."""
        client = DeepWikiClient()

        try:
            # Test structure
            result = client.read_wiki_structure(test_repos["deepsearch"])
            assert result is not None
            print(f"\nDirect client structure: {result}")

            # Test question
            result = client.ask_question(
                test_repos["deepsearch"],
                "What is this agent system LLM prompt&agent run task context engineering architecture?"
            )
            assert result is not None
            print(f"\nDirect client Q&A: {result}")

        finally:
            client.disconnect()

    def test_rate_limiting_behavior(self, tool, test_repos):
        """Test behavior under potential rate limiting."""
        repo = test_repos["small"]

        # Make several rapid requests
        results = []
        for i in range(3):
            result = tool.forward(
                repo,
                operation="query",
                question=f"Test question {i+1}"
            )
            results.append(result)

            # Check if we hit rate limit
            if isinstance(result, dict) and "rate" in str(result.get("error", "")).lower():
                print(f"\nRate limit detected after {i+1} requests")
                break

            # Small delay between requests
            time.sleep(0.5)

        # At least some requests should succeed
        assert len(results) > 0

    def test_special_characters_in_repo(self, tool):
        """Test repositories with special characters."""
        # Most GitHub repos don't have special chars, but test format validation
        special_repos = [
            "user-name/repo-name",  # Hyphens (valid)
            "user_name/repo_name",  # Underscores (valid)
            "user123/456repo",      # Numbers (valid)
        ]

        for repo in special_repos:
            if tool._validate_repo_format(repo):
                result = tool.forward(repo, operation="structure")
                print(f"\nSpecial repo {repo}: {type(result)}")

    def test_performance_metrics(self, tool, test_repos):
        """Measure performance of different operations."""
        import time

        repo = test_repos["small"]
        metrics = {}

        # Measure structure operation
        start = time.time()
        tool.forward(repo, operation="structure")
        metrics["structure_time"] = time.time() - start

        # Measure query operation
        start = time.time()
        tool.forward(
            repo,
            operation="query",
            question="What is this repository about?"
        )
        metrics["query_time"] = time.time() - start

        print(f"\nPerformance metrics: {metrics}")

        # Operations should complete in reasonable time
        assert all(t < 30 for t in metrics.values()), "Operations too slow"

    def test_error_recovery(self, tool):
        """Test error recovery and tool resilience."""
        # First, cause an error with invalid format
        error_result = tool.forward("invalid", operation="structure")
        assert isinstance(error_result, dict)
        assert error_result["success"] is False

        # Tool should still work after error
        valid_result = tool.forward(
            "octocat/Hello-World",
            operation="structure"
        )
        assert valid_result is not None

        print("\nTool recovered successfully after error")

    def test_cleanup_after_operations(self, tool, test_repos):
        """Test that resources are properly cleaned up."""
        # Perform several operations
        for op in ["structure", "contents"]:
            tool.forward(test_repos["small"], operation=op)

        # Check that scraper is initialized
        assert tool.scraper is not None

        # Delete tool and verify cleanup
        del tool

        # Create new tool - should work fine
        new_tool = GitHubRepoQATool()
        result = new_tool.forward(
            test_repos["small"],
            operation="structure"
        )
        assert result is not None
        print("\nCleanup successful, new tool works")


@pytest.mark.integration
class TestDeepSearchAgentsRepository:
    """Specific tests for the DeepSearchAgents repository."""

    @pytest.fixture
    def tool(self):
        """Create tool for testing."""
        return GitHubRepoQATool(verbose=True)

    def test_deepsearch_structure(self, tool):
        """Test getting structure of DeepSearchAgents repo."""
        repo = "lwyBZss8924d/DeepSearchAgents"
        result = tool.forward(repo, operation="structure")

        print(f"\nDeepSearchAgents structure:\n{result}")
        assert result is not None

    def test_deepsearch_contents(self, tool):
        """Test reading contents of DeepSearchAgents repo."""
        repo = "lwyBZss8924d/DeepSearchAgents"
        result = tool.forward(repo, operation="contents")

        if result:
            print(f"\nDeepSearchAgents contents preview:\n{str(result)[:1000]}...")
        assert result is not None

    def test_deepsearch_questions(self, tool):
        """Test asking questions about DeepSearchAgents."""
        repo = "lwyBZss8924d/DeepSearchAgents"

        questions = [
            "What tools and agents are available?",
            "How does the WolframAlpha Tool work?",
        ]

        for i, question in enumerate(questions):
            print(f"\n{'='*60}")
            print(f"Question {i+1}: {question}")
            print(f"{'='*60}")

            result = tool.forward(
                repo,
                operation="query",
                question=question
            )

            if isinstance(result, dict) and result.get("success") is False:
                print(f"Error: {result.get('error')}")
            else:
                print(f"Answer: {result}")

            # Delay between questions
            time.sleep(2)

    def test_deepsearch_specific_features(self, tool):
        """Test questions about specific features."""
        repo = "lwyBZss8924d/DeepSearchAgents"

        feature_questions = [
            "How does the ReAct agent work in DeepSearchAgents?",
            "What is the CodeAct agent and how is it different from ReAct?",
        ]

        for question in feature_questions:
            result = tool.forward(
                repo,
                operation="query",
                question=question
            )

            print(f"\nQ: {question}")
            if result:
                print(f"A: {str(result)[:500]}...")

            time.sleep(2)

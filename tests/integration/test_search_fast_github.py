#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_search_fast_github.py
# code style: PEP 8

"""
Integration tests for SearchLinksFastTool with GitHub domain filtering.

These tests perform real API calls to verify domain filtering functionality.
"""

import os
import json
import pytest
from typing import Dict
from src.tools.search_fast import SearchLinksFastTool


class TestSearchLinksFastGitHub:
    """Test SearchLinksFastTool with GitHub domain filtering."""

    @pytest.fixture(scope="class")
    def api_keys(self) -> Dict[str, str]:
        """Get API keys from environment."""
        api_keys = {}

        # Try to get API keys from environment
        for key_name, env_var in [
            ("serper", "SERPER_API_KEY"),
            ("xai", "XAI_API_KEY"),
            ("jina", "JINA_API_KEY"),
            ("exa", "EXA_API_KEY")
        ]:
            api_key = os.getenv(env_var)
            if api_key:
                api_keys[key_name] = api_key

        return api_keys

    @pytest.fixture
    def search_tool(self, api_keys) -> SearchLinksFastTool:
        """Create SearchLinksFastTool instance."""
        if not api_keys:
            pytest.skip("No API keys available for testing")

        return SearchLinksFastTool(api_keys=api_keys)

    def test_github_domain_filter_specific_query(self, search_tool):
        """
        Test SearchLinksFastTool with GitHub domain filtering using the
        specific query provided.

        Test parameters:
        - domains: ["github.com"]
        - query: "litellm /tags releases/ compare/ Full Changelog"

        Note: Due to how search providers handle domain filtering, some
        results may not be perfectly filtered. We'll track and report
        the effectiveness of the filter.
        """
        # Perform search with GitHub domain filter
        results = search_tool.forward(
            query="litellm /tags releases/ compare/ Full Changelog",
            num_results=20,
            domains=["github.com"],
            output_format="list"
        )

        # Verify we got results
        assert isinstance(results, list), "Results should be a list"
        assert len(results) > 0, "Should have at least one result"

        # Track GitHub vs non-GitHub results
        github_results = []
        other_results = []

        # Analyze all results
        for result in results:
            assert isinstance(result, dict), "Each result should be a dict"
            assert "url" in result, "Result should have 'url' field"
            assert "title" in result, "Result should have 'title' field"
            assert "content" in result, "Result should have 'content' field"
            assert "provider" in result, "Result should have 'provider' field"

            # Check if URL is from github.com
            url = result["url"]
            if "github.com" in url:
                github_results.append(result)
            else:
                other_results.append(result)

        # Print analysis
        print(f"\n=== Domain Filter Analysis ===")
        print(f"Total results: {len(results)}")
        print(f"GitHub results: {len(github_results)} ({len(github_results)/len(results)*100:.1f}%)")
        print(f"Other domains: {len(other_results)} ({len(other_results)/len(results)*100:.1f}%)")

        if github_results:
            print("\nGitHub Results:")
            for i, result in enumerate(github_results[:5]):
                print(f"{i+1}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Provider: {result['provider']}")

        if other_results:
            print("\nNon-GitHub Results (should be filtered):")
            for i, result in enumerate(other_results[:3]):
                print(f"{i+1}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Provider: {result['provider']}")

        # Verify we have at least some GitHub results
        assert len(github_results) > 0, \
            "Should have at least one GitHub result when filtering by github.com"

        # Check effectiveness of domain filter
        github_percentage = len(github_results) / len(results) * 100
        print(f"\nDomain filter effectiveness: {github_percentage:.1f}% GitHub results")

        # The filter should improve GitHub result ratio significantly
        # We expect at least 50% to be from GitHub when filtering
        assert github_percentage >= 50, \
            f"Domain filter should result in at least 50% GitHub results, got {github_percentage:.1f}%"

    def test_github_domain_filter_json_output(self, search_tool):
        """Test GitHub domain filtering with JSON output format."""
        # Perform search with JSON output
        results_json = search_tool.forward(
            query="pytorch documentation tutorials",
            num_results=10,
            domains=["github.com"],
            output_format="json"
        )

        # Verify JSON format
        assert isinstance(results_json, str), "JSON output should be string"

        # Parse JSON
        results = json.loads(results_json)
        assert isinstance(results, list), "Parsed JSON should be a list"

        # Verify all URLs are from github.com
        for result in results:
            url = result.get("url", "")
            assert "github.com" in url, f"URL should contain github.com: {url}"

    def test_github_domain_filter_text_output(self, search_tool):
        """Test GitHub domain filtering with text output format."""
        # Perform search with text output
        results_text = search_tool.forward(
            query="tensorflow models examples",
            num_results=5,
            domains=["github.com"],
            output_format="text"
        )

        # Verify text format
        assert isinstance(results_text, str), "Text output should be string"
        assert "github.com" in results_text, \
            "Text output should contain github.com URLs"
        assert "Search results for" in results_text, \
            "Text output should have header"

    def test_multiple_github_subdomains(self, search_tool):
        """Test searching across multiple GitHub subdomains."""
        # Search with multiple GitHub-related domains
        results = search_tool.forward(
            query="API documentation",
            num_results=15,
            domains=["github.com", "docs.github.com", "gist.github.com"],
            output_format="list"
        )

        # Verify results
        assert len(results) > 0, "Should have results"

        # Check all URLs are from specified domains
        allowed_domains = ["github.com", "docs.github.com", "gist.github.com"]
        for result in results:
            url = result["url"]
            assert any(domain in url for domain in allowed_domains), \
                f"URL should be from allowed domains: {url}"

    def test_comparison_with_without_domain_filter(self, search_tool):
        """Compare results with and without domain filtering."""
        query = "machine learning repository"

        # Search without domain filter
        results_all = search_tool.forward(
            query=query,
            num_results=20,
            output_format="list"
        )

        # Search with GitHub domain filter
        results_github = search_tool.forward(
            query=query,
            num_results=20,
            domains=["github.com"],
            output_format="list"
        )

        # Analyze results
        all_domains = {}
        github_count_unfiltered = 0
        github_count_filtered = 0

        # Count domains in unfiltered results
        for result in results_all:
            url = result["url"]
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            all_domains[domain] = all_domains.get(domain, 0) + 1
            if "github.com" in url:
                github_count_unfiltered += 1

        # Count GitHub results in filtered search
        non_github_domains = set()
        for result in results_github:
            url = result["url"]
            if "github.com" in url:
                github_count_filtered += 1
            else:
                domain = urlparse(url).netloc
                non_github_domains.add(domain)

        # Calculate percentages
        github_pct_unfiltered = (github_count_unfiltered / len(results_all) * 100 
                                 if results_all else 0)
        github_pct_filtered = (github_count_filtered / len(results_github) * 100 
                               if results_github else 0)

        # Print analysis
        print(f"\n=== Domain Filter Comparison ===")
        print(f"Query: {query}")
        print(f"\nUnfiltered search ({len(results_all)} results):")
        print(f"  GitHub results: {github_count_unfiltered} ({github_pct_unfiltered:.1f}%)")
        print(f"  Unique domains: {len(all_domains)}")
        print(f"  Top domains:")
        for domain, count in sorted(all_domains.items(), 
                                    key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {domain}: {count}")

        print(f"\nFiltered search ({len(results_github)} results):")
        print(f"  GitHub results: {github_count_filtered} ({github_pct_filtered:.1f}%)")
        print(f"  Non-GitHub domains found: {len(non_github_domains)}")
        if non_github_domains:
            print(f"  Non-GitHub domains: {non_github_domains}")

        # Verify filtering improved GitHub percentage
        print("\nFiltering effectiveness:")
        print(f"  GitHub % increased from {github_pct_unfiltered:.1f}% to {github_pct_filtered:.1f}%")

        # Assert that filtering improved GitHub result ratio
        assert github_pct_filtered > github_pct_unfiltered, \
            f"Domain filter should increase GitHub percentage, but got {github_pct_unfiltered:.1f}% -> {github_pct_filtered:.1f}%"

        # Assert we got at least some GitHub results
        assert github_count_filtered > 0, \
            "Should have at least one GitHub result when filtering"

    def test_empty_results_with_restrictive_filter(self, search_tool):
        """Test behavior when domain filter returns no results."""
        # Search for something unlikely to be on GitHub
        results = search_tool.forward(
            query="local restaurant reviews near me",
            num_results=10,
            domains=["github.com"],
            output_format="list"
        )

        # May or may not have results, but if we do, they must be from GitHub
        if len(results) > 0:
            for result in results:
                assert "github.com" in result["url"], \
                    "Any results must be from github.com"
        else:
            # Empty results are acceptable for this query
            assert results == [], "Should return empty list if no results"

    def test_github_specific_search_patterns(self, search_tool):
        """Test various GitHub-specific search patterns."""
        test_queries = [
            "site:github.com python machine learning",
            "github stars:>1000 language:python",
            "awesome-python curated list",
            "tensorflow models zoo"
        ]

        for query in test_queries:
            results = search_tool.forward(
                query=query,
                num_results=5,
                domains=["github.com"],
                output_format="list"
            )

            # Verify GitHub results
            if results:
                for result in results:
                    assert "github.com" in result["url"], \
                        f"Result should be from github.com for query: {query}"

            print(f"\nQuery: {query}")
            print(f"Results found: {len(results)}")


if __name__ == "__main__":
    # Run specific test if executed directly
    pytest.main([__file__, "-v", "-s"])

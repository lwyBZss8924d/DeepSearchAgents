#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/search_helpers.py
# code style: PEP 8

"""
Helper tools and methods for specialized search patterns in DeepSearchAgents.
"""

import json
from typing import Dict, Optional, List, Any
from smolagents import Tool, tool
from src.tools.search_fast import SearchLinksFastTool
from src.tools.search import SearchLinksTool


class MultiQuerySearchTool(Tool):
    """
    Performs multiple searches in parallel and returns combined results.
    Useful for comprehensive research on related topics.

    Example:
        results = multi_query_search([
            "machine learning basics",
            "deep learning tutorial",
            "neural network examples"
        ])
    """
    name = "multi_query_search"
    description = (
        "Performs multiple web searches in parallel and returns combined "
        "results. Useful for researching multiple related topics at once. "
        "Each query is searched independently and results are grouped by "
        "query."
    )
    inputs: Dict[str, Any] = {
        "queries": {
            "type": "array",
            "description": "List of search queries to execute.",
        },
        "results_per_query": {
            "type": "integer",
            "description": "Number of results per query (default: 5).",
            "default": 5,
            "nullable": True,
        },
        "deduplicate": {
            "type": "boolean",
            "description": "Remove duplicate URLs across queries.",
            "default": True,
            "nullable": True,
        }
    }
    output_type = "any"

    def __init__(self):
        super().__init__()
        self.search_tool = SearchLinksFastTool()

    def forward(
        self,
        queries: List[str],
        results_per_query: Optional[int] = 5,
        deduplicate: Optional[bool] = True
    ) -> Dict[str, Any]:
        """
        Perform multiple searches and combine results.

        Args:
            queries: List of search queries
            results_per_query: Results per query
            deduplicate: Remove duplicate URLs

        Returns:
            Dict with results grouped by query
        """
        results_per_query = results_per_query or 5
        deduplicate = deduplicate if deduplicate is not None else True

        all_results = {}
        seen_urls = set()

        for query in queries:
            if not query.strip():
                continue

            # Search for this query
            search_results = self.search_tool.forward(
                query=query,
                num_results=results_per_query,
                output_format="list"
            )

            # Handle case where results might be JSON string
            if isinstance(search_results, str):
                try:
                    results = json.loads(search_results)
                except json.JSONDecodeError:
                    results = []
            else:
                results = search_results

            # Filter duplicates if requested
            if deduplicate:
                filtered_results = []
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        filtered_results.append(result)
                results = filtered_results

            all_results[query] = results

        return {
            "queries": list(all_results.keys()),
            "results_by_query": all_results,
            "total_results": sum(len(r) for r in all_results.values()),
            "unique_urls": len(seen_urls) if deduplicate else None
        }


class DomainSearchTool(Tool):
    """
    Searches within specific domains or websites.
    Perfect for finding information from trusted sources.

    Example:
        # Search only on GitHub
        results = domain_search("python async examples",
                              domains=["github.com"])

        # Search academic sites
        results = domain_search("machine learning research",
                              domains=["arxiv.org", "scholar.google.com"])
    """
    name = "domain_search"
    description = (
        "Searches within specific domains or websites. "
        "Useful for finding information from trusted or specific sources. "
        "Can search within multiple domains or exclude certain domains."
    )
    inputs: Dict[str, Any] = {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "domains": {
            "type": "array",
            "description": "List of domains to search within.",
            "default": None,
            "nullable": True,
        },
        "exclude_domains": {
            "type": "array",
            "description": "List of domains to exclude.",
            "default": None,
            "nullable": True,
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return.",
            "default": 10,
            "nullable": True,
        }
    }
    output_type = "any"

    def __init__(self):
        super().__init__()
        self.search_tool = SearchLinksFastTool()

    def forward(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        num_results: Optional[int] = 10
    ) -> List[Dict[str, str]]:
        """
        Search within specific domains.

        Args:
            query: Search query
            domains: Domains to search within
            exclude_domains: Domains to exclude
            num_results: Number of results

        Returns:
            List of search results from specified domains
        """
        search_results = self.search_tool.forward(
            query=query,
            num_results=num_results or 10,
            domains=domains,
            exclude_domains=exclude_domains,
            output_format="list"
        )

        # Handle case where results might be JSON string
        if isinstance(search_results, str):
            try:
                return json.loads(search_results)
            except json.JSONDecodeError:
                return []

        return search_results if isinstance(search_results, list) else []


# Create convenient function-based tools using @tool decorator
@tool
def search_code(
    query: str, language: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Search for code examples and programming solutions.

    This tool searches GitHub, StackOverflow, and other code repositories
    for programming examples and solutions.

    Args:
        query: What code or programming concept to search for
        language: Optional programming language filter (e.g., 'python',
                 'javascript')

    Returns:
        List of code-related search results with title, url, and content
    """
    # Add language to query if specified
    if language:
        query = f"{language} {query}"

    # Search code-focused domains
    tool = DomainSearchTool()
    code_domains = ["github.com", "stackoverflow.com", "gist.github.com"]
    return tool.forward(
        query=query,
        domains=code_domains,
        num_results=10
    )


@tool
def search_docs(
    query: str,
    project: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Search for documentation and technical references.

    This tool searches official documentation sites and technical references
    for APIs, libraries, and frameworks.

    Args:
        query: What documentation to search for
        project: Optional project name to focus on (e.g., 'pytorch', 'react')

    Returns:
        List of documentation search results
    """
    # Add project name to query if specified
    if project:
        query = f"{project} {query}"

    # Common documentation domains
    doc_domains = [
        "docs.python.org",
        "pytorch.org",
        "tensorflow.org",
        "reactjs.org",
        "developer.mozilla.org",
        "docs.microsoft.com",
        "docs.aws.amazon.com"
    ]

    tool = DomainSearchTool()
    return tool.forward(
        query=query,
        domains=doc_domains,
        num_results=10
    )


@tool
def search_recent(query: str, days: int = 7) -> str:
    """
    Search for recent information from the last N days.

    This tool searches for the most recent information on a topic,
    useful for news, updates, and current events.

    Args:
        query: What to search for
        days: How many days back to search (default: 7)

    Returns:
        Text summary of recent search results
    """
    from datetime import datetime, timedelta

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Use the full search tool for date filtering
    search_tool = SearchLinksTool()
    results_data = search_tool.forward(
        query=query,
        from_date=start_date.strftime("%Y-%m-%d"),
        to_date=end_date.strftime("%Y-%m-%d"),
        source="hybrid",
        num_results=10
    )

    # Parse results
    try:
        if isinstance(results_data, str):
            results = json.loads(results_data)
        else:
            results = results_data
    except json.JSONDecodeError:
        no_results_msg = (
            f"No recent results found for '{query}' "
            f"in the last {days} days."
        )
        return no_results_msg

    if not results:
        no_results_msg = (
            f"No recent results found for '{query}' "
            f"in the last {days} days."
        )
        return no_results_msg

    # Create summary
    summary = f"Recent results for '{query}' (last {days} days):\n\n"

    # Ensure results is a list
    if not isinstance(results, list):
        results = []

    for i, result in enumerate(results[:5], 1):
        if not isinstance(result, dict):
            continue
        summary += f"{i}. {result.get('title', 'Unknown')}\n"
        snippet = result.get('snippet', '')[:200]
        summary += f"   {snippet}...\n\n"

    return summary.strip()


# Export all tools
__all__ = [
    'MultiQuerySearchTool',
    'DomainSearchTool',
    'search_code',
    'search_docs',
    'search_recent'
]

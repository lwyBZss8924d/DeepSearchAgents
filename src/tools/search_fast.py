#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/search_fast.py
# code style: PEP 8

"""
Fast Web Search Tool for DeepSearchAgents.
"""

import os
import json
from typing import Dict, Optional, List, Any, Union
from smolagents import Tool
from src.core.search_engines.search_hybrid import HybridSearchEngine


class SearchLinksFastTool(Tool):
    """
    A fast web search tool optimized for quickly obtaining search result URLs.
    Returns structured search results from multiple providers.

    This tool automatically selects the best search provider based on
    your query and returns the most relevant results in a clean format.

    Example usage:
        # Fast web search
        results = search_fast("latest AI developments")

        # Search with more results
        results = search_fast("machine learning tutorials", num_results=20)

        # Search specific domains
        results = search_fast("pytorch documentation", domains=["pytorch.org"])
    """
    name = "search_fast"
    description = (
        "Fast web search tool that quickly returns URLs and titles from search results. "
        "Optimized for speed with minimal parameters. Input a query string to search "
        "across multiple providers. Returns results with title, url, and content snippet. "
        "Perfect for when you need search results quickly without complex filtering."
    )
    inputs: Dict[str, Any] = {
        "query": {
            "type": "string",
            "description": "The search query string.",
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (default: 10, max: 50).",
            "default": 10,
            "nullable": True,
        },
        "domains": {
            "type": "array",
            "description": (
                "Optional list of domains to search within "
                "(e.g., ['github.com', 'stackoverflow.com'])."
            ),
            "default": None,
            "nullable": True,
        },
        "exclude_domains": {
            "type": "array",
            "description": "Optional list of domains to exclude from results.",
            "default": None,
            "nullable": True,
        },
        "output_format": {
            "type": "string",
            "description": (
                "Output format: 'list' for list of dicts, "
                "'json' for JSON string, 'text' for plain text summary."
            ),
            "default": "list",
            "nullable": True,
        }
    }
    output_type = "any"  # Can return list, string, or dict

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize SearchLinksFastTool.

        Args:
            api_keys: Optional dict of API keys. If not provided,
                     will load from environment variables.
        """
        super().__init__()

        # Load API keys from environment if not provided
        if not api_keys:
            api_keys = {}
            # Load available API keys from environment
            for key_name, env_var in [
                ("serper", "SERPER_API_KEY"),
                ("xai", "XAI_API_KEY"),
                ("jina", "JINA_API_KEY"),
                ("exa", "EXA_API_KEY")
            ]:
                api_key = os.getenv(env_var)
                if api_key:
                    api_keys[key_name] = api_key

        if not api_keys:
            raise ValueError(
                "No API keys provided. At least one search provider API key "
                "is required (SERPER_API_KEY, XAI_API_KEY, JINA_API_KEY, "
                "or EXA_API_KEY)."
            )

        self.search_engine = HybridSearchEngine(api_keys=api_keys)

    def forward(
        self,
        query: str,
        num_results: Optional[int] = 10,
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        output_format: Optional[str] = "list"
    ) -> Union[List[Dict[str, str]], str]:
        """
        Perform a simplified web search.

        Args:
            query: The search query string
            num_results: Number of results to return (max 50)
            domains: Optional list of domains to search within
            exclude_domains: Optional list of domains to exclude
            output_format: Output format ('list', 'json', or 'text')

        Returns:
            Search results in the specified format:
            - 'list': List of dicts with title, url, content
            - 'json': JSON string of the results
            - 'text': Plain text summary of results

        Response fields for each result:
            - title: The title of the search result
            - url: The URL of the search result
            - content: A snippet or summary of the content
            - provider: Which search engine provided this result
        """
        # Validate inputs
        if not query or not query.strip():
            return [] if output_format == "list" else "[]"

        num_results = min(num_results or 10, 50)  # Cap at 50
        output_format = (output_format or "list").lower()

        try:
            # Perform hybrid search
            response = self.search_engine.search(
                query=query,
                num=num_results,
                include_domains=domains,
                exclude_domains=exclude_domains,
                aggregation_strategy="merge"  # Use merge for best results
            )

            # Extract and format results
            results = []
            for result in response.get("results", []):
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "provider": result.get("provider", "unknown")
                }
                results.append(formatted_result)

            # Return in requested format
            if output_format == "json":
                return json.dumps(results, ensure_ascii=False, indent=2)
            elif output_format == "text":
                # Create a text summary
                if not results:
                    return "No results found."

                text_parts = [f"Search results for '{query}':\n"]
                for i, result in enumerate(results, 1):
                    text_parts.append(
                        f"{i}. {result['title']}\n"
                        f"   URL: {result['url']}\n"
                        f"   {result['content'][:200]}...\n"
                    )
                return "\n".join(text_parts)
            else:  # Default to list
                return results

        except Exception as e:
            # Return empty results on error
            if output_format == "json":
                return json.dumps({"error": str(e), "results": []})
            elif output_format == "text":
                return f"Search failed: {str(e)}"
            else:
                return []


# Convenience function for direct usage
def search_fast(
    query: str,
    num_results: int = 10,
    domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    output_format: str = "list"
) -> Union[List[Dict[str, str]], str]:
    """
    Fast web search function.

    Args:
        query: Search query
        num_results: Number of results (default: 10, max: 50)
        domains: Domains to search within
        exclude_domains: Domains to exclude
        output_format: 'list', 'json', or 'text'

    Returns:
        Search results in the specified format
    """
    tool = SearchLinksFastTool()
    return tool.forward(
        query=query,
        num_results=num_results,
        domains=domains,
        exclude_domains=exclude_domains,
        output_format=output_format
    )

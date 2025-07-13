#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/search.py
# code style: PEP 8

"""
Search Links Agent Tool for DeepSearchAgents.
"""

import os
import json
from typing import Dict, Optional, Literal, List, Any, Union
from smolagents import Tool
from src.core.search_engines.search_serper import SerperAPI
from src.core.search_engines.search_xcom import (
    XAISearchClient, detect_x_query, extract_x_handles
)
from src.core.search_engines.search_hybrid import HybridSearchEngine


class SearchLinksTool(Tool):
    """
    Performs a web search using a query and returns search results
    with links, titles, and content snippets.

    This tool supports multiple search providers:
    - "serper": Google search via Serper API (default)
    - "xai": xAI Live Search with multiple sources (X.com, web, news, RSS)
    - "hybrid": Aggregated search across multiple providers

    Example usage:
        # Basic web search
        results = search_links("machine learning tutorials")

        # Search X.com (Twitter)
        results = search_links("@elonmusk AI", source="xai", xai_sources=["x"])

        # Hybrid search with domain filtering
        results = search_links("pytorch documentation",
                             source="hybrid",
                             allowed_websites=["pytorch.org", "github.com"])

    Response format:
        Each result contains:
        - title: The title of the search result
        - link/url: The URL of the result
        - snippet/content: A text snippet from the result
        - position: The ranking position (for some providers)
        - provider: Which search engine provided the result
    """
    name = "search_links"
    description = (
        "Performs a web search using a query and returns search results. "
        "Can search Google (via Serper), X.com/Twitter (via xAI), or aggregate "
        "results from multiple providers. Returns a list of results with "
        "title, link, and snippet for each result. Use return_dict=True "
        "for structured dict output, or False for JSON string."
    )
    inputs: Dict[str, Any] = {
        "query": {
            "type": "string",
            "description": "The search query string.",
        },
        "num_results": {
            "type": "integer",
            "description": "The desired number of search results.",
            "default": 10,
            "nullable": True,
        },
        "return_dict": {
            "type": "boolean",
            "description": (
                "If True, returns a dict with structured results. "
                "If False, returns JSON string for compatibility."
            ),
            "default": False,
            "nullable": True,
        },
        "location": {
            "type": "string",
            "description": (
                "The geographic location for the search (e.g., 'us'). "
                "Only applicable for web search."
            ),
            "default": "us",
            "nullable": True,
        },
        "source": {
            "type": "string",
            "description": (
                "The search source to use: 'auto' (detect automatically based on query), "
                "'serper' (Google search), 'xai' (xAI Live Search), or 'hybrid' "
                "(aggregate results from multiple providers)."
            ),
            "default": "auto",
            "nullable": True,
        },
        "xai_sources": {
            "type": "array",
            "description": (
                "For xAI search, specify which sources to search: "
                "['x', 'web', 'news', 'rss']. Defaults to ['web', 'x']."
            ),
            "default": None,
            "nullable": True,
        },
        "xai_mode": {
            "type": "string",
            "description": (
                "xAI search mode: 'auto' (model decides), 'on' (always search), "
                "'off' (no search). Default is 'auto'."
            ),
            "default": "auto",
            "nullable": True,
        },
        "x_handles": {
            "type": "array",
            "description": (
                "Optional list of X.com handles to include in search. "
                "Only applicable when using xAI with X source."
            ),
            "default": None,
            "nullable": True,
        },
        "excluded_x_handles": {
            "type": "array",
            "description": (
                "Optional list of X.com handles to exclude from search. "
                "Cannot be used with x_handles. Only for xAI with X source."
            ),
            "default": None,
            "nullable": True,
        },
        "post_favorite_count": {
            "type": "integer",
            "description": (
                "Minimum number of favorites for X posts. "
                "Only applicable when using xAI with X source."
            ),
            "default": None,
            "nullable": True,
        },
        "post_view_count": {
            "type": "integer",
            "description": (
                "Minimum number of views for X posts. "
                "Only applicable when using xAI with X source."
            ),
            "default": None,
            "nullable": True,
        },
        "country": {
            "type": "string",
            "description": (
                "ISO alpha-2 country code for web/news search (e.g., 'US', 'UK'). "
                "Only applicable when using xAI with web or news sources."
            ),
            "default": None,
            "nullable": True,
        },
        "excluded_websites": {
            "type": "array",
            "description": (
                "List of websites to exclude from web/news search (max 5). "
                "Only applicable when using xAI with web or news sources."
            ),
            "default": None,
            "nullable": True,
        },
        "allowed_websites": {
            "type": "array",
            "description": (
                "List of websites to restrict web search to (max 5). "
                "Cannot be used with excluded_websites. Only for xAI web source."
            ),
            "default": None,
            "nullable": True,
        },
        "safe_search": {
            "type": "boolean",
            "description": (
                "Enable safe search for web/news results. Default is True. "
                "Only applicable when using xAI with web or news sources."
            ),
            "default": True,
            "nullable": True,
        },
        "rss_links": {
            "type": "array",
            "description": (
                "RSS feed URLs to fetch data from (currently limited to 1). "
                "Only applicable when using xAI with rss source."
            ),
            "default": None,
            "nullable": True,
        },
        "from_date": {
            "type": "string",
            "description": (
                "Optional start date in ISO format (YYYY-MM-DD) for search. "
                "Only applicable when using xAI."
            ),
            "default": None,
            "nullable": True,
        },
        "to_date": {
            "type": "string",
            "description": (
                "Optional end date in ISO format (YYYY-MM-DD) for search. "
                "Only applicable when using xAI."
            ),
            "default": None,
            "nullable": True,
        }
    }
    output_type = "any"  # Can return string or dict

    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        xai_api_key: Optional[str] = None,
        jina_api_key: Optional[str] = None,
        exa_api_key: Optional[str] = None,
        search_provider: Literal["auto", "serper", "xai", "hybrid"] = "auto",
        cli_console=True,
        verbose: bool = False
    ):
        """
        Initialize SearchLinksTool.

        Args:
            serper_api_key (str, optional): SerperAPI key. If None, load from
                environment variable SERPER_API_KEY.
            xai_api_key (str, optional): xAI API key. If None, load from
                environment variable XAI_API_KEY.
            jina_api_key (str, optional): Jina API key. If None, load from
                environment variable JINA_API_KEY.
            exa_api_key (str, optional): Exa API key. If None, load from
                environment variable EXA_API_KEY.
            search_provider (str): Default search provider
                ('auto', 'serper', 'xai', or 'hybrid')
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.search_provider = search_provider

        # Initialize Serper API for Google search
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        if not self.serper_api_key:
            raise ValueError(
                "SERPER_API_KEY is required but not provided or found in "
                "environment."
            )
        self.serp_search_api = SerperAPI(api_key=self.serper_api_key)

        # Initialize XAI Search client for X.com search
        self.xai_api_key = xai_api_key or os.getenv("XAI_API_KEY")
        self.xai_search_api = None
        if self.xai_api_key:
            self.xai_search_api = XAISearchClient(api_key=self.xai_api_key)

        # Initialize Jina and Exa API keys
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY")

        # Initialize Hybrid Search Engine if needed
        self.hybrid_search_api = None
        if search_provider == "hybrid" or search_provider == "auto":
            api_keys = {}
            if self.serper_api_key:
                api_keys["serper"] = self.serper_api_key
            if self.xai_api_key:
                api_keys["xai"] = self.xai_api_key
            if self.jina_api_key:
                api_keys["jina"] = self.jina_api_key
            if self.exa_api_key:
                api_keys["exa"] = self.exa_api_key

            if api_keys:
                self.hybrid_search_api = HybridSearchEngine(
                    api_keys=api_keys
                )

        self.cli_console = cli_console
        self.verbose = verbose

    def forward(
        self,
        query: str,
        num_results: Optional[int] = 10,
        return_dict: Optional[bool] = False,
        location: Optional[str] = "us",
        source: Optional[str] = "auto",
        xai_sources: Optional[List[str]] = None,
        xai_mode: Optional[str] = "auto",
        x_handles: Optional[List[str]] = None,
        excluded_x_handles: Optional[List[str]] = None,
        post_favorite_count: Optional[int] = None,
        post_view_count: Optional[int] = None,
        country: Optional[str] = None,
        excluded_websites: Optional[List[str]] = None,
        allowed_websites: Optional[List[str]] = None,
        safe_search: Optional[bool] = True,
        rss_links: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """
        Performs a search and returns search results.

        Args:
            query (str): The search query.
            num_results (int, optional): The number of results to return.
                Default: 10.
            return_dict (bool, optional): If True, returns structured dict.
                If False, returns JSON string. Default: False.
            location (str, optional): The search location. Default: 'us'.
            source (str, optional): Search source to use ('auto', 'serper',
                'xai', or 'hybrid'). Default: 'auto'.
            xai_sources (List[str], optional): Sources for xAI search.
            xai_mode (str, optional): xAI search mode.
            x_handles (List[str], optional): X.com handles to include.
            excluded_x_handles (List[str], optional): X.com handles to exclude.
            post_favorite_count (int, optional): Minimum X post favorites.
            post_view_count (int, optional): Minimum X post views.
            country (str, optional): Country code for web/news search.
            excluded_websites (List[str], optional): Websites to exclude.
            allowed_websites (List[str], optional): Websites to restrict to.
            safe_search (bool, optional): Enable safe search.
            rss_links (List[str], optional): RSS feed URLs.
            from_date (str, optional): Start date in ISO format.
            to_date (str, optional): End date in ISO format.

        Returns:
            Union[str, Dict]: If return_dict=False, returns JSON string.
                If return_dict=True, returns dict with 'results' key
                containing list of search results.
        """
        num_results = num_results if num_results is not None else 10
        location = location if location is not None else "us"
        source = source if source is not None else "auto"
        xai_mode = xai_mode if xai_mode is not None else "auto"
        safe_search = safe_search if safe_search is not None else True

        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)

        # Determine the search source to use
        search_source = source.lower()
        if search_source == "auto":
            # Auto-detect if the query is related to X.com
            if detect_x_query(query):
                search_source = "xai"
                # Default to X source for X-specific queries
                if not xai_sources:
                    xai_sources = ["x"]
            elif self.hybrid_search_api:
                # Use hybrid search if available
                search_source = "hybrid"
            else:
                search_source = "serper"

        # Extract X handles from query if none provided explicitly
        if search_source == "xai" and "x" in (xai_sources or []):
            if not x_handles and not excluded_x_handles:
                extracted_handles = extract_x_handles(query)
                if extracted_handles:
                    x_handles = extracted_handles
                    log_func(
                        f"[dim]Extracted X handles from query: "
                        f"{x_handles}[/dim]"
                    )

        # Log search parameters
        log_func(f"[bold blue]Performing {search_source} "
                 f"search[/bold blue]: {query}")
        if search_source == "serper":
            log_func(
                f"[dim]Parameters: num_results={num_results}, "
                f"location={location}[/dim]"
            )
        elif search_source == "xai":
            log_func(
                f"[dim]Parameters: num_results={num_results}, "
                f"sources={xai_sources}, mode={xai_mode}[/dim]"
            )
            if x_handles or excluded_x_handles:
                log_func(
                    f"[dim]X params: handles={x_handles}, "
                    f"excluded={excluded_x_handles}[/dim]"
                )

        results_list: List[Dict] = []

        # Perform search using the appropriate search engine
        if search_source == "serper":
            # Google search via Serper API
            try:
                search_response = self.serp_search_api.search(
                    query=query,
                    num=num_results,
                    gl=location
                )

                if search_response.get("results"):
                    # Convert results to expected format
                    for result in search_response["results"]:
                        results_list.append({
                            "title": result.title,
                            "link": result.url,
                            "snippet": result.snippet,
                            "position": result.position
                        })
                    log_func(
                        f"[bold green]Web search completed, found "
                        f"{len(results_list)} results.[/bold green]"
                    )
                else:
                    log_func("[yellow]No search results found.[/yellow]")

            except Exception as e:
                log_func(f"[bold red]Web search failed[/bold red]: {str(e)}")

        elif search_source == "xai":
            # xAI Live Search
            if not self.xai_search_api:
                if not self.xai_api_key:
                    log_func(
                        "[bold red]xAI search failed: XAI_API_KEY is required "
                        "but not provided or found in environment.[/bold red]"
                    )
                else:
                    # Initialize XAI Search client if not already done
                    self.xai_search_api = XAISearchClient(
                        api_key=self.xai_api_key
                    )

            if self.xai_search_api:
                try:
                    # Build parameters for xAI search
                    xai_params = {
                        "query": query,
                        "num": num_results,
                        "sources": xai_sources or ["web", "x"],
                        "mode": xai_mode,
                        "from_date": from_date,
                        "to_date": to_date,
                    }

                    # Add X-specific parameters if X source is included
                    if "x" in (xai_sources or ["web", "x"]):
                        if x_handles:
                            xai_params["included_x_handles"] = x_handles
                        elif excluded_x_handles:
                            xai_params["excluded_x_handles"] = (
                                excluded_x_handles
                            )
                        if post_favorite_count is not None:
                            xai_params["post_favorite_count"] = (
                                post_favorite_count
                            )
                        if post_view_count is not None:
                            xai_params["post_view_count"] = post_view_count

                    # Add web/news parameters if those sources are included
                    if "web" in (xai_sources or []) or "news" in (
                        xai_sources or []
                    ):
                        if country:
                            xai_params["country"] = country
                        if excluded_websites:
                            xai_params["excluded_websites"] = (
                                excluded_websites
                            )
                        elif allowed_websites and "web" in (
                            xai_sources or []
                        ):
                            xai_params["allowed_websites"] = allowed_websites
                        xai_params["safe_search"] = safe_search

                    # Add RSS parameters if RSS source is included
                    if "rss" in (xai_sources or []) and rss_links:
                        xai_params["rss_links"] = rss_links

                    # Perform xAI search
                    xai_response = self.xai_search_api.search(**xai_params)

                    # Extract results from the standardized format
                    if isinstance(xai_response, dict) and (
                        "results" in xai_response
                    ):
                        results_list = xai_response["results"]
                    else:
                        results_list = []

                    log_func(
                        f"[bold green]xAI search completed, found "
                        f"{len(results_list)} results.[/bold green]"
                    )
                except Exception as e:
                    log_func(
                        f"[bold red]xAI search failed[/bold red]: {str(e)}"
                    )

        elif search_source == "hybrid":
            # Hybrid search across multiple providers
            if not self.hybrid_search_api:
                log_func(
                    "[bold red]Hybrid search failed: No providers "
                    "configured.[/bold red]"
                )
            else:
                try:
                    # Build parameters for hybrid search
                    hybrid_params = {
                        "query": query,
                        "num": num_results,
                        "start_date": from_date,
                        "end_date": to_date,
                    }

                    # Add domain filters
                    if allowed_websites:
                        hybrid_params["include_domains"] = allowed_websites
                    elif excluded_websites:
                        hybrid_params["exclude_domains"] = excluded_websites

                    # Add provider-specific parameters
                    if x_handles or excluded_x_handles:
                        hybrid_params["xai_params"] = {
                            "included_x_handles": x_handles,
                            "excluded_x_handles": excluded_x_handles,
                            "post_favorite_count": post_favorite_count,
                            "post_view_count": post_view_count,
                        }

                    # Perform hybrid search
                    hybrid_response = self.hybrid_search_api.search(
                        **hybrid_params
                    )

                    # Convert to expected format
                    if isinstance(hybrid_response, dict) and (
                        "results" in hybrid_response
                    ):
                        for result in hybrid_response["results"]:
                            results_list.append({
                                "title": result.get("title", ""),
                                "link": result.get("url", ""),
                                "snippet": result.get("content", ""),
                                "provider": result.get("provider", "hybrid")
                            })

                    log_func(
                        f"[bold green]Hybrid search completed, found "
                        f"{len(results_list)} results from "
                        f"{len(hybrid_response.get('providers_used', []))} "
                        f"providers.[/bold green]"
                    )
                except Exception as e:
                    log_func(f"[bold red]Hybrid search failed[/bold red]: {str(e)}")
        else:
            log_func(f"[bold red]Unsupported search source: {search_source}[/bold red]")

        # Return results in requested format
        if return_dict:
            # Return structured dict
            return {
                "results": results_list,
                "query": query,
                "total_results": len(results_list),
                "source": search_source
            }
        else:
            # Return JSON string for backward compatibility
            try:
                return json.dumps(results_list, ensure_ascii=False, indent=2)
            except TypeError as e:
                log_func(f"[bold red]Error serializing search results: "
                         f"{e}")
                return "[]"

    def setup(self):
        """Tool setup (if needed). Currently initialized in __init__."""
        pass

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/search.py
# code style: PEP 8

"""
Search Links Agent Tool for DeepSearchAgents.
"""

import os
import json
from typing import Dict, Optional, Literal, List
from smolagents import Tool
from src.core.search_engines.search_serper import (
    SerperAPI, SearchResult, SerperConfig
)
from src.core.search_engines.search_xcom import (
    XAISearchClient, detect_x_query, extract_x_handles
)


class SearchLinksTool(Tool):
    """
    Performs a web search using a query and returns a JSON string
    representing a list of Search Engine Results Page (SERP) links,
    titles, and snippets.

    This tool supports multiple search providers:
    - "serper": Google search via Serper API (default)
    - "xcom": X.com (Twitter) search via xAI API
    """
    name = "search_links"
    description = (
        "Performs a web search using a query and returns a JSON string "
        "representing a list of Search Engine Results Page (SERP) links, "
        "titles, and snippets. Can search both regular web content (via Google) "
        "or X.com (Twitter) content depending on the query and source parameter."
    )
    inputs = {
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
                "'serper' (Google search), or 'xcom' (X.com/Twitter search)."
            ),
            "default": "auto",
            "nullable": True,
        },
        "x_handles": {
            "type": "array",
            "description": (
                "Optional list of X.com handles to restrict search to. "
                "Only applicable when source is 'xcom'."
            ),
            "default": None,
            "nullable": True,
        },
        "from_date": {
            "type": "string",
            "description": (
                "Optional start date in ISO format (YYYY-MM-DD) for X.com search. "
                "Only applicable when source is 'xcom'."
            ),
            "default": None,
            "nullable": True,
        },
        "to_date": {
            "type": "string",
            "description": (
                "Optional end date in ISO format (YYYY-MM-DD) for X.com search. "
                "Only applicable when source is 'xcom'."
            ),
            "default": None,
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        xai_api_key: Optional[str] = None,
        search_provider: Literal["auto", "serper", "xcom"] = "auto",
        cli_console=None,
        verbose: bool = False
    ):
        """
        Initialize SearchLinksTool.

        Args:
            serper_api_key (str, optional): SerperAPI key. If None, load from
                environment variable SERPER_API_KEY.
            xai_api_key (str, optional): xAI API key. If None, load from
                environment variable XAI_API_KEY.
            search_provider (str): Default search provider ('auto', 'serper', or 'xcom')
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
        serper_config = SerperConfig(api_key=self.serper_api_key)
        self.serp_search_api = SerperAPI(config=serper_config)

        # Initialize XAI Search client for X.com search
        self.xai_api_key = xai_api_key or os.getenv("XAI_API_KEY")
        self.xai_search_api = None
        if self.xai_api_key:
            self.xai_search_api = XAISearchClient(api_key=self.xai_api_key)

        self.cli_console = cli_console
        self.verbose = verbose

    def forward(
        self,
        query: str,
        num_results: Optional[int] = 10,
        location: Optional[str] = "us",
        source: Optional[str] = "auto",
        x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> str:
        """
        Performs a search and returns a JSON string containing a list of
        Search Engine Results Page (SERP) results.

        Args:
            query (str): The search query.
            num_results (int, optional): The number of results to return.
                Default: 10.
            location (str, optional): The search location. Default: 'us'.
            source (str, optional): Search source to use ('auto', 'serper', or 'xcom').
                Default: 'auto'.
            x_handles (List[str], optional): List of X.com handles to restrict search to.
                Only applicable when source is 'xcom'.
            from_date (str, optional): Start date in ISO format (YYYY-MM-DD) for X.com search.
                Only applicable when source is 'xcom'.
            to_date (str, optional): End date in ISO format (YYYY-MM-DD) for X.com search.
                Only applicable when source is 'xcom'.

        Returns:
            str: A JSON string containing a list of Search Engine Results Page
                (SERP) results. If the search fails or returns no results,
                return a JSON string of an empty list ('[]').
        """
        num_results = num_results if num_results is not None else 10
        location = location if location is not None else "us"
        source = source if source is not None else "auto"

        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)

        # Determine the search source to use
        search_source = source.lower()
        if search_source == "auto":
            # Auto-detect if the query is related to X.com
            if detect_x_query(query):
                search_source = "xcom"
            else:
                search_source = "serper"

        # Extract X handles from query if none provided explicitly
        if search_source == "xcom" and not x_handles:
            extracted_handles = extract_x_handles(query)
            if extracted_handles:
                x_handles = extracted_handles
                log_func(f"[dim]Extracted X handles from query: {x_handles}[/dim]")

        # Log search parameters
        log_func(f"[bold blue]Performing {search_source} search[/bold blue]: {query}")
        if search_source == "serper":
            log_func(
                f"[dim]Parameters: num_results={num_results}, "
                f"location={location}[/dim]"
            )
        elif search_source == "xcom":
            log_func(
                f"[dim]Parameters: num_results={num_results}, "
                f"x_handles={x_handles}, from_date={from_date}, "
                f"to_date={to_date}[/dim]"
            )

        results_list: List[Dict] = []

        # Perform search using the appropriate search engine
        if search_source == "serper":
            # Google search via Serper API
            search_result: SearchResult[Dict] = self.serp_search_api.get_sources(
                query,
                num_results=num_results,
                stored_location=location
            )

            if search_result.failed:
                log_func(f"[bold red]Web search failed[/bold red]: "
                         f"{search_result.error}")
            elif not search_result.data or not search_result.data.get('organic'):
                log_func("[yellow]No organic search results found.[/yellow]")
            else:
                results_list = search_result.data['organic']
                log_func(
                    f"[bold green]Web search completed, found "
                    f"{len(results_list)} results.[/bold green]"
                )

        elif search_source == "xcom":
            # X.com search via xAI API
            if not self.xai_search_api:
                if not self.xai_api_key:
                    log_func(
                        "[bold red]X.com search failed: XAI_API_KEY is required "
                        "but not provided or found in environment.[/bold red]"
                    )
                else:
                    # Initialize XAI Search client if not already done
                    self.xai_search_api = XAISearchClient(
                        query=query,
                        max_results=num_results,
                        api_key=self.xai_api_key
                    )

            if self.xai_search_api:
                try:
                    # Perform X.com search
                    x_results = self.xai_search_api.search_x_content(
                        query=query,
                        x_handles=x_handles,
                        from_date=from_date,
                        to_date=to_date
                    )

                    # Add source metadata to results
                    for result in x_results:
                        result["source"] = "xcom"

                    results_list = x_results
                    log_func(
                        f"[bold green]X.com search completed, found "
                        f"{len(results_list)} results.[/bold green]"
                    )
                except Exception as e:
                    log_func(f"[bold red]X.com search failed[/bold red]: {str(e)}")
        else:
            log_func(f"[bold red]Unsupported search source: {search_source}[/bold red]")

        # convert the results list to a JSON string
        try:
            return json.dumps(results_list, ensure_ascii=False, indent=2)
        except TypeError as e:
            log_func(f"[bold red]Error serializing search results: "
                     f"{e}")
            return "[]"

    def setup(self):
        """Tool setup (if needed). Currently initialized in __init__."""
        pass

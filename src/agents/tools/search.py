import os
import json
from typing import Dict, Optional, Literal, List
from smolagents import Tool
from ..core.search_engines.serper import SerperAPI, SearchResult, SerperConfig


class SearchLinksTool(Tool):
    """
    Performs a web search using a query and returns a JSON string
    representing a list of Search Engine Results Page (SERP) links,
    titles, and snippets.
    """
    name = "search_links"
    description = (
        "Performs a web search using a query and returns a JSON string "
        "representing a list of Search Engine Results Page (SERP) links, "
        "titles, and snippets."
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
                "The geographic location for the search (e.g., 'us', 'cn')."
            ),
            "default": "us",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        search_provider: Literal["serper"] = "serper",
        cli_console=None,
        verbose: bool = False
    ):
        """
        Initialize SearchLinksTool.

        Args:
            serper_api_key (str, optional): SerperAPI key. If None, load from
                environment variable SERPER_API_KEY.
            search_provider (str): Search provider (currently fixed to 'serper').
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.search_provider = search_provider
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        if not self.serper_api_key:
            raise ValueError(
                "SERPER_API_KEY is required but not provided or found in environment."
            )

        # initialize SerperAPI instance
        serper_config = SerperConfig(api_key=self.serper_api_key)
        self.serp_search_api = SerperAPI(config=serper_config)

        self.cli_console = cli_console
        self.verbose = verbose

    def forward(
        self,
        query: str,
        num_results: Optional[int] = 10,
        location: Optional[str] = "us"
    ) -> str:
        """
        Performs a search and returns a JSON string containing a list of
        Search Engine Results Page (SERP) results.

        Args:
            query (str): The search query.
            num_results (int, optional): The number of results to return.
                Default: 10.
            location (str, optional): The search location. Default: 'us'.

        Returns:
            str: A JSON string containing a list of Search Engine Results Page
                (SERP) results. If the search fails or returns no results,
                return a JSON string of an empty list ('[]').
        """
        num_results = num_results if num_results is not None else 10
        location = location if location is not None else "us"

        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)
        log_func(f"[bold blue]Performing web search[/bold blue]: {query}")
        log_func(
            f"[dim]Parameters: num_results={num_results}, location={location}[/dim]"
        )

        search_result: SearchResult[Dict] = self.serp_search_api.get_sources(
            query,
            num_results=num_results,
            stored_location=location
        )

        results_list: List[Dict] = []
        if search_result.failed:
            log_func(f"[bold red]Web search failed[/bold red]: {search_result.error}")
        elif not search_result.data or not search_result.data.get('organic'):
            log_func("[yellow]No organic search results found.[/yellow]")
        else:
            results_list = search_result.data['organic']
            log_func(
                f"[bold green]Web search completed, found "
                f"{len(results_list)} results.[/bold green]"
            )

        # convert the results list to a JSON string
        try:
            return json.dumps(results_list, ensure_ascii=False, indent=2)
        except TypeError as e:
            log_func(f"[bold red]Error serializing search results: {e}")
            return "[]"

    def setup(self):
        """Tool setup (if needed). Currently initialized in __init__."""
        pass

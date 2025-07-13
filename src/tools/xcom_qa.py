#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/xcom_qa.py
# code style: PEP 8

"""
X.com (Twitter) Deep Q&A Tool for DeepSearchAgents.
Uses xAI's Live Search API to analyze X.com content.
"""

import re
import logging
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
from smolagents import Tool

if TYPE_CHECKING:
    from rich.console import Console

from src.core.xcom_toolkit import XAILiveSearchClient

logger = logging.getLogger(__name__)


class XcomDeepQATool(Tool):
    """
    Deep query and analyze X.com (Twitter) content using xAI's Live Search.
    This tool can:
    - Search X posts with advanced filters
    - Read specific X.com post URLs
    - Ask questions about X.com content
    """

    name = "xcom_deep_qa"
    description = (
        "Deep query and analyze X.com content using xAI's Live Search. "
        "Operations: 'search' (find posts), 'read' (extract post content), "
        "'query' (ask questions). Supports filters like user handles, "
        "engagement metrics, and date ranges."
    )
    inputs = {
        "query_or_url": {
            "type": "string",
            "description": (
                "Search query for 'search'/'query' operations, or X.com URL "
                "for 'read' operation"
            ),
        },
        "operation": {
            "type": "string",
            "description": (
                "Operation to perform: 'search' (find posts), 'read' "
                "(extract post content), or 'query' (ask questions)"
            ),
            "default": "search",
            "nullable": True,
        },
        "search_params": {
            "type": "any",
            "description": (
                "Search filters dict: included_x_handles (list), "
                "excluded_x_handles (list), post_favorite_count (int), "
                "post_view_count (int), from_date (str), to_date (str)"
            ),
            "default": None,
            "nullable": True,
        },
        "question": {
            "type": "string",
            "description": (
                "Question to ask about X.com content (required when "
                "operation='query')"
            ),
            "default": None,
            "nullable": True,
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results for search operations",
            "default": 20,
            "nullable": True,
        },
    }
    output_type = "any"  # returns structured data

    def __init__(
        self,
        xai_api_key: Optional[str] = None,
        cli_console: Optional["Console"] = None,
        verbose: bool = False,
    ):
        """
        Initialize XcomDeepQATool.

        Args:
            xai_api_key: xAI API key (defaults to XAI_API_KEY env var)
            cli_console: Optional rich.console.Console for verbose CLI output
            verbose: Whether to enable verbose logging
        """
        super().__init__()

        self.xai_api_key = xai_api_key
        self.cli_console = cli_console
        self.verbose = verbose

        # XAILiveSearchClient instance will be created when needed
        self.client: Optional[XAILiveSearchClient] = None

    def _ensure_client(self):
        """Ensure XAILiveSearchClient instance is created."""
        if self.client is None:
            self.client = XAILiveSearchClient(api_key=self.xai_api_key)
            if self.verbose and self.cli_console:
                self.cli_console.print(
                    "[green]Connected to xAI Live Search API[/green]"
                )

    def _is_x_url(self, text: str) -> bool:
        """Check if text is an X.com URL."""
        return bool(re.match(
            r'https?://(www\.)?(x\.com|twitter\.com)/.*',
            text
        ))

    def _validate_search_params(
        self, 
        search_params: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate and clean search parameters.

        Args:
            search_params: Raw search parameters

        Returns:
            Cleaned parameters or None
        """
        if not search_params:
            return None

        cleaned = {}

        # Validate handles
        for key in ["included_x_handles", "excluded_x_handles"]:
            if key in search_params:
                handles = search_params[key]
                if isinstance(handles, str):
                    handles = [handles]
                elif not isinstance(handles, list):
                    continue

                # Clean handles (remove @ if present)
                cleaned_handles = []
                for handle in handles[:10]:  # Max 10
                    if isinstance(handle, str):
                        handle = handle.strip().lstrip("@")
                        if handle:
                            cleaned_handles.append(handle)

                if cleaned_handles:
                    cleaned[key] = cleaned_handles

        # Validate metrics
        for key in ["post_favorite_count", "post_view_count"]:
            if key in search_params:
                try:
                    value = int(search_params[key])
                    if value > 0:
                        cleaned[key] = value
                except (ValueError, TypeError):
                    pass

        # Validate dates
        for key in ["from_date", "to_date"]:
            if key in search_params:
                cleaned[key] = search_params[key]

        return cleaned if cleaned else None

    def forward(
        self,
        query_or_url: str,
        operation: str = "search",
        search_params: Optional[Dict[str, Any]] = None,
        question: Optional[str] = None,
        max_results: int = 20,
    ) -> Union[str, Dict[str, Any]]:
        """
        Query X.com content using xAI Live Search.

        Args:
            query_or_url: Search query or X.com URL
            operation: Operation to perform ('search', 'read', 'query')
            search_params: Optional search filters
            question: Question for 'query' operation
            max_results: Maximum results for search

        Returns:
            Query results as structured data
        """
        self._ensure_client()

        # Validate search parameters
        search_params = self._validate_search_params(search_params)

        # Log the operation
        if self.verbose and self.cli_console:
            self.cli_console.print(
                f"[blue]X.com Deep QA:[/blue] {operation} - '{query_or_url}'"
            )

        try:
            assert self.client is not None, "Client not initialized"

            if operation == "search":
                # Search X posts
                result = self.client.search_x_posts(
                    query=query_or_url,
                    search_params=search_params,
                    max_results=max_results,
                )

            elif operation == "read":
                # Validate URL
                if not self._is_x_url(query_or_url):
                    error_msg = (
                        f"Invalid X.com URL: '{query_or_url}'. "
                        f"Expected URL starting with https://x.com/ or "
                        f"https://twitter.com/"
                    )
                    if self.verbose and self.cli_console:
                        self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                    return {"error": error_msg, "success": False}

                # Read specific post
                result = self.client.read_x_post(url=query_or_url)

            elif operation == "query":
                # Validate question
                if not question:
                    error_msg = "Question is required when operation='query'"
                    if self.verbose and self.cli_console:
                        self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                    return {"error": error_msg, "success": False}

                # Query about X content
                result = self.client.query_x_content(
                    question=question,
                    search_context=query_or_url,
                    search_params=search_params,
                )

            else:
                error_msg = (
                    f"Unknown operation: '{operation}'. "
                    f"Valid operations: 'search', 'read', 'query'"
                )
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return {"error": error_msg, "success": False}

            # Process result
            if result.get("success"):
                if self.verbose and self.cli_console:
                    self.cli_console.print(
                        f"[green]X.com Deep QA completed successfully[/green]"
                    )

                # For better integration, return content directly for read/query
                if operation in ["read", "query"]:
                    # Include metadata in response
                    response = result.get("content", "")
                    if result.get("citations"):
                        response += "\n\n## Sources\n"
                        for i, citation in enumerate(result["citations"], 1):
                            response += f"{i}. {citation}\n"
                    return response
                else:
                    # Return full result for search
                    return result
            else:
                error_msg = result.get("error", "Unknown error occurred")
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return result

        except Exception as e:
            error_msg = f"Error in X.com Deep QA: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if self.verbose and self.cli_console:
                self.cli_console.print(f"[red]Error: {error_msg}[/red]")
            return {
                "error": error_msg,
                "success": False,
                "operation": operation,
                "query_or_url": query_or_url,
            }

    def setup(self):
        """Tool setup (if needed)."""
        # Initialization is done on demand
        pass

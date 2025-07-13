#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/github_qa.py
# code style: PEP 8

"""
GitHub Repository Deep Q&A Tool for DeepSearchAgents.
Uses DeepWiki Remote MCP Server to analyze GitHub repositories.
"""

import re
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
import logging
from smolagents import Tool

if TYPE_CHECKING:
    from rich.console import Console
from src.core.github_toolkit import DeepWikiClient

logger = logging.getLogger(__name__)


class GitHubRepoQATool(Tool):
    """
    Query GitHub repositories using DeepWiki's AI-powered documentation
    and search capabilities. This tool can:
    - Get repository documentation structure
    - Read full repository documentation
    - Ask specific questions about a repository
    """

    name = "github_repo_qa"
    description = (
        "Query GitHub repositories using DeepWiki's AI-powered documentation "
        "and search. Operations: 'structure' (get docs structure), 'contents' "
        "(read full docs), 'query' (ask questions). Repository format: "
        "'owner/repo' (e.g., 'google-gemini/gemini-cli')."
    )
    inputs = {
        "repo": {
            "type": "string",
            "description": (
                "GitHub repository name(or link) in format 'owner/repo' "
                "(e.g., 'google-gemini/gemini-cli')"
            ),
        },
        "operation": {
            "type": "string",
            "description": (
                "Operation to perform: 'structure' (get doc topics), "
                "'contents' (read full documentation), or 'query' (ask a "
                "specific question)"
            ),
            "default": "structure",
            "nullable": True,
        },
        "question": {
            "type": "string",
            "description": (
                "Question to ask about the repository (required when "
                "operation='query')"
            ),
            "default": "Help me analyze this Repo...",
            "nullable": True,
        },
    }
    output_type = "any"  # returns structured data or text

    def __init__(
        self,
        server_url: str = "https://mcp.deepwiki.com/mcp",
        transport: str = "streamable-http",
        cli_console: Optional["Console"] = None,
        verbose: bool = False,
    ):
        """
        Initialize GitHubRepoQATool.

        Args:
            server_url: URL of the DeepWiki MCP server
            transport: Transport protocol ("sse" or "streamable-http")
            cli_console: Optional rich.console.Console for verbose CLI output
            verbose: Whether to enable verbose logging
        """
        super().__init__()

        # Configure server URL based on transport
        if transport == "streamable-http":
            server_url = "https://mcp.deepwiki.com/mcp"

        self.server_url = server_url
        self.transport = transport
        self.cli_console = cli_console
        self.verbose = verbose

        # DeepWikiClient instance will be created when needed
        self.scraper: Optional[DeepWikiClient] = None

        # Thread pool for handling async operations
        self._executor = ThreadPoolExecutor(max_workers=10)

        # Thread local storage for isolation
        self._local = threading.local()

    def _validate_repo_format(self, repo: str) -> bool:
        """
        Validate GitHub repository format.

        Args:
            repo: Repository string to validate

        Returns:
            True if valid format, False otherwise
        """
        # Pattern for owner/repo format
        pattern = r"^[a-zA-Z0-9][\w.-]*/[a-zA-Z0-9][\w.-]*$"
        return bool(re.match(pattern, repo))

    def _ensure_scraper(self):
        """Ensure DeepWikiClient instance is created."""
        if self.scraper is None:
            self.scraper = DeepWikiClient(
                server_url=self.server_url, transport=self.transport
            )
            if self.verbose and self.cli_console:
                self.cli_console.print(
                    "[green]Connected to DeepWiki MCP server[/green]"
                )

    def _run_in_thread(self, coro):
        """Run async coroutine in thread pool."""
        loop = None
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's already a running loop, use thread pool
                future = self._executor.submit(asyncio.run, coro)
                return future.result(timeout=300)  # 5 minute timeout
            else:
                # If no running loop, run directly
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(coro)

    async def _async_forward(
        self,
        repo: str,
        operation: str = "structure",
        question: Optional[str] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Async implementation of the tool's forward method."""
        self._ensure_scraper()

        # Validate repository format
        if not self._validate_repo_format(repo):
            error_msg = (
                f"Invalid repository format: '{repo}'. "
                f"Expected format: 'owner/repo' (e.g., 'facebook/react')"
            )
            if self.verbose and self.cli_console:
                self.cli_console.print(f"[red]Error: {error_msg}[/red]")
            return {"error": error_msg, "success": False}

        # Log the operation
        if self.verbose and self.cli_console:
            self.cli_console.print(
                f"[blue]Querying GitHub repo:[/blue] {repo} "
                f"(operation: {operation})"
            )

        try:
            # Execute the appropriate operation
            assert self.scraper is not None, "Scraper not initialized"

            if operation == "structure":
                result = await self.scraper.read_wiki_structure_async(repo)

            elif operation == "contents":
                result = await self.scraper.read_wiki_contents_async(repo)

            elif operation == "query":
                if not question:
                    error_msg = "Question is required when operation='query'"
                    if self.verbose and self.cli_console:
                        self.cli_console.print(
                            f"[red]Error: {error_msg}[/red]"
                        )
                    return {"error": error_msg, "success": False}

                result = await self.scraper.ask_question_async(repo, question)

            else:
                error_msg = (
                    f"Unknown operation: '{operation}'. "
                    f"Valid operations: 'structure', 'contents', 'query'"
                )
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return {"error": error_msg, "success": False}

            # Process the result
            if result.get("success"):
                data = result.get("data", "")

                if self.verbose and self.cli_console:
                    self.cli_console.print(
                        f"[green]Successfully queried {repo}[/green]"
                    )

                # Return data directly for better integration
                return data
            else:
                error_msg = result.get("error", "Unknown error occurred")
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return {
                    "error": error_msg,
                    "success": False,
                    "repo": repo,
                    "operation": operation,
                }

        except Exception as e:
            error_msg = f"Error querying repository {repo}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if self.verbose and self.cli_console:
                self.cli_console.print(f"[red]Error: {error_msg}[/red]")
            return {
                "error": error_msg,
                "success": False,
                "repo": repo,
                "operation": operation,
            }

    def forward(
        self,
        repo: str,
        operation: str = "structure",
        question: Optional[str] = None,
    ) -> Union[str, Dict[str, Any]]:
        """
        Query a GitHub repository using DeepWiki.

        Args:
            repo: GitHub repository in format 'owner/repo'
            operation: Operation to perform ('structure', 'contents', 'query')
            question: Question to ask (required when operation='query')

        Returns:
            Query results as string or structured data
        """
        # Use synchronous methods directly if available
        self._ensure_scraper()

        # Validate repository format
        if not self._validate_repo_format(repo):
            error_msg = (
                f"Invalid repository format: '{repo}'. "
                f"Expected format: 'owner/repo' (e.g., 'facebook/react')"
            )
            if self.verbose and self.cli_console:
                self.cli_console.print(f"[red]Error: {error_msg}[/red]")
            return {"error": error_msg, "success": False}

        # Log the operation
        if self.verbose and self.cli_console:
            self.cli_console.print(
                f"[blue]Querying GitHub repo:[/blue] {repo} "
                f"(operation: {operation})"
            )

        try:
            # Execute the appropriate operation using sync methods
            assert self.scraper is not None, "Scraper not initialized"

            if operation == "structure":
                result = self.scraper.read_wiki_structure(repo)

            elif operation == "contents":
                result = self.scraper.read_wiki_contents(repo)

            elif operation == "query":
                if not question:
                    error_msg = "Question is required when operation='query'"
                    if self.verbose and self.cli_console:
                        self.cli_console.print(
                            f"[red]Error: {error_msg}[/red]"
                        )
                    return {"error": error_msg, "success": False}

                result = self.scraper.ask_question(repo, question)

            else:
                error_msg = (
                    f"Unknown operation: '{operation}'. "
                    f"Valid operations: 'structure', 'contents', 'query'"
                )
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return {"error": error_msg, "success": False}

            # Process the result
            if result.get("success"):
                data = result.get("data", "")

                if self.verbose and self.cli_console:
                    self.cli_console.print(
                        f"[green]Successfully queried {repo}[/green]"
                    )

                # Return data directly for better integration
                return data
            else:
                error_msg = result.get("error", "Unknown error occurred")
                if self.verbose and self.cli_console:
                    self.cli_console.print(f"[red]Error: {error_msg}[/red]")
                return {
                    "error": error_msg,
                    "success": False,
                    "repo": repo,
                    "operation": operation,
                }

        except Exception as e:
            error_msg = f"Error querying repository {repo}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if self.verbose and self.cli_console:
                self.cli_console.print(f"[red]Error: {error_msg}[/red]")
            return {
                "error": error_msg,
                "success": False,
                "repo": repo,
                "operation": operation,
            }

    def __del__(self):
        """Cleanup resources."""
        if self.scraper:
            self.scraper.disconnect()
        self._executor.shutdown(wait=False)

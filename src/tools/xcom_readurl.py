#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/xcom_readurl.py
# code style: PEP 8
# DEPRECATED: This tool is deprecated in favor of XcomDeepQATool.
# Use xcom_deep_qa tool for more advanced X.com search and analysis capabilities.

"""
Read X.com (Twitter) URL Agent Tool for DeepSearchAgents.

DEPRECATED: This tool is deprecated in favor of XcomDeepQATool.
Use xcom_deep_qa tool for more advanced X.com search and analysis capabilities.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import logging
from smolagents import Tool
from src.core.scraping.scraper_xcom import XcomScraper

# setup logging
logger = logging.getLogger(__name__)


def is_xcom_url(url: str) -> bool:
    """
    Check if the URL is an X.com (Twitter) URL.

    Args:
        url: URL to check

    Returns:
        True if it's an X.com/Twitter URL, False otherwise
    """
    return bool(re.match(r'https?://(www\.)?(x\.com|twitter\.com).*', url))


class XcomReadURLTool(Tool):
    """
    Reads the content of a given X.com (Twitter) URL using xAI's Live Search API
    and returns the processed content in a structured format.
    """
    name = "xcom_read_url"
    description = (
        "DEPRECATED: Use xcom_deep_qa tool instead. "
        "Reads the content of a given X.com (Twitter) URL using xAI's "
        "Live Search API and returns the processed content in a structured "
        "format. Can extract posts, profiles, and search results."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "The X.com (Twitter) URL to read content from.",
        },
        "output_format": {
            "type": "string",
            "description": "Desired output format (e.g., 'markdown', 'text', 'json').",
            "default": "markdown",
            "nullable": True,
        }
    }
    output_type = "string"  # returns the processed content

    def __init__(
        self,
        xai_api_key: Optional[str] = None,
        cli_console=None,
        verbose: bool = False  # for logging (optional)
    ):
        """
        Initialize XcomReadURLTool.

        Args:
            xai_api_key (str, optional): xAI API key. If None, load from
                environment variable XAI_API_KEY.
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.xai_api_key = xai_api_key

        # XcomScraper instance will be created when needed or setup()
        self.scraper: Optional[XcomScraper] = None
        self.cli_console = cli_console
        self.verbose = verbose

        # Thread pool for handling async operations
        self._executor = ThreadPoolExecutor(max_workers=10)

    def _ensure_scraper(self, output_format: str = "markdown"):
        """Ensure XcomScraper instance is created and configured correctly."""
        if self.scraper is None or self.scraper.output_format != output_format:
            self.scraper = XcomScraper(
                api_key=self.xai_api_key,
                output_format=output_format,
                timeout=120
            )

    def _run_in_thread(self, url, output_format):
        """
        Run scraper in a new thread to avoid blocking.

        Args:
            url: Target X.com URL
            output_format: Output format

        Returns:
            Content of the URL or error message
        """
        try:
            self._ensure_scraper(output_format)
            result = self.scraper.scrape(url)

            if result.success:
                return result.content
            else:
                return f"Error reading X.com URL: {result.error}"

        except Exception as e:
            error_msg = f"Unexpected error in XcomReadURLTool for {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def forward(
        self,
        url: str,
        output_format: Optional[str] = "markdown"
    ) -> str:
        """
        Reads the content of a given X.com URL using xAI's Live Search API
        and returns the processed content.

        DEPRECATED: This tool is deprecated. Use xcom_deep_qa tool instead
        for more advanced X.com search and analysis capabilities.

        Args:
            url (str): The X.com URL to read content from.
            output_format (str, optional): The output format. Default is 'markdown'.

        Returns:
            str: The processed content. If reading fails, return an error
                message string.
        """
        # Log deprecation warning
        logger.warning(
            "XcomReadURLTool is deprecated. Use XcomDeepQATool "
            "(xcom_deep_qa) instead for more advanced capabilities."
        )
        # Validate the URL is an X.com URL
        if not is_xcom_url(url):
            return (
                f"Error: URL '{url}' is not a valid X.com or Twitter URL. "
                "Please provide a URL starting with 'https://x.com/' or "
                "'https://twitter.com/'"
            )

        effective_output_format = (
            output_format if output_format is not None else "markdown"
        )

        # Logging
        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)
        log_func(f"[bold blue]Reading X.com URL[/bold blue]: {url}")

        try:
            # Run the scraper in a separate thread
            logger.info(f"Starting to read X.com URL: {url}")
            future = self._executor.submit(self._run_in_thread, url, effective_output_format)
            result = future.result(timeout=180)  # 3 minutes timeout

            # Log success
            content_length = len(result) if result else 0
            log_func(
                f"[bold green]X.com URL reading completed[/bold green]: {url} "
                f"(content length: {content_length})"
            )
            logger.info(f"X.com URL reading completed: {url} (length: {content_length})")

            return result

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error in XcomReadURLTool for {url}: {str(e)}"
            log_func(f"[bold red]{error_msg}[/bold red]")
            logger.error(error_msg, exc_info=True)
            return error_msg

    def setup(self):
        """Tool setup (if needed)."""
        # Initialization can be done on demand in the first forward call
        pass

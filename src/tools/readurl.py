#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/readurl.py
# code style: PEP 8

"""
Read URL Agent Tool for DeepSearchAgents.
"""

import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, TYPE_CHECKING
import logging
from smolagents import Tool

if TYPE_CHECKING:
    from rich.console import Console
from src.core.scraping.scraper import JinaReaderScraper

# setup logging
logger = logging.getLogger(__name__)


class ReadURLTool(Tool):
    """
    Reads the content of any given URLs using Jina Reader API and returns
    the processed content, typically in Markdown format.
    """
    name = "read_url"
    description = (
        "Reads the content of any given URLs using Jina Reader API and returns "
        "the processed content, typically in Markdown format. This tool "
        "response need some time to complete, when you call this tool, "
        "please wait for some time."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "The URL to read content from.",
        },
        "output_format": {
            "type": "string",
            "description": "Desired output format (e.g., 'markdown', 'text').",
            "default": "markdown",
            "nullable": True,
        }
    }
    output_type = "string"  # returns the processed content

    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        reader_model: str = "readerlm-v2",
        cli_console: Optional["Console"] = None,
        verbose: bool = False  # for logging (optional)
    ):
        """
        Initialize ReadURLTool.

        Args:
            jina_api_key (str, optional): Jina AI API key. If None, load from
                environment variable JINA_API_KEY.
            reader_model (str): The Jina Reader model to use.
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        if not self.jina_api_key:
            raise ValueError(
                "JINA_API_KEY is required but not provided "
                "or found in environment."
            )

        self.reader_model = reader_model
        # JinaReaderScraper instance will be created when needed
        # or setup()
        self.scraper: Optional[JinaReaderScraper] = None
        self.cli_console = cli_console
        self.verbose = verbose

        # Thread pool for handling async operations
        self._executor = ThreadPoolExecutor(max_workers=50)

        # Thread local storage for isolation
        self._local = threading.local()

    def _ensure_scraper(self, output_format: str = "markdown"):
        """Ensure JinaReaderScraper instance is created and
        configured correctly."""
        if self.scraper is None or self.scraper.output_format != output_format:
            self.scraper = JinaReaderScraper(
                api_key=self.jina_api_key,
                model=self.reader_model,
                output_format=output_format,
                # should read from config
                max_concurrent_requests=5,
                timeout=30000
            )

    async def _async_scrape(self, url: str, output_format: str) -> str:
        """
        Asynchronous implementation of URL scraping.

        Args:
            url (str): The URL to read content from.
            output_format (str): The output format.

        Returns:
            str: The scraped content or error message.
        """
        self._ensure_scraper(output_format)

        if not self.scraper:
            return f"Error: Scraper not initialized for URL {url}"

        try:
            logger.info(f"Starting to scrape URL: {url}")
            async with self.scraper as scraper_instance:
                result = await asyncio.wait_for(
                    scraper_instance.scrape(url),
                    timeout=1200
                )

            # check result
            if result and result.success:
                content = result.content or ""
                logger.info(f"Successfully scraped URL: {url} "
                            f"(length: {len(content)})")
                return content
            else:
                error_msg = f"Error reading URL {url}: "
                error_msg += f"{result.error if result else 'No result'}"
                logger.warning(error_msg)
                return error_msg
        except asyncio.TimeoutError:
            error_msg = f"Timeout error scraping URL {url} after 1200 seconds"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error in ReadURLTool for {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def _run_in_new_thread(self, url, output_format):
        """
        Run async task in a new thread, avoiding blocking the main thread.

        Args:
            url: target URL
            output_format: output format

        Returns:
            webpage content or error message
        """
        def thread_worker():
            # create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # run async task in new loop
                return loop.run_until_complete(
                    self._async_scrape(url, output_format)
                )
            finally:
                # ensure cleanup
                loop.close()

        # submit task to thread pool and wait for result
        future = self._executor.submit(thread_worker)
        try:
            # set a reasonable timeout
            return future.result(timeout=1200)
        except Exception as e:
            logger.error(f"Thread execution error for URL {url}: {str(e)}")
            return f"Error processing URL {url}: {str(e)}"

    def forward(
        self,
        url: str,
        output_format: Optional[str] = "markdown"
    ) -> str:
        """
        Reads the content of a given URL and returns the processed text.

        Completely redesigned implementation to avoid deadlocks and ensure
        consistent behavior in both sync and async environments.

        Args:
            url (str): The URL to read content from.
            output_format (str, optional): The output format. Default is
                'markdown'.

        Returns:
            str: The processed content. If reading fails, return an error
                message string.
        """
        effective_output_format = (
            output_format if output_format is not None else "markdown"
        )

        # logging
        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)
        log_func(f"[bold blue]Reading URL[/bold blue]: {url}")

        try:
            # always run in a new thread, avoiding any event loop pollution
            logger.info(f"Starting to read URL in thread: {url}")
            result = self._run_in_new_thread(url, effective_output_format)

            # log success result
            content_length = len(result) if result else 0
            log_func(
                f"[bold green]URL reading completed[/bold green]: {url} "
                f"(content length: {content_length})"
            )
            logger.info(f"URL reading completed: {url} "
                        f"(length: {content_length})")

            return result

        except Exception as e:
            # handle unexpected errors
            error_msg = f"Unexpected error in ReadURLTool for {url}: {str(e)}"
            log_func(f"[bold red]{error_msg}[/bold red]")
            logger.error(error_msg, exc_info=True)
            return error_msg

    def setup(self):
        """Tool setup (if needed)."""
        # initialization can be done on demand in the first forward call
        pass

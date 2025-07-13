#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/scraper_firecrawl.py
# code style: PEP 8

"""
Firecrawl Scraper implementation for web page extraction.

This module provides a scraper using the Firecrawl API to extract content
from web pages with JavaScript rendering support and various output formats.

API Docs: https://docs.firecrawl.dev/
Get your Firecrawl API key: https://firecrawl.dev/
"""

import os
import asyncio
import logging
from datetime import timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

try:
    from firecrawl import FirecrawlApp, AsyncFirecrawlApp
except ImportError:
    raise ImportError(
        "firecrawl-py is required for FirecrawlScraper. "
        "Install it with: pip install firecrawl-py"
    )

from .base import BaseScraper, RateLimiter
from .result import ExtractionResult

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT_SECONDS = 1200
DEFAULT_MAX_RETRIES = 1
DEFAULT_CRAWL_LIMIT = 10


class FirecrawlException(Exception):
    """Custom exception for Firecrawl API related errors"""
    pass


class FirecrawlScraper(BaseScraper):
    """
    Firecrawl-based web scraper implementation.

    Firecrawl provides powerful web scraping with JavaScript rendering,
    structured data extraction, and multiple output formats.

    Get your Firecrawl API key: https://firecrawl.dev/
    """

    # Rate limit configuration (based on Firecrawl's limits)
    _rate_limit_window = timedelta(minutes=1)
    _standard_rate_limit = 100  # 100 RPM for standard tier
    _premium_rate_limit = 1000  # Higher for premium tiers

    def __init__(
        self,
        api_key: Optional[str] = None,
        output_format: str = "markdown",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        enable_async: bool = False,
    ):
        """
        Initialize FirecrawlScraper.

        Args:
            api_key: Firecrawl API key. If None, load from FIRECRAWL_API_KEY
            output_format: Primary output format ('markdown', 'html', 'text')
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts when requests fail
            enable_async: Whether to use async Firecrawl client
        """
        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv('FIRECRAWL_API_KEY')
            if not api_key:
                raise FirecrawlException(
                    "No API key provided, and FIRECRAWL_API_KEY not found "
                    "in environment variables. Get your API key at: "
                    "https://firecrawl.dev/"
                )

        # Initialize rate limiter
        rate_limiter = RateLimiter(
            calls=self._standard_rate_limit,
            period=self._rate_limit_window
        )

        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            rate_limiter=rate_limiter
        )

        self.output_format = output_format
        self.enable_async = enable_async

        # Initialize Firecrawl client
        if enable_async:
            self.client = AsyncFirecrawlApp(api_key=self.api_key)
        else:
            self.client = FirecrawlApp(api_key=self.api_key)

    def _map_format(self, format_str: str) -> List[str]:
        """
        Map output format to Firecrawl formats list.

        Args:
            format_str: Requested format

        Returns:
            List of Firecrawl-compatible formats
        """
        format_mapping = {
            "markdown": ["markdown"],
            "html": ["html"],
            "text": ["markdown"],  # Firecrawl markdown is clean text
            "raw_html": ["raw_html"],
            "all": ["markdown", "html", "raw_html", "links"]
        }
        return format_mapping.get(format_str, ["markdown"])

    def scrape(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Scrape a single URL using Firecrawl.

        Args:
            url: The URL to scrape
            **kwargs: Additional parameters:
                - formats: List of output formats
                - screenshot: Whether to take screenshot
                - wait_for: CSS selector to wait for
                - timeout: Override default timeout
                - actions: Browser actions to perform

        Returns:
            ExtractionResult containing scraped content
        """
        # Apply retry logic
        return self.retry_with_backoff(
            self._scrape_internal,
            url,
            exceptions=(FirecrawlException, Exception),
            **kwargs
        )

    def _scrape_internal(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Internal scraping method without retry logic.

        Args:
            url: URL to scrape
            **kwargs: Scraping parameters

        Returns:
            ExtractionResult
        """
        try:
            # Prepare formats
            formats = kwargs.get(
                'formats', self._map_format(self.output_format)
            )

            # Prepare parameters
            params = {
                'formats': formats,
            }

            # Add optional parameters
            if kwargs.get('screenshot'):
                params['screenshot'] = True

            if kwargs.get('wait_for'):
                params['waitFor'] = kwargs['wait_for']

            if kwargs.get('actions'):
                params['actions'] = kwargs['actions']

            if kwargs.get('timeout'):
                params['timeout'] = kwargs['timeout']

            # Make the scraping request
            result = self.client.scrape_url(url, params=params)

            # Extract content based on primary format
            if self.output_format == "markdown" and result.get('markdown'):
                content = result['markdown']
            elif self.output_format == "html" and result.get('html'):
                content = result['html']
            elif self.output_format == "text" and result.get('markdown'):
                content = result['markdown']
            else:
                # Fallback to any available content
                content = (
                    result.get('markdown') or
                    result.get('html') or
                    result.get('rawHtml', '')
                )

            # Build metadata
            metadata = {
                'source': 'firecrawl',
                'url': url
            }

            # Add available metadata from result
            if result.get('metadata'):
                metadata.update(result['metadata'])

            if result.get('links'):
                metadata['links'] = result['links']

            if result.get('screenshot'):
                metadata['screenshot'] = result['screenshot']

            return self.standardize_result(
                url=url,
                content=content,
                success=True,
                metadata=metadata
            )

        except Exception as e:
            error_msg = str(e)

            # Handle specific error cases
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise FirecrawlException(
                    "Invalid API key. Get your API key at: "
                    "https://firecrawl.dev/"
                )
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise FirecrawlException(
                    "Rate limit exceeded. Consider upgrading your plan."
                )
            elif "timeout" in error_msg.lower():
                raise FirecrawlException(
                    f"Request timeout after {self.timeout} seconds: {url}"
                )
            else:
                raise FirecrawlException(
                    f"Error scraping {url}: {error_msg}"
                )

    async def scrape_async(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Async version of scrape.

        Args:
            url: URL to scrape
            **kwargs: Scraping parameters

        Returns:
            ExtractionResult
        """
        if not self.enable_async:
            # Run sync version in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.scrape,
                url,
                **kwargs
            )

        # Use async client
        return await self.async_retry_with_backoff(
            self._scrape_async_internal,
            url,
            exceptions=(FirecrawlException, Exception),
            **kwargs
        )

    async def _scrape_async_internal(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Internal async scraping method.

        Args:
            url: URL to scrape
            **kwargs: Scraping parameters

        Returns:
            ExtractionResult
        """
        # Similar to sync version but using async client
        # Note: Implementation depends on if firecrawl-py supports true async
        # For now, we'll use sync in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._scrape_internal,
            url,
            **kwargs
        )

    def crawl_website(
        self,
        url: str,
        limit: int = DEFAULT_CRAWL_LIMIT,
        **kwargs
    ) -> List[ExtractionResult]:
        """
        Crawl an entire website starting from the given URL.

        Args:
            url: Starting URL for crawl
            limit: Maximum number of pages to crawl
            **kwargs: Additional crawl parameters

        Returns:
            List of ExtractionResult objects
        """
        try:
            # Prepare crawl parameters
            params = {
                'limit': limit,
                'scrapeOptions': {
                    'formats': self._map_format(self.output_format)
                }
            }

            # Add optional parameters
            if kwargs.get('include_paths'):
                params['includes'] = kwargs['include_paths']

            if kwargs.get('exclude_paths'):
                params['excludes'] = kwargs['exclude_paths']

            # Start crawl
            crawl_result = self.client.crawl_url(
                url,
                params=params,
                wait_until_done=True,
                timeout=self.timeout
            )

            # Process results
            results = []
            if crawl_result.get('data'):
                for page_data in crawl_result['data']:
                    page_url = page_data.get('url', url)
                    content = (
                        page_data.get('markdown') or
                        page_data.get('html') or
                        page_data.get('rawHtml', '')
                    )

                    result = self.standardize_result(
                        url=page_url,
                        content=content,
                        success=True,
                        metadata=page_data.get('metadata', {})
                    )
                    results.append(result)

            return results

        except Exception as e:
            raise FirecrawlException(f"Error crawling {url}: {str(e)}")

    def map_website(
        self,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Map all URLs from a website.

        Args:
            url: Website URL to map
            **kwargs: Additional parameters

        Returns:
            Dictionary with 'urls' key containing list of discovered URLs
        """
        try:
            result = self.client.map_url(url)
            # Handle the response based on its type
            if hasattr(result, 'links'):
                return {
                    'urls': result.links if result.links else [],
                    'success': True
                }
            elif isinstance(result, dict):
                return {
                    'urls': result.get('links', []),
                    'success': result.get('status') == 'success'
                }
            else:
                return {
                    'urls': [],
                    'success': False,
                    'error': 'Unexpected response format'
                }
        except Exception as e:
            raise FirecrawlException(f"Error mapping {url}: {str(e)}")


# Convenience functions
def scrape_with_firecrawl(url: str, **kwargs) -> ExtractionResult:
    """
    Convenience function for one-off scraping with Firecrawl.

    Args:
        url: URL to scrape
        **kwargs: Scraping parameters

    Returns:
        ExtractionResult
    """
    scraper = FirecrawlScraper()
    return scraper.scrape(url, **kwargs)

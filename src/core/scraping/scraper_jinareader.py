#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/scraper_jinareader.py
# code style: PEP 8

"""
Jina Reader Scraper API Client for scraping web pages.
API Base URL: (r.jina.ai)
API Docs: @(https://github.com/jina-ai/meta-prompt/blob/main/v8.txt)
"""

import os
import aiohttp
import asyncio
import re
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dotenv import load_dotenv

from .base import BaseScraper, RateLimiter
from .result import ExtractionResult

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 1200
DEFAULT_MAX_RETRIES = 1
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 16
BACKOFF_MULTIPLIER = 2

# Valid return formats for Jina Reader API
VALID_RETURN_FORMATS = ["markdown", "html", "text", "screenshot", "pageshot"]
VALID_ENGINES = ["browser", "direct", "cf-browser-rendering"]
VALID_PROXY_OPTIONS = ["auto", "none"]  # Plus country codes


class JinaReaderException(Exception):
    """Custom exception for Jina Reader API related errors"""
    pass


class JinaReaderScraper(BaseScraper):
    """
    Implementation of a Scraper using Jina AI Reader API (r.jina.ai)
    to get webpage content. Can directly get processed Markdown or text
    content.

    Get your Jina AI API key for free: https://jina.ai/?sui=apikey
    """

    # Rate limit configuration
    _rate_limit_window = timedelta(minutes=1)
    _standard_rate_limit = 200  # 200 RPM for standard
    _premium_rate_limit = 2000  # 2k RPM for premium

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "readerlm-v2",
        output_format: str = "markdown",
        api_base_url: str = "https://r.jina.ai/",
        max_concurrent_requests: int = 2,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        use_eu_endpoint: bool = False,
    ):
        """
        Initialize JinaReaderScraper.

        Args:
            api_key: Jina AI API key. If None, load from JINA_API_KEY env
            model: The Reader model to use (default: readerlm-v2)
            output_format: Output format ('markdown', 'text', 'html', etc.)
            api_base_url: Base URL of the Jina Reader API
            max_concurrent_requests: Maximum number of concurrent requests
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts when requests fail
            use_eu_endpoint: Use EU endpoint for data processing in EU
        """
        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv('JINA_API_KEY')
            if not api_key:
                raise JinaReaderException(
                    "No API key provided, and JINA_API_KEY not found in "
                    "environment variables. Get your free API key at: "
                    "https://jina.ai/?sui=apikey"
                )

        # Validate output format
        if output_format not in VALID_RETURN_FORMATS:
            raise JinaReaderException(
                f"Invalid output_format. Must be one of: "
                f"{', '.join(VALID_RETURN_FORMATS)}"
            )

        # Initialize rate limiter with standard tier
        # (Will be updated to premium if detected)
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

        # Set base URL based on region
        if use_eu_endpoint:
            self.api_base_url = "https://eu.r.jina.ai"
        else:
            self.api_base_url = api_base_url.rstrip("/")

        self.model = model
        self.output_format = output_format
        self.max_concurrent_requests = max_concurrent_requests

        # Session management
        self._session = None
        self._semaphore = None

        # Rate limit tracking
        self._request_times: List[datetime] = []
        self._is_premium: Optional[bool] = None
        self._lock = threading.Lock()  # Thread safety for rate limit tracking

        # Default headers
        self._default_headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'X-Respond-With': model,
            'X-Return-Format': output_format,
        }

    def _build_headers(self, **kwargs) -> Dict[str, str]:
        """
        Build request headers with optional overrides.

        Args:
            **kwargs: Optional header overrides

        Returns:
            Complete headers dictionary
        """
        headers = self._default_headers.copy()

        # Map of parameter names to header names
        header_mapping = {
            'engine': 'X-Engine',
            'timeout_seconds': 'X-Timeout',
            'target_selector': 'X-Target-Selector',
            'wait_for_selector': 'X-Wait-For-Selector',
            'remove_selector': 'X-Remove-Selector',
            'with_links_summary': 'X-With-Links-Summary',
            'with_images_summary': 'X-With-Images-Summary',
            'with_generated_alt': 'X-With-Generated-Alt',
            'no_cache': 'X-No-Cache',
            'with_iframe': 'X-With-Iframe',
            'return_format': 'X-Return-Format',
            'token_budget': 'X-Token-Budget',
            'retain_images': 'X-Retain-Images',
            'respond_with': 'X-Respond-With',
            'set_cookie': 'X-Set-Cookie',
            'proxy_url': 'X-Proxy-Url',
            'proxy': 'X-Proxy',
            'locale': 'X-Locale',
            'robots_txt': 'X-Robots-Txt',
            'with_shadow_dom': 'X-With-Shadow-Dom',
            'base': 'X-Base',
            'md_heading_style': 'X-Md-Heading-Style',
            'md_hr': 'X-Md-Hr',
            'md_bullet_list_marker': 'X-Md-Bullet-List-Marker',
            'md_em_delimiter': 'X-Md-Em-Delimiter',
            'md_strong_delimiter': 'X-Md-Strong-Delimiter',
            'md_link_style': 'X-Md-Link-Style',
            'md_link_reference_style': 'X-Md-Link-Reference-Style',
            'no_gfm': 'X-No-Gfm',
        }

        # Apply header overrides
        for param, header_name in header_mapping.items():
            if param in kwargs and kwargs[param] is not None:
                value = kwargs[param]
                # Convert boolean values to strings
                if isinstance(value, bool):
                    value = 'true' if value else 'false'
                # Convert timeout to milliseconds string
                elif param == 'timeout_seconds':
                    value = str(int(value * 1000))
                else:
                    value = str(value)
                headers[header_name] = value

        # DNT is a special case
        if kwargs.get('dnt'):
            headers['DNT'] = '1'

        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get a reusable aiohttp session with proper configuration"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool limit
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache timeout
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self._session

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get a concurrency control semaphore"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self._semaphore

    async def _close_session(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _clean_error_response(
        self,
        response_text: str,
        status_code: int
    ) -> str:
        """
        Clean up error response, especially HTML content.

        Args:
            response_text: Raw response text
            status_code: HTTP status code

        Returns:
            Cleaned error message
        """
        # Handle 524 CloudFlare timeout specifically
        if status_code == 524 and "524: A timeout occurred" in response_text:
            return "CloudFlare timeout error (524)"

        # Check if response is HTML
        if (response_text.startswith("<!DOCTYPE html") or
                response_text.startswith("<html")):
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>',
                                    response_text, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'\\s+', ' ', title)
                if title:
                    return title

            # Look for error code
            error_match = re.search(r'Error code (\\d+)', response_text)
            if error_match:
                return f"Error code {error_match.group(1)}"

            # Try to extract h1 or h2 headers
            header_match = re.search(r'<h[12]>(.*?)</h[12]>',
                                     response_text, re.IGNORECASE | re.DOTALL)
            if header_match:
                header = header_match.group(1).strip()
                header = re.sub(r'\\s+', ' ', header)
                if header:
                    return header

            # Return generic HTML error message
            return "HTML error page (content omitted)"

        # For non-HTML responses, limit length
        max_length = 200
        if len(response_text) > max_length:
            return response_text[:max_length] + "..."
        return response_text

    def _track_request(self):
        """Track a request for rate limiting."""
        current_time = datetime.now()
        with self._lock:
            self._request_times.append(current_time)

            # Clean old entries
            window_start = current_time - self._rate_limit_window
            self._request_times = [
                t for t in self._request_times if t > window_start
            ]

    def _check_premium_status(self) -> bool:
        """
        Check if the API key has premium access.

        Returns:
            True if premium, False otherwise
        """
        if self._is_premium is not None:
            return self._is_premium

        # Check rate limit by examining recent request history
        current_time = datetime.now()
        window_start = current_time - self._rate_limit_window

        # Count requests in the current window
        with self._lock:
            recent_requests = [
                t for t in self._request_times if t > window_start
            ]

        # If we've made more than standard limit without errors, likely premium
        self._is_premium = len(recent_requests) > self._standard_rate_limit

        # Update rate limiter if premium
        if self._is_premium and self.rate_limiter:
            self.rate_limiter.calls = self._premium_rate_limit

        return self._is_premium

    async def scrape_async(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Use Jina Reader API to scrape a single URL.

        Args:
            url: The URL to scrape
            **kwargs: Optional parameters for headers (see _build_headers)

        Returns:
            ExtractionResult: An object containing the scraping result
        """
        # Track request for rate limiting
        self._track_request()

        # Build headers
        headers = self._build_headers(**kwargs)

        # Get session and semaphore
        session = await self._get_session()
        semaphore = await self._get_semaphore()

        # Make request with semaphore for concurrency control
        async with semaphore:
            # Construct full URL
            full_url = f"{self.api_base_url}/{url}"

            try:
                async with session.get(
                    full_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        # Try to parse as JSON first
                        try:
                            data = await response.json()
                            if data.get("code") == 200 and data.get("data"):
                                content_data = data["data"]
                                content = content_data.get("content", "")

                                # Extract metadata
                                metadata = {}
                                for key in [
                                    "title", "description", "url",
                                    "images", "links", "usage"
                                ]:
                                    if key in content_data:
                                        metadata[key] = content_data[key]

                                return self.standardize_result(
                                    url=url,
                                    content=content,
                                    success=True,
                                    metadata=metadata
                                )
                            else:
                                # API returned error
                                error_msg = data.get(
                                    "message",
                                    f"API error: {data}"
                                )
                                raise JinaReaderException(error_msg)
                        except (ValueError, KeyError) as e:
                            # If not JSON, try to get raw text content
                            content = await response.text()
                            return self.standardize_result(
                                url=url,
                                content=content,
                                success=True,
                                metadata={"format": "raw_text"}
                            )
                    else:
                        # Handle error responses
                        error_text = await response.text()
                        cleaned_error = self._clean_error_response(
                            error_text, response.status
                        )

                        if response.status == 401:
                            raise JinaReaderException(
                                "Invalid API key. Get your free API key at: "
                                "https://jina.ai/?sui=apikey"
                            )
                        elif response.status == 429:
                            raise JinaReaderException(
                                "Rate limit exceeded. Consider upgrading to "
                                "premium for higher limits."
                            )
                        elif response.status == 422:
                            raise JinaReaderException(
                                f"Invalid request parameters: {cleaned_error}"
                            )
                        elif response.status == 524:
                            raise JinaReaderException(
                                f"CloudFlare timeout (524) for URL: {url}. "
                                "The origin server took too long to respond."
                            )
                        else:
                            raise JinaReaderException(
                                f"HTTP {response.status}: {cleaned_error}"
                            )

            except asyncio.TimeoutError:
                raise JinaReaderException(
                    f"Request timeout after {self.timeout} seconds: {url}"
                )
            except aiohttp.ClientError as e:
                raise JinaReaderException(
                    f"Network error while scraping {url}: {str(e)}"
                )

    async def _scrape_with_retry(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Sync wrapper for scrape_async with retry logic.

        Args:
            url: The URL to scrape
            **kwargs: Optional parameters for headers

        Returns:
            ExtractionResult: An object containing the scraping result
        """
        return await self.async_retry_with_backoff(
            self.scrape_async,
            url,
            exceptions=(
                JinaReaderException,
                asyncio.TimeoutError,
                aiohttp.ClientError
            ),
            **kwargs
        )

    def scrape(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Synchronous scraping method.

        Args:
            url: The URL to scrape
            **kwargs: Optional parameters for headers

        Returns:
            ExtractionResult: An object containing the scraping result
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from async context, create new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._scrape_with_retry(url, **kwargs)
                    )
                    return future.result()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._scrape_with_retry(url, **kwargs)
        )

    async def scrape_many(
        self,
        urls: List[str],
        batch_size: Optional[int] = None,
        **kwargs
    ) -> Dict[str, ExtractionResult]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            batch_size: Optional batch size for processing
            **kwargs: Additional parameters passed to scrape

        Returns:
            Dictionary mapping URLs to ExtractionResults
        """
        return await self.scrape_many_async(
            urls,
            batch_size=batch_size,
            **kwargs
        )

    def simple_scrape(self, url: str, **kwargs) -> str:
        """
        Simple synchronous scrape that returns just the content string.

        Args:
            url: URL to scrape
            **kwargs: Optional parameters

        Returns:
            Content string or empty string on error
        """
        try:
            result = self.scrape(url, engine="direct", **kwargs)
            return result.content or ""
        except Exception as e:
            logger.error(f"Error in simple_scrape: {str(e)}")
            return ""

    async def validate_api_key(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate the API key and get account information.

        Returns:
            Tuple of (is_valid, account_info)
            account_info contains: is_premium, rate_limit, error (if any)
        """
        try:
            # Make a minimal request to check API key
            await self.scrape_async(
                "https://example.com",
                no_cache=True,
                respond_with="no-content"
            )

            # If we got here, the API key is valid
            is_premium = self._check_premium_status()
            rate_limit = (
                self._premium_rate_limit if is_premium
                else self._standard_rate_limit
            )

            return True, {
                "is_premium": is_premium,
                "rate_limit": rate_limit,
                "rate_limit_unit": "requests per minute"
            }
        except JinaReaderException as e:
            if "Invalid API key" in str(e):
                return False, {"error": "Invalid API key"}
            elif "Rate limit exceeded" in str(e):
                # Valid key but rate limited
                return True, {
                    "is_premium": False,
                    "rate_limit": self._standard_rate_limit,
                    "rate_limit_unit": "requests per minute",
                    "error": "Rate limited"
                }
            else:
                return False, {"error": str(e)}
        except Exception as e:
            return False, {"error": f"Unexpected error: {str(e)}"}

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        if self.rate_limiter:
            status = self.rate_limiter.get_status()
            # Add premium status
            status["is_premium"] = self._check_premium_status()
            return status
        else:
            return {
                "rate_limit": "unlimited",
                "requests_made": 0,
                "requests_remaining": "unlimited"
            }

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()


# Convenience functions for backward compatibility and one-off usage
def scrape(url: str, **kwargs) -> ExtractionResult:
    """
    Convenience function for scraping a single URL with Jina Reader.

    Args:
        url: URL to scrape
        **kwargs: Optional parameters

    Returns:
        ExtractionResult
    """
    scraper = JinaReaderScraper()
    return scraper.scrape(url, **kwargs)


async def scrape_async(url: str, **kwargs) -> ExtractionResult:
    """
    Async convenience function for scraping with Jina Reader.

    Args:
        url: URL to scrape
        **kwargs: Optional parameters

    Returns:
        ExtractionResult
    """
    scraper = JinaReaderScraper()
    return await scraper.scrape_async(url, **kwargs)


async def scrape_multiple_async(
    urls: List[str],
    **kwargs
) -> Dict[str, ExtractionResult]:
    """
    Scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape
        **kwargs: Optional parameters

    Returns:
        Dictionary mapping URLs to ExtractionResults
    """
    scraper = JinaReaderScraper()
    return await scraper.scrape_many(urls, **kwargs)

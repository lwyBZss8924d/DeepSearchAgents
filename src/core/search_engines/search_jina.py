#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_jina.py
# code style: PEP 8

"""
Jina AI Web Search API Client for "HybridSearchEngine"
API Base URL: (s.jina.ai)
API Docs: @(.cursor/rules/jina-ai-api-rules.mdc)
s.jina.ai API Examp Request & Response: @(tests/test_jina/jina_search/examp.txt)
"""

import os
import logging
import asyncio
import time
import threading
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, cast
import requests
import aiohttp
from dotenv import load_dotenv

from .base import BaseSearchClient, RateLimiter
from .utils.search_token_counter import SearchUsage, count_search_tokens

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_PER_QUERY = 100
MIN_RESULTS_PER_QUERY = 1
VALID_RETURN_FORMATS = ["markdown", "html", "text", "screenshot", "pageshot"]
VALID_ENGINES = ["direct", "browser", "cf-browser-rendering"]
VALID_PROXY_OPTIONS = ["auto", "none"]  # Plus country codes
DEFAULT_TIMEOUT_SECONDS = 1000
DEFAULT_MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 16
BACKOFF_MULTIPLIER = 2


class JinaSearchException(Exception):
    """Custom exception for Jina Search API related errors"""

    pass


class JinaSearchClient(BaseSearchClient):
    """
    Client for Jina AI Search API that provides web search capabilities
    optimized for LLMs and downstream applications.

    Rate Limits:
    - s.jina.ai: 40 RPM (400 RPM with premium key)
    - For high-volume usage, consider upgrading to premium

    Get your Jina AI API key for free: https://jina.ai/?sui=apikey
    """

    # Rate limit tracking
    _rate_limit_window = timedelta(minutes=1)
    _standard_rate_limit = 40
    _premium_rate_limit = 400

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://s.jina.ai/",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize the Jina Search Client.

        Args:
            api_key: Jina AI API key (defaults to JINA_API_KEY from env)
            base_url: Base URL for Jina Search API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv("JINA_API_KEY")
            if not api_key:
                raise JinaSearchException(
                    "No API key provided, and JINA_API_KEY not found in "
                    "environment variables. Get your free API key at: "
                    "https://jina.ai/?sui=apikey"
                )

        # Initialize base class with rate limiter for standard tier
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

        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Rate limit tracking
        self._request_times: List[datetime] = []
        self._is_premium: Optional[bool] = None
        self._lock = threading.Lock()  # Thread safety for rate limit tracking

    def _clean_error_response(self, response_text: str, status_code: int) -> str:
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
                title = re.sub(r'\s+', ' ', title)
                if title:
                    return title

            # Look for error code
            error_match = re.search(r'Error code (\d+)', response_text)
            if error_match:
                return f"Error code {error_match.group(1)}"

            # Try to extract h1 or h2 headers
            header_match = re.search(r'<h[12]>(.*?)</h[12]>', 
                                     response_text, re.IGNORECASE | re.DOTALL)
            if header_match:
                header = header_match.group(1).strip()
                header = re.sub(r'\s+', ' ', header)
                if header:
                    return header

            # Return generic HTML error message
            return "HTML error page (content omitted)"

        # For non-HTML responses, limit length
        max_length = 40000
        if len(response_text) > max_length:
            return response_text[:max_length] + "..."
        return response_text

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        num: int = 10,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        no_cache: bool = True,
        return_format: str = "markdown",
        with_links: bool = True,
        with_images: bool = True,
        retain_images: bool = False,
        with_generated_alt: bool = False,
        with_favicons: bool = False,
        timeout_seconds: Optional[int] = None,
        engine: str = "direct",
        locale: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_url: Optional[str] = None,
        set_cookie: Optional[str] = None,
        respond_with: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for information using Jina AI Search API.

        Args:
            query: Search query string
            domain: Optional domain to limit search to (e.g., "arxiv.org")
            num: Maximum number of results to return
            gl: Country code for search (e.g., "us", "cn")
            hl: Language code for search (e.g., "en", "zh")
            location: Location to originate search from
            page: Page number for pagination
            no_cache: Whether to bypass cache for real-time data
            return_format: Format of returned content
                ("markdown", "html", "text", "screenshot", "pageshot")
            with_links: Whether to include links summary
            with_images: Whether to include images summary
            retain_images: Remove all images from the response in content
                (False removes all images)
            with_generated_alt: Generate alt text for images without
                captions (adds 'Image [idx]: [caption]')
            with_favicons: Include favicon of each URL in the search
                results
            timeout_seconds: Maximum time to wait for webpage loading
                (overrides default)
            engine: Engine to use ("direct" for speed, "browser" for quality)
            locale: Browser locale to render the page
                (e.g., "en-US", "de-DE")
            proxy: Country code for location-based proxy server
                ("auto", "none", or country code)
            proxy_url: Custom proxy URL to access pages
            set_cookie: Custom cookie settings for authentication
            respond_with: Use "no-content" to exclude page content from
                response

        Returns:
            Dictionary containing search results with title, url,
                content, and usage info
        """
        # Input validation
        if not query or not query.strip():
            raise JinaSearchException("Search query cannot be empty")

        if num < MIN_RESULTS_PER_QUERY or num > MAX_RESULTS_PER_QUERY:
            raise JinaSearchException(
                f"Number of results must be between "
                f"{MIN_RESULTS_PER_QUERY} and {MAX_RESULTS_PER_QUERY}"
            )

        if page < 1:
            raise JinaSearchException("Page number must be >= 1")

        # Validate return format
        if return_format not in VALID_RETURN_FORMATS:
            raise JinaSearchException(
                f"Invalid return_format. Must be one of: "
                f"{', '.join(VALID_RETURN_FORMATS)}")

        # Validate engine
        if engine not in VALID_ENGINES:
            raise JinaSearchException(
                f"Invalid engine. Must be one of: {', '.join(VALID_ENGINES)}")

        # Validate proxy if provided
        if proxy and proxy not in VALID_PROXY_OPTIONS and len(proxy) != 2:
            raise JinaSearchException(
                "Invalid proxy. Must be 'auto', 'none', or a 2-letter "
                "country code")

        # Prepare request payload
        payload = {"q": query, "num": num, "page": page}

        # Add optional parameters
        if gl:
            payload["gl"] = gl
        if hl:
            payload["hl"] = hl
        if location:
            payload["location"] = location

        # Prepare headers
        headers = self.headers.copy()

        # Add optional headers
        if domain:
            headers["X-Site"] = f"https://{domain}"
        if no_cache:
            headers["X-No-Cache"] = "true"
        if return_format != "markdown":
            headers["X-Return-Format"] = return_format
        if with_links:
            headers["X-With-Links-Summary"] = "true"
        if with_images:
            headers["X-With-Images-Summary"] = "true"
        if not retain_images:
            headers["X-Retain-Images"] = "none"
        if with_generated_alt:
            headers["X-With-Generated-Alt"] = "true"
        if with_favicons:
            headers["X-With-Favicons"] = "true"
        if timeout_seconds:
            headers["X-Timeout"] = str(timeout_seconds)
        if engine != "direct":
            headers["X-Engine"] = engine
        if locale:
            headers["X-Locale"] = locale
        if proxy:
            headers["X-Proxy"] = proxy
        if proxy_url:
            headers["X-Proxy-Url"] = proxy_url
        if set_cookie:
            headers["X-Set-Cookie"] = set_cookie
        if respond_with:
            headers["X-Respond-With"] = respond_with

        # Track request for rate limiting
        self._track_request()

        # Make API request with retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url, headers=headers, json=payload,
                    timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()

                    # Check response format
                    if data.get("code") == 200 and "data" in data:
                        return self._process_search_results(data, query)
                    else:
                        error_msg = data.get("message", "Unknown error")
                        raise JinaSearchException(f"API error: {error_msg}")

                else:
                    # Handle specific HTTP status codes
                    if response.status_code == 401:
                        raise JinaSearchException(
                            "Invalid API key. Get your free API key at: "
                            "https://jina.ai/?sui=apikey"
                        )
                    elif response.status_code == 429:
                        raise JinaSearchException(
                            "Rate limit exceeded. Consider upgrading to "
                            "premium for higher limits."
                        )
                    elif response.status_code == 422:
                        try:
                            error_data = response.json()
                            error_detail = error_data.get(
                                "detail", "Validation error")
                            raise JinaSearchException(
                                f"Invalid request: {error_detail}")
                        except (ValueError, KeyError):
                            cleaned_text = self._clean_error_response(
                                response.text, response.status_code
                            )
                            raise JinaSearchException(
                                f"Invalid request parameters: {cleaned_text}")
                    else:
                        cleaned_text = self._clean_error_response(
                            response.text, response.status_code
                        )
                        error_msg = f"HTTP {response.status_code}: {cleaned_text}"
                        if attempt < self.max_retries - 1:
                            logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                            # Exponential backoff
                            backoff_time = min(
                                INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS
                            )
                            logger.info(f"Retrying after {backoff_time} seconds...")
                            time.sleep(backoff_time)
                            continue
                        else:
                            raise JinaSearchException(f"Request failed: {error_msg}")

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request timeout (attempt {attempt + 1}), retrying...")
                    # Exponential backoff
                    backoff_time = min(INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS)
                    time.sleep(backoff_time)
                    continue
                else:
                    raise JinaSearchException(f"Request timed out after {self.timeout} seconds")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request error (attempt {attempt + 1}): {str(e)}")
                    # Exponential backoff
                    backoff_time = min(INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS)
                    time.sleep(backoff_time)
                    continue
                else:
                    raise JinaSearchException(f"Request failed: {str(e)}")

        # This should not be reached due to the retry logic
        raise JinaSearchException("Maximum retries exceeded")

    def _process_search_results(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Process the raw API response into standardized format.

        Args:
            data: Raw API response data
            query: Original search query

        Returns:
            Processed search results
        """
        results = []
        total_tokens = 0
        native_usage = None

        # Check for top-level usage data (if Jina provides it)
        if "usage" in data:
            usage_data = data["usage"]
            if isinstance(usage_data, dict):
                native_usage = {
                    "total_tokens": usage_data.get("total_tokens", usage_data.get("tokens", 0)),
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens": usage_data.get("completion_tokens", usage_data.get("tokens", 0)),
                }

        # Process search results
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "description": item.get("description", ""),
                }

                # Accumulate per-item usage if available
                if "usage" in item and isinstance(item["usage"], dict):
                    item_tokens = item["usage"].get("tokens", 0)
                    total_tokens += item_tokens

                # Add links and images if available
                if "links" in item:
                    result["links"] = item["links"]
                if "images" in item:
                    result["images"] = item["images"]

                # Add favicon if available
                if "favicon" in item:
                    result["favicon"] = item["favicon"]

                results.append(result)

        # If we have native usage data, use it; otherwise count tokens
        if native_usage:
            usage = SearchUsage(
                total_tokens=native_usage["total_tokens"],
                prompt_tokens=native_usage["prompt_tokens"],
                completion_tokens=native_usage["completion_tokens"],
                counting_method="native",
            )
        else:
            # Use unified token counting
            usage = count_search_tokens(
                query=query,
                response=data,
                provider="jina",
                native_usage=(
                    {
                        "total_tokens": total_tokens,
                        "prompt_tokens": 0,  # Jina doesn't separate prompt tokens
                        "completion_tokens": total_tokens,
                    }
                    if total_tokens > 0
                    else None
                ),
            )

        # Return processed results
        return {
            "results": results,
            "query": query,
            "total_results": len(results),
            "usage": usage,
        }

    def search_arxiv(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search specifically within arXiv domain.

        Args:
            query: Search query
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            Search results from arXiv
        """
        return self.search(query=query, domain="arxiv.org", num=num, **kwargs)

    def simple_search(self, query: str, num: int = 5) -> List[str]:
        """
        Simple search that returns just the content strings.

        Args:
            query: Search query
            num: Number of results (default: 5 for faster response)

        Returns:
            List of content strings
        """
        response = self.search(query=query, num=num, engine="direct")
        return [item.get("content", "") for item in response.get("results", [])]

    def search_with_content(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Search and return results in the format expected by other tools.

        Args:
            query: Search query
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            List of search results with title, url, content
        """
        response = self.search(query=query, num=num, **kwargs)

        # Convert to the format expected by other tools
        results = []
        for item in response.get("results", []):
            results.append(
                {"title": item.get("title", ""), "url": item.get("url", ""), "content": item.get("content", "")}
            )

        return results

    def validate_api_key(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate the API key and get account information.

        Returns:
            Tuple of (is_valid, account_info)
            account_info contains: is_premium, rate_limit, error (if any)
        """
        try:
            # Make a minimal request to check API key
            _ = self.search(query="test", num=1, no_cache=True, respond_with="no-content")

            # If we got here, the API key is valid
            # Assume premium if we can make many requests without rate limiting
            is_premium = self._check_premium_status()
            rate_limit = self._premium_rate_limit if is_premium else self._standard_rate_limit

            return True, {"is_premium": is_premium, "rate_limit": rate_limit, "rate_limit_unit": "requests per minute"}
        except JinaSearchException as e:
            if "Invalid API key" in str(e):
                return False, {"error": "Invalid API key"}
            elif "Rate limit exceeded" in str(e):
                # Valid key but rate limited
                return True, {
                    "is_premium": False,
                    "rate_limit": self._standard_rate_limit,
                    "rate_limit_unit": "requests per minute",
                    "error": "Rate limited",
                }
            else:
                return False, {"error": str(e)}
        except Exception as e:
            return False, {"error": f"Unexpected error: {str(e)}"}

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
            recent_requests = [t for t in self._request_times if t > window_start]

        # If we've made more than standard limit without errors, likely premium
        self._is_premium = len(recent_requests) > self._standard_rate_limit
        return self._is_premium

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        current_time = datetime.now()
        window_start = current_time - self._rate_limit_window

        # Clean old request times
        with self._lock:
            self._request_times = [t for t in self._request_times if t > window_start]
            requests_made = len(self._request_times)
            oldest_request = min(self._request_times) if self._request_times else None

        # Get rate limit based on account type
        is_premium = self._check_premium_status()
        rate_limit = self._premium_rate_limit if is_premium else self._standard_rate_limit

        # Calculate remaining requests
        requests_remaining = max(0, rate_limit - requests_made)

        # Calculate reset time
        if oldest_request:
            reset_time = oldest_request + self._rate_limit_window
            seconds_until_reset = max(0, (reset_time - current_time).total_seconds())
        else:
            seconds_until_reset = 0

        return {
            "is_premium": is_premium,
            "rate_limit": rate_limit,
            "requests_made": requests_made,
            "requests_remaining": requests_remaining,
            "reset_in_seconds": int(seconds_until_reset),
            "window_minutes": int(self._rate_limit_window.total_seconds() / 60),
        }

    def _track_request(self):
        """
        Track a request for rate limiting.
        """
        current_time = datetime.now()
        with self._lock:
            self._request_times.append(current_time)

            # Clean old entries
            window_start = current_time - self._rate_limit_window
            self._request_times = [t for t in self._request_times if t > window_start]

    async def search_async(
        self,
        query: str,
        domain: Optional[str] = None,
        num: int = 10,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        no_cache: bool = True,
        return_format: str = "markdown",
        with_links: bool = True,
        with_images: bool = True,
        retain_images: bool = False,
        with_generated_alt: bool = False,
        with_favicons: bool = False,
        timeout_seconds: Optional[int] = None,
        engine: str = "direct",
        locale: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_url: Optional[str] = None,
        set_cookie: Optional[str] = None,
        respond_with: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Async version of search method for concurrent requests.

        See search() method for parameter documentation.
        """
        # Input validation (same as sync version)
        if not query or not query.strip():
            raise JinaSearchException("Search query cannot be empty")

        if num < MIN_RESULTS_PER_QUERY or num > MAX_RESULTS_PER_QUERY:
            raise JinaSearchException(
                f"Number of results must be between "
                f"{MIN_RESULTS_PER_QUERY} and {MAX_RESULTS_PER_QUERY}"
            )

        if page < 1:
            raise JinaSearchException("Page number must be >= 1")

        # Validate return format
        if return_format not in VALID_RETURN_FORMATS:
            raise JinaSearchException(
                f"Invalid return_format. Must be one of: "
                f"{', '.join(VALID_RETURN_FORMATS)}")

        # Validate engine
        if engine not in VALID_ENGINES:
            raise JinaSearchException(
                f"Invalid engine. Must be one of: {', '.join(VALID_ENGINES)}")

        # Validate proxy if provided
        if proxy and proxy not in VALID_PROXY_OPTIONS and len(proxy) != 2:
            raise JinaSearchException(
                "Invalid proxy. Must be 'auto', 'none', or a 2-letter "
                "country code")

        # Prepare request payload
        payload = {"q": query, "num": num, "page": page}

        # Add optional parameters
        if gl:
            payload["gl"] = gl
        if hl:
            payload["hl"] = hl
        if location:
            payload["location"] = location

        # Prepare headers
        headers = self.headers.copy()

        # Add optional headers
        if domain:
            headers["X-Site"] = f"https://{domain}"
        if no_cache:
            headers["X-No-Cache"] = "true"
        if return_format != "markdown":
            headers["X-Return-Format"] = return_format
        if with_links:
            headers["X-With-Links-Summary"] = "true"
        if with_images:
            headers["X-With-Images-Summary"] = "true"
        if not retain_images:
            headers["X-Retain-Images"] = "none"
        if with_generated_alt:
            headers["X-With-Generated-Alt"] = "true"
        if with_favicons:
            headers["X-With-Favicons"] = "true"
        if timeout_seconds:
            headers["X-Timeout"] = str(timeout_seconds)
        if engine != "direct":
            headers["X-Engine"] = engine
        if locale:
            headers["X-Locale"] = locale
        if proxy:
            headers["X-Proxy"] = proxy
        if proxy_url:
            headers["X-Proxy-Url"] = proxy_url
        if set_cookie:
            headers["X-Set-Cookie"] = set_cookie
        if respond_with:
            headers["X-Respond-With"] = respond_with

        # Track request for rate limiting
        self._track_request()

        # Async request with retry logic
        timeout = aiohttp.ClientTimeout(total=timeout_seconds or self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(self.base_url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Check response format
                            if data.get("code") == 200 and "data" in data:
                                return self._process_search_results(data, query)
                            else:
                                error_msg = data.get("message", "Unknown error")
                                raise JinaSearchException(f"API error: {error_msg}")
                        else:
                            # Handle specific HTTP status codes
                            if response.status == 401:
                                raise JinaSearchException(
                                    "Invalid API key. Get your free API key at: "
                            "https://jina.ai/?sui=apikey"
                                )
                            elif response.status == 429:
                                raise JinaSearchException(
                                    "Rate limit exceeded. Consider upgrading to "
                            "premium for higher limits."
                                )
                            elif response.status == 422:
                                try:
                                    error_data = await response.json()
                                    error_detail = error_data.get(
                                "detail", "Validation error")
                                    raise JinaSearchException(
                                f"Invalid request: {error_detail}")
                                except (ValueError, KeyError):
                                    text = await response.text()
                                    cleaned_text = self._clean_error_response(
                                        text, response.status
                                    )
                                    raise JinaSearchException(f"Invalid request parameters: {cleaned_text}")
                            else:
                                text = await response.text()
                                cleaned_text = self._clean_error_response(
                                    text, response.status
                                )
                                error_msg = f"HTTP {response.status}: {cleaned_text}"
                                if attempt < self.max_retries - 1:
                                    logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                                    # Exponential backoff
                                    backoff_time = min(
                                        INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS
                                    )
                                    logger.info(f"Retrying after {backoff_time} seconds...")
                                    await asyncio.sleep(backoff_time)
                                    continue
                                else:
                                    raise JinaSearchException(f"Request failed: {error_msg}")

                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request timeout (attempt {attempt + 1}), retrying...")
                        # Exponential backoff
                        backoff_time = min(INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS)
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        raise JinaSearchException(f"Request timed out after {self.timeout} seconds")
                except aiohttp.ClientError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request error (attempt {attempt + 1}): {str(e)}")
                        # Exponential backoff
                        backoff_time = min(INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt), MAX_BACKOFF_SECONDS)
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        raise JinaSearchException(f"Request failed: {str(e)}")

        # This should not be reached due to the retry logic
        raise JinaSearchException("Maximum retries exceeded")

    async def search_arxiv_async(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Async search specifically within arXiv domain.

        Args:
            query: Search query
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            Search results from arXiv
        """
        return await self.search_async(query=query, domain="arxiv.org", num=num, **kwargs)

    async def search_multiple_async(self, queries: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Perform multiple searches concurrently.

        Args:
            queries: List of search queries
            **kwargs: Parameters to pass to each search

        Returns:
            List of search results for each query

        Raises:
            JinaSearchException: If any search fails
        """
        tasks = [self.search_async(query=q, **kwargs) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for exceptions and raise if any
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise JinaSearchException(f"Search for query '{queries[i]}' failed: {result}")

        # At this point, all results are Dict[str, Any] since exceptions have been handled
        return cast(List[Dict[str, Any]], results)


# Convenience functions for backward compatibility
def search(query: str, domain: Optional[str] = None, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for searching with Jina AI.

    Args:
        query: Search query
        domain: Optional domain to limit search
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        Search results
    """
    client = JinaSearchClient()
    return client.search(query=query, domain=domain, num=num, **kwargs)


def search_arxiv(query: str, num: int = 10) -> Dict[str, Any]:
    """
    Convenience function for searching arXiv.

    Args:
        query: Search query
        num: Number of results

    Returns:
        arXiv search results
    """
    client = JinaSearchClient()
    return client.search_arxiv(query=query, num=num)


# Async convenience functions
async def search_async(query: str, domain: Optional[str] = None, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Async convenience function for searching with Jina AI.

    Args:
        query: Search query
        domain: Optional domain to limit search
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        Search results
    """
    client = JinaSearchClient()
    return await client.search_async(query=query, domain=domain, num=num, **kwargs)


async def search_arxiv_async(query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Async convenience function for searching arXiv.

    Args:
        query: Search query
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        arXiv search results
    """
    client = JinaSearchClient()
    return await client.search_arxiv_async(query=query, num=num, **kwargs)


async def search_multiple_async(queries: List[str], **kwargs) -> List[Dict[str, Any]]:
    """
    Perform multiple searches concurrently.

    Args:
        queries: List of search queries
        **kwargs: Parameters to pass to each search

    Returns:
        List of search results
    """
    client = JinaSearchClient()
    return await client.search_multiple_async(queries=queries, **kwargs)

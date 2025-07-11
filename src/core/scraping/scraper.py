#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/scraper.py
# code style: PEP 8

"""
Jina Reader Scraper API for scraping web pages.
"""

import os
import aiohttp
import asyncio
import random
import re
from typing import Optional, Dict, List
from dotenv import load_dotenv
from .result import ExtractionResult


class JinaReaderScraper:
    """
    Implementation of a Scraper using Jina AI Reader API (r.jina.ai)
    to get webpage content. Can directly get processed Markdown or text
    content.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        # Default is ReaderLM v2 model & Use r.jina.ai
        # to read a URL and fetch its content
        model: str = "readerlm-v2",
        output_format: str = "markdown",  # or "markdown", "text", "html"
        api_base_url: str = "https://r.jina.ai/",
        max_concurrent_requests: int = 5,
        timeout: int = 600,  # timeout setting (seconds)
        retry_attempts: int = 1,  # increased retry attempts
        retry_delay_base: int = 5  # base delay for exponential backoff
    ):
        """
        Initialize JinaReaderScraper.

        Args:
            api_key (Optional[str]): Jina AI API key.
                                     If None, load from environment variable
                                     JINA_API_KEY.
            model (str): The Reader model to use.
            output_format (str): The requested output format
                ('markdown', 'text', 'html', ...).
            api_base_url (str): The base URL of the Jina Reader API.
            max_concurrent_requests (int): The maximum number of concurrent
                requests.
            timeout (int): The timeout for requests (seconds).
            retry_attempts (int): The number of retry attempts when requests
                fail.
            retry_delay_base (int): Base delay for exponential backoff
                (seconds).
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('JINA_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided, and JINA_API_KEY not found in "
                    "environment variables"
                )

        # Remove trailing slash for consistency
        self.api_base_url = api_base_url.rstrip("/")
        # Configure headers according to Jina Reader API documentation
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json',
            'X-Respond-With': model,
            'X-Return-Format': output_format,
            'X-No-Cache': 'true',  # Force fresh fetch
            'X-Timeout': '1000',  # Explicit timeout in seconds
            'X-With-Links-Summary': 'all',  # Include links summary
            'X-Engine': 'browser'  # Use browser engine as it's more robust
        }
        self.output_format = output_format
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay_base = retry_delay_base
        self._session = None
        self._semaphore = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get a reusable aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
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

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter

        Args:
            attempt: Current attempt number (zero-based)

        Returns:
            Delay in seconds
        """
        # Exponential backoff with base delay
        delay = self.retry_delay_base * (2 ** attempt)
        # Add jitter (±20%)
        jitter = delay * 0.2
        return delay + random.uniform(-jitter, jitter)

    def _extract_error_info(self, html_content: str, status_code: int) -> str:
        """
        Extract clean error information from HTML error pages.

        Args:
            html_content: The raw HTML response content
            status_code: The HTTP status code

        Returns:
            Clean error message without HTML noise
        """
        # Handle 524 CloudFlare timeout specifically
        if status_code == 524 and "524: A timeout occurred" in html_content:
            return "CloudFlare timeout error (524)"

        # Try to extract text content from HTML
        if (html_content.startswith("<!DOCTYPE html") or
                html_content.startswith("<html")):
            # Extract title tag content
            title_match = re.search(r'<title>(.*?)</title>',
                                    html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up common patterns
                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                if title:
                    return title

            # Look for error code pattern in content
            error_match = re.search(r'Error code (\d+)', html_content)
            if error_match:
                return f"Error code {error_match.group(1)}"

            # Try to extract h1 or h2 headers
            header_match = re.search(r'<h[12]>(.*?)</h[12]>',
                                     html_content, re.IGNORECASE | re.DOTALL)
            if header_match:
                header = header_match.group(1).strip()
                header = re.sub(r'\s+', ' ', header)  # Normalize whitespace
                if header:
                    return header

        # For non-HTML or if extraction fails, limit content length
        max_length = 40000
        if len(html_content) > max_length:
            return html_content[:max_length] + "..."
        return html_content

    async def scrape(
        self,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
        attempt: int = 0
    ) -> ExtractionResult:
        """
        Use Jina Reader API to scrape a single URL.

        Args:
            url (str): The URL to scrape.
            session (Optional[aiohttp.ClientSession]): An optional aiohttp
                session instance.
            attempt (int): The current retry count.

        Returns:
            ExtractionResult: An object containing the scraping result.
        """
        semaphore = await self._get_semaphore()
        provided_session = session is not None

        if not provided_session:
            session = await self._get_session()

        try:
            async with semaphore:
                # Use URL directly appended to the API base URL
                full_url = f"{self.api_base_url}/{url}"

                # Make a GET request instead of POST
                async with session.get(
                    full_url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        # Handle CloudFlare timeout error specifically
                        if response.status == 524:
                            error_msg = (
                                f"CloudFlare timeout error (524) for URL: {url}. "
                                f"The origin server took too long to respond. "
                                f"This often happens with slow or overloaded websites."
                            )
                        else:
                            error_msg = (
                                f"Jina Reader API returned HTTP error: "
                                f"{response.status}"
                            )
                            try:
                                error_details = await response.json()
                                error_msg += (
                                    f" API error details: "
                                    f"{error_details}"
                                )
                            except Exception:
                                # Clean up HTML responses
                                raw_response = await response.text()
                                cleaned_response = self._extract_error_info(
                                    raw_response, response.status
                                )
                                error_msg += f" Response: {cleaned_response}"

                        # Handle retryable errors (429, 500, 502, 503, 504, 524)
                        if (response.status in (429, 500, 502, 503, 504, 524)
                                and attempt < self.retry_attempts):
                            # Calculate backoff with jitter
                            retry_delay = self._calculate_retry_delay(attempt)
                            if response.status == 524:
                                print(f"CloudFlare timeout (524). Waiting "
                                      f"{retry_delay:.1f} seconds before retrying {url}")
                            else:
                                print(f"HTTP {response.status} error. Waiting "
                                      f"{retry_delay:.1f} seconds before retrying {url}")
                            await asyncio.sleep(retry_delay)
                            return await self.scrape(url, session, attempt + 1)

                        print(error_msg)
                        return ExtractionResult(
                            name="jina_reader",
                            success=False,
                            error=error_msg
                        )

                    # Try to parse as JSON first
                    try:
                        data = await response.json()
                        if data.get("code") == 200 and data.get("data"):
                            content_data = data["data"]
                            content = content_data.get("content", "")
                            # Extract additional metadata
                            metadata = {}
                            for key in [
                                "title", "description", "images", "links"
                            ]:
                                if key in content_data:
                                    metadata[key] = content_data[key]

                            return ExtractionResult(
                                name="jina_reader",
                                success=True,
                                content=content,
                                metadata=metadata
                            )
                    except Exception:
                        # If not JSON, try to get raw text content
                        content = await response.text()
                        return ExtractionResult(
                            name="jina_reader",
                            success=True,
                            content=content,
                            metadata={"title": "", "description": ""}
                        )

                    # If we reach here with JSON data but wrong format
                    data_str = "Unknown format"
                    if 'data' in locals():
                        data_str = str(data)

                    error_msg = (
                        f"Jina Reader API returned error or no data: "
                        f"{data_str}"
                    )
                    print(error_msg)
                    return ExtractionResult(
                        name="jina_reader",
                        success=False,
                        error=error_msg
                    )

        except asyncio.TimeoutError:
            error_msg = (
                f"Jina Reader API request timeout or asyncio timeout: "
                f"{url}"
            )
            print(error_msg)
            # Timeout retry with backoff
            if attempt < self.retry_attempts:
                retry_delay = self._calculate_retry_delay(attempt)
                print(f"Waiting {retry_delay:.1f} seconds before retrying "
                      f"{url}")
                await asyncio.sleep(retry_delay)
                return await self.scrape(url, session, attempt + 1)

            return ExtractionResult(
                name="jina_reader",
                success=False,
                error=error_msg
            )
        except aiohttp.ClientError as e:
            error_msg = (
                f"Error calling Jina Reader API ({url}): {str(e)}"
            )
            print(error_msg)
            # Connection error retry with backoff
            if attempt < self.retry_attempts:
                retry_delay = self._calculate_retry_delay(attempt)
                print(f"Waiting {retry_delay:.1f} seconds before retrying "
                      f"{url}")
                await asyncio.sleep(retry_delay)
                return await self.scrape(url, session, attempt + 1)

            return ExtractionResult(
                name="jina_reader",
                success=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = (
                f"Unknown error occurred while processing Jina Reader "
                f"response ({url}): {str(e)}"
            )
            print(error_msg)
            return ExtractionResult(
                name="jina_reader",
                success=False,
                error=error_msg
            )
        finally:
            if not provided_session:
                # Do not close the session, keep the connection pool reused
                pass

    async def scrape_many(
        self,
        urls: List[str],
        batch_size: Optional[int] = None
    ) -> Dict[str, ExtractionResult]:
        """
        Scrape multiple URLs concurrently.

        Use aiohttp to implement asynchronous concurrent requests,
        improving multi-URL processing efficiency.

        Args:
            urls (List[str]): The list of URLs to scrape.
            batch_size (Optional[int]): The batch size, None means process all
                at once.

        Returns:
            Dict[str, ExtractionResult]: A mapping of URLs to scraping results.
        """
        results = {}

        # If batch size is not specified, process all at once
        if batch_size is None:
            session = await self._get_session()
            try:
                tasks = [self.scrape(url, session) for url in urls]
                responses = await asyncio.gather(*tasks)

                for url, response in zip(urls, responses):
                    results[url] = response
            finally:
                # Do not close the session, keep the connection pool reused
                pass
        else:
            # Process in batches, execute each batch concurrently
            batches = [
                urls[i:i + batch_size]
                for i in range(0, len(urls), batch_size)
            ]
            session = await self._get_session()

            try:
                for batch in batches:
                    batch_tasks = [self.scrape(url, session) for url in batch]
                    batch_results = await asyncio.gather(*batch_tasks)

                    for url, result in zip(batch, batch_results):
                        results[url] = result
            finally:
                # Do not close the session, keep the connection pool reused
                pass

        return results

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

    def __del__(self):
        """Destructor, ensure resource cleanup"""
        if self._session and not self._session.closed:
            # Create a new event loop to close the session
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception:
                pass

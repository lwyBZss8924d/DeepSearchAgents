#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/base.py
# code style: PEP 8

"""
Base class for web scraper clients with common functionality.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar
from functools import wraps

from .result import ExtractionResult

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RateLimiter:
    """Rate limiter implementation for API calls."""

    def __init__(self, calls: int, period: timedelta):
        """
        Initialize rate limiter.

        Args:
            calls: Number of allowed calls
            period: Time period for the calls
        """
        self.calls = calls
        self.period = period
        self.call_times: List[datetime] = []

    def __call__(self, func: Callable) -> Callable:
        """Decorator for rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            result = func(*args, **kwargs)
            self.record_call()
            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await self.async_wait_if_needed()
            result = await func(*args, **kwargs)
            self.record_call()
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        window_start = now - self.period

        # Remove old calls outside window
        self.call_times = [t for t in self.call_times if t > window_start]

        if len(self.call_times) >= self.calls:
            # Need to wait
            oldest_call = min(self.call_times)
            wait_time = (oldest_call + self.period - now).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)

    async def async_wait_if_needed(self):
        """Async version of wait_if_needed."""
        now = datetime.now()
        window_start = now - self.period

        # Remove old calls outside window
        self.call_times = [t for t in self.call_times if t > window_start]

        if len(self.call_times) >= self.calls:
            # Need to wait
            oldest_call = min(self.call_times)
            wait_time = (oldest_call + self.period - now).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

    def record_call(self):
        """Record a call timestamp."""
        self.call_times.append(datetime.now())

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = datetime.now()
        window_start = now - self.period

        # Clean old calls
        self.call_times = [t for t in self.call_times if t > window_start]

        requests_made = len(self.call_times)
        requests_remaining = max(0, self.calls - requests_made)

        # Calculate reset time
        if self.call_times:
            oldest_call = min(self.call_times)
            reset_time = oldest_call + self.period
            seconds_until_reset = max(
                0, (reset_time - now).total_seconds()
            )
        else:
            seconds_until_reset = 0

        return {
            "rate_limit": self.calls,
            "requests_made": requests_made,
            "requests_remaining": requests_remaining,
            "reset_in_seconds": int(seconds_until_reset),
            "window_minutes": int(self.period.total_seconds() / 60),
        }


class BaseScraper(ABC):
    """
    Abstract base class for web scraper clients.

    Provides common functionality:
    - Retry logic with exponential backoff
    - Rate limiting
    - Standardized return format
    - Timeout handling
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_INITIAL_RETRY_DELAY = 1.0
    DEFAULT_MAX_RETRY_DELAY = 16.0
    DEFAULT_RETRY_MULTIPLIER = 2.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize base scraper client.

        Args:
            api_key: API key for the service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limiter: Optional rate limiter instance
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter

    def retry_with_backoff(
        self,
        func: Callable,
        *args,
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to execute
            exceptions: Tuple of exceptions to catch and retry
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self.rate_limiter:
                    return self.rate_limiter(func)(*args, **kwargs)
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = min(
                        self.DEFAULT_INITIAL_RETRY_DELAY *
                        (self.DEFAULT_RETRY_MULTIPLIER ** attempt),
                        self.DEFAULT_MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")

        if last_exception:
            raise last_exception

    async def async_retry_with_backoff(
        self,
        func: Callable,
        *args,
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """
        Async version of retry_with_backoff.

        Args:
            func: Async function to execute
            exceptions: Tuple of exceptions to catch and retry
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self.rate_limiter:
                    return await self.rate_limiter(func)(*args, **kwargs)
                return await func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = min(
                        self.DEFAULT_INITIAL_RETRY_DELAY *
                        (self.DEFAULT_RETRY_MULTIPLIER ** attempt),
                        self.DEFAULT_MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")

        if last_exception:
            raise last_exception

    def standardize_result(
        self,
        url: str,
        content: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **extra
    ) -> ExtractionResult:
        """
        Standardize scraping result format.

        Args:
            url: URL that was scraped
            content: Extracted content
            success: Whether extraction was successful
            error: Error message if failed
            metadata: Additional metadata
            **extra: Additional fields to include

        Returns:
            Standardized ExtractionResult
        """
        result = ExtractionResult(
            name=self.__class__.__name__,
            success=success,
            content=content,
            error=error,
            metadata=metadata or {}
        )

        # Add extra fields
        for key, value in extra.items():
            setattr(result, key, value)

        return result

    @abstractmethod
    def scrape(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            **kwargs: Additional provider-specific parameters

        Returns:
            ExtractionResult with scraped content
        """
        raise NotImplementedError("Subclass must implement scrape method")

    @abstractmethod
    async def scrape_async(
        self,
        url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Async version of scrape.

        Args:
            url: URL to scrape
            **kwargs: Additional provider-specific parameters

        Returns:
            ExtractionResult with scraped content
        """
        raise NotImplementedError(
            "Subclass must implement scrape_async method"
        )

    async def scrape_many_async(
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
            **kwargs: Additional parameters passed to scrape_async

        Returns:
            Dictionary mapping URLs to ExtractionResults
        """
        results = {}

        if batch_size is None:
            # Process all at once
            tasks = [
                self.scrape_async(url, **kwargs) for url in urls
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for url, response in zip(urls, responses):
                if isinstance(response, Exception):
                    results[url] = self.standardize_result(
                        url=url,
                        success=False,
                        error=str(response)
                    )
                else:
                    results[url] = response
        else:
            # Process in batches
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                batch_tasks = [
                    self.scrape_async(url, **kwargs) for url in batch
                ]
                batch_responses = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                for url, response in zip(batch, batch_responses):
                    if isinstance(response, Exception):
                        results[url] = self.standardize_result(
                            url=url,
                            success=False,
                            error=str(response)
                        )
                    else:
                        results[url] = response

        return results

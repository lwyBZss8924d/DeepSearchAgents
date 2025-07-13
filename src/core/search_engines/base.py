#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/base.py
# code style: PEP 8

"""
Base class for search engine clients with common functionality.
"""

import asyncio
import logging
import time
from abc import ABC
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar
from functools import wraps

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


class BaseSearchClient(ABC):
    """
    Abstract base class for search engine clients.

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
        Initialize base search client.

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

    def standardize_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        usage: Optional[Dict[str, Any]] = None,
        **metadata
    ) -> Dict[str, Any]:
        """
        Standardize search results format.

        Args:
            results: List of search results
            query: Original search query
            usage: Token usage information
            **metadata: Additional metadata

        Returns:
            Standardized result dictionary
        """
        return {
            "results": results,
            "query": query,
            "total_results": len(results),
            "usage": usage or {"total_tokens": 0, "counting_method": "none"},
            **metadata
        }

    def search(
        self,
        query: str,
        num: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a search.

        Args:
            query: Search query
            num: Number of results to return
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized search results
        """
        raise NotImplementedError("Subclass must implement search method")

    async def search_async(
        self,
        query: str,
        num: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of search.

        Args:
            query: Search query
            num: Number of results to return
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized search results
        """
        raise NotImplementedError(
            "Subclass must implement search_async method"
            )

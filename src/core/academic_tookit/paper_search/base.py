#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_search/base.py
# code style: PEP 8

"""
Base abstract class for all paper search client implementations.
"""

import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from ..models import Paper, SearchParams

logger = logging.getLogger(__name__)


class BasePaperSearchClient(ABC):
    """
    Abstract base class for all paper search implementations.

    This class defines the interface that all paper search clients must
    implement, ensuring consistency across different academic sources.
    """

    def __init__(self):
        """Initialize the base client."""
        # Extract source name from class name
        self.source_name = (
            self.__class__.__name__.replace('Client', '').lower()
        )

        # Rate limiting information
        self._rate_limit_info: Dict[str, Any] = {
            'requests_remaining': None,
            'reset_time': None,
            'last_request_time': None
        }

        # Usage statistics
        self._usage_stats = {
            'total_requests': 0,
            'total_papers_fetched': 0,
            'errors_count': 0
        }

        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    async def search(self, params: SearchParams) -> List[Paper]:
        """
        Search for papers based on the provided parameters.

        Args:
            params: Search parameters including query, filters, etc.

        Returns:
            List of Paper objects matching the search criteria

        Raises:
            Exception: If the search fails
        """
        pass

    @abstractmethod
    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get detailed information about a specific paper.

        Args:
            paper_id: The source-specific paper identifier

        Returns:
            Paper object if found, None otherwise

        Raises:
            Exception: If the request fails
        """
        pass

    @abstractmethod
    async def get_paper_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get paper by DOI if supported by the source.

        Args:
            doi: The Digital Object Identifier

        Returns:
            Paper object if found, None otherwise

        Raises:
            NotImplementedError: If the source doesn't support DOI lookup
            Exception: If the request fails
        """
        pass

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary containing rate limit information:
            - requests_remaining: Number of requests remaining
            - reset_time: When the rate limit resets
            - last_request_time: Time of last request
        """
        return self._rate_limit_info.copy()

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this client.

        Returns:
            Dictionary containing usage statistics:
            - total_requests: Total number of API requests made
            - total_papers_fetched: Total number of papers retrieved
            - errors_count: Number of errors encountered
        """
        return self._usage_stats.copy()

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Test if the API is accessible and credentials are valid.

        Returns:
            True if connection is successful, False otherwise

        Raises:
            Exception: If validation fails catastrophically
        """
        pass

    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit information from response headers.

        This is a helper method that subclasses can use to update
        rate limiting information based on API response headers.

        Args:
            headers: Response headers from the API
        """
        # Common header patterns
        rate_limit_headers = {
            'x-ratelimit-remaining': 'requests_remaining',
            'x-ratelimit-reset': 'reset_time',
            'x-rate-limit-remaining': 'requests_remaining',
            'x-rate-limit-reset': 'reset_time',
            'retry-after': 'retry_after'
        }

        for header, field in rate_limit_headers.items():
            if header in headers:
                try:
                    if field == 'reset_time':
                        # Convert to datetime if it's a timestamp
                        timestamp = int(headers[header])
                        self._rate_limit_info[field] = (
                            datetime.datetime.fromtimestamp(timestamp)
                        )
                    else:
                        self._rate_limit_info[field] = int(headers[header])
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse rate limit header {header}: "
                        f"{headers[header]}"
                    )

    def _increment_stats(
        self,
        papers_count: int = 0,
        error: bool = False
    ) -> None:
        """
        Update usage statistics.

        Args:
            papers_count: Number of papers fetched in this request
            error: Whether this request resulted in an error
        """
        self._usage_stats['total_requests'] += 1
        if error:
            self._usage_stats['errors_count'] += 1
        else:
            self._usage_stats['total_papers_fetched'] += papers_count

    async def search_with_retry(
        self,
        params: SearchParams,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ) -> List[Paper]:
        """
        Search with automatic retry on failure.

        This method provides a common retry mechanism that subclasses
        can use or override.

        Args:
            params: Search parameters
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier

        Returns:
            List of Paper objects

        Raises:
            Exception: If all retries fail
        """
        import asyncio

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                results = await self.search(params)
                return results

            except Exception as e:
                last_exception = e
                self._increment_stats(error=True)

                if attempt < max_retries:
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{self.__class__.__name__} search failed "
                        f"(attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"{self.__class__.__name__} search failed after "
                        f"{max_retries + 1} attempts: {e}"
                    )

        raise last_exception or Exception("Search failed after retries")

    def __repr__(self) -> str:
        """String representation of the client."""
        return (
            f"<{self.__class__.__name__} "
            f"source='{self.source_name}' "
            f"requests={self._usage_stats['total_requests']}>"
        )

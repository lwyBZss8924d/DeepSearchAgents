#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_exa.py
# code style: PEP 8

"""
Exa AI Web Search API Client for "HybridSearchEngine"
API Base URL: (api.exa.ai)
Get your Exa AI API key for free: https://exa.ai
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from dotenv import load_dotenv

from .base import BaseSearchClient, RateLimiter
from .utils.search_token_counter import count_search_tokens
from datetime import timedelta

try:
    from exa_py import Exa

    HAS_EXA_PY = True
except ImportError:
    HAS_EXA_PY = False
    Exa = None

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result"""

    title: str
    url: str
    id: str
    content: Optional[str] = None
    highlights: Optional[List[str]] = None
    score: Optional[float] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    extract: Optional[str] = None


@dataclass
class DocumentContent:
    """Represents document content"""

    id: str
    url: str
    title: str
    extract: str
    author: Optional[str] = None
    highlights: Optional[List[str]] = None


class ExaSearchException(Exception):
    """Custom exception for Exa Search API related errors"""

    pass


class ExaSearchClient(BaseSearchClient):
    """
    Client for Exa AI Search API that provides advanced search capabilities
    including neural search, similarity search, and content retrieval.

    Features:
    - Neural search for understanding natural language queries
    - Keyword search for exact matches
    - Find similar documents based on URL
    - Content extraction with highlights
    - Question answering capabilities

    Rate Limits:
    - Contact Exa for rate limit information
    - Consider using caching for repeated queries

    Get your Exa AI API key: https://exa.ai
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.exa.ai",
        user_agent: str = "exa-search-client/1.0.0",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_calls: Optional[int] = None,
        rate_limit_period: Optional[timedelta] = None,
    ):
        """
        Initialize the Exa Search Client.

        Args:
            api_key: Exa AI API key (defaults to EXA_API_KEY from env)
            base_url: Base URL for Exa API
            user_agent: User agent string for requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        if not HAS_EXA_PY:
            raise ExaSearchException(
                "exa_py package is not installed. "
                "Please install it with: pip install exa-py"
            )

        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv("EXA_API_KEY")
            if not api_key:
                raise ExaSearchException(
                    "No API key provided, and EXA_API_KEY not found in "
                    "environment variables. Get your free API key at: "
                    "https://exa.ai"
                )

        # Set up rate limiter if specified
        rate_limiter = None
        if rate_limit_calls and rate_limit_period:
            rate_limiter = RateLimiter(rate_limit_calls, rate_limit_period)

        # Initialize base class
        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            rate_limiter=rate_limiter
        )

        self.base_url = base_url
        self.user_agent = user_agent

        # Initialize Exa client
        try:
            self.client = Exa(
                api_key=self.api_key,
                base_url=self.base_url,
                user_agent=self.user_agent,
            )  # type: ignore
        except Exception as e:
            raise ExaSearchException(f"Failed to initialize Exa client: {str(e)}")

        logger.info(f"Exa Search Client initialized with base URL: {self.base_url}")

    def search(
        self,
        query: str,
        num: int = 10,
        search_type: str = "neural",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        use_autoprompt: bool = False,
        category: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a search using Exa's neural or keyword search.

        Args:
            query: Search query string
            num_results: Number of results to return (default: 10)
            search_type: Type of search - "neural" or "keyword" (default: "neural")
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            start_published_date: Filter by publication date (YYYY-MM-DD)
            end_published_date: Filter by publication date (YYYY-MM-DD)
            start_crawl_date: Filter by crawl date (YYYY-MM-DD)
            end_crawl_date: Filter by crawl date (YYYY-MM-DD)
            use_autoprompt: Convert query to optimized Exa query
            category: Category to focus on (e.g., "company")

        Returns:
            Dictionary containing search results and metadata
        """
        if not query or not query.strip():
            raise ExaSearchException("Search query cannot be empty")

        if num < 1 or num > 100:
            raise ExaSearchException("Number of results must be between 1 and 100")

        # Define search function for retry
        def perform_search():
            return self.client.search(
                query=query,
                num_results=num,
                type=search_type,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_published_date=start_published_date,
                end_published_date=end_published_date,
                start_crawl_date=start_crawl_date,
                end_crawl_date=end_crawl_date,
                use_autoprompt=use_autoprompt,
                category=category,
            )

        try:
            # Perform search with retry
            search_response = self.retry_with_backoff(
                perform_search,
                exceptions=(Exception,)
            )

            # Process and return results
            return self._process_search_results(search_response, query)

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            raise ExaSearchException(f"Search failed: {str(e)}")

    def _process_search_results(self, response: Any, query: str) -> Dict[str, Any]:
        """
        Process raw search response into standardized format.

        Args:
            response: Raw response from Exa API
            query: Original search query

        Returns:
            Processed search results
        """
        results = []

        # Process each result
        for result in response.results:
            processed_result = SearchResult(
                title=result.title,
                url=result.url,
                id=result.id,
                score=getattr(result, "score", None),
                published_date=getattr(result, "published_date", None),
                author=getattr(result, "author", None),
                extract=getattr(result, "extract", None),
            )
            results.append(processed_result)

        result_dict = {
            "results": results,
            "query": query,
            "total_results": len(results),
            "autoprompt_string": getattr(response, "autoprompt_string", None),
        }

        # Use unified token counter instead of hardcoded 0
        result_dict["usage"] = count_search_tokens(
            query=query, response=result_dict, provider="exa"
        )

        return result_dict

    def search_and_contents(
        self,
        query: str,
        num: int = 10,
        search_type: str = "neural",
        text: Union[bool, Dict[str, Any]] = True,
        highlights: Optional[Dict[str, Any]] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        use_autoprompt: bool = False,
    ) -> Dict[str, Any]:
        """
        Search and retrieve contents in a single API call.

        Args:
            query: Search query string
            num_results: Number of results to return
            search_type: Type of search - "neural" or "keyword"
            text: Content options - True for default, or dict with options:
                  - include_html_tags: Include HTML tags in content
                  - max_characters: Maximum characters to return
            highlights: Highlight options dict:
                  - num_sentences: Number of sentences per highlight
                  - highlights_per_url: Number of highlights per URL
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            start_published_date: Filter by publication date (YYYY-MM-DD)
            end_published_date: Filter by publication date (YYYY-MM-DD)
            use_autoprompt: Convert query to optimized Exa query

        Returns:
            Dictionary containing search results with content
        """
        if not query or not query.strip():
            raise ExaSearchException("Search query cannot be empty")

        # Define function for retry
        def perform_search():
            return self.client.search_and_contents(
                query=query,
                num_results=num,
                type=search_type,
                text=text,  # type: ignore
                highlights=highlights,  # type: ignore
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_published_date=start_published_date,
                end_published_date=end_published_date,
                use_autoprompt=use_autoprompt,
            )

        try:
            # Perform search with retry
            response = self.retry_with_backoff(
                perform_search,
                exceptions=(Exception,)
            )

            # Process results with content
            return self._process_search_results_with_content(response, query)

        except Exception as e:
            logger.error(f"Search and contents error: {str(e)}")
            raise ExaSearchException(f"Search and contents failed: {str(e)}")

    def _process_search_results_with_content(
        self, response: Any, query: str
    ) -> Dict[str, Any]:
        """
        Process search results that include content.

        Args:
            response: Raw response with content
            query: Original search query

        Returns:
            Processed results with content
        """
        results = []

        for result in response.results:
            processed_result = SearchResult(
                title=result.title,
                url=result.url,
                id=result.id,
                content=getattr(result, "text", None),
                highlights=getattr(result, "highlights", None),
                score=getattr(result, "score", None),
                published_date=getattr(result, "published_date", None),
                author=getattr(result, "author", None),
                extract=getattr(result, "extract", None),
            )
            results.append(processed_result)

        result_dict = {
            "results": results,
            "query": query,
            "total_results": len(results),
            "autoprompt_string": getattr(response, "autoprompt_string", None),
        }

        # Use unified token counter
        result_dict["usage"] = count_search_tokens(
            query=query, response=result_dict, provider="exa"
        )

        return result_dict

    def find_similar(
        self,
        url: str,
        num: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        exclude_source_domain: bool = True,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find documents similar to the given URL.

        Args:
            url: URL to find similar documents for
            num_results: Number of results to return
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            start_published_date: Filter by publication date (YYYY-MM-DD)
            end_published_date: Filter by publication date (YYYY-MM-DD)
            exclude_source_domain: Exclude results from the source domain
            category: Category to focus on (e.g., "company")

        Returns:
            Dictionary containing similar documents
        """
        if not url or not url.strip():
            raise ExaSearchException("URL cannot be empty")

        # Define function for retry
        def perform_search():
            return self.client.find_similar(
                url=url,
                num_results=num,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_published_date=start_published_date,
                end_published_date=end_published_date,
                exclude_source_domain=exclude_source_domain,
                category=category,
            )

        try:
            response = self.retry_with_backoff(
                perform_search,
                exceptions=(Exception,)
            )

            return self._process_search_results(response, f"Similar to: {url}")

        except Exception as e:
            logger.error(f"Find similar error: {str(e)}")
            raise ExaSearchException(f"Find similar failed: {str(e)}")

    def find_similar_and_contents(
        self,
        url: str,
        num: int = 10,
        text: Union[bool, Dict[str, Any]] = True,
        highlights: Optional[Dict[str, Any]] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        exclude_source_domain: bool = True,
    ) -> Dict[str, Any]:
        """
        Find similar documents and retrieve their contents.

        Args:
            url: URL to find similar documents for
            num_results: Number of results to return
            text: Content options - True for default, or dict with options
            highlights: Highlight options dict
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            exclude_source_domain: Exclude results from the source domain

        Returns:
            Dictionary containing similar documents with content
        """
        if not url or not url.strip():
            raise ExaSearchException("URL cannot be empty")

        # Define function for retry
        def perform_search():
            return self.client.find_similar_and_contents(
                url=url,
                num_results=num,
                text=text,  # type: ignore
                highlights=highlights,  # type: ignore
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                exclude_source_domain=exclude_source_domain,
            )

        try:
            response = self.retry_with_backoff(
                perform_search,
                exceptions=(Exception,)
            )

            return self._process_search_results_with_content(
                response, f"Similar to: {url}"
            )

        except Exception as e:
            logger.error(f"Find similar and contents error: {str(e)}")
            raise ExaSearchException(f"Find similar and contents failed: {str(e)}")

    def get_contents(
        self,
        ids: List[str],
        text: Union[bool, Dict[str, Any]] = True,
        highlights: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve contents for a list of document IDs.

        Args:
            ids: List of document IDs from previous search results
            text: Content options - True for default, or dict with options
            highlights: Highlight options dict

        Returns:
            Dictionary containing document contents
        """
        if not ids:
            raise ExaSearchException("Document IDs list cannot be empty")

        try:
            response = self.client.get_contents(
                ids=ids,
                text=text,  # type: ignore
                highlights=highlights,  # type: ignore
            )

            # Process content results
            contents = []
            for content in response.contents:
                doc_content = DocumentContent(
                    id=content.id,
                    url=content.url,
                    title=content.title,
                    extract=content.extract,
                    author=getattr(content, "author", None),
                    highlights=getattr(content, "highlights", None),
                )
                contents.append(doc_content)

            result_dict = {
                "contents": contents,
                "total_contents": len(contents),
            }

            # Use unified token counter
            result_dict["usage"] = count_search_tokens(
                query=str(ids),
                response=result_dict,
                provider="exa",  # Use IDs as query proxy
            )

            return result_dict

        except Exception as e:
            logger.error(f"Get contents error: {str(e)}")
            raise ExaSearchException(f"Get contents failed: {str(e)}")

    def answer(self, query: str, text: bool = False) -> str:
        """
        Get a direct answer to a question.

        Args:
            query: Question to answer
            text: Include source text in response

        Returns:
            Answer string
        """
        try:
            response = self.client.answer(query, text=text)
            return response  # type: ignore
        except Exception as e:
            logger.error(f"Answer error: {str(e)}")
            raise ExaSearchException(f"Answer failed: {str(e)}")

    def stream_answer(self, query: str):
        """
        Stream answer to a question.

        Args:
            query: Question to answer

        Yields:
            Answer chunks as they arrive
        """
        try:
            for chunk in self.client.stream_answer(query):
                yield chunk
        except Exception as e:
            logger.error(f"Stream answer error: {str(e)}")
            raise ExaSearchException(f"Stream answer failed: {str(e)}")

    def simple_search(self, query: str, num: int = 5) -> List[str]:
        """
        Simple search that returns just the content strings.

        Args:
            query: Search query
            num: Number of results (default: 5 for faster response)

        Returns:
            List of content strings
        """
        response = self.search_and_contents(query=query, num=num)
        results = []
        for result in response.get("results", []):
            # Handle both dataclass and dict results
            if hasattr(result, "content"):
                content = result.content if result.content else result.extract or ""
            else:
                content = result.get("content") if result.get("content") else result.get("extract", "")
            results.append(content)
        return results

    async def search_async(
        self,
        query: str,
        num: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of search method.

        Note: This is a wrapper that runs the sync Exa client in an executor
        since the exa_py library doesn't provide native async support.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.search(query, num, **kwargs)
        )

    async def find_similar_async(
        self,
        url: str,
        num: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of find_similar method.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.find_similar(url, num, **kwargs)
        )


# Convenience functions for backward compatibility
def search(query: str, num_results: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for searching with Exa AI.

    Args:
        query: Search query
        num_results: Number of results
        **kwargs: Additional parameters

    Returns:
        Search results
    """
    client = ExaSearchClient()
    return client.search(query=query, num=num_results, **kwargs)


def find_similar(url: str, num_results: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for finding similar documents.

    Args:
        url: URL to find similar documents for
        num_results: Number of results
        **kwargs: Additional parameters

    Returns:
        Similar documents
    """
    client = ExaSearchClient()
    return client.find_similar(url=url, num=num_results, **kwargs)

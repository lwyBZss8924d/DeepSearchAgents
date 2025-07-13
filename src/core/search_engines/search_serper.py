#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_serper.py
# code style: PEP 8

"""
[Serper] Google Search API Web Search API Client for "HybridSearchEngine"
API Base URL: (google.serper.dev)
"""

import os
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass
from dotenv import load_dotenv
import requests
import aiohttp

from .base import BaseSearchClient, RateLimiter
from .utils.search_token_counter import count_search_tokens
from datetime import timedelta

logger = logging.getLogger(__name__)


class SerperAPIException(Exception):
    """Custom exception for Serper API related errors"""

    pass


@dataclass
class SearchResult:
    """Represents a single search result"""

    title: str
    url: str
    snippet: str
    position: Optional[int] = None
    date: Optional[str] = None
    sitelinks: Optional[List[Dict[str, str]]] = None
    attributes: Optional[Dict[str, Any]] = None
    faq: Optional[Dict[str, str]] = None
    thumbnail: Optional[str] = None


class GoogleSerperClient(BaseSearchClient):
    """
    Client for Google Serper API that provides comprehensive web search capabilities.

    Features:
    - Multiple search types: web, news, images, places
    - Advanced filtering and localization
    - Retry logic with exponential backoff
    - Async support for high-performance applications
    - Rich result extraction (answer boxes, knowledge graph, etc.)

    Rate Limits:
    - Free tier: 2,500 queries/month
    - Pro tier: Higher limits available

    Get your API key at: https://serper.dev
    """

    # Result key mapping for different search types
    RESULT_KEY_FOR_TYPE = {
        "news": "news",
        "places": "places",
        "images": "images",
        "search": "organic",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://google.serper.dev",
        timeout: int = 30,
        max_retries: int = 3,
        gl: str = "us",
        hl: str = "en",
        aiosession: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Initialize the Google Serper Client.

        Args:
            api_key: Serper API key (defaults to SERPER_API_KEY from env)
            base_url: Base URL for Serper API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            gl: Country code for search (e.g., "us", "uk", "de")
            hl: Language code for search (e.g., "en", "es", "fr")
            aiosession: Optional aiohttp session for async requests
        """
        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv("SERPER_API_KEY")
            if not api_key:
                raise SerperAPIException(
                    "No API key provided, and SERPER_API_KEY not found in "
                    "environment variables. Get your free API key at: "
                    "https://serper.dev"
                )

        # Set up rate limiter for free tier (2,500/month = ~83/day)
        rate_limiter = RateLimiter(
            calls=83,
            period=timedelta(days=1)
        )

        # Initialize base class
        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            rate_limiter=rate_limiter
        )

        self.base_url = base_url
        self.gl = gl
        self.hl = hl
        self.aiosession = aiosession
        self.headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        logger.info(f"Google Serper Client initialized with base URL: {self.base_url}")

    def _make_request_with_retry(
        self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            endpoint: API endpoint
            payload: Request payload
            headers: Optional custom headers

        Returns:
            Response data as dictionary

        Raises:
            SerperAPIException: On request failure
        """
        url = f"{self.base_url}/{endpoint}"
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)

        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, headers=request_headers, json=payload, timeout=self.timeout)

                if response.status_code == 200:
                    return response.json()

                # Handle specific HTTP status codes
                if response.status_code == 401:
                    raise SerperAPIException("Invalid API key. Get your free API key at: https://serper.dev")
                elif response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff for rate limiting
                        wait_time = (2**attempt) * 1
                        logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise SerperAPIException("Rate limit exceeded. Consider upgrading your plan for higher limits.")
                elif response.status_code == 400:
                    error_data = response.json()
                    raise SerperAPIException(f"Bad request: {error_data.get('message', 'Invalid parameters')}")
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                        time.sleep(1 * (attempt + 1))  # Linear backoff for other errors
                        continue
                    else:
                        raise SerperAPIException(f"Request failed: {error_msg}")

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request timeout (attempt {attempt + 1}), retrying...")
                    continue
                else:
                    raise SerperAPIException(f"Request timed out after {self.timeout} seconds")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request error (attempt {attempt + 1}): {str(e)}")
                    continue
                else:
                    raise SerperAPIException(f"Request failed: {str(e)}")

        raise SerperAPIException("Maximum retries exceeded")

    def search(
        self,
        query: str,
        search_type: Literal["search", "news", "images", "places"] = "search",
        num: int = 10,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        tbs: Optional[str] = None,
        page: int = 1,
        autocorrect: bool = True,
        safe: Optional[str] = None,
        location: Optional[str] = None,
        uule: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a search using Google Serper API.

        Args:
            query: Search query string
            search_type: Type of search - "search", "news", "images", "places"
            num: Number of results to return (max: 100)
            gl: Country code (overrides instance default)
            hl: Language code (overrides instance default)
            tbs: Time-based search parameter (e.g., "qdr:d" for past day)
            page: Page number for pagination
            autocorrect: Whether to autocorrect query
            safe: Safe search setting
            location: Location string for local results
            uule: Encoded location parameter
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude

        Returns:
            Dictionary containing search results with metadata
        """
        if not query or not query.strip():
            raise SerperAPIException("Search query cannot be empty")

        if num < 1 or num > 100:
            raise SerperAPIException("Number of results must be between 1 and 100")

        if page < 1:
            raise SerperAPIException("Page number must be >= 1")

        # Build search query with domain filters
        search_query = query
        if include_domains:
            site_includes = " OR ".join([f"site:{domain}" for domain in include_domains])
            search_query = f"({search_query}) AND ({site_includes})"
        if exclude_domains:
            site_excludes = " ".join([f"-site:{domain}" for domain in exclude_domains])
            search_query = f"{search_query} {site_excludes}"

        # Prepare request payload
        payload = {
            "q": search_query,
            "num": num,
            "gl": gl or self.gl,
            "hl": hl or self.hl,
            "page": page,
            "autocorrect": autocorrect,
        }

        # Add optional parameters
        if tbs:
            payload["tbs"] = tbs
        if safe:
            payload["safe"] = safe
        if location:
            payload["location"] = location
        if uule:
            payload["uule"] = uule

        # Make API request
        try:
            data = self._make_request_with_retry(search_type, payload)
            return self._process_search_results(data, query, search_type)
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            raise

    def _process_search_results(self, data: Dict[str, Any], query: str, search_type: str) -> Dict[str, Any]:
        """
        Process raw API response into standardized format.

        Args:
            data: Raw API response data
            query: Original search query
            search_type: Type of search performed

        Returns:
            Processed search results
        """
        results = []
        result_key = self.RESULT_KEY_FOR_TYPE.get(search_type, "organic")

        # Process main search results
        if result_key in data:
            for idx, item in enumerate(data[result_key]):
                if search_type == "search":
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=item.get("position", idx + 1),
                        date=item.get("date"),
                        sitelinks=item.get("sitelinks"),
                        attributes=item.get("attributes"),
                        faq=item.get("faq"),
                    )
                elif search_type == "news":
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=idx + 1,
                        date=item.get("date"),
                        thumbnail=item.get("imageUrl"),
                    )
                elif search_type == "images":
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("source", ""),
                        thumbnail=item.get("imageUrl"),
                        position=idx + 1,
                    )
                elif search_type == "places":
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("address", ""),
                        position=item.get("position", idx + 1),
                        attributes=item.get("attributes"),
                    )
                results.append(result)

        # Extract additional rich results
        processed_results = {
            "results": results,
            "query": query,
            "search_type": search_type,
            "total_results": len(results),
            "search_metadata": {
                "id": data.get("searchParameters", {}).get("id"),
                "status": data.get("searchParameters", {}).get("status"),
                "created_at": data.get("searchParameters", {}).get("createdAt"),
                "credits_used": data.get("credits", 1),
            },
        }

        # Add rich results if available
        if "answerBox" in data:
            processed_results["answer_box"] = self._process_answer_box(data["answerBox"])

        if "knowledgeGraph" in data:
            processed_results["knowledge_graph"] = self._process_knowledge_graph(data["knowledgeGraph"])

        if "peopleAlsoAsk" in data:
            processed_results["people_also_ask"] = data["peopleAlsoAsk"]

        if "relatedSearches" in data:
            processed_results["related_searches"] = data["relatedSearches"]

        if "topStories" in data:
            processed_results["top_stories"] = [
                {
                    "title": story.get("title", ""),
                    "url": story.get("link", ""),
                    "source": story.get("source", ""),
                    "date": story.get("date"),
                    "imageUrl": story.get("imageUrl"),
                }
                for story in data["topStories"]
            ]

        # Add usage information using unified token counter
        processed_results["usage"] = count_search_tokens(query=query, response=data, provider="serper")

        return processed_results

    def _process_answer_box(self, answer_box: Dict[str, Any]) -> Dict[str, Any]:
        """Process answer box data"""
        processed = {}

        if "answer" in answer_box:
            processed["answer"] = answer_box["answer"]
        if "snippet" in answer_box:
            processed["snippet"] = answer_box["snippet"]
        if "snippetHighlighted" in answer_box:
            processed["snippet_highlighted"] = answer_box["snippetHighlighted"]
        if "title" in answer_box:
            processed["title"] = answer_box["title"]
        if "link" in answer_box:
            processed["url"] = answer_box["link"]

        return processed

    def _process_knowledge_graph(self, kg: Dict[str, Any]) -> Dict[str, Any]:
        """Process knowledge graph data"""
        processed = {
            "title": kg.get("title", ""),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "url": kg.get("descriptionLink"),
            "image_url": kg.get("imageUrl"),
        }

        if "attributes" in kg:
            processed["attributes"] = kg["attributes"]

        return processed

    def simple_search(self, query: str, num: int = 5) -> List[str]:
        """
        Simple search that returns just the content strings.

        Args:
            query: Search query
            num: Number of results (default: 5 for faster response)

        Returns:
            List of content strings (snippets)
        """
        response = self.search(query=query, num=num)
        snippets = []

        # First check for answer box
        if "answer_box" in response:
            answer_box = response["answer_box"]
            if "answer" in answer_box:
                snippets.append(answer_box["answer"])
            elif "snippet" in answer_box:
                snippets.append(answer_box["snippet"])

        # Then add regular search results
        for result in response.get("results", []):
            if result.snippet:
                snippets.append(result.snippet)

        return snippets[:num] if snippets else ["No results found"]

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

        # Convert to standardized format
        results = []
        for item in response.get("results", []):
            results.append({"title": item.title, "url": item.url, "content": item.snippet})

        return results

    def search_news(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search for news articles.

        Args:
            query: Search query
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            News search results
        """
        return self.search(query=query, search_type="news", num=num, **kwargs)

    def search_images(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search for images.

        Args:
            query: Search query
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            Image search results
        """
        return self.search(query=query, search_type="images", num=num, **kwargs)

    def search_places(self, query: str, location: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search for places/local results.

        Args:
            query: Search query
            location: Location for local results
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            Places search results
        """
        return self.search(query=query, search_type="places", location=location, num=num, **kwargs)

    def get_answer(self, query: str) -> Optional[str]:
        """
        Get a direct answer to a question if available.

        Args:
            query: Question to answer

        Returns:
            Answer string if available, None otherwise
        """
        response = self.search(query=query, num=1)

        # Check answer box first
        if "answer_box" in response:
            answer_box = response["answer_box"]
            if "answer" in answer_box:
                return answer_box["answer"]
            elif "snippet" in answer_box:
                return answer_box["snippet"]

        # Check knowledge graph
        if "knowledge_graph" in response:
            kg = response["knowledge_graph"]
            if "description" in kg:
                return kg["description"]

        return None

    async def asearch(
        self, query: str, search_type: Literal["search", "news", "images", "places"] = "search", num: int = 10, **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of search method.

        Args:
            query: Search query string
            search_type: Type of search
            num: Number of results
            **kwargs: Additional search parameters

        Returns:
            Dictionary containing search results
        """
        if not self.aiosession:
            async with aiohttp.ClientSession() as session:
                return await self._async_search(session, query, search_type, num, **kwargs)
        else:
            return await self._async_search(self.aiosession, query, search_type, num, **kwargs)

    async def _async_search(
        self, session: aiohttp.ClientSession, query: str, search_type: str, num: int, **kwargs
    ) -> Dict[str, Any]:
        """Internal async search implementation"""
        if not query or not query.strip():
            raise SerperAPIException("Search query cannot be empty")

        url = f"{self.base_url}/{search_type}"

        # Build search query with domain filters (same as sync version)
        search_query = query
        include_domains = kwargs.get("include_domains")
        exclude_domains = kwargs.get("exclude_domains")

        if include_domains:
            site_includes = " OR ".join([f"site:{domain}" for domain in include_domains])
            search_query = f"({search_query}) AND ({site_includes})"
        if exclude_domains:
            site_excludes = " ".join([f"-site:{domain}" for domain in exclude_domains])
            search_query = f"{search_query} {site_excludes}"

        payload = {
            "q": search_query,
            "num": num,
            "gl": kwargs.get("gl", self.gl),
            "hl": kwargs.get("hl", self.hl),
            "page": kwargs.get("page", 1),
            "autocorrect": kwargs.get("autocorrect", True),
        }

        # Add optional parameters
        for key in ["tbs", "safe", "location", "uule"]:
            if key in kwargs and kwargs[key]:
                payload[key] = kwargs[key]

        try:
            async with session.post(
                url, headers=self.headers, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_search_results(data, query, search_type)
                else:
                    text = await response.text()
                    if response.status == 401:
                        raise SerperAPIException("Invalid API key")
                    elif response.status == 429:
                        raise SerperAPIException("Rate limit exceeded")
                    else:
                        raise SerperAPIException(f"HTTP {response.status}: {text}")

        except asyncio.TimeoutError:
            raise SerperAPIException(f"Request timed out after {self.timeout} seconds")
        except Exception as e:
            raise SerperAPIException(f"Async request failed: {str(e)}")


# Backward compatibility - keep the old SerperAPI class name
SerperAPI = GoogleSerperClient


# Convenience functions for backward compatibility
def search(query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for searching with Google Serper.

    Args:
        query: Search query
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        Search results
    """
    client = GoogleSerperClient()
    return client.search(query=query, num=num, **kwargs)


def search_news(query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for news search.

    Args:
        query: Search query
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        News search results
    """
    client = GoogleSerperClient()
    return client.search_news(query=query, num=num, **kwargs)


def search_images(query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for image search.

    Args:
        query: Search query
        num: Number of results
        **kwargs: Additional parameters

    Returns:
        Image search results
    """
    client = GoogleSerperClient()
    return client.search_images(query=query, num=num, **kwargs)


def get_answer(query: str) -> Optional[str]:
    """
    Convenience function to get a direct answer.

    Args:
        query: Question to answer

    Returns:
        Answer string if available
    """
    client = GoogleSerperClient()
    return client.get_answer(query=query)


# Example usage
if __name__ == "__main__":
    # Example 1: Basic search
    try:
        client = GoogleSerperClient()
        results = client.search("artificial intelligence recent developments", num=5)
        print(f"Found {results['total_results']} results")

        for result in results["results"]:
            print(f"\nTitle: {result.title}")
            print(f"URL: {result.url}")
            print(f"Snippet: {result.snippet}")

    except SerperAPIException as e:
        print(f"Search error: {e}")

    # Example 2: Get direct answer
    try:
        answer = client.get_answer("what is the capital of France")
        if answer:
            print(f"\nDirect answer: {answer}")
    except SerperAPIException as e:
        print(f"Answer error: {e}")

    # Example 3: News search
    try:
        news_results = client.search_news("AI breakthrough", num=3)
        print(f"\nNews results: {news_results['total_results']}")
    except SerperAPIException as e:
        print(f"News search error: {e}")

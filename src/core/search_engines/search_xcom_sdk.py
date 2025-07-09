#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_xcom_sdk.py
# code style: PEP 8

"""
[XAI] for (x.com), (twitter.com) live search API using xai-sdk
Specialized search engine using xAI's Grok LLM for live search
API Base URL: (api.x.ai)
"""

import os
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dotenv import load_dotenv
import logging

try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.search import (
        SearchParameters,
        web_source,
        x_source,
        news_source,
        rss_source,
    )
except ImportError:
    raise ImportError("xai-sdk is required. Install with: pip install xai-sdk")

from .base import BaseSearchClient
from .utils.search_token_counter import count_search_tokens

logger = logging.getLogger(__name__)


class XAISearchClient(BaseSearchClient):
    """
    Client for xAI's Live Search API using the official SDK.

    This client provides access to multiple search sources including
    X.com (Twitter), web, news, and RSS feeds through the Grok model.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-3-latest",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the XAISearchClient.

        Args:
            api_key: xAI API key (defaults to XAI_API_KEY from env)
            model: xAI model to use (default: grok-3-latest)
            timeout: Timeout in seconds for API requests
            max_retries: Maximum number of retry attempts
        """
        # Get API key from environment if not provided
        if not api_key:
            load_dotenv()
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "No API key provided, and XAI_API_KEY not found in "
                    "environment variables"
                )

        # Initialize base class (no documented rate limits for xAI)
        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            rate_limiter=None,  # No documented rate limits
        )

        self.model = model
        # Initialize xAI SDK client
        self.client = Client(api_key=self.api_key)

    def _extract_token_usage(self, usage_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage from xAI API response.

        xAI returns detailed usage info including reasoning tokens.
        We extract the basic fields for compatibility.

        Args:
            usage_data: Usage data from xAI API response

        Returns:
            Dict with total_tokens, prompt_tokens, completion_tokens
        """
        if not usage_data:
            return {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        # Extract basic token counts
        total = usage_data.get("total_tokens", 0)
        prompt = usage_data.get("prompt_tokens", 0)
        completion = usage_data.get("completion_tokens", 0)

        # Log detailed usage if available (for debugging)
        if "prompt_tokens_details" in usage_data:
            details = usage_data["prompt_tokens_details"]
            logger.debug(
                f"xAI prompt details: text={details.get('text_tokens', 0)}, "
                f"cached={details.get('cached_tokens', 0)}"
            )

        if "completion_tokens_details" in usage_data:
            details = usage_data["completion_tokens_details"]
            reasoning = details.get("reasoning_tokens", 0)
            if reasoning > 0:
                logger.debug(f"xAI used {reasoning} reasoning tokens")

        return {
            "total_tokens": total,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
        }

    def _build_search_sources(
        self, sources: List[str], **kwargs
    ) -> List[Union[Dict[str, Any], Any]]:
        """
        Build search source configurations using SDK helpers.

        Args:
            sources: List of source types to include
            **kwargs: Source-specific parameters

        Returns:
            List of source configurations
        """
        search_sources = []

        for source_type in sources:
            if source_type == "x":
                # Build X source
                x_params = {}

                # Handle backward compatibility
                x_handles = kwargs.get("x_handles")
                included = kwargs.get("included_x_handles")
                excluded = kwargs.get("excluded_x_handles")

                if x_handles and not included:
                    included = x_handles

                if included and excluded:
                    raise ValueError(
                        "Cannot specify both included_x_handles and excluded_x_handles"
                    )

                if included:
                    if len(included) > 10:
                        raise ValueError(
                            "Maximum 10 handles allowed for included_x_handles"
                        )
                    x_params["included_x_handles"] = included

                if excluded:
                    if len(excluded) > 10:
                        raise ValueError(
                            "Maximum 10 handles allowed for excluded_x_handles"
                        )
                    x_params["excluded_x_handles"] = excluded

                # Add post metric filters
                if "post_favorite_count" in kwargs:
                    x_params["post_favorite_count"] = kwargs["post_favorite_count"]
                if "post_view_count" in kwargs:
                    x_params["post_view_count"] = kwargs["post_view_count"]

                search_sources.append(x_source(**x_params))

            elif source_type == "web":
                # Build web source
                web_params = {}

                if "country" in kwargs:
                    web_params["country"] = kwargs["country"]

                excluded = kwargs.get("excluded_websites", [])
                allowed = kwargs.get("allowed_websites", [])

                if excluded and allowed:
                    raise ValueError(
                        "Cannot specify both excluded_websites and allowed_websites"
                    )

                if excluded:
                    if len(excluded) > 5:
                        raise ValueError(
                            "Maximum 5 websites allowed for excluded_websites"
                        )
                    web_params["excluded_websites"] = excluded

                if allowed:
                    if len(allowed) > 5:
                        raise ValueError(
                            "Maximum 5 websites allowed for allowed_websites"
                        )
                    web_params["allowed_websites"] = allowed

                if "safe_search" in kwargs:
                    web_params["safe_search"] = kwargs["safe_search"]

                search_sources.append(web_source(**web_params))

            elif source_type == "news":
                # Build news source
                news_params = {}

                if "country" in kwargs:
                    news_params["country"] = kwargs["country"]

                excluded = kwargs.get("excluded_websites", [])
                if excluded:
                    if len(excluded) > 5:
                        raise ValueError(
                            "Maximum 5 websites allowed for excluded_websites"
                        )
                    news_params["excluded_websites"] = excluded

                if "safe_search" in kwargs:
                    news_params["safe_search"] = kwargs["safe_search"]

                search_sources.append(news_source(**news_params))

            elif source_type == "rss":
                # Build RSS source
                rss_links = kwargs.get("rss_links", [])
                if not rss_links:
                    raise ValueError("RSS source requires rss_links parameter")

                if len(rss_links) > 1:
                    raise ValueError("Only one RSS link is supported at the moment")

                search_sources.append(rss_source(links=rss_links))

        return search_sources

    def search(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using xAI's Live Search API.

        Args:
            query: Search query
            num: Maximum number of results to return
            **kwargs: Additional parameters including:
                - sources: List of source types ("x", "web", "news", "rss")
                - mode: Search mode ("auto", "on", "off")
                - from_date, to_date: Date range
                - x_handles, included_x_handles, excluded_x_handles
                - post_favorite_count, post_view_count
                - country, excluded_websites, allowed_websites
                - safe_search, rss_links

        Returns:
            Dictionary containing search results with metadata
        """
        if not query:
            raise ValueError("Search query cannot be empty")

        # Extract parameters
        sources = kwargs.pop("sources", None)
        if sources is None:
            # Check if it's an X-specific query
            if detect_x_query(query):
                sources = ["x"]
            else:
                # Default to web and X sources
                sources = ["web", "x"]

        mode = kwargs.pop("mode", "auto")
        from_date = kwargs.pop("from_date", None)
        to_date = kwargs.pop("to_date", None)

        # Build search parameters
        search_params = {
            "mode": mode,
            "max_search_results": num,
            "return_citations": True,
        }

        # Add date range if specified
        if from_date:
            if isinstance(from_date, str):
                search_params["from_date"] = datetime.fromisoformat(from_date)
            else:
                search_params["from_date"] = from_date

        if to_date:
            if isinstance(to_date, str):
                search_params["to_date"] = datetime.fromisoformat(to_date)
            else:
                search_params["to_date"] = to_date

        # Build sources
        search_params["sources"] = self._build_search_sources(sources, **kwargs)

        try:
            # Create chat with search parameters
            chat = self.client.chat.create(
                model=self.model, search_parameters=SearchParameters(**search_params)
            )

            # Add user query
            chat.append(user(query))

            # Get response
            response = chat.sample()

            # Extract content and citations
            content = response.content if hasattr(response, "content") else ""
            citations = response.citations if hasattr(response, "citations") else []

            # Extract usage if available
            usage_data = {}
            if hasattr(response, "usage") and response.usage:
                usage_data = {
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(
                        response.usage, "completion_tokens", 0
                    ),
                }
                # Check for detailed usage
                if hasattr(response.usage, "prompt_tokens_details"):
                    usage_data["prompt_tokens_details"] = (
                        response.usage.prompt_tokens_details
                    )
                if hasattr(response.usage, "completion_tokens_details"):
                    usage_data["completion_tokens_details"] = (
                        response.usage.completion_tokens_details
                    )

            # Process results into standard format
            results = self._process_xai_results(
                content, list(citations), usage_data, query
            )
            return results

        except Exception as e:
            logger.error(f"xAI search error: {str(e)}")
            raise ValueError(f"Error in xAI search: {str(e)}")

    def search_x_content(
        self,
        query: str,
        num: int = 20,
        x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search specifically for X.com content.

        Args:
            query: Search query
            num: Maximum number of search results to return
            x_handles: Optional list of X.com handles to restrict search to
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)
            **kwargs: Additional parameters

        Returns:
            Dictionary containing search results with metadata
        """
        # Call generic search with X source only
        return self.search(
            query=query,
            num=num,
            sources=["x"],
            from_date=from_date,
            to_date=to_date,
            x_handles=x_handles,
            **kwargs,
        )

    async def search_async(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Async version of search method.

        Note: The xai-sdk doesn't have native async support yet,
        so we run the sync version in an executor.

        Args:
            query: Search query
            num: Maximum number of results to return
            **kwargs: Additional parameters

        Returns:
            Dictionary containing search results with metadata
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.search(query, num, **kwargs)
        )

    async def search_x_content_async(
        self,
        query: str,
        num: int = 20,
        x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Async version of search_x_content.

        Args:
            query: Search query
            num: Maximum number of search results to return
            x_handles: Optional list of X.com handles to restrict search to
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)
            **kwargs: Additional parameters

        Returns:
            Dictionary containing search results with metadata
        """
        return await self.search_async(
            query=query,
            num=num,
            sources=["x"],
            from_date=from_date,
            to_date=to_date,
            x_handles=x_handles,
            **kwargs,
        )

    def search_multiple_sources(
        self,
        query: str,
        num: int = 20,
        sources: Optional[List[str]] = None,
        mode: str = "auto",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search across multiple sources.

        This method exists for backward compatibility.
        It just calls the main search method.

        Args:
            query: Search query
            num: Maximum number of search results to return
            sources: List of source types ("x", "web", "news", "rss")
            mode: Search mode ("auto", "on", "off")
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)
            **kwargs: Source-specific parameters

        Returns:
            Dictionary containing search results with metadata
        """
        return self.search(
            query=query,
            num=num,
            sources=sources,
            mode=mode,
            from_date=from_date,
            to_date=to_date,
            **kwargs,
        )

    async def search_multiple_sources_async(
        self,
        query: str,
        num: int = 20,
        sources: Optional[List[str]] = None,
        mode: str = "auto",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Async version of search_multiple_sources.

        Args:
            query: Search query
            num: Maximum number of search results to return
            sources: List of source types ("x", "web", "news", "rss")
            mode: Search mode ("auto", "on", "off")
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)
            **kwargs: Source-specific parameters

        Returns:
            Dictionary containing search results with metadata
        """
        return await self.search_async(
            query=query,
            num=num,
            sources=sources,
            mode=mode,
            from_date=from_date,
            to_date=to_date,
            **kwargs,
        )

    def _process_xai_results(
        self, content: str, citations: List[str], usage_data: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        """
        Process the xAI API response into a standardized format.

        Args:
            content: The content response from xAI
            citations: List of URLs cited in the response
            usage_data: Token usage data from API
            query: Original search query

        Returns:
            Dictionary with search results and metadata
        """
        search_results = []

        # If there are no citations but there is content,
        # create a generic result
        if not citations and content:
            search_results.append(
                {
                    "title": "AI Summary",
                    "url": "https://api.x.ai",
                    "content": (
                        content[:8192] + ("..." if len(content) > 8192 else "")
                    ),
                    "source": "xai_summary",
                }
            )
            # Early return - need to return proper dict format
            usage = count_search_tokens(
                query=query,
                response={"content": content, "results": search_results},
                provider="xai",
                native_usage=(
                    self._extract_token_usage(usage_data) if usage_data else None
                ),
            )
            return {
                "results": search_results,
                "query": query,
                "total_results": len(search_results),
                "usage": usage,
            }

        # Process each citation
        for i, url in enumerate(citations):
            # Try to extract relevant part of the content for this citation
            # For simplicity, we'll just divide the content proportionally
            content_segment = ""
            if content:
                segment_length = len(content) // len(citations)
                start_idx = i * segment_length
                if i < len(citations) - 1:
                    end_idx = start_idx + segment_length
                else:
                    end_idx = len(content)
                content_segment = content[start_idx:end_idx]

            # Determine source type and format title accordingly
            source_type = self._determine_source_type(url)
            title = self._format_title_by_source(url, source_type)

            search_results.append(
                {
                    "title": title,
                    "url": url,
                    "content": content_segment or f"Content from {url}",
                    "source": source_type,
                }
            )

        # Count tokens using native data if available
        usage = count_search_tokens(
            query=query,
            response={"content": content, "citations": citations},
            provider="xai",
            native_usage=(
                self._extract_token_usage(usage_data) if usage_data else None
            ),
        )

        return {
            "results": search_results,
            "query": query,
            "total_results": len(search_results),
            "usage": usage,
        }

    def _determine_source_type(self, url: str) -> str:
        """
        Determine the source type from a URL.

        Args:
            url: The URL to analyze

        Returns:
            Source type string (x, web, news, rss)
        """
        url_lower = url.lower()

        # X.com/Twitter detection
        if "x.com" in url_lower or "twitter.com" in url_lower:
            return "x"

        # News site detection (common news domains)
        news_domains = [
            "cnn.com",
            "bbc.com",
            "bbc.co.uk",
            "nytimes.com",
            "theguardian.com",
            "reuters.com",
            "bloomberg.com",
            "wsj.com",
            "ft.com",
            "apnews.com",
            "npr.org",
            "news.google.com",
            "news.yahoo.com",
        ]
        if any(domain in url_lower for domain in news_domains):
            return "news"

        # RSS feed detection
        if url_lower.endswith((".rss", ".xml", "/feed", "/rss")):
            return "rss"

        # Default to web
        return "web"

    def _format_title_by_source(self, url: str, source_type: str) -> str:
        """
        Format title based on source type and URL.

        Args:
            url: The URL
            source_type: The determined source type

        Returns:
            Formatted title string
        """
        if source_type == "x":
            # Try to extract username from URL
            username_match = None
            if "/status/" in url:
                try:
                    if "x.com/" in url:
                        username_match = url.split("x.com/")[1].split("/")[0]
                    elif "twitter.com/" in url:
                        username_match = url.split("twitter.com/")[1].split("/")[0]
                except (IndexError, AttributeError):
                    pass

            if username_match:
                return f"X Post by @{username_match}"
            return "X.com Post"

        elif source_type == "news":
            # Extract domain name for news
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc
                domain = domain.replace("www.", "")
                return f"News from {domain}"
            except Exception:
                return "News Article"

        elif source_type == "rss":
            return "RSS Feed Item"

        else:
            # Web source - try to extract domain
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc
                domain = domain.replace("www.", "")
                return f"Web: {domain}"
            except Exception:
                return "Web Result"


def detect_x_query(query: str) -> bool:
    """
    Detect if a query is specifically about X.com/Twitter content.

    Args:
        query: The search query

    Returns:
        True if the query is specific to X.com/Twitter, False otherwise
    """
    # Check for X.com specific terms
    x_terms = [
        "x.com",
        "twitter",
        "tweet",
        "tweets",
        "retweet",
        "x post",
        "@",
        "hashtag",
        "#",
        "trending on x",
        "trending on twitter",
        "viral on x",
        "viral on twitter",
        "x thread",
        "twitter thread",
    ]

    query_lower = query.lower()

    # Check if any X terms are in the query
    for term in x_terms:
        if term in query_lower:
            return True

    # Check for @username pattern
    if "@" in query and any(part.startswith("@") for part in query.split()):
        return True

    # Check for hashtag pattern
    if "#" in query and any(part.startswith("#") for part in query.split()):
        return True

    return False


def extract_x_handles(query: str) -> List[str]:
    """
    Extract X.com handles from a query.

    Args:
        query: The search query

    Returns:
        List of X.com handles found in the query
    """
    handles = []

    # Look for @username pattern
    for word in query.split():
        if word.startswith("@"):
            # Remove punctuation at the end if present
            handle = word.strip("@.,;:!?\"'()[]{}")
            if handle:
                handles.append(handle)

    return handles

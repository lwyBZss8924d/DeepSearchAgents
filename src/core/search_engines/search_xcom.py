#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_xcom.py
# code style: PEP 8

"""
x.com(twitter) live search api engine for Agentic Search Tools API Client.
"""

import os
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv
import logging

# setup logging
logger = logging.getLogger(__name__)


class XAISearchClient:
    """
    Client for xAI's Live Search API that provides access to X.com (Twitter)
    content and advanced search capabilities through the Grok model.
    """

    def __init__(
        self,
        query: str = None,
        max_results: int = 20,
        model: str = "grok-3-latest",
        api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Initialize the XAISearchClient.

        Args:
            query: The search query
            max_results: Maximum number of search results to return
            model: xAI model to use (default: grok-3-latest)
            api_key: xAI API key (defaults to XAI_API_KEY from env)
            timeout: Timeout in seconds for API requests
        """
        self.query = query
        self.max_results = max_results
        self.model = model
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.timeout = timeout

        if api_key is None:
            load_dotenv()
            api_key = os.getenv('XAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided, and XAI_API_KEY not found in "
                    "environment variables"
                )

        # Base URL for xAI API
        self.api_base_url = "https://api.x.ai/v1/chat/completions"

        if not self.api_key:
            logger.warning("XAI_API_KEY not found. Make sure it's set in your environment variables.")

    def _construct_search_payload(
        self,
        query: str,
        x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        mode: str = "on"
    ) -> Dict[str, Any]:
        """
        Construct the payload for the xAI Live Search API.

        Args:
            query: The search query
            x_handles: Optional list of X.com handles to restrict search to
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)
            mode: Search mode ("on", "off", "auto")

        Returns:
            Dict containing the API request payload
        """
        # Start with basic payload
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "model": self.model,
            "search_parameters": {
                "mode": mode,
                "max_search_results": self.max_results,
                "return_citations": True
            }
        }

        # Add date range if specified
        if from_date:
            payload["search_parameters"]["from_date"] = from_date
        if to_date:
            payload["search_parameters"]["to_date"] = to_date

        # Configure sources
        sources = []

        # Add X source with optional handles
        x_source = {"type": "x"}
        if x_handles:
            x_source["x_handles"] = x_handles
        sources.append(x_source)

        # Add sources to payload
        payload["search_parameters"]["sources"] = sources

        return payload

    def search_x_content(
        self,
        query: Optional[str] = None,
        x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for X.com content using xAI's Live Search API.

        Args:
            query: Search query (overrides instance query if provided)
            x_handles: Optional list of X.com handles to restrict search to
            from_date: Optional start date in ISO format (YYYY-MM-DD)
            to_date: Optional end date in ISO format (YYYY-MM-DD)

        Returns:
            List of dictionaries containing search results
            with title, url, and content
        """
        search_query = query or self.query

        if not search_query:
            raise ValueError("No search query provided.")

        if not self.api_key:
            logger.warning("XAI API key not available.")

        # Construct payload
        payload = self._construct_search_payload(
            query=search_query,
            x_handles=x_handles,
            from_date=from_date,
            to_date=to_date
        )

        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Make the API request
        try:
            response = requests.post(
                self.api_base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            # Check for successful response
            if response.status_code == 200:
                response_data = response.json()

                # Extract content and citations
                assistant_message = response_data["choices"][0]["message"]
                content = assistant_message.get("content", "")
                citations = assistant_message.get("citations", [])

                # Process results into standard format
                results = self._process_xai_results(content, citations)
                return results

            else:
                error_msg = (
                    f"xAI API request failed with status code "
                    f"{response.status_code}: {response.text}"
                )
                raise ValueError(error_msg)

        except requests.exceptions.Timeout:
            raise ValueError(
                f"xAI API request timed out after {self.timeout} seconds"
            )
        except Exception as e:
            raise ValueError(
                f"Error in xAI search: {str(e)}"
            )

    def _process_xai_results(
        self,
        content: str,
        citations: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Process the xAI API response into a standardized format.

        Args:
            content: The content response from xAI
            citations: List of URLs cited in the response

        Returns:
            List of dictionaries with standardized search result format
        """
        search_results = []

        # If there are no citations but there is content,
        # create a generic result
        if not citations and content:
            search_results.append({
                "title": "X.com Content Summary",
                "url": "https://x.com/search",
                "content": (
                    content[:8192] + ("..." if len(content) > 8192 else "")
                )
            })
            return search_results

        # Process each citation
        for i, url in enumerate(citations):
            # Try to extract relevant part of the content for this citation
            # For simplicity, we'll just divide the content proportionally
            content_segment = ""
            if content:
                segment_length = len(content) // len(citations)
                start_idx = i * segment_length
                end_idx = (
                    start_idx + segment_length
                    if i < len(citations) - 1
                    else len(content)
                )
                content_segment = content[start_idx:end_idx]

            # Clean the URL and extract username if it's a X.com URL
            title = "X.com Post"
            if "x.com" in url or "twitter.com" in url:
                # Try to extract username from URL
                username_match = None
                if "/status/" in url:
                    username_match = (
                        url.split("x.com/")[1].split("/status/")[0]
                        if "x.com/" in url
                        else url.split("twitter.com/")[1].split("/status/")[0]
                    )

                if username_match:
                    title = f"X Post by @{username_match}"

            search_results.append({
                "title": title,
                "url": url,
                "content": content_segment or f"Content from {url}"
            })

        return search_results

    def search(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generic search method that aligns with the SearchClient interface.

        Args:
            query: Search query (overrides instance query if provided)
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries with search results
        """
        search_query = query or self.query

        if not search_query:
            raise ValueError("No search query provided.")

        # Update max_results if provided
        if max_results is not None:
            self.max_results = max_results

        # Call the X-specific search method (no max_results parameter)
        return self.search_x_content(query=search_query)


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
        "x.com", "twitter", "tweet", "tweets", "retweet", "x post",
        "@", "hashtag", "#", "trending on x", "trending on twitter",
        "viral on x", "viral on twitter", "x thread", "twitter thread"
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

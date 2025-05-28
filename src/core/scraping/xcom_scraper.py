#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/xcom_scraper.py
# code style: PEP 8

"""
X.com (Twitter) content extraction API using xAI's Live Search API.

This module provides specialized functionality for extracting content from
X.com (Twitter) posts, profiles, and timelines using xAI's Live Search API.
"""

import os
import re
import logging
from dotenv import load_dotenv
import requests
from typing import Dict, Any, Optional

from .result import ExtractionResult

# Setup logging
logger = logging.getLogger(__name__)

# Default xAI model
XAI_MODEL = "grok-3-latest"

# Default timeout for API requests (seconds)
XAI_TIMEOUT = 120


class XcomScraper:
    """
    A class that uses xAI's Live Search API to extract and process content
    from X.com (Twitter) URLs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = XAI_MODEL,
        output_format: str = "markdown",
        timeout: int = XAI_TIMEOUT
    ):
        """
        Initialize the XcomScraper.

        Args:
            api_key: Optional xAI API key (defaults to env var XAI_API_KEY)
            model: xAI model to use for content extraction
            output_format: Output format ('markdown', 'text', or 'json')
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.model = model
        self.output_format = output_format
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

    @staticmethod
    def is_x_url(url: str) -> bool:
        """
        Check if a URL is from X.com (Twitter).

        Args:
            url: URL to check

        Returns:
            True if the URL is from X.com or Twitter, False otherwise
        """
        return bool(re.search(r'(twitter\.com|x\.com)', url))

    @staticmethod
    def extract_username_from_url(url: str) -> Optional[str]:
        """
        Extract username from X.com URL.

        Args:
            url: X.com URL

        Returns:
            Username if found, None otherwise
        """
        if not url:
            return None

        # Pattern for X.com profile URLs
        match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)(?:/|$)', url)
        if match and match.group(1) not in ['search', 'hashtag', 'explore', 'i', 'settings']:
            return match.group(1)

        return None

    @staticmethod
    def get_url_type(url: str) -> str:
        """
        Determine the type of X.com URL.

        Args:
            url: X.com URL

        Returns:
            URL type: 'profile', 'post', 'search', or 'other'
        """
        if not url:
            return 'other'

        # Check for post URL pattern
        if re.search(r'(?:twitter\.com|x\.com)/[^/]+/status/\d+', url):
            return 'post'

        # Check for search URL pattern
        if re.search(r'(?:twitter\.com|x\.com)/search', url):
            return 'search'

        # Check for profile URL pattern (must come last as it's most general)
        if re.search(r'(?:twitter\.com|x\.com)/[^/]+(?:/|$)', url):
            username = XcomScraper.extract_username_from_url(url)
            if username and username not in ['search', 'hashtag', 'explore', 'i', 'settings']:
                return 'profile'

        return 'other'

    def _construct_scraping_payload(self, url: str) -> Dict[str, Any]:
        """
        Construct the payload for the xAI Live Search API to scrape content.

        Args:
            url: The X.com URL to scrape

        Returns:
            Dict containing the API request payload
        """
        # Extract username if present in URL
        username = self.extract_username_from_url(url)
        x_handles = [username] if username else None

        # Determine URL type
        url_type = self.get_url_type(url)

        # Create appropriate query based on URL type
        if url_type == 'post':
            query = f"Please extract the full content from this X post: {url}. Include the full text of the post, the author's username and display name, the date posted, and any engagement metrics if available. Format the output in {self.output_format} format."
        elif url_type == 'profile':
            query = f"Please extract the profile information for this X user: {url}. Include the username, display name, bio, follower count, following count, and recent posts if available. Format the output in {self.output_format} format."
        elif url_type == 'search':
            query = f"Please extract the search results from this X search: {url}. List the top results with their content, authors, and dates. Format the output in {self.output_format} format."
        else:
            query = f"Please extract and summarize the content from this X page: {url}. Format the output in {self.output_format} format."

        # Start with basic payload
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a helpful assistant specialized in extracting and summarizing content from X.com (Twitter). Please format your response in {self.output_format} format with clear sections."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "model": self.model,
            "search_parameters": {
                "mode": "on",  # Force search mode on
                "return_citations": True,
                "max_search_results": 5  # Limit to avoid excessive data
            }
        }

        # Configure sources to focus on X.com
        sources = [{"type": "x"}]

        # Add x_handles if available
        if x_handles:
            sources[0]["x_handles"] = x_handles

        # Add sources to payload
        payload["search_parameters"]["sources"] = sources

        return payload

    def scrape(self, url: str) -> ExtractionResult:
        """
        Scrape content from the X.com URL using xAI's Live Search API.

        Args:
            url: The X.com URL to scrape

        Returns:
            ExtractionResult containing the extracted content
        """
        # Validate URL
        if not self.is_x_url(url):
            return ExtractionResult(
                name="xcom_scraper",
                success=False,
                error=f"URL '{url}' is not a valid X.com or Twitter URL"
            )

        if not self.api_key:
            return ExtractionResult(
                name="xcom_scraper",
                success=False,
                error="XAI API key not available. Make sure XAI_API_KEY is set in your environment variables."
            )

        # Construct payload for the API request
        payload = self._construct_scraping_payload(url)

        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            # Make the API request
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

                # Generate title based on URL type
                url_type = self.get_url_type(url)
                username = self.extract_username_from_url(url) or "Unknown User"

                if url_type == 'post':
                    title = f"X Post by @{username}"
                elif url_type == 'profile':
                    title = f"X Profile: @{username}"
                elif url_type == 'search':
                    search_term = url.split('q=')[-1].split('&')[0] if 'q=' in url else "unknown"
                    title = f"X Search Results for: {search_term}"
                else:
                    title = f"X.com Content: {url}"

                # Add citations to content if using markdown format
                if self.output_format == 'markdown' and citations:
                    content += "\n\n## Sources\n"
                    for i, citation in enumerate(citations, 1):
                        content += f"{i}. [{citation}]({citation})\n"

                # Build metadata
                metadata = {
                    "title": title,
                    "url": url,
                    "citations": citations,
                    "source": "xai_api"
                }

                # Add username to metadata if available
                if username != "Unknown User":
                    metadata["username"] = username

                return ExtractionResult(
                    name="xcom_scraper",
                    success=True,
                    content=content,
                    metadata=metadata
                )

            else:
                error_msg = f"xAI API request failed with status code {response.status_code}: {response.text}"
                logger.error(error_msg)
                return ExtractionResult(
                    name="xcom_scraper",
                    success=False,
                    error=error_msg
                )

        except requests.exceptions.Timeout:
            error_msg = f"xAI API request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return ExtractionResult(
                name="xcom_scraper",
                success=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error while scraping X.com content: {str(e)}"
            logger.error(error_msg)
            return ExtractionResult(
                name="xcom_scraper",
                success=False,
                error=error_msg
            )

    async def scrape_async(self, url: str, session=None) -> ExtractionResult:
        """
        Asynchronous interface for scraping (for compatibility with JinaReaderScraper).
        Currently just calls the synchronous method as xAI API calls are not async.

        Args:
            url: The X.com URL to scrape
            session: Not used, for compatibility with JinaReaderScraper

        Returns:
            ExtractionResult containing the extracted content
        """
        # This is a synchronous call as the current implementation doesn't use asyncio
        # It's here for API compatibility with JinaReaderScraper
        return self.scrape(url)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/xcom_scraper.py
# code style: PEP 8

"""
X.com (Twitter) content extraction using xAI SDK.

This module provides specialized functionality for extracting content from
X.com (Twitter) posts, profiles, and timelines using xAI's official SDK
with Live Search API capabilities.
"""

import os
import re
import logging
from dotenv import load_dotenv
from typing import Optional

try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.search import SearchParameters, x_source
except ImportError:
    raise ImportError(
        "xai-sdk is required. Install with: pip install xai-sdk"
    )

from .base import BaseScraper
from .result import ExtractionResult

# Setup logging
logger = logging.getLogger(__name__)

# Default xAI model
XAI_MODEL = "grok-4"

# Default timeout for API requests (seconds)
XAI_TIMEOUT = 1200


class XcomScraper(BaseScraper):
    """
    A class that uses xAI SDK to extract and process content
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
        # Get API key from environment if not provided
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('XAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided, and XAI_API_KEY not found in "
                    "environment variables"
                )

        # Initialize parent class
        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_retries=1,
            rate_limiter=None  # X.com scraper doesn't need rate limiting
        )

        self.model = model
        self.output_format = output_format

        # Initialize xAI SDK client
        self.client = Client(api_key=self.api_key)

    @staticmethod
    def is_x_url(url: str) -> bool:
        """
        Check if a URL is from X.com (Twitter).

        Args:
            url: URL to check

        Returns:
            True if the URL is from X.com or Twitter, False otherwise
        """
        # More precise regex that checks for twitter.com or x.com as the domain
        # This prevents matching URLs like github.com/x.com
        # Allows subdomains like api.twitter.com, mobile.x.com etc.
        return bool(re.search(
            r'^https?://(?:[\w\-]+\.)?(?:twitter\.com|x\.com)(?:/|$)',
            url
        ))

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
        if match and match.group(1) not in [
            'search', 'hashtag', 'explore', 'i', 'settings'
        ]:
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
            if username and username not in [
                'search', 'hashtag', 'explore', 'i', 'settings'
            ]:
                return 'profile'

        return 'other'

    def _build_search_parameters(
        self, url: str
    ) -> SearchParameters:
        """
        Build SearchParameters for X.com content extraction.

        Args:
            url: The X.com URL to scrape

        Returns:
            SearchParameters configured for X.com search
        """
        # Extract username if present in URL
        username = self.extract_username_from_url(url)

        # Build X source configuration
        x_config = {}
        if username:
            x_config["included_x_handles"] = [username]

        # Create search parameters
        return SearchParameters(
            mode="on",  # Force search mode on
            sources=[x_source(**x_config)],
            return_citations=True,
            max_search_results=5  # Limit to avoid excessive data
        )

    def _construct_prompt(self, url: str) -> str:
        """
        Construct the prompt for content extraction based on URL type.

        Args:
            url: The X.com URL

        Returns:
            Formatted prompt string
        """
        url_type = self.get_url_type(url)

        if url_type == 'post':
            return (
                f"Please extract the full content from this X post: {url}\n\n"
                "Include the following information:\n"
                "1. Full text of the post\n"
                "2. Author's username and display name\n"
                "3. Date and time posted\n"
                "4. Engagement metrics (likes, retweets, views) if available\n"
                "5. Any media descriptions\n"
                "6. Thread context if applicable\n\n"
                f"Format the output in {self.output_format} format."
            )
        elif url_type == 'profile':
            return (
                f"Please extract the profile information for this X user: "
                f"{url}\n\n"
                "Include:\n"
                "1. Username and display name\n"
                "2. Bio/description\n"
                "3. Follower and following counts\n"
                "4. Recent posts if available\n\n"
                f"Format the output in {self.output_format} format."
            )
        elif url_type == 'search':
            return (
                f"Please extract the search results from this X search: "
                f"{url}\n\n"
                "List the top results with:\n"
                "1. Post content\n"
                "2. Authors\n"
                "3. Dates\n"
                "4. Engagement metrics\n\n"
                f"Format the output in {self.output_format} format."
            )
        else:
            return (
                f"Please extract and summarize the content from this X page: "
                f"{url}\n\n"
                f"Format the output in {self.output_format} format."
            )

    def scrape(self, url: str, **kwargs) -> ExtractionResult:
        """
        Scrape content from the X.com URL using xAI SDK.

        Args:
            url: The X.com URL to scrape
            **kwargs: Additional parameters (for compatibility)

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
                error=(
                    "XAI API key not available. Make sure XAI_API_KEY "
                    "is set in your environment variables."
                )
            )

        try:
            # Build search parameters
            search_parameters = self._build_search_parameters(url)

            # Create chat with search
            chat = self.client.chat.create(
                model=self.model,
                search_parameters=search_parameters,
            )

            # Construct and send prompt
            prompt = self._construct_prompt(url)
            chat.append(user(prompt))

            # Get response
            response = chat.sample()

            # Extract content and citations
            content = response.content if hasattr(
                response, 'content'
            ) else ""
            citations = list(response.citations) if hasattr(
                response, 'citations'
            ) and response.citations else []

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
                "source": "xai_sdk"
            }

            # Add username to metadata if available
            if username != "Unknown User":
                metadata["username"] = username

            # Add usage information if available
            if hasattr(response, 'usage') and response.usage:
                metadata["usage"] = {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }

            return ExtractionResult(
                name="xcom_scraper",
                success=True,
                content=content,
                metadata=metadata
            )

        except Exception as e:
            error_msg = (
                f"Error while scraping X.com content: {str(e)}"
            )
            logger.error(error_msg)
            return ExtractionResult(
                name="xcom_scraper",
                success=False,
                error=error_msg
            )

    async def scrape_async(
        self, url: str, session=None, **kwargs
    ) -> ExtractionResult:
        """
        Asynchronous interface for scraping.

        Currently wraps the synchronous implementation as the xAI SDK
        doesn't have native async support yet.

        Args:
            url: The X.com URL to scrape
            session: Not used, for compatibility
            **kwargs: Additional parameters passed to scrape method

        Returns:
            ExtractionResult containing the extracted content
        """
        # The xAI SDK doesn't have native async support yet,
        # so we wrap the sync implementation
        return self.scrape(url, **kwargs)

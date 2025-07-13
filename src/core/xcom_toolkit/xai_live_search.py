#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/xcom_toolkit/xai_live_search.py
# code style: PEP 8

"""
XAI Live Search Client for X.com Deep Q&A Tool.
Uses xAI SDK's Live Search API to provide advanced X.com search and analysis.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.search import (
        SearchParameters,
        x_source,
    )
except ImportError:
    raise ImportError("xai-sdk is required. Install with: pip install xai-sdk")

logger = logging.getLogger(__name__)


class XAILiveSearchClient:
    """
    Client for xAI's Live Search API focused on X.com content.

    Provides advanced search, content reading, and Q&A capabilities
    for X.com (Twitter) using Grok's AI-powered understanding.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-4",
        timeout: int = 1200,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize XAILiveSearchClient.

        Args:
            api_key: xAI API key (defaults to XAI_API_KEY from env)
            model: Grok model to use (default: grok-3-latest)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
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

        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize xAI SDK client
        self.client = Client(api_key=self.api_key)

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
        match = re.search(
            r'(?:twitter\.com|x\.com)/([^/]+)(?:/|$)',
            url
        )
        if match:
            username = match.group(1)
            # Exclude system pages
            if username not in [
                'search', 'hashtag', 'explore', 'i',
                'settings', 'home', 'notifications'
            ]:
                return username

        return None

    @staticmethod
    def extract_status_id_from_url(url: str) -> Optional[str]:
        """
        Extract status ID from X.com post URL.

        Args:
            url: X.com post URL

        Returns:
            Status ID if found, None otherwise
        """
        if not url:
            return None

        # Pattern for X.com post URLs
        match = re.search(
            r'(?:twitter\.com|x\.com)/[^/]+/status/(\d+)',
            url
        )
        if match:
            return match.group(1)

        return None

    def _build_search_parameters(
        self,
        search_params: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
    ) -> SearchParameters:
        """
        Build SearchParameters for X.com search.

        Args:
            search_params: Optional search filters
            max_results: Maximum number of results

        Returns:
            SearchParameters object
        """
        if search_params is None:
            search_params = {}

        # Build X source configuration
        x_config = {}

        # Handle user handles
        if "included_x_handles" in search_params:
            handles = search_params["included_x_handles"]
            if isinstance(handles, str):
                handles = [handles]
            x_config["included_x_handles"] = handles[:10]  # Max 10

        if "excluded_x_handles" in search_params:
            handles = search_params["excluded_x_handles"]
            if isinstance(handles, str):
                handles = [handles]
            x_config["excluded_x_handles"] = handles[:10]  # Max 10

        # Handle engagement metrics
        if "post_favorite_count" in search_params:
            x_config["post_favorite_count"] = search_params[
                "post_favorite_count"
            ]

        if "post_view_count" in search_params:
            x_config["post_view_count"] = search_params["post_view_count"]

        # Build search parameters
        params = {
            "mode": "on",  # Force search mode on
            "sources": [x_source(**x_config)],
            "return_citations": True,
            "max_search_results": max_results,
        }

        # Handle date range
        if "from_date" in search_params:
            from_date = search_params["from_date"]
            if isinstance(from_date, str):
                from_date = datetime.fromisoformat(from_date)
            params["from_date"] = from_date

        if "to_date" in search_params:
            to_date = search_params["to_date"]
            if isinstance(to_date, str):
                to_date = datetime.fromisoformat(to_date)
            params["to_date"] = to_date

        return SearchParameters(**params)

    def search_x_posts(
        self,
        query: str,
        search_params: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
    ) -> Dict[str, Any]:
        """
        Search X.com posts with advanced filtering.

        Args:
            query: Search query
            search_params: Optional search filters
            max_results: Maximum number of results

        Returns:
            Dict with search results and metadata
        """
        try:
            # Build search parameters
            search_parameters = self._build_search_parameters(
                search_params, max_results
            )

            # Create chat with search
            chat = self.client.chat.create(
                model=self.model,
                search_parameters=search_parameters,
            )

            # Construct search prompt
            prompt = (
                f"Search X.com for: {query}\n\n"
                "Please find and analyze the most relevant X posts. "
                "For each post, include:\n"
                "1. Author username and display name\n"
                "2. Post content (full text)\n"
                "3. Date and time posted\n"
                "4. Engagement metrics (likes, retweets, views)\n"
                "5. Post URL\n"
                "6. Any relevant context or thread information\n\n"
                "Format the results as a structured list with clear "
                "sections for each post."
            )

            chat.append(user(prompt))
            response = chat.sample()

            # Extract structured results
            results = {
                "success": True,
                "query": query,
                "search_params": search_params,
                "content": response.content,
                "citations": list(response.citations) if response.citations else [],
                "posts_found": len(response.citations) if response.citations else 0,
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            }

            logger.info(
                f"X.com search completed: '{query}' - "
                f"found {results['posts_found']} posts"
            )

            return results

        except Exception as e:
            error_msg = f"Error searching X.com posts: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "query": query,
                "search_params": search_params,
            }

    def read_x_post(self, url: str) -> Dict[str, Any]:
        """
        Read and extract detailed content from a specific X.com post URL.

        Args:
            url: X.com post URL

        Returns:
            Dict with post content and metadata
        """
        try:
            # Extract username for targeted search
            username = self.extract_username_from_url(url)
            status_id = self.extract_status_id_from_url(url)

            # Build search parameters targeting the specific post
            search_params = {}
            if username:
                search_params["included_x_handles"] = [username]

            search_parameters = self._build_search_parameters(
                search_params, max_results=5
            )

            # Create chat with search
            chat = self.client.chat.create(
                model=self.model,
                search_parameters=search_parameters,
            )

            # Construct read prompt
            prompt = (
                f"Please extract and analyze the content from this "
                f"specific X.com post: {url}\n\n"
                "Include the following information:\n"
                "1. Author details (username, display name, verification status)\n"
                "2. Full post content (including any threads or replies)\n"
                "3. Timestamp (exact date and time)\n"
                "4. Engagement metrics (likes, retweets, quotes, views)\n"
                "5. Media descriptions (if any images/videos)\n"
                "6. Context (what the post is replying to, if applicable)\n"
                "7. Top replies or notable interactions\n\n"
                "Format the information in a clear, structured way."
            )

            chat.append(user(prompt))
            response = chat.sample()

            # Extract structured results
            results = {
                "success": True,
                "url": url,
                "username": username,
                "status_id": status_id,
                "content": response.content,
                "citations": list(response.citations) if response.citations else [],
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            }

            logger.info(f"Successfully read X.com post: {url}")

            return results

        except Exception as e:
            error_msg = f"Error reading X.com post {url}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "url": url,
            }

    def query_x_content(
        self,
        question: str,
        search_context: Optional[str] = None,
        search_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ask questions about X.com content with optional search context.

        Args:
            question: Question to ask
            search_context: Optional search query for context
            search_params: Optional search filters

        Returns:
            Dict with AI-powered answer and supporting data
        """
        try:
            # Build search parameters if context provided
            if search_context:
                search_parameters = self._build_search_parameters(
                    search_params, max_results=30
                )
            else:
                # Minimal search for general questions
                search_parameters = SearchParameters(
                    mode="auto",
                    sources=[x_source()],
                    return_citations=True,
                )

            # Create chat with search
            chat = self.client.chat.create(
                model=self.model,
                search_parameters=search_parameters,
            )

            # Construct query prompt
            if search_context:
                prompt = (
                    f"Search context: {search_context}\n\n"
                    f"Question: {question}\n\n"
                    "Please search X.com for relevant posts and provide "
                    "a comprehensive answer based on the findings. "
                    "Include specific examples, quotes, and citations "
                    "from X posts to support your answer."
                )
            else:
                prompt = (
                    f"Question about X.com: {question}\n\n"
                    "Please provide a comprehensive answer. If relevant "
                    "X posts can help answer this question, search for "
                    "and include them with proper citations."
                )

            chat.append(user(prompt))
            response = chat.sample()

            # Extract structured results
            results = {
                "success": True,
                "question": question,
                "search_context": search_context,
                "search_params": search_params,
                "answer": response.content,
                "citations": list(response.citations) if response.citations else [],
                "sources_used": len(response.citations) if response.citations else 0,
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            }

            logger.info(
                f"X.com Q&A completed: '{question}' - "
                f"used {results['sources_used']} sources"
            )

            return results

        except Exception as e:
            error_msg = f"Error querying X.com content: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "question": question,
                "search_context": search_context,
            }

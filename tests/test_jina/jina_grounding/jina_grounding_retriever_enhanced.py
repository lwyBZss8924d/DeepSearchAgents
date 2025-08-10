#!/usr/bin/env python3
"""
Enhanced Jina Grounding API as a LangChain Custom Retriever.

This enhanced version includes:
- Session reuse for better performance
- Configuration validation
- Connection pooling
- Batch processing support
- Better error handling

Usage:
    retriever = EnhancedJinaGroundingRetriever(api_key="your-api-key")
    docs = retriever.get_relevant_documents("The Earth is flat")
"""

import os
import time
import asyncio
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import warnings

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import Field, SecretStr, validator

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun

# Import base classes from original implementation
from jina_grounding_retriever import (
    JinaGroundingAPIError,
    JinaGroundingTimeoutError,
    JinaGroundingRateLimitError,
)

# Global session for connection pooling
_HTTP_SESSION: Optional[requests.Session] = None
_AIOHTTP_SESSION: Optional[aiohttp.ClientSession] = None


def get_http_session() -> requests.Session:
    """Get or create a global HTTP session with connection pooling."""
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        _HTTP_SESSION = requests.Session()

        # Configure connection pooling and retries
        retry_strategy = Retry(
            total=0,  # We handle retries ourselves
            backoff_factor=0,
            status_forcelist=[],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False,
        )
        _HTTP_SESSION.mount("http://", adapter)
        _HTTP_SESSION.mount("https://", adapter)

    return _HTTP_SESSION


@asynccontextmanager
async def get_aiohttp_session():
    """Get or create a global aiohttp session with connection pooling."""
    global _AIOHTTP_SESSION
    if _AIOHTTP_SESSION is None or _AIOHTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
        )
        _AIOHTTP_SESSION = aiohttp.ClientSession(connector=connector)

    try:
        yield _AIOHTTP_SESSION
    except Exception:
        # Don't close on error, let session be reused
        raise


class EnhancedJinaGroundingRetriever(BaseRetriever):
    """
    Enhanced LangChain retriever for Jina Grounding API with better resource management.

    Improvements over base implementation:
    - Session reuse for better performance
    - Configuration validation
    - Connection pooling
    - Batch processing support
    - Enhanced error handling
    """

    api_key: SecretStr = Field(description="Jina AI API key")
    base_url: str = Field(default="https://g.jina.ai", description="Grounding API endpoint")
    include_reason: bool = Field(default=True, description="Include full reasoning in metadata")
    trusted_references: Optional[List[str]] = Field(default=None, description="List of trusted websites")
    timeout: int = Field(default=600, description="Request timeout in seconds (max: 600)")
    verbose: bool = Field(default=False, description="Enable verbose logging through callback manager")
    max_retries: int = Field(default=3, description="Maximum number of retries for API calls (min: 1)")
    retry_delay: float = Field(default=1.0, description="Initial delay between retries in seconds (min: 0.1)")
    enable_caching: bool = Field(default=False, description="Enable caching for repeated queries")
    batch_size: int = Field(default=5, description="Maximum batch size for concurrent requests")

    # Private cache
    _cache: Dict[str, List[Document]] = {}

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    @validator("timeout")
    def validate_timeout(cls, v):
        """Validate timeout is within reasonable bounds."""
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 600:
            warnings.warn(f"Timeout of {v}s is very high. Consider using a value under 600s.")
        return v

    @validator("max_retries")
    def validate_max_retries(cls, v):
        """Validate max_retries is positive."""
        if v < 1:
            raise ValueError("max_retries must be at least 1")
        if v > 5:
            warnings.warn(f"max_retries of {v} is high. Consider using 3 or fewer retries.")
        return v

    @validator("retry_delay")
    def validate_retry_delay(cls, v):
        """Validate retry_delay is positive."""
        if v < 0.1:
            raise ValueError("retry_delay must be at least 0.1 seconds")
        if v > 10:
            warnings.warn(f"retry_delay of {v}s is high. Consider using a value under 10s.")
        return v

    @validator("batch_size")
    def validate_batch_size(cls, v):
        """Validate batch_size is reasonable."""
        if v < 1:
            raise ValueError("batch_size must be at least 1")
        if v > 20:
            warnings.warn(f"batch_size of {v} is high. Consider using 10 or fewer for stability.")
        return v

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize the enhanced retriever with validation."""
        if api_key is None:
            api_key = os.getenv("JINA_API_KEY")
            if not api_key:
                raise ValueError(
                    "Jina API key not provided. "
                    "Set JINA_API_KEY environment variable or pass api_key parameter. "
                    "Get your free API key at https://jina.ai/?sui=apikey"
                )

        kwargs["api_key"] = SecretStr(api_key)
        super().__init__(**kwargs)

        # Initialize cache if enabled
        if self.enable_caching:
            self._cache = {}

    def _get_cache_key(self, statement: str) -> str:
        """Generate cache key for a statement."""
        # Include trusted references in cache key if present
        if self.trusted_references:
            refs_hash = hash(tuple(sorted(self.trusted_references)))
            return f"{statement}_{refs_hash}"
        return statement

    def _call_grounding_api(
        self,
        statement: str,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> Dict[str, Any]:
        """Call the Jina Grounding API synchronously with retry logic and session reuse."""
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key.get_secret_value()}"}

        payload: Dict[str, Any] = {"statement": statement}
        if self.trusted_references:
            payload["references"] = self.trusted_references

        session = get_http_session()
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if run_manager and self.verbose and attempt > 0:
                    run_manager.on_text(f"Retry attempt {attempt + 1}/{self.max_retries}\n", verbose=True)

                response = session.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                last_exception = JinaGroundingTimeoutError(f"Request timed out after {self.timeout}s: {str(e)}")
                if run_manager and self.verbose:
                    run_manager.on_text(f"Request timeout: {str(e)}\n", verbose=True)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    last_exception = JinaGroundingRateLimitError(f"Rate limit exceeded: {str(e)}")
                elif e.response.status_code >= 500:
                    last_exception = JinaGroundingAPIError(f"Server error: {str(e)}")
                    if run_manager and self.verbose:
                        run_manager.on_text(f"Server error: {str(e)}\n", verbose=True)
                else:
                    # Client errors (4xx) are not retryable
                    raise JinaGroundingAPIError(f"Client error calling Jina Grounding API: {str(e)}")

            except requests.exceptions.RequestException as e:
                last_exception = JinaGroundingAPIError(f"Request error: {str(e)}")
                if run_manager and self.verbose:
                    run_manager.on_text(f"Request error: {str(e)}\n", verbose=True)

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2**attempt)
                if run_manager and self.verbose:
                    run_manager.on_text(f"Waiting {delay:.1f}s before retry...\n", verbose=True)
                time.sleep(delay)

        # All retries exhausted
        raise last_exception or JinaGroundingAPIError(
            f"Failed to call Jina Grounding API after {self.max_retries} attempts"
        )

    async def _acall_grounding_api(
        self,
        statement: str,
        run_manager: Optional[AsyncCallbackManagerForRetrieverRun] = None,
    ) -> Dict[str, Any]:
        """Call the Jina Grounding API asynchronously with retry logic and session reuse."""
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key.get_secret_value()}"}

        payload: Dict[str, Any] = {"statement": statement}
        if self.trusted_references:
            payload["references"] = self.trusted_references

        last_exception = None

        async with get_aiohttp_session() as session:
            for attempt in range(self.max_retries):
                try:
                    if run_manager and self.verbose and attempt > 0:
                        await run_manager.on_text(f"Retry attempt {attempt + 1}/{self.max_retries}\n", verbose=True)

                    async with session.post(
                        self.base_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        response.raise_for_status()
                        return await response.json()

                except asyncio.TimeoutError as e:
                    last_exception = JinaGroundingTimeoutError(f"Request timed out after {self.timeout}s: {str(e)}")
                    if run_manager and self.verbose:
                        await run_manager.on_text(f"Request timeout: {str(e)}\n", verbose=True)

                except aiohttp.ClientResponseError as e:
                    if e.status == 429:
                        last_exception = JinaGroundingRateLimitError(f"Rate limit exceeded: {str(e)}")
                    elif e.status >= 500:
                        last_exception = JinaGroundingAPIError(f"Server error: {str(e)}")
                        if run_manager and self.verbose:
                            await run_manager.on_text(f"Server error: {str(e)}\n", verbose=True)
                    else:
                        # Client errors (4xx) are not retryable
                        raise JinaGroundingAPIError(f"Client error calling Jina Grounding API: {str(e)}")

                except aiohttp.ClientError as e:
                    last_exception = JinaGroundingAPIError(f"Request error: {str(e)}")
                    if run_manager and self.verbose:
                        await run_manager.on_text(f"Request error: {str(e)}\n", verbose=True)

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    if run_manager and self.verbose:
                        await run_manager.on_text(f"Waiting {delay:.1f}s before retry...\n", verbose=True)
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception or JinaGroundingAPIError(
            f"Failed to call Jina Grounding API after {self.max_retries} attempts"
        )

    def _parse_grounding_response(self, response: Dict[str, Any], statement: str) -> List[Document]:
        """Parse the Grounding API response into LangChain Documents."""
        documents = []

        # Extract main results
        data = response.get("data", {})
        factuality = data.get("factuality", 0)
        result = data.get("result", False)
        reason = data.get("reason", "")
        references = data.get("references", [])
        usage = data.get("usage", {})

        # If no references, create a summary document
        if not references:
            doc = Document(
                page_content=reason if reason else f"No references found for: {statement}",
                metadata={
                    "source": "grounding_summary",
                    "statement": statement,
                    "factuality_score": factuality,
                    "grounding_result": result,
                    "is_summary": True,
                    "token_usage": usage.get("tokens", 0),
                },
            )
            if self.include_reason:
                doc.metadata["reason"] = reason
            documents.append(doc)
            return documents

        # Convert each reference to a Document
        for ref in references:
            metadata = {
                "source": ref.get("url", ""),
                "statement": statement,
                "is_supportive": ref.get("isSupportive", False),
                "factuality_score": factuality,
                "grounding_result": result,
                "is_summary": False,
                "token_usage": usage.get("tokens", 0) // len(references),  # Distribute tokens
            }

            if self.include_reason and documents == []:  # Add reason to first doc
                metadata["reason"] = reason

            doc = Document(page_content=ref.get("keyQuote", ""), metadata=metadata)
            documents.append(doc)

        return documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Get fact-checking documents for a statement with caching support."""
        # Check cache if enabled
        if self.enable_caching:
            cache_key = self._get_cache_key(query)
            if cache_key in self._cache:
                if run_manager and self.verbose:
                    run_manager.on_text(f"Cache hit for: {query}\n", verbose=True)
                return self._cache[cache_key]

        # Log the query
        if run_manager and self.verbose:
            run_manager.on_text(f"Fact-checking statement: {query}\n", verbose=True)
            run_manager.on_text(f"Using Jina Grounding API at {self.base_url}\n", verbose=True)
            if self.trusted_references:
                run_manager.on_text(
                    f"Using trusted references: {', '.join(self.trusted_references[:3])}...\n",
                    verbose=True,
                )

        # Call the Grounding API
        response = self._call_grounding_api(query, run_manager)

        # Log response info
        if run_manager and self.verbose:
            data = response.get("data", {})
            factuality = data.get("factuality", 0)
            num_refs = len(data.get("references", []))
            run_manager.on_text(
                f"Received response: factuality={factuality:.2f}, references={num_refs}\n",
                verbose=True,
            )

        # Parse response into documents
        documents = self._parse_grounding_response(response, query)

        # Cache results if enabled
        if self.enable_caching:
            self._cache[cache_key] = documents

        # Log final results
        if run_manager and self.verbose:
            run_manager.on_text(f"Returning {len(documents)} documents\n", verbose=True)

        return documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[AsyncCallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Async version with caching support."""
        # Check cache if enabled
        if self.enable_caching:
            cache_key = self._get_cache_key(query)
            if cache_key in self._cache:
                if run_manager and self.verbose:
                    await run_manager.on_text(f"Cache hit for: {query}\n", verbose=True)
                return self._cache[cache_key]

        # Log the query
        if run_manager and self.verbose:
            await run_manager.on_text(f"Fact-checking statement: {query}\n", verbose=True)
            await run_manager.on_text(f"Using Jina Grounding API at {self.base_url}\n", verbose=True)
            if self.trusted_references:
                await run_manager.on_text(
                    f"Using trusted references: {', '.join(self.trusted_references[:3])}...\n",
                    verbose=True,
                )

        # Call the Grounding API asynchronously
        response = await self._acall_grounding_api(query, run_manager)

        # Log response info
        if run_manager and self.verbose:
            data = response.get("data", {})
            factuality = data.get("factuality", 0)
            num_refs = len(data.get("references", []))
            await run_manager.on_text(
                f"Received response: factuality={factuality:.2f}, references={num_refs}\n",
                verbose=True,
            )

        # Parse response into documents
        documents = self._parse_grounding_response(response, query)

        # Cache results if enabled
        if self.enable_caching:
            self._cache[cache_key] = documents

        # Log final results
        if run_manager and self.verbose:
            await run_manager.on_text(f"Returning {len(documents)} documents\n", verbose=True)

        return documents

    async def abatch_get_relevant_documents(
        self,
        queries: List[str],
        *,
        run_manager: Optional[AsyncCallbackManagerForRetrieverRun] = None,
    ) -> List[List[Document]]:
        """
        Batch fact-check multiple statements concurrently.

        Args:
            queries: List of statements to fact-check
            run_manager: Optional callback manager

        Returns:
            List of document lists, one for each query
        """
        if run_manager and self.verbose:
            await run_manager.on_text(
                f"Batch fact-checking {len(queries)} statements (batch_size={self.batch_size})\n", verbose=True
            )

        results = []

        # Process in batches to avoid overwhelming the API
        for i in range(0, len(queries), self.batch_size):
            batch = queries[i : i + self.batch_size]

            if run_manager and self.verbose:
                await run_manager.on_text(
                    f"Processing batch {i//self.batch_size + 1} ({len(batch)} queries)\n", verbose=True
                )

            # Create tasks for concurrent execution
            tasks = [self._aget_relevant_documents(query, run_manager=run_manager) for query in batch]

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results and exceptions
            for query, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    if run_manager and self.verbose:
                        await run_manager.on_text(f"Error processing '{query}': {str(result)}\n", verbose=True)
                    # Return empty list for failed queries
                    results.append([])
                else:
                    results.append(result)

        return results

    def clear_cache(self):
        """Clear the document cache."""
        if self.enable_caching:
            self._cache.clear()
            if self.verbose:
                print("Cache cleared")


# Convenience functions
def create_enhanced_jina_grounding_retriever(
    api_key: Optional[str] = None,
    include_reason: bool = True,
    trusted_references: Optional[List[str]] = None,
    verbose: bool = False,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    enable_caching: bool = False,
    batch_size: int = 5,
    **kwargs,
) -> EnhancedJinaGroundingRetriever:
    """
    Create an enhanced Jina Grounding retriever instance.

    Improvements over base implementation:
    - Session reuse for better performance
    - Configuration validation with warnings
    - Connection pooling
    - Optional caching for repeated queries
    - Batch processing support

    Args:
        api_key: Jina AI API key (or set JINA_API_KEY env var)
        include_reason: Whether to include full reasoning in metadata
        trusted_references: Optional list of trusted websites
        verbose: Enable verbose logging through callback manager
        max_retries: Maximum number of retries for API calls
        retry_delay: Initial delay between retries in seconds
        enable_caching: Enable caching for repeated queries
        batch_size: Maximum batch size for concurrent requests
        **kwargs: Additional parameters for the retriever

    Returns:
        Configured EnhancedJinaGroundingRetriever instance
    """
    return EnhancedJinaGroundingRetriever(
        api_key=api_key,
        include_reason=include_reason,
        trusted_references=trusted_references,
        verbose=verbose,
        max_retries=max_retries,
        retry_delay=retry_delay,
        enable_caching=enable_caching,
        batch_size=batch_size,
        **kwargs,
    )


# Cleanup function for global sessions
def cleanup_sessions():
    """Clean up global HTTP sessions."""
    global _HTTP_SESSION, _AIOHTTP_SESSION

    if _HTTP_SESSION:
        _HTTP_SESSION.close()
        _HTTP_SESSION = None

    if _AIOHTTP_SESSION and not _AIOHTTP_SESSION.closed:
        asyncio.create_task(_AIOHTTP_SESSION.close())
        _AIOHTTP_SESSION = None

#!/usr/bin/env python3
"""
Jina Grounding API as a LangChain Custom Retriever.

This module implements the Jina Grounding API (g.jina.ai) as a LangChain retriever,
allowing fact-checking functionality to be used within the LangChain ecosystem.

The retriever takes a statement as input and returns documents with fact-checking
results, including supporting/contradicting references with factuality scores.

Usage:
    retriever = JinaGroundingRetriever(api_key="your-api-key")
    docs = retriever.get_relevant_documents("The Earth is flat")

    # Each doc contains:
    # - page_content: The key quote from the reference
    # - metadata: URL, factuality score, support status, etc.
"""

import os
import time
import asyncio
from typing import List, Optional, Dict, Any
import aiohttp
import requests
from pydantic import Field, SecretStr

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun


class JinaGroundingRetriever(BaseRetriever):
    """
    Custom LangChain retriever that uses Jina Grounding API for fact-checking.

    This retriever takes a statement and returns documents containing:
    - References that support or contradict the statement
    - Factuality scores and grounding results
    - Detailed reasoning about the statement's truthfulness

    Attributes:
        api_key: Jina AI API key (get free at https://jina.ai)
        base_url: API endpoint (default: https://g.jina.ai)
        include_reason: Whether to include the full reasoning in metadata
        trusted_references: Optional list of trusted websites
        timeout: Request timeout in seconds
    """

    api_key: SecretStr = Field(description="Jina AI API key")
    base_url: str = Field(default="https://g.jina.ai", description="Grounding API endpoint")
    include_reason: bool = Field(default=True, description="Include full reasoning in metadata")
    trusted_references: Optional[List[str]] = Field(default=None, description="List of trusted websites")
    timeout: int = Field(default=120, description="Request timeout in seconds")
    verbose: bool = Field(default=False, description="Enable verbose logging through callback manager")
    max_retries: int = Field(default=2, description="Maximum number of retries for API calls")
    retry_delay: float = Field(default=2.0, description="Initial delay between retries in seconds")

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize the retriever with API key from parameter or environment."""
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

    def _call_grounding_api(
        self,
        statement: str,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> Dict[str, Any]:
        """Call the Jina Grounding API synchronously with retry logic."""
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key.get_secret_value()}"}

        payload: Dict[str, Any] = {"statement": statement}
        if self.trusted_references:
            payload["references"] = self.trusted_references

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if run_manager and self.verbose and attempt > 0:
                    run_manager.on_text(f"Retry attempt {attempt + 1}/{self.max_retries}\n", verbose=True)

                response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                last_exception = e
                if run_manager and self.verbose:
                    run_manager.on_text(f"Request timeout: {str(e)}\n", verbose=True)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500:  # Server errors are retryable
                    last_exception = e
                    if run_manager and self.verbose:
                        run_manager.on_text(f"Server error: {str(e)}\n", verbose=True)
                else:
                    # Client errors (4xx) are not retryable
                    raise RuntimeError(f"Client error calling Jina Grounding API: {str(e)}")

            except requests.exceptions.RequestException as e:
                last_exception = e
                if run_manager and self.verbose:
                    run_manager.on_text(f"Request error: {str(e)}\n", verbose=True)

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2**attempt)
                time.sleep(delay)

        # All retries exhausted
        raise RuntimeError(
            f"Failed to call Jina Grounding API after {self.max_retries} attempts: {str(last_exception)}"
        )

    async def _acall_grounding_api(
        self,
        statement: str,
        run_manager: Optional[AsyncCallbackManagerForRetrieverRun] = None,
    ) -> Dict[str, Any]:
        """Call the Jina Grounding API asynchronously with retry logic."""
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key.get_secret_value()}"}

        payload: Dict[str, Any] = {"statement": statement}
        if self.trusted_references:
            payload["references"] = self.trusted_references

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if run_manager and self.verbose and attempt > 0:
                    await run_manager.on_text(f"Retry attempt {attempt + 1}/{self.max_retries}\n", verbose=True)

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        response.raise_for_status()
                        return await response.json()

            except asyncio.TimeoutError as e:
                last_exception = e
                if run_manager and self.verbose:
                    await run_manager.on_text(f"Request timeout: {str(e)}\n", verbose=True)

            except aiohttp.ClientResponseError as e:
                if e.status >= 500:  # Server errors are retryable
                    last_exception = e
                    if run_manager and self.verbose:
                        await run_manager.on_text(f"Server error: {str(e)}\n", verbose=True)
                else:
                    # Client errors (4xx) are not retryable
                    raise RuntimeError(f"Client error calling Jina Grounding API: {str(e)}")

            except aiohttp.ClientError as e:
                last_exception = e
                if run_manager and self.verbose:
                    await run_manager.on_text(f"Request error: {str(e)}\n", verbose=True)

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2**attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        raise RuntimeError(
            f"Failed to call Jina Grounding API after {self.max_retries} attempts: {str(last_exception)}"
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
        """
        Get fact-checking documents for a statement.

        Args:
            query: The statement to fact-check
            run_manager: Callback manager for the retrieval run

        Returns:
            List of documents with fact-checking results
        """
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
        """
        Async version of get_relevant_documents.

        Args:
            query: The statement to fact-check
            run_manager: Async callback manager for the retrieval run

        Returns:
            List of documents with fact-checking results
        """
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

        # Log final results
        if run_manager and self.verbose:
            await run_manager.on_text(f"Returning {len(documents)} documents\n", verbose=True)

        return documents


# Custom exceptions for better error handling
class JinaGroundingAPIError(Exception):
    """Base exception for Jina Grounding API errors."""

    pass


class JinaGroundingTimeoutError(JinaGroundingAPIError):
    """Raised when API request times out."""

    pass


class JinaGroundingRateLimitError(JinaGroundingAPIError):
    """Raised when API rate limit is exceeded."""

    pass


# Convenience function for creating the retriever
def create_jina_grounding_retriever(
    api_key: Optional[str] = None,
    include_reason: bool = True,
    trusted_references: Optional[List[str]] = None,
    verbose: bool = False,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs,
) -> JinaGroundingRetriever:
    """
    Create a Jina Grounding retriever instance.

    Args:
        api_key: Jina AI API key (or set JINA_API_KEY env var)
        include_reason: Whether to include full reasoning in metadata
        trusted_references: Optional list of trusted websites
        verbose: Enable verbose logging through callback manager
        max_retries: Maximum number of retries for API calls
        retry_delay: Initial delay between retries in seconds
        **kwargs: Additional parameters for the retriever

    Returns:
        Configured JinaGroundingRetriever instance

    Example:
        >>> retriever = create_jina_grounding_retriever(
        ...     api_key="your-key",
        ...     verbose=True,
        ...     max_retries=3
        ... )
        >>> docs = retriever.get_relevant_documents("Python was created in 1991")
        >>> for doc in docs:
        ...     print(f"Source: {doc.metadata['source']}")
        ...     print(f"Quote: {doc.page_content}")
        ...     print(f"Supports statement: {doc.metadata['is_supportive']}")
    """
    return JinaGroundingRetriever(
        api_key=api_key,
        include_reason=include_reason,
        trusted_references=trusted_references,
        verbose=verbose,
        max_retries=max_retries,
        retry_delay=retry_delay,
        **kwargs,
    )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/ranking/jina_embedder.py
# code style: PEP 8

"""
Jina AI Embeddings API for getting text or image embeddings.
"""

import os
import aiohttp
import asyncio
from typing import List, Optional, Dict, Union, Any
import torch
from dotenv import load_dotenv


class JinaAIEmbedder:
    """
    Implementation of Jina AI Embeddings API (/v1/embeddings)
    for getting text or image embeddings.
    Supports multiple input types and models.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "jina-clip-v2",  # multimodal model
        api_base_url: str = "https://api.jina.ai/v1/embeddings",
        max_concurrent_requests: int = 3,
        timeout: int = 600
    ):
        """
        Initialize JinaEmbedder.

        Args:
            api_key (Optional[str]): Jina AI API key.
            model (str): The name of the embedding model to use.
                         Common options: "jina-embeddings-v3", "jina-clip-v2"
            api_base_url (str): The URL of the Jina Embeddings API.
            max_concurrent_requests (int):
                Maximum number of concurrent requests.
            timeout (int): Request timeout (seconds).
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('JINA_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided, and JINA_API_KEY not found in "
                    "environment variables"
                )

        self.api_url = api_base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
        self.model = model
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self._session = None
        self._semaphore = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get reusable aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get concurrency control semaphore"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self._semaphore

    async def _close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_embeddings_async(
        self,
        inputs: List[Union[str, Dict[str, str]]],
        embedding_type: str = "float",
        task: Optional[str] = None,
        dimensions: Optional[int] = None,
        normalized: bool = False,
        truncate: bool = False,
        batch_size: int = 50
    ) -> torch.Tensor:
        """
        Asynchronously get embeddings for a list of inputs.

        Supports efficient processing of large input batches,
        automatically batching requests.

        Args:
            inputs: Input list (text or image dictionaries)
            embedding_type: Returned embedding format
            task: Specify downstream task to optimize embeddings
            dimensions: Embedding dimension truncation
            normalized: Whether to normalize embeddings
            truncate: Whether to automatically truncate long inputs
            batch_size: Maximum number of inputs per batch

        Returns:
            torch.Tensor: Tensor containing embeddings
        """
        if not inputs:
            raise ValueError("Input list cannot be empty")

        # Batch inputs for efficiency
        batches = [
            inputs[i:i + batch_size]
            for i in range(0, len(inputs), batch_size)
        ]

        all_embeddings = []
        session = await self._get_session()
        semaphore = await self._get_semaphore()

        try:
            tasks = []
            for batch in batches:
                # Prepare request data
                data = self._prepare_request_data(
                    batch,
                    embedding_type,
                    task,
                    dimensions,
                    normalized,
                    truncate
                )
                # Use semaphore to control concurrency, not create all tasks
                tasks.append(
                    self._process_batch_with_semaphore(
                        session, data, semaphore
                    )
                )

            # Batch requests in parallel, but controlled by semaphore
            batch_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            # Process results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"Batch {i+1}/{len(batches)} failed: {str(result)}")
                    # Continue processing other batches, not interrupt
                    continue
                all_embeddings.extend(result)

        except Exception as e:
            raise RuntimeError(f"Embedding processing failed: {str(e)}")

        # Merge all batch results
        if not all_embeddings:
            raise RuntimeError("No valid embeddings obtained after "
                               "processing all batches")

        return torch.tensor(all_embeddings, dtype=torch.float)

    def _prepare_request_data(
        self,
        batch: List[Any],
        embedding_type: str,
        task: Optional[str],
        dimensions: Optional[int],
        normalized: bool,
        truncate: bool
    ) -> Dict:
        """Prepare request data dictionary"""
        data = {
            "model": self.model,
            "input": batch,
            "embedding_type": embedding_type,
            "normalized": normalized,
            "truncate": truncate
        }

        # Add optional parameters
        if task:
            data["task"] = task
        if dimensions:
            data["dimensions"] = dimensions

        return data

    async def _process_batch_with_semaphore(
        self,
        session: aiohttp.ClientSession,
        data: Dict,
        semaphore: asyncio.Semaphore
    ) -> List:
        """Use semaphore to process a single batch, control concurrency"""
        async with semaphore:
            return await self._process_batch(session, data)

    async def _process_batch(
        self,
        session: aiohttp.ClientSession,
        data: Dict
    ) -> List:
        """Process a single batch of embedding requests"""
        retry_count = 0
        max_retries = 3
        retry_delay = 1

        while retry_count <= max_retries:
            try:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        # Handle errors that need to be retried
                        if response.status in (
                            429, 500, 502, 503, 504
                        ) and retry_count < max_retries:
                            retry_count += 1
                            wait_time = retry_delay * (2 ** (retry_count - 1))
                            print(f"API request failed (status code: "
                                  f"{response.status}), retrying in "
                                  f"{wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue

                        error_text = await response.text()
                        raise RuntimeError(
                            f"Jina API returned error ({response.status}): "
                            f"{error_text}"
                        )

                    api_result = await response.json()

                    if 'data' in api_result and isinstance(
                        api_result['data'], list
                    ):
                        embeddings_data = [
                            item.get("embedding")
                            for item in api_result['data']
                        ]
                        # Filter out possible None values
                        valid_embeddings = [
                            emb for emb in embeddings_data if emb is not None
                        ]

                        if len(valid_embeddings) != len(data["input"]):
                            print(
                                f"Warning: Requested {len(data['input'])} "
                                f"embeddings, but received only "
                                f"{len(valid_embeddings)} valid embeddings."
                            )
                        if not valid_embeddings:
                            raise RuntimeError("API response did not contain "
                                               "valid embedding data")

                        # Ensure data format is correct
                        if not all(isinstance(e, (list, tuple))
                                   for e in valid_embeddings):
                            raise RuntimeError("Embedding data format is"
                                               "incorrect (not list/tuple)")

                        return valid_embeddings
                    else:
                        raise RuntimeError(
                            f"Jina API response format error: {api_result}"
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Network error retry
                if retry_count < max_retries:
                    retry_count += 1
                    wait_time = retry_delay * (2 ** (retry_count - 1))
                    print(f"Network error ({str(e)}), retrying in "
                          f"{wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"Jina API request failed: {str(e)}")

    def get_embeddings(
        self,
        inputs: List[Union[str, Dict[str, str]]],
        embedding_type: str = "float",
        task: Optional[str] = None,
        dimensions: Optional[int] = None,
        normalized: bool = False,
        truncate: bool = False
    ) -> torch.Tensor:
        """
        Get embeddings for input list (synchronous version).

        This method is a synchronous wrapper for the asynchronous method,
        maintaining backward compatibility.

        Args:
            inputs: Input list (text or image dictionaries)
            embedding_type: Returned embedding format
            task: Specify downstream task to optimize embeddings
            dimensions: Embedding dimension truncation
            normalized: Whether to normalize embeddings
            truncate: Whether to automatically truncate long inputs

        Returns:
            torch.Tensor: Tensor containing embeddings
        """
        # Set event loop to run asynchronous code in synchronous environment
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in event loop, use nest_asyncio
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            # If no event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.get_embeddings_async(
                inputs,
                embedding_type,
                task,
                dimensions,
                normalized,
                truncate
            )
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

    def __del__(self):
        """Destructor, ensure resource cleanup"""
        if hasattr(self, '_session') and (
            self._session and not self._session.closed
        ):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception:
                pass

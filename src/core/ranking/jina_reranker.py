#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/ranking/jina_reranker.py
# code style: PEP 8

"""
Jina AI Reranker API for reranking documents.
"""

import os
import aiohttp
import asyncio
from typing import List, Optional, Dict, Union, Any
from dotenv import load_dotenv


class JinaAIReranker:
    """
    Implementation of document reranking using Jina AI's Rerank API
    (https://api.jina.ai/v1/rerank). This class directly calls the API
    to get reranking results.

    Supports the latest jina-reranker-m0 multimodal reranker,
    which can handle text and image content.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "jina-reranker-m0",  # m0 is the multimodal model
        max_concurrent_requests: int = 3,  # concurrent request limit
        timeout: int = 600,  # timeout setting (seconds)
        retry_attempts: int = 2  # retry attempts
    ):
        """
        Initialize Jina reranker.

        Args:
            api_key (Optional[str]):
                Jina AI API key. If None: will attempt to load from
                environment variable JINA_API_KEY.
            model (str):
                Name of the Jina Reranker model to use.
                Default: "jina-reranker-m0" (multimodal model).
                Optional: "jina-reranker-v2-base-multilingual" (text-only)
            max_concurrent_requests (int):
                Maximum number of concurrent requests.
            timeout (int): Request timeout (seconds).
            retry_attempts (int): Number of retry attempts on request failure.
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('JINA_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided, and JINA_API_KEY not found in "
                    "environment variables"
                )

        # use rerank API address
        self.api_url = 'https://api.jina.ai/v1/rerank'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
        self.model = model
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self._session = None
        self._semaphore = None

        # check if using multimodal model
        self.is_multimodal = "m0" in model

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

    async def rerank_async(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int] = None,
        batch_size: int = 100,  # batch size
        query_image_url: Optional[str] = None  # query image URL
    ) -> List[Dict[str, Union[str, float, int]]]:
        """
        Asynchronously rerank a list of documents using Jina AI Rerank API.

        Supports large-scale reranking, automatically batching to improve
        efficiency.
        For jina-reranker-m0 supports multimodal content.

        Args:
            query: The query string for reranking.
            documents: List of document strings or dictionaries containing
                text and image URL pairs. For pure text: ['doc1', 'doc2', ...]
                For multimodal: [
                    {'text': 'doc1', 'image_url': 'example.com/img1.jpg'},
                    {'text': 'doc2', 'image_url': None},
                    ...
                ]
            top_n: Specify the number of most relevant documents to return.
            batch_size: Maximum number of documents per batch.
            query_image_url: URL of the query image (only for m0 model).

        Returns:
            List of reranked documents, containing relevance scores and
            original indices.
        """
        if not documents:
            return []

        # use reusable session and semaphore
        session = await self._get_session()
        semaphore = await self._get_semaphore()

        # preprocess documents, ensure correct format
        processed_documents = self._preprocess_documents(documents)

        # if document number is less than batch size, process directly
        if len(processed_documents) <= batch_size:
            return await self._process_rerank_request_with_retry(
                query, processed_documents, top_n, session,
                offset=0, query_image_url=query_image_url
            )

        # otherwise, batch process
        batches = [
            processed_documents[i:i + batch_size]
            for i in range(0, len(processed_documents), batch_size)
        ]

        all_results = []
        offset = 0  # for tracking original indices

        try:
            tasks = []
            for batch in batches:
                tasks.append(
                    self._process_batch_with_semaphore(
                        session, semaphore, query, batch, top_n, offset,
                        query_image_url
                    )
                )
                offset += len(batch)

            # parallel execution of all batches, but controlled by semaphore
            batch_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            # process results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"Batch {i+1}/{len(batches)} failed: {str(result)}")
                    # continue processing after failure
                    continue

                all_results.extend(result)

        except Exception as e:
            print(f"Reranking failed: {str(e)}")
            # return empty list when failed
            return []

        # if top_n is specified, sort by relevance and truncate results
        if top_n and len(all_results) > top_n:
            # sort by relevance score in descending order
            all_results.sort(
                key=lambda x: x.get('relevance_score', 0),
                reverse=True
            )
            return all_results[:top_n]

        return all_results

    def _preprocess_documents(
        self,
        documents: List[Union[str, Dict[str, Any]]]
    ) -> List[Union[str, Dict[str, Any]]]:
        """
        Preprocess document list, ensure correct format

        Args:
            documents: List of documents, can be a list of strings or a list
                of dictionaries.

        Returns:
            Processed document list
        """
        processed = []

        for doc in documents:
            if isinstance(doc, str):
                # pure text document, for multimodal model, convert to dict
                if self.is_multimodal:
                    processed.append({"text": doc})
                else:
                    processed.append(doc)
            elif isinstance(doc, dict):
                # already in dict format
                if not self.is_multimodal:
                    # if not multimodal model, but dict input, extract text
                    text = doc.get('text', '')
                    processed.append(text)
                else:
                    # for multimodal model, keep dict format
                    processed.append(doc)
            else:
                # unsupported format
                print(f"Warning: unsupported document format: {type(doc)}, "
                      "will be skipped")

        return processed

    async def _process_batch_with_semaphore(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int],
        offset: int = 0,
        query_image_url: Optional[str] = None
    ) -> List[Dict[str, Union[str, float, int]]]:
        """Use semaphore to process a single batch, control concurrency"""
        async with semaphore:
            return await self._process_batch(
                session, query, documents, top_n, offset, query_image_url
            )

    async def _process_batch(
        self,
        session: aiohttp.ClientSession,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int],
        offset: int = 0,  # original index offset
        query_image_url: Optional[str] = None
    ) -> List[Dict[str, Union[str, float, int]]]:
        """Process a single batch of reranking requests"""
        return await self._process_rerank_request_with_retry(
            query, documents, top_n, session, offset, query_image_url
        )

    async def _process_rerank_request_with_retry(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None,
        offset: int = 0,
        query_image_url: Optional[str] = None,
        attempt: int = 0
    ) -> List[Dict[str, Union[str, float, int]]]:
        """Process reranking request, including retry logic"""
        provided_session = session is not None

        if not provided_session:
            session = await self._get_session()

        try:
            # prepare request data
            data = {
                "model": self.model,
                "query": query,
                "documents": documents,
                # request full sorting, then truncate
                "top_n": len(documents),
                "return_documents": True  # return document content
            }

            # for multimodal model, add query image
            if self.is_multimodal and query_image_url:
                data["query_image_url"] = query_image_url

            async with session.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    # handle errors that need to be retried
                    if (response.status in (429, 500, 502, 503, 504)
                            and attempt < self.retry_attempts):
                        # exponential backoff retry
                        wait_time = 2 ** attempt
                        print(f"Waiting {wait_time} seconds before retrying "
                              "reranking request")
                        await asyncio.sleep(wait_time)
                        return await self._process_rerank_request_with_retry(
                            query, documents, top_n, session, offset,
                            query_image_url, attempt + 1
                        )

                    error_text = await response.text()
                    error_msg = (
                        f"Jina Rerank API returned error ({response.status}): "
                        f"{error_text}"
                    )
                    print(error_msg)
                    return []

                api_result = await response.json()

                if 'results' in api_result:
                    # process results, adjust index
                    results = []
                    for item in api_result['results']:
                        # extract document content
                        doc_content = ""
                        if 'document' in item:
                            if isinstance(item['document'], dict):
                                # multimodal model returned format
                                doc_content = item['document'].get('text', '')
                                # can handle image URL here
                                image_url = item['document'].get('image_url')
                                if image_url:
                                    # keep image URL information
                                    pass
                            else:
                                # pure text
                                doc_content = str(item['document'])

                        results.append({
                            "document": doc_content,
                            "relevance_score": item.get('relevance_score', 0),
                            "index": item.get('index', 0) + offset
                        })

                    return results
                else:
                    print(f"Warning: Jina Rerank API response missing "
                          f"'results' field: {api_result}")
                    return []

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < self.retry_attempts:
                wait_time = 2 ** attempt
                print(f"Network error ({str(e)}), waiting {wait_time} "
                      "seconds before retrying")
                await asyncio.sleep(wait_time)
                return await self._process_rerank_request_with_retry(
                    query, documents, top_n, session, offset,
                    query_image_url, attempt + 1
                )
            else:
                print(f"Reranking request failed: {str(e)}")
                return []
        except Exception as e:
            print(f"Unknown error occurred while processing reranking request:"
                  f"{str(e)}")
            return []

    async def _process_rerank_request(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Union[str, float, int]]]:
        """Process single reranking request, no retry mechanism (deprecated)"""
        data = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_n if top_n is not None else len(documents),
            "return_documents": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Jina Rerank API returned error ({response.status}): "
                        f"{error_text}"
                    )

                api_result = await response.json()

                if 'results' in api_result:
                    return [
                        {
                            "document": item.get('document', {}).get('text', ''),
                            "relevance_score": item.get('relevance_score'),
                            "index": item.get('index')
                        }
                        for item in api_result['results']
                    ]
                else:
                    print(f"Warning: Jina Rerank API response missing "
                          f"'results' field: {api_result}")
                    return []

    def rerank(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int] = None,
        query_image_url: Optional[str] = None
    ) -> List[Dict[str, Union[str, float, int]]]:
        """
        Use Jina AI Rerank API to rerank document list (synchronous version).

        This method is a synchronous wrapper for the asynchronous method,
        maintaining backward compatibility.
        Supports multimodal reranking (using jina-reranker-m0 model).

        Args:
            query: Query string for reranking.
            documents: List of documents to rerank (strings or dictionaries
                containing text and image URLs).
            top_n: Specify the number of most relevant documents to return.
            query_image_url: Query image URL (only for m0 model).

        Returns:
            List of reranked documents, sorted by relevance score in descending
            order.
        """
        # set event loop to run asynchronous code in synchronous environment
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # if already in event loop, use nest_asyncio
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            # if no event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.rerank_async(
                query, documents, top_n, query_image_url=query_image_url
            )
        )

    async def get_reranked_documents_async(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int] = None,
        query_image_url: Optional[str] = None
    ) -> List[str]:
        """
        Asynchronously get reranked document text list, sorted by relevance.

        Args:
            query: Query string.
            documents: List of documents to rerank.
            top_n: Return top n documents.
            query_image_url: Query image URL (only for m0 model).

        Returns:
            List of reranked document text, sorted by relevance.
        """
        reranked_results = await self.rerank_async(
            query, documents, top_n, query_image_url=query_image_url
        )
        return [result['document'] for result in reranked_results]

    def get_reranked_documents(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        top_n: Optional[int] = None,
        query_image_url: Optional[str] = None
    ) -> List[str]:
        """
        Return reranked document text list, sorted by relevance (synchronous
        version).

        Args:
            query: Query string.
            documents: List of documents to rerank.
            top_n: Return top n documents.
            query_image_url: Query image URL (only for m0 model).

        Returns:
            List of reranked document text, sorted by relevance.
        """
        reranked_results = self.rerank(
            query, documents, top_n, query_image_url=query_image_url
        )
        return [result['document'] for result in reranked_results]

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

    def __del__(self):
        """Destructor, ensure resource cleanup"""
        if (hasattr(self, '_session') and self._session
                and not self._session.closed):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception:
                pass

import os
import aiohttp
import asyncio
from typing import List, Optional
from dotenv import load_dotenv


class JinaAISegmenter:
    """
    Implementation of Jina AI Segmenter API (/v1/segment)
    for splitting text into smaller, more manageable chunks.

    This is useful for breaking down long texts into smaller segments
    that can be passed to the embeddings API or other downstream tasks.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        tokenizer: str = "o200k_base",  # Default tokenizer model
        api_base_url: str = "https://api.jina.ai/v1/segment",
        max_concurrent_requests: int = 3,
        timeout: int = 600,
        retry_attempts: int = 2
    ):
        """
        Initialize JinaAISegmenter.

        Args:
            api_key (Optional[str]): Jina AI API key.
                If None, will load from environment variable JINA_API_KEY.
            tokenizer (str): The tokenizer model to use.
            api_base_url (str): The URL of the Jina Segmenter API.
            max_concurrent_requests (int): Maximum number of concurrent requests.
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

        self.api_url = api_base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
        self.tokenizer = tokenizer
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self._session = None
        self._semaphore = None

        # Get your Jina AI API key for free: https://jina.ai/?sui=apikey

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

    async def split_text_async(
        self,
        text: str,
        max_chunk_length: int = 1000,
        return_tokens: bool = False,
        return_chunks: bool = True,
        session: Optional[aiohttp.ClientSession] = None,
        attempt: int = 0
    ) -> List[str]:
        """
        Asynchronously split text into chunks using Jina AI Segmenter API.

        Args:
            text (str): The text to split into chunks.
            max_chunk_length (int): Maximum length of each chunk.
            return_tokens (bool): Whether to return the tokens.
            return_chunks (bool): Whether to return the chunks.
            session (Optional[aiohttp.ClientSession]): Optional session for requests.
            attempt (int): Current retry attempt.

        Returns:
            List[str]: A list of text chunks.
        """
        if not text:
            return []

        semaphore = await self._get_semaphore()
        provided_session = session is not None

        if not provided_session:
            session = await self._get_session()

        try:
            async with semaphore:
                data = {
                    "content": text,
                    "tokenizer": self.tokenizer,
                    "return_tokens": return_tokens,
                    "return_chunks": return_chunks,
                    "max_chunk_length": max_chunk_length
                }

                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        # Handle errors that need to be retried
                        if (response.status in (429, 500, 502, 503, 504) 
                                and attempt < self.retry_attempts):
                            # Exponential backoff retry
                            wait_time = 2 ** attempt
                            print(f"API request failed (status code: "
                                  f"{response.status}), retrying in "
                                  f"{wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            return await self.split_text_async(
                                text, max_chunk_length, return_tokens, 
                                return_chunks, session, attempt + 1
                            )

                        error_text = await response.text()
                        error_msg = (
                            f"Jina Segmenter API returned error "
                            f"({response.status}): {error_text}"
                        )
                        print(error_msg)
                        return []

                    api_result = await response.json()

                    if 'chunks' in api_result:
                        # Fix: chunks field is a string array, not an object array
                        # Return the chunks array directly, do not try to access the 'text' property
                        return api_result['chunks']
                    else:
                        print(f"Warning: Jina Segmenter API response missing "
                              f"'chunks' field: {api_result}")
                        return []

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            # Network error retry
            if attempt < self.retry_attempts:
                wait_time = 2 ** attempt
                print(f"Network error ({str(e)}), retrying in "
                      f"{wait_time} seconds")
                await asyncio.sleep(wait_time)
                return await self.split_text_async(
                    text, max_chunk_length, return_tokens, 
                    return_chunks, session, attempt + 1
                )
            else:
                print(f"Segmenter API request failed: {str(e)}")
                return []
        except Exception as e:
            print(f"Unknown error occurred while processing segmenter "
                  f"request: {str(e)}")
            return []
        finally:
            if not provided_session:
                # Do not close the session here, reuse for other requests
                pass

    async def split_texts_async(
        self, 
        texts: List[str],
        max_chunk_length: int = 1000,
        return_tokens: bool = False,
        return_chunks: bool = True,
        batch_size: int = 10
    ) -> List[List[str]]:
        """
        Asynchronously split multiple texts into chunks.

        Args:
            texts (List[str]): List of texts to split.
            max_chunk_length (int): Maximum length of each chunk.
            return_tokens (bool): Whether to return the tokens.
            return_chunks (bool): Whether to return the chunks.
            batch_size (int): Number of texts to process in each batch.

        Returns:
            List[List[str]]: A list of lists, where each inner list contains
                             the chunks for one input text.
        """
        if not texts:
            return []

        # Process in batches to avoid overwhelming the API
        batches = [
            texts[i:i + batch_size]
            for i in range(0, len(texts), batch_size)
        ]

        all_results = []
        session = await self._get_session()

        try:
            for batch in batches:
                tasks = []
                for text in batch:
                    tasks.append(
                        self.split_text_async(
                            text, max_chunk_length, return_tokens, 
                            return_chunks, session
                        )
                    )

                batch_results = await asyncio.gather(
                    *tasks, return_exceptions=True
                )

                # Process results, handle any exceptions
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        print(f"Error processing text {i}: {str(result)}")
                        all_results.append([])
                    else:
                        all_results.append(result)

            return all_results

        except Exception as e:
            print(f"Error processing batch of texts: {str(e)}")
            return [[] for _ in texts]

    def split_text(
        self,
        text: str,
        max_chunk_length: int = 1000,
        return_tokens: bool = False,
        return_chunks: bool = True
    ) -> List[str]:
        """
        Split text into chunks using Jina AI Segmenter API (synchronous version).

        This method is a synchronous wrapper for the asynchronous method,
        maintaining backward compatibility.

        Args:
            text (str): The text to split into chunks.
            max_chunk_length (int): Maximum length of each chunk.
            return_tokens (bool): Whether to return the tokens.
            return_chunks (bool): Whether to return the chunks.

        Returns:
            List[str]: A list of text chunks.
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
            self.split_text_async(
                text, max_chunk_length, return_tokens, return_chunks
            )
        )

    def split_texts(
        self,
        texts: List[str],
        max_chunk_length: int = 1000,
        return_tokens: bool = False,
        return_chunks: bool = True
    ) -> List[List[str]]:
        """
        Split multiple texts into chunks (synchronous version).

        Args:
            texts (List[str]): List of texts to split.
            max_chunk_length (int): Maximum length of each chunk.
            return_tokens (bool): Whether to return the tokens.
            return_chunks (bool): Whether to return the chunks.

        Returns:
            List[List[str]]: A list of lists, where each inner list contains
                             the chunks for one input text.
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
            self.split_texts_async(
                texts, max_chunk_length, return_tokens, return_chunks
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
        if hasattr(self, '_session') and self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception:
                pass


# Compatibility wrapper that implements the same interface as the original Chunker
class Chunker:
    """
    A wrapper class that provides the same interface as the original Chunker
    but uses JinaAISegmenter under the hood.
    """
    def __init__(
        self,
        chunk_size: int = 150,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        length_function: callable = len,
        api_key: Optional[str] = None,
        tokenizer: str = "o200k_base"
    ):
        """
        Initialize the Chunker with specified parameters.

        Args:
            chunk_size (int, optional):
                Target size for each chunk in tokens. Defaults to 150.
            chunk_overlap (int, optional):
                Not used directly, maintained for compatibility. Defaults to 50.
            separators (List[str], optional):
                Not used directly, maintained for compatibility.
            length_function (callable, optional):
                Not used directly, maintained for compatibility.
            api_key (Optional[str], optional):
                Jina AI API key. Defaults to None.
            tokenizer (str, optional):
                The tokenizer model to use. Defaults to "o200k_base".
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap  # Kept for compatibility
        self.separators = separators  # Kept for compatibility
        self.length_function = length_function  # Kept for compatibility

        # Initialize the Jina Segmenter with the given parameters
        self.segmenter = JinaAISegmenter(
            api_key=api_key,
            tokenizer=tokenizer
        )

    def split_text(self, text: str) -> List[str]:
        """
        Split a single text into chunks using Jina Segmenter API.

        Args:
            text (str): The input text to be split into chunks.

        Returns:
            List[str]: A list of text chunks.
        """
        return self.segmenter.split_text(
            text=text,
            max_chunk_length=self.chunk_size,
            return_tokens=False,
            return_chunks=True
        )

    def split_texts(self, texts: List[str]) -> List[List[str]]:
        """
        Split multiple texts into chunks using Jina Segmenter API.

        Args:
            texts (List[str]): A list of input texts to be split into chunks.

        Returns:
            List[List[str]]: A list of lists, where each inner list contains
                the chunks for one input text.
        """
        return self.segmenter.split_texts(
            texts=texts,
            max_chunk_length=self.chunk_size,
            return_tokens=False,
            return_chunks=True
        )

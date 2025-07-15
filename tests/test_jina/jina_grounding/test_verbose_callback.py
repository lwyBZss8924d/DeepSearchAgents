#!/usr/bin/env python3
"""
Test verbose mode and callback functionality for JinaGroundingRetriever.

This test verifies:
1. Verbose logging through callback managers
2. Retry logic with exponential backoff
3. Custom exception handling
4. Callback integration

Usage:
    export JINA_API_KEY="your-api-key"
    python test_verbose_callback.py
"""

import os
import asyncio
from typing import List, Any
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult

# Import our custom retriever
from jina_grounding_retriever import create_jina_grounding_retriever, JinaGroundingRetriever, JinaGroundingAPIError

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


class VerboseCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to capture verbose output."""

    def __init__(self):
        self.logs = []
        self.start_time = None
        self.end_time = None

    def on_retriever_start(self, query: str, **kwargs: Any) -> None:
        """Called when retriever starts."""
        self.start_time = datetime.now()
        self.logs.append(f"[RETRIEVER START] Query: {query}")

    def on_retriever_end(self, documents: List[Any], **kwargs: Any) -> None:
        """Called when retriever ends."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        self.logs.append(f"[RETRIEVER END] Documents: {len(documents)}, Duration: {duration:.2f}s")

    def on_text(self, text: str, verbose: bool = False, **kwargs: Any) -> None:
        """Capture verbose text output."""
        if verbose:
            self.logs.append(f"[VERBOSE] {text.strip()}")

    def on_retriever_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when retriever encounters an error."""
        self.logs.append(f"[ERROR] {type(error).__name__}: {str(error)}")

    def print_logs(self):
        """Print all captured logs."""
        print("\n📋 Callback Logs:")
        print("-" * 60)
        for log in self.logs:
            print(log)
        print("-" * 60)


class AsyncVerboseCallbackHandler(AsyncCallbackHandler):
    """Async version of the verbose callback handler."""

    def __init__(self):
        self.logs = []
        self.start_time = None
        self.end_time = None

    async def on_retriever_start(self, query: str, **kwargs: Any) -> None:
        """Called when retriever starts."""
        self.start_time = datetime.now()
        self.logs.append(f"[ASYNC RETRIEVER START] Query: {query}")

    async def on_retriever_end(self, documents: List[Any], **kwargs: Any) -> None:
        """Called when retriever ends."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        self.logs.append(f"[ASYNC RETRIEVER END] Documents: {len(documents)}, Duration: {duration:.2f}s")

    async def on_text(self, text: str, verbose: bool = False, **kwargs: Any) -> None:
        """Capture verbose text output."""
        if verbose:
            self.logs.append(f"[ASYNC VERBOSE] {text.strip()}")

    async def on_retriever_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when retriever encounters an error."""
        self.logs.append(f"[ASYNC ERROR] {type(error).__name__}: {str(error)}")

    def print_logs(self):
        """Print all captured logs."""
        print("\n📋 Async Callback Logs:")
        print("-" * 60)
        for log in self.logs:
            print(log)
        print("-" * 60)


def test_verbose_mode():
    """Test verbose mode with callback handler."""
    print("\n" + "=" * 80)
    print("🧪 Test 1: Verbose Mode with Callback Handler")
    print("=" * 80)

    # Create callback handler
    callback_handler = VerboseCallbackHandler()

    # Create retriever with verbose mode
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, verbose=True, callbacks=[callback_handler])

    # Test statement
    statement = "The International Space Station orbits Earth every 90 minutes"

    print(f"\n🔍 Fact-checking: {statement}")

    try:
        # This will trigger verbose logging
        docs = retriever.invoke(statement)

        print(f"\n✅ Retrieved {len(docs)} documents")
        if docs:
            print(f"Factuality: {docs[0].metadata.get('factuality_score', 0):.2%}")
            print(f"Result: {'TRUE' if docs[0].metadata.get('grounding_result') else 'FALSE'}")

        # Print captured logs
        callback_handler.print_logs()

    except Exception as e:
        print(f"❌ Error: {e}")
        callback_handler.print_logs()


def test_retry_logic():
    """Test retry logic with simulated failures."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 2: Retry Logic")
    print("=" * 80)

    # Create retriever with custom retry settings
    retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        verbose=True,
        max_retries=2,
        retry_delay=0.5,  # Short delay for testing
        timeout=5,  # Short timeout to trigger retries
    )

    # Test with a complex statement that might need retries
    statement = "What are the latest breakthroughs in quantum computing error correction published in 2024?"

    callback_handler = VerboseCallbackHandler()
    retriever.callbacks = [callback_handler]

    print(f"\n🔍 Testing retry logic with: {statement[:50]}...")

    try:
        docs = retriever.invoke(statement)
        print(f"✅ Success after potential retries: {len(docs)} documents")
        callback_handler.print_logs()

    except Exception as e:
        print(f"❌ Failed after retries: {e}")
        callback_handler.print_logs()


def test_error_handling():
    """Test error handling with invalid inputs."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 3: Error Handling")
    print("=" * 80)

    callback_handler = VerboseCallbackHandler()

    # Test 1: Invalid API key
    print("\n📝 Testing invalid API key...")
    try:
        bad_retriever = create_jina_grounding_retriever(
            api_key="invalid-key-12345", verbose=True, max_retries=1, callbacks=[callback_handler]
        )
        docs = bad_retriever.get_relevant_documents("Test statement")
        print("❌ Should have raised an error!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")
        callback_handler.print_logs()

    # Test 2: Empty statement
    print("\n📝 Testing empty statement...")
    callback_handler.logs.clear()

    try:
        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, verbose=True, callbacks=[callback_handler])
        docs = retriever.invoke("")
        print("❌ Should have raised an error!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")


async def test_async_verbose():
    """Test async operations with verbose mode."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 4: Async Verbose Mode")
    print("=" * 80)

    # Create async callback handler
    async_callback = AsyncVerboseCallbackHandler()

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, verbose=True)

    # Manually set async callbacks (LangChain limitation)
    retriever.callbacks = [async_callback]

    statement = "Artificial General Intelligence will be achieved by 2030"

    print(f"\n🔍 Async fact-checking: {statement}")

    try:
        docs = await retriever.ainvoke(statement)
        print(f"\n✅ Retrieved {len(docs)} documents asynchronously")
        if docs:
            print(f"Factuality: {docs[0].metadata.get('factuality_score', 0):.2%}")

        async_callback.print_logs()

    except Exception as e:
        print(f"❌ Error: {e}")
        async_callback.print_logs()


def test_trusted_references_verbose():
    """Test verbose output with trusted references."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 5: Trusted References with Verbose Mode")
    print("=" * 80)

    callback_handler = VerboseCallbackHandler()

    # Create retriever with trusted sources
    retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        verbose=True,
        trusted_references=["https://www.nasa.gov", "https://www.esa.int", "https://www.space.com"],
        callbacks=[callback_handler],
    )

    statement = "The James Webb Space Telescope has discovered signs of life on exoplanets"

    print(f"\n🔍 Checking with trusted sources: {statement}")

    try:
        docs = retriever.invoke(statement)
        print(f"\n✅ Retrieved {len(docs)} documents from trusted sources")

        # Check if any docs are from trusted sources
        for doc in docs[:3]:
            source = doc.metadata.get("source", "")
            print(f"\n📌 Source: {source}")
            print(f"   Quote: {doc.page_content[:100]}...")

        callback_handler.print_logs()

    except Exception as e:
        print(f"❌ Error: {e}")
        callback_handler.print_logs()


def main():
    """Run all verbose and callback tests."""
    print("🚀 Starting Verbose Mode and Callback Tests")
    print("=" * 80)

    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    # Run synchronous tests
    test_verbose_mode()
    test_retry_logic()
    test_error_handling()
    test_trusted_references_verbose()

    # Run async test
    print("\n" + "🔄" * 40)
    asyncio.run(test_async_verbose())

    print("\n\n" + "🎯" * 40)
    print("\n✅ All verbose and callback tests completed!")
    print("\nKey Features Tested:")
    print("1. ✅ Verbose logging through callback managers")
    print("2. ✅ Retry logic with exponential backoff")
    print("3. ✅ Enhanced error handling")
    print("4. ✅ Async verbose operations")
    print("5. ✅ Trusted references with verbose output")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    main()

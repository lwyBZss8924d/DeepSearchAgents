#!/usr/bin/env python3
"""
Test Jina DeepSearch API with LangChain ChatOpenAI interface.

This test demonstrates:
1. LangChain ChatOpenAI integration with Jina DeepSearch
2. Streaming responses with callback handlers
3. Structured outputs with JSON schema
4. Multi-turn conversations
5. Async/concurrent queries
6. Error handling

Note: Jina DeepSearch provides an OpenAI-compatible API endpoint. However,
some DeepSearch-specific parameters (like reasoning_effort, max_returned_urls, etc.)
may not be available through the standard OpenAI interface. These tests focus on
features that work through the OpenAI-compatible endpoint.

Prerequisites:
- Set JINA_API_KEY environment variable
- Get your Jina AI API key for free: https://jina.ai/?sui=apikey
- Install dependencies: pip install langchain-openai

Usage:
    export JINA_API_KEY="your-api-key"
    python test_jina_DS_api.py
"""

import json
import os
import datetime
from typing import List, Dict, Any

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
import asyncio

OPENAI_API_KEY = "JINA_API_KEY"
JINA_API_KEY = os.getenv("JINA_API_KEY")


# ------- Helper Functions -------


def save_response_to_file(response_data: Dict[str, Any], filename: str = "response.json") -> str:
    """Save the complete response to a JSON log file."""
    # Create logs directory if it doesn't exist
    log_dir = "test-logs"
    os.makedirs(log_dir, exist_ok=True)

    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)

    return filepath


# ------- LangChain ChatOpenAI Test for Jina DeepSearch API -------


class StreamingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to process streaming events from DeepSearch."""

    def __init__(self):
        self.tokens = []
        self.reasoning_tokens = []
        self.is_reasoning = False

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        print("🚀 Starting LangChain DeepSearch request...")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # In DeepSearch, reasoning is often wrapped in <think> tags
        if "<think>" in token:
            self.is_reasoning = True
        elif "</think>" in token:
            self.is_reasoning = False

        if self.is_reasoning:
            self.reasoning_tokens.append(token)
        else:
            self.tokens.append(token)
            print(token, end="", flush=True)

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        print("\n✅ Streaming completed!")
        print(f"📊 Total tokens: {len(self.tokens)}")
        if self.reasoning_tokens:
            print(f"🤔 Reasoning tokens: {len(self.reasoning_tokens)}")


def test_deepsearch_with_langchain():
    """
    Test Jina DeepSearch API using LangChain's ChatOpenAI interface.

    This demonstrates how to use Jina DeepSearch as an OpenAI-compatible endpoint
    with LangChain, including streaming, structured outputs, and advanced features.
    """
    print("=" * 80)
    print("🧪 Testing Jina DeepSearch with LangChain ChatOpenAI")
    print("=" * 80)

    # Initialize ChatOpenAI with Jina DeepSearch endpoint
    # Get your Jina AI API key for free: https://jina.ai/?sui=apikey
    chat = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
        temperature=0,  # DeepSearch doesn't use temperature
        timeout=300,
        max_retries=2,
    )

    # Test 1: Basic non-streaming query
    print("\n📝 Test 1: Basic Non-Streaming Query")
    print("-" * 40)

    try:
        response = chat.invoke([HumanMessage(content="What are the core features in Jina AI's embedding-v4 model?")])

        print("Response:", response.content)
        print(f"✅ Basic test passed! Response length: {len(response.content)} chars")

        # Save response
        test_data = {
            "test": "basic_langchain",
            "response": response.content,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        save_response_to_file(test_data, "langchain_basic_test.json")

    except Exception as e:
        print(f"❌ Basic test failed: {e}")

    # Test 2: Streaming with callback handler
    print("\n\n📝 Test 2: Streaming with Callback Handler")
    print("-" * 40)

    try:
        callback_handler = StreamingCallbackHandler()
        streaming_chat = ChatOpenAI(
            model="jina-deepsearch-v2",
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
            streaming=True,
            callbacks=[callback_handler],
            timeout=300,
        )

        response = streaming_chat.invoke(
            [
                HumanMessage(
                    content="Search for the latest LiteLLM nightly version tag releases and summarize the changes"
                )
            ]
        )

        print(f"\n✅ Streaming test passed! Final response length: {len(response.content)} chars")

    except Exception as e:
        print(f"❌ Streaming test failed: {e}")

    # Test 3: Structured output with response_format
    print("\n\n📝 Test 3: Structured Output with JSON Schema")
    print("-" * 40)

    try:
        # Create chat instance with structured output
        structured_chat = ChatOpenAI(
            model="jina-deepsearch-v2",
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
            model_kwargs={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "Name of the product"},
                            "latest_version": {"type": "string", "description": "Latest version number"},
                            "release_date": {"type": "string", "description": "Release date of latest version"},
                            "key_features": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of key features",
                            },
                            "sources": {"type": "array", "items": {"type": "string"}, "description": "Source URLs"},
                        },
                        "required": ["product_name", "latest_version", "key_features"],
                    },
                }
            },
            timeout=300,
        )

        response = structured_chat.invoke(
            [HumanMessage(content="What is the latest version of Jina Embeddings-v4 model and its key features?")]
        )

        # Parse structured response
        try:
            content = response.content if isinstance(response.content, str) else str(response.content)
            structured_data = json.loads(content)
            print("Structured Response:")
            print(json.dumps(structured_data, indent=2))
            print("✅ Structured output test passed!")
        except json.JSONDecodeError:
            content = response.content if isinstance(response.content, str) else str(response.content)
            print(f"Response (non-JSON): {content[:200]}...")
            structured_data = {"raw_response": content}

        # Save structured response
        save_response_to_file(structured_data, "langchain_structured_test.json")

    except Exception as e:
        print(f"❌ Structured output test failed: {e}")

    # Test 4: Complex queries with longer timeout
    print("\n\n📝 Test 4: Complex Query with Extended Timeout")
    print("-" * 40)

    try:
        # Note: Only standard OpenAI parameters are supported through the ChatOpenAI interface
        # DeepSearch automatically handles complex queries with its internal optimization
        advanced_chat = ChatOpenAI(
            model="jina-deepsearch-v2",
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
            temperature=0,
            timeout=600,  # Longer timeout for complex queries
        )

        response = advanced_chat.invoke(
            [
                HumanMessage(
                    content=(
                        "Compare Jina's embedding models (jina-clip-v2 vs jina-embeddings-v4) in terms of performance, "
                        "features, and use cases. Include benchmark results if available."
                    )
                )
            ]
        )

        print("Advanced Response Preview:")
        content = str(response.content)
        print(content[:500] + "..." if len(content) > 500 else content)
        print(f"\n✅ Advanced parameters test passed! Response length: {len(content)} chars")

    except Exception as e:
        print(f"❌ Advanced parameters test failed: {e}")

    # Test 5: Multi-turn conversation
    print("\n\n📝 Test 5: Multi-turn Conversation")
    print("-" * 40)

    try:
        conversation_chat = ChatOpenAI(
            model="jina-deepsearch-v2",
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
            temperature=0,
            timeout=300,
        )

        # Multi-turn conversation
        messages: List[Any] = [
            HumanMessage(content="What is Jina AI's DeepSearch API?"),
        ]

        response1 = conversation_chat.invoke(messages)
        content1 = str(response1.content)
        print("Turn 1 Response:", content1[:200] + "...")

        # Add response to conversation
        messages.append(AIMessage(content=content1))
        messages.append(
            HumanMessage(
                content="How does it compare to other web deep-search APIs like Perplexity , `you.com` or `exa.ai` ?"
            )
        )

        response2 = conversation_chat.invoke(messages)
        content2 = str(response2.content)
        print("\nTurn 2 Response:", content2[:200] + "...")

        print("\n✅ Multi-turn conversation test passed!")

        # Save conversation
        conversation_data = {
            "test": "multi_turn_conversation",
            "turns": [
                {"role": "user", "content": messages[0].content},
                {"role": "assistant", "content": content1},
                {"role": "user", "content": messages[2].content},
                {"role": "assistant", "content": content2},
            ],
            "timestamp": datetime.datetime.now().isoformat(),
        }
        save_response_to_file(conversation_data, "langchain_conversation_test.json")

    except Exception as e:
        print(f"❌ Multi-turn conversation test failed: {e}")

    print("\n" + "=" * 80)
    print("🎉 LangChain ChatOpenAI tests completed!")
    print("=" * 80)


async def test_deepsearch_langchain_async():
    """
    Test async usage of Jina DeepSearch with LangChain.
    """
    print("\n" + "=" * 80)
    print("🧪 Testing Async LangChain with Jina DeepSearch")
    print("=" * 80)

    # Initialize async ChatOpenAI
    async_chat = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
        temperature=0,
        timeout=300,
    )

    try:
        # Async invoke
        print("\n📝 Async Test: Concurrent Queries")
        print("-" * 40)

        queries = [
            "1. What are the latest updates in Jina AI's reranker models?",
            "2. How does Jina's ColBERT v2 compare to traditional rerankers?",
            "3. What are the best practices for using Jina embeddings in LLM-DeepSearch case production?",
        ]

        # Create tasks for concurrent execution
        tasks = [async_chat.ainvoke([HumanMessage(content=query)]) for query in queries]

        # Execute concurrently
        print("🚀 Sending 3 queries concurrently...")
        start_time = datetime.datetime.now()
        responses = await asyncio.gather(*tasks)
        end_time = datetime.datetime.now()

        print(f"⏱️  Total time: {(end_time - start_time).total_seconds():.2f} seconds")

        for i, (query, response) in enumerate(zip(queries, responses)):
            print(f"\nQuery {i+1}: {query}")
            print(f"Response preview: {response.content[:150]}...")

        print("\n✅ Async test passed!")

        # Save async results
        async_data = {
            "test": "async_concurrent",
            "queries": queries,
            "responses": [r.content for r in responses],
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        save_response_to_file(async_data, "langchain_async_test.json")

    except Exception as e:
        print(f"❌ Async test failed: {e}")


def test_deepsearch_error_handling():
    """
    Test error handling with LangChain and DeepSearch.
    """
    print("\n" + "=" * 80)
    print("🧪 Testing Error Handling")
    print("=" * 80)

    # Test with invalid API key
    print("\n📝 Test: Invalid API Key")
    print("-" * 40)

    try:
        invalid_chat = ChatOpenAI(
            model="jina-deepsearch-v2",
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr("invalid-api-key"),
            timeout=30,
        )

        _ = invalid_chat.invoke([HumanMessage(content="This should fail")])

    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}: {str(e)[:100]}...")

    # Test with invalid model
    print("\n📝 Test: Invalid Model")
    print("-" * 40)

    try:
        invalid_model_chat = ChatOpenAI(
            model="jina-deepsearch-v99",  # Non-existent model
            base_url="https://deepsearch.jina.ai/v1",
            api_key=SecretStr(JINA_API_KEY) if JINA_API_KEY else SecretStr("dummy-key"),
            timeout=30,
        )

        _ = invalid_model_chat.invoke([HumanMessage(content="This should also fail")])

    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}: {str(e)[:100]}...")

    print("\n" + "=" * 80)
    print("🎉 Error handling tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run LangChain tests
    print("🚀 Starting LangChain ChatOpenAI Tests for Jina DeepSearch")
    print("=" * 80)

    # Check if API key is set
    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your Jina AI API key for free: https://jina.ai/?sui=apikey")
        exit(1)

    # Run synchronous tests
    test_deepsearch_with_langchain()

    # Run async tests
    print("\n" + "🔄" * 40)
    asyncio.run(test_deepsearch_langchain_async())

    # Run error handling tests
    test_deepsearch_error_handling()

    print("\n\n" + "🎯" * 40)
    print("\n✅ All tests completed! Check test-logs/ directory for detailed results.")
    print("\n" + "🎯" * 40)

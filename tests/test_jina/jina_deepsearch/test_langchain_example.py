#!/usr/bin/env python3
"""
Example: Using Jina DeepSearch API with LangChain ChatOpenAI

This example demonstrates how to use Jina's DeepSearch API as an OpenAI-compatible
endpoint with LangChain, showcasing various features and use cases.

Prerequisites:
- Set JINA_API_KEY environment variable
- Get your Jina AI API key for free: https://jina.ai/?sui=apikey
- Install: pip install langchain-openai

Usage:
    export JINA_API_KEY="your-api-key"
    python test_langchain_example.py
"""

import os
import json
from typing import Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
JINA_API_KEY = os.getenv("JINA_API_KEY", "")


class DeepSearchStreamHandler(BaseCallbackHandler):
    """Handle streaming tokens from DeepSearch."""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Print tokens as they arrive."""
        print(token, end="", flush=True)


def example_basic_query():
    """Example 1: Basic query to Jina DeepSearch."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Query")
    print("=" * 60)

    # Create ChatOpenAI instance configured for Jina DeepSearch
    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        temperature=0,
        timeout=300,
    )

    # Send a query
    response = llm.invoke([HumanMessage(content="What are the key features of Jina AI's embedding-v4 model?")])

    print("Response:", response.content)


def example_streaming():
    """Example 2: Streaming responses."""
    print("\n" + "=" * 60)
    print("Example 2: Streaming Response")
    print("=" * 60)

    # Create streaming instance with callback
    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        streaming=True,
        callbacks=[DeepSearchStreamHandler()],
        timeout=300,
    )

    print("Streaming response:\n")
    _ = llm.invoke([HumanMessage(content="Explain how Jina's ColBERT v2 reranker works")])
    print("\n\nDone!")


def example_structured_output():
    """Example 3: Structured output with JSON schema."""
    print("\n" + "=" * 60)
    print("Example 3: Structured Output")
    print("=" * 60)

    # Define JSON schema for response
    response_schema = {
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "version": {"type": "string"},
            "key_features": {"type": "array", "items": {"type": "string"}},
            "use_cases": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model_name", "version", "key_features"],
    }

    # Configure with response format
    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        model_kwargs={"response_format": {"type": "json_schema", "json_schema": response_schema}},
        timeout=300,
    )

    response = llm.invoke([HumanMessage(content="Tell me about Jina's latest embedding model")])

    # Parse JSON response
    try:
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(content)
        print("Structured Response:")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        content = response.content if isinstance(response.content, str) else str(response.content)
        print("Response:", content)


def example_advanced_search():
    """Example 4: Advanced search with DeepSearch parameters."""
    print("\n" + "=" * 60)
    print("Example 4: Advanced Search Parameters")
    print("=" * 60)

    # Configure advanced parameters
    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        model_kwargs={
            "reasoning_effort": "high",  # More thorough search
            "no_direct_answer": True,  # Force web search
            "max_attempts": 5,  # Search iterations
            "max_returned_urls": 10,  # Number of sources
            "boost_hostnames": ["docs.jina.ai", "github.com/jina-ai"],  # Prioritize these domains
        },
        timeout=600,  # Longer timeout for deep search
    )

    response = llm.invoke(
        [
            HumanMessage(
                content=(
                    "Compare Jina embeddings v3 vs v4: performance benchmarks, "
                    "multilingual support, and best use cases for each"
                )
            )
        ]
    )

    print("Deep Research Result:")
    content = response.content if isinstance(response.content, str) else str(response.content)
    print(content[:1000] + "..." if len(content) > 1000 else content)


def example_conversation():
    """Example 5: Multi-turn conversation."""
    print("\n" + "=" * 60)
    print("Example 5: Multi-turn Conversation")
    print("=" * 60)

    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        model_kwargs={
            "reasoning_effort": "medium",
            "max_returned_urls": 5,
        },
        timeout=300,
    )

    # Start conversation
    messages: List[Any] = []

    # Turn 1
    user_msg = HumanMessage(content="What is Jina AI's DeepSearch API?")
    messages.append(user_msg)

    response1 = llm.invoke(messages)
    print(f"User: {user_msg.content}")
    print(f"DeepSearch: {response1.content[:300]}...\n")

    # Add to conversation history
    messages.append(AIMessage(content=response1.content))

    # Turn 2
    user_msg2 = HumanMessage(
        content=(
            "How to use Submodular Optimization for "
            "Diverse Query Generation in DeepResearch Agent? "
            "Reading this https://jina.ai/news/submodular-optimization-for-diverse-query-generation-in-deepresearch/ "
            "and use Zh(中文) answer for me"
        )
    )
    messages.append(user_msg2)

    response2 = llm.invoke(messages)
    print(f"User: {user_msg2.content}")
    print(f"DeepSearch: {response2.content[:300]}...")


def example_with_langchain_agents():
    """Example 6: Using DeepSearch in LangChain agents/chains."""
    print("\n" + "=" * 60)
    print("Example 6: Integration with LangChain")
    print("=" * 60)

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages(
        [("system", "You are a helpful AI assistant powered by Jina DeepSearch."), ("human", "{question}")]
    )

    # Create LLM
    llm = ChatOpenAI(
        model="jina-deepsearch-v2",
        base_url="https://deepsearch.jina.ai/v1",
        api_key=JINA_API_KEY,  # type: ignore
        model_kwargs={
            "reasoning_effort": "medium",
            "max_returned_urls": 5,
        },
        timeout=300,
    )

    # Create chain
    chain = prompt | llm | StrOutputParser()

    # Use the chain
    result = chain.invoke({"question": "What are the latest developments in multimodal AI search?"})

    print("Chain Result:")
    print(result[:500] + "..." if len(result) > 500 else result)


if __name__ == "__main__":
    # Check API key
    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your Jina AI API key for free: https://jina.ai/?sui=apikey")
        exit(1)

    # Run examples
    try:
        example_basic_query()
        example_streaming()
        example_structured_output()
        example_advanced_search()
        example_conversation()
        example_with_langchain_agents()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure your JINA_API_KEY is valid.")

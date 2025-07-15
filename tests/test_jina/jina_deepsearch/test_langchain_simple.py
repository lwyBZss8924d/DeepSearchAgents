#!/usr/bin/env python3
"""
Simple test for Jina DeepSearch API with LangChain ChatOpenAI

This is a minimal example to test the integration.

Usage:
    export JINA_API_KEY="your-api-key"
    python test_langchain_simple.py
"""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import SecretStr

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
JINA_API_KEY = os.getenv("JINA_API_KEY")

if not JINA_API_KEY:
    print("❌ Error: JINA_API_KEY environment variable not set!")
    print("Get your Jina AI API key for free: https://jina.ai/?sui=apikey")
    exit(1)

print("🚀 Testing Jina DeepSearch with LangChain ChatOpenAI")
print("=" * 60)

# Create ChatOpenAI instance configured for Jina DeepSearch
llm = ChatOpenAI(
    model="jina-deepsearch-v2",
    base_url="https://deepsearch.jina.ai/v1",
    api_key=SecretStr(JINA_API_KEY),
    temperature=0,
    timeout=300,
)

# Test query
query = (
    "What is the litellm version tag for the last 2 latest `nightly` versions? "
    "Provide the full changelog of all changes. Then analyze the key improvements with a table for me."
)

print(f"Query: {query[:100]}...")
print("-" * 60)

try:
    # Send the query
    response = llm.invoke([HumanMessage(content=query)])

    print("\nResponse:")
    print(response.content)
    print("\n✅ Test passed!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure your JINA_API_KEY is valid.")

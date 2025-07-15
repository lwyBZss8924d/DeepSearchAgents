#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_xcom_deep_qa.py
# Example usage of the new XcomDeepQATool

"""
Example usage of XcomDeepQATool for X.com content analysis.
"""

from dotenv import load_dotenv
from src.tools.xcom_qa import XcomDeepQATool

# Load environment variables
load_dotenv()

# Initialize the tool
tool = XcomDeepQATool(verbose=True)

print("=== XcomDeepQATool Examples ===\n")

# Example 1: Search X posts
print("1. Searching X posts about Grok latest version Grok-4 benchmark tset info frome @elonmusk:")
print("-" * 50)
result = tool.forward(
    query_or_url="Grok latest version Grok-4 benchmark tset info",
    operation="search",
    search_params={
        "included_x_handles": ["elonmusk"],
        "post_favorite_count": 100,
    },
    max_results=10
)
print(f"Search completed. Found {result.get('posts_found', 0)} posts.\n")

# Example 2: Read a specific X.com post (example URL)
print("2. Reading a specific X.com post:")
print("-" * 50)
# Note: Replace with an actual X.com URL
example_url = "https://x.com/deedydas/status/1943190393602068801"
result = tool.forward(
    query_or_url=example_url,
    operation="read"
)
print("Post content extracted.\n")

# Example 3: Ask a question about X.com content
print("3. Asking a question about X.com content:")
print("-" * 50)
result = tool.forward(
    query_or_url="xAI announcements",
    operation="query",
    question="What are the latest updates from xAI Grok-4 benchmark tset info based on X posts?",
    search_params={"included_x_handles": ["xai"]}
)
print("Question answered based on X.com analysis.\n")

print("=== Demo Complete ===")

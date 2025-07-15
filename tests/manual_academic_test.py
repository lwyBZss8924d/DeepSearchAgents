#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/manual_academic_test.py
# code style: PEP 8

"""
Manual test script for AcademicRetrieval tool.

Run this script to manually test the academic retrieval functionality
when API rate limits allow.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.academic_retrieval import AcademicRetrieval


def test_search_operation():
    """Test search operation with a simple query."""
    print("=" * 60)
    print("Test 1: Academic Search Operation")
    print("=" * 60)
    
    # Create tool
    tool = AcademicRetrieval(verbose=True)
    
    # Test query
    query = "AI-LLM Agent papers about ReAct agent methodology"
    print(f"\nQuery: {query}")
    print("\nExecuting search...")
    
    # Execute search
    result = tool.forward(
        query=query,
        operation="search",
        num_results=5,
        verbose=True
    )
    
    # Display results
    print(f"\nOperation: {result.get('operation')}")
    print(f"Total results: {result.get('total_results')}")
    
    if result.get('results'):
        print("\nResults:")
        for i, paper in enumerate(result['results'], 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            print(f"   URL: {paper.get('url', 'N/A')}")
            print(f"   Description: {paper.get('description', 'N/A')[:100]}...")
    elif result.get('error'):
        print(f"\nError: {result['error']}")
    else:
        print("\nNo results found")


def test_research_operation():
    """Test research operation with a complex query."""
    print("\n" + "=" * 60)
    print("Test 2: Academic Research Operation")
    print("=" * 60)
    
    # Create tool
    tool = AcademicRetrieval(verbose=True)
    
    # Test query
    query = (
        "What are the key differences between ReAct and CodeAct "
        "methodologies in LLM agent architectures? "
        "最终总结请用中文输出。"
    )
    print(f"\nQuery: {query}")
    print("\nExecuting research (this may take several minutes)...")
    
    # Execute research
    result = tool.forward(
        query=query,
        operation="research",
        timeout=600  # 10 minutes
    )
    
    # Display results
    print(f"\nOperation: {result.get('operation')}")
    
    if result.get('content'):
        print("\nResearch Report:")
        print("-" * 40)
        print(result['content'][:1000])  # First 1000 chars
        if len(result['content']) > 1000:
            print("\n... [truncated]")
        print("-" * 40)
        
        # Check for Chinese content
        chinese_chars = ["框架", "方法", "总结", "区别", "架构"]
        has_chinese = any(char in result['content'] for char in chinese_chars)
        print(f"\nChinese output detected: {has_chinese}")
    elif result.get('error'):
        print(f"\nError: {result['error']}")
    else:
        print("\nNo content generated")


def test_cli_command():
    """Test through CLI command."""
    print("\n" + "=" * 60)
    print("Test 3: CLI Command Test")
    print("=" * 60)
    
    print("\nYou can test the tool through CLI with:")
    print("\n# React agent:")
    print('python -m src.cli --agent-type react --query "Use academic_retrieval to search for papers about transformer architecture"')
    print("\n# CodeAct agent:")
    print('python -m src.cli --agent-type codact --query "Use academic_retrieval with operation=\'research\' to analyze recent advances in neural architecture search"')


def main():
    """Run all tests."""
    print("Manual Academic Retrieval Tool Test")
    print("=" * 60)
    
    # Check API key
    if not os.getenv("FUTUREHOUSE_API_KEY"):
        print("❌ Error: FUTUREHOUSE_API_KEY not set")
        print("Please set: export FUTUREHOUSE_API_KEY='your-key'")
        return 1
    
    print("✅ API key is set")
    print("\nNote: If you get rate limit errors, wait a few minutes and try again.\n")
    
    try:
        # Run tests
        test_search_operation()
        
        # Wait between tests to avoid rate limiting
        print("\nWaiting 30 seconds before next test...")
        time.sleep(30)
        
        test_research_operation()
        
        # Show CLI test info
        test_cli_command()
        
        print("\n✅ All tests completed!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
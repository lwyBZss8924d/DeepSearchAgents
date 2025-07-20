#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_react_examples.py
# Test script to validate React agent examples

"""
Test React agent with example queries to ensure they work correctly
and produce realistic tool calls and observations.
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.runtime import AgentRuntime
from src.core.config.settings import settings, load_toml_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Example queries to test
EXAMPLE_QUERIES = {
    "example1": (
        "Research the latest developments in quantum error correction "
        "techniques from 2025, comparing different approaches and their "
        "practical implementations"
    ),
    "example2": (
        "Analyze the global AI investment trends in 2025, calculate "
        "year-over-year growth rates, and identify the top funded sectors"
    )
}


def test_react_agent(query: str, example_name: str):
    """Test React agent with a specific query"""
    print(f"\n{'='*80}")
    print(f"Testing {example_name}: {query[:60]}...")
    print(f"{'='*80}\n")

    try:
        # Initialize runtime
        runtime = AgentRuntime()

        # Get or create agent
        agent = runtime.get_or_create_agent(
            agent_type="react"
        )

        # Run the query
        print("Running agent...")
        result = agent.run(query)

        print(f"\n{'='*40}")
        print("FINAL RESULT:")
        print(f"{'='*40}")
        print(result)

        # Extract and display tool calls
        if hasattr(agent, 'logs') and agent.logs:
            print(f"\n{'='*40}")
            print("TOOL CALLS MADE:")
            print(f"{'='*40}")
            for i, log in enumerate(agent.logs):
                if log.get('tool_name'):
                    print(f"\n{i+1}. Tool: {log['tool_name']}")
                    print(f"   Arguments: {log.get('tool_args', {})}")
                    if 'tool_output' in log:
                        output = str(log['tool_output'])[:200]
                        if len(str(log['tool_output'])) > 200:
                            output += "..."
                        print(f"   Output: {output}")

        return result

    except Exception as e:
        logger.error(f"Error testing {example_name}: {e}", exc_info=True)
        return None


def main():
    """Main test function"""
    # Load configuration
    load_toml_config(settings)

    # Test each example
    results = {}
    for example_name, query in EXAMPLE_QUERIES.items():
        result = test_react_agent(query, example_name)
        results[example_name] = {
            "query": query,
            "success": result is not None,
            "result": result
        }

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY:")
    print(f"{'='*80}")
    for example_name, data in results.items():
        status = "✓ PASSED" if data["success"] else "✗ FAILED"
        print(f"{example_name}: {status}")

    # Save results for analysis
    import json
    with open("react_examples_test_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nResults saved to react_examples_test_results.json")

if __name__ == "__main__":
    main()

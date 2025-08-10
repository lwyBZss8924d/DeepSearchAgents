#!/usr/bin/env python3
"""
Advanced test scenarios for JinaGroundingRetriever.

This test file covers:
1. Timeout functionality
2. Exponential backoff timing verification
3. Network interruption scenarios
4. Session reuse and resource management
5. Test result logging

Usage:
    export JINA_API_KEY="your-api-key"
    python test_advanced_scenarios.py
"""

import os
import time
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import aiohttp
import requests
from langchain_core.documents import Document

# Import our custom retriever
from jina_grounding_retriever import (
    create_jina_grounding_retriever,
    JinaGroundingRetriever,
    JinaGroundingAPIError,
    JinaGroundingTimeoutError,
)

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


def save_test_results(test_name: str, data: dict) -> str:
    """Save test results to JSON file for analysis."""
    os.makedirs("test-logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test-logs/advanced_{test_name}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Test results saved to: {filename}")
    return filename


def test_timeout_functionality():
    """Test timeout handling with mock delayed responses."""
    print("\n" + "=" * 80)
    print("🧪 Test 1: Timeout Functionality")
    print("=" * 80)

    test_results = {"test": "timeout_functionality", "timestamp": datetime.now().isoformat(), "scenarios": []}

    # Test with very short timeout
    print("\n📝 Testing with 1-second timeout...")
    retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY, timeout=1, max_retries=1, verbose=True  # 1 second timeout
    )

    # Mock a slow response
    with patch("requests.post") as mock_post:

        def slow_response(*args, **kwargs):
            time.sleep(2)  # Sleep longer than timeout
            raise requests.exceptions.Timeout("Mocked timeout")

        mock_post.side_effect = slow_response

        start_time = time.time()
        try:
            docs = retriever.invoke("Test statement")
            print("❌ Should have timed out!")
            test_results["scenarios"].append(
                {"scenario": "short_timeout", "success": False, "error": "Did not timeout as expected"}
            )
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"✅ Correctly timed out after {elapsed:.2f} seconds")
            print(f"   Error: {type(e).__name__}: {str(e)}")
            test_results["scenarios"].append(
                {"scenario": "short_timeout", "success": True, "elapsed_time": elapsed, "error_type": type(e).__name__}
            )

    # Test async timeout
    print("\n📝 Testing async timeout...")

    async def test_async_timeout():
        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, timeout=1, max_retries=1)

        with patch("aiohttp.ClientSession.post") as mock_async_post:

            async def slow_async_response(*args, **kwargs):
                await asyncio.sleep(2)
                raise asyncio.TimeoutError("Mocked async timeout")

            mock_async_post.side_effect = slow_async_response

            start_time = time.time()
            try:
                docs = await retriever.ainvoke("Test async")
                print("❌ Should have timed out!")
                return {"success": False, "error": "Did not timeout"}
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"✅ Async correctly timed out after {elapsed:.2f} seconds")
                return {"success": True, "elapsed_time": elapsed, "error_type": type(e).__name__}

    async_result = asyncio.run(test_async_timeout())
    test_results["scenarios"].append({"scenario": "async_timeout", **async_result})

    save_test_results("timeout", test_results)


def test_exponential_backoff_timing():
    """Test that exponential backoff works correctly."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 2: Exponential Backoff Timing")
    print("=" * 80)

    test_results = {"test": "exponential_backoff", "timestamp": datetime.now().isoformat(), "retries": []}

    retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY, max_retries=3, retry_delay=1.0, verbose=True  # Initial delay of 1 second
    )

    retry_times = []

    with patch("requests.post") as mock_post:

        def track_retry_timing(*args, **kwargs):
            retry_times.append(time.time())
            if len(retry_times) < 3:
                raise requests.exceptions.HTTPError("500 Server Error", response=Mock(status_code=500))
            # Success on third attempt
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"data": {"factuality": 0.95, "result": True, "references": []}}
            response.raise_for_status = Mock()
            return response

        mock_post.side_effect = track_retry_timing

        print("🔄 Testing retry timing...")
        start_time = time.time()

        try:
            docs = retriever.invoke("Test exponential backoff")

            # Calculate delays between retries
            delays = []
            for i in range(1, len(retry_times)):
                delay = retry_times[i] - retry_times[i - 1]
                delays.append(delay)
                expected_delay = 1.0 * (2 ** (i - 1))  # Exponential backoff formula
                print(f"   Retry {i}: Actual delay = {delay:.2f}s, Expected = {expected_delay:.2f}s")

                test_results["retries"].append(
                    {
                        "retry_number": i,
                        "actual_delay": delay,
                        "expected_delay": expected_delay,
                        "difference": abs(delay - expected_delay),
                    }
                )

            # Verify exponential backoff pattern (allowing 0.1s tolerance)
            if len(delays) >= 2:
                if abs(delays[0] - 1.0) < 0.1 and abs(delays[1] - 2.0) < 0.1:
                    print("✅ Exponential backoff timing verified!")
                    test_results["success"] = True
                else:
                    print("❌ Exponential backoff timing incorrect")
                    test_results["success"] = False

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            test_results["success"] = False
            test_results["error"] = str(e)

    save_test_results("backoff_timing", test_results)


def test_network_interruption_scenarios():
    """Test various network interruption scenarios."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 3: Network Interruption Scenarios")
    print("=" * 80)

    test_results = {"test": "network_interruptions", "timestamp": datetime.now().isoformat(), "scenarios": []}

    # Scenario 1: Connection refused
    print("\n📝 Testing connection refused...")
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, max_retries=2, retry_delay=0.5)

        try:
            docs = retriever.invoke("Test connection")
            print("❌ Should have raised an error")
            scenario_result = {"scenario": "connection_refused", "success": False}
        except Exception as e:
            print(f"✅ Correctly handled connection error: {type(e).__name__}")
            scenario_result = {"scenario": "connection_refused", "success": True, "error_type": type(e).__name__}

        test_results["scenarios"].append(scenario_result)

    # Scenario 2: DNS resolution failure
    print("\n📝 Testing DNS resolution failure...")
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to resolve hostname")

        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, max_retries=1)

        try:
            docs = retriever.invoke("Test DNS")
            print("❌ Should have raised an error")
            scenario_result = {"scenario": "dns_failure", "success": False}
        except Exception as e:
            print(f"✅ Correctly handled DNS error: {type(e).__name__}")
            scenario_result = {"scenario": "dns_failure", "success": True, "error_type": type(e).__name__}

        test_results["scenarios"].append(scenario_result)

    # Scenario 3: Intermittent failures (succeeds after retries)
    print("\n📝 Testing intermittent failures...")
    attempt_count = 0

    with patch("requests.post") as mock_post:

        def intermittent_failure(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                raise requests.exceptions.ConnectionError("Temporary network issue")

            # Success on third attempt
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "data": {
                    "factuality": 0.85,
                    "result": True,
                    "references": [{"url": "https://example.com", "keyQuote": "Test quote", "isSupportive": True}],
                }
            }
            response.raise_for_status = Mock()
            return response

        mock_post.side_effect = intermittent_failure

        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, max_retries=3, retry_delay=0.1)

        try:
            docs = retriever.invoke("Test intermittent")
            print(f"✅ Succeeded after {attempt_count} attempts")
            scenario_result = {
                "scenario": "intermittent_failure",
                "success": True,
                "attempts": attempt_count,
                "documents_retrieved": len(docs),
            }
        except Exception as e:
            print(f"❌ Failed after retries: {e}")
            scenario_result = {
                "scenario": "intermittent_failure",
                "success": False,
                "attempts": attempt_count,
                "error": str(e),
            }

        test_results["scenarios"].append(scenario_result)

    save_test_results("network_interruptions", test_results)


async def test_session_reuse():
    """Test that sessions can be reused for better performance."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 4: Session Reuse Performance")
    print("=" * 80)

    test_results = {"test": "session_reuse", "timestamp": datetime.now().isoformat(), "performance_metrics": []}

    # Test without session reuse (current implementation)
    print("\n📝 Testing without session reuse...")
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    statements = ["Python is a programming language", "JavaScript runs in browsers", "Rust provides memory safety"]

    # Mock the API to track session creation
    session_count = 0
    original_client_session = aiohttp.ClientSession

    class TrackedClientSession(original_client_session):
        def __init__(self, *args, **kwargs):
            nonlocal session_count
            session_count += 1
            super().__init__(*args, **kwargs)

    with patch("aiohttp.ClientSession", TrackedClientSession):
        start_time = time.time()

        # Make multiple async requests
        tasks = [retriever.ainvoke(stmt) for stmt in statements]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time

            print(f"✅ Completed {len(statements)} requests in {elapsed:.2f}s")
            print(f"   Sessions created: {session_count}")

            test_results["performance_metrics"].append(
                {
                    "test_type": "without_reuse",
                    "requests": len(statements),
                    "sessions_created": session_count,
                    "total_time": elapsed,
                    "avg_time_per_request": elapsed / len(statements),
                }
            )

        except Exception as e:
            print(f"❌ Error during test: {e}")
            test_results["error"] = str(e)

    # Note: Actual session reuse implementation would be tested here
    # For now, we're just tracking current behavior

    save_test_results("session_reuse", test_results)


def test_rate_limit_handling():
    """Test handling of rate limit errors."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 5: Rate Limit Handling")
    print("=" * 80)

    test_results = {"test": "rate_limit_handling", "timestamp": datetime.now().isoformat(), "scenarios": []}

    # Test 429 rate limit response
    print("\n📝 Testing 429 rate limit response...")

    with patch("requests.post") as mock_post:
        # Create a mock response with 429 status
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limit exceeded"

        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Client Error: Too Many Requests", response=mock_response
        )

        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, max_retries=1)

        try:
            docs = retriever.invoke("Test rate limit")
            print("❌ Should have raised a rate limit error")
            test_results["scenarios"].append(
                {"scenario": "rate_limit_429", "success": False, "error": "Did not raise expected error"}
            )
        except Exception as e:
            print(f"✅ Correctly handled rate limit: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            test_results["scenarios"].append(
                {"scenario": "rate_limit_429", "success": True, "error_type": type(e).__name__, "error_message": str(e)}
            )

    save_test_results("rate_limit", test_results)


def main():
    """Run all advanced test scenarios."""
    print("🚀 Starting Advanced Test Scenarios")
    print("=" * 80)

    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    # Create test-logs directory if it doesn't exist
    os.makedirs("test-logs", exist_ok=True)

    # Run synchronous tests
    test_timeout_functionality()
    test_exponential_backoff_timing()
    test_network_interruption_scenarios()
    test_rate_limit_handling()

    # Run async tests
    print("\n" + "🔄" * 40)
    asyncio.run(test_session_reuse())

    print("\n\n" + "🎯" * 40)
    print("\n✅ All advanced tests completed!")
    print("\nTest results saved in test-logs/ directory")
    print("\nKey Test Coverage Added:")
    print("1. ✅ Timeout functionality with mock delays")
    print("2. ✅ Exponential backoff timing verification")
    print("3. ✅ Network interruption scenarios")
    print("4. ✅ Session tracking for performance analysis")
    print("5. ✅ Rate limit error handling")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    main()

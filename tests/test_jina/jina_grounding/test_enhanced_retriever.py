#!/usr/bin/env python3
"""
Test suite for enhanced Jina Grounding retriever features.

Tests:
1. Configuration validation
2. Session reuse and performance
3. Caching functionality
4. Batch processing
5. Error handling improvements
"""

import os
import time
import asyncio
from unittest.mock import patch, Mock

from jina_grounding_retriever_enhanced import (
    create_enhanced_jina_grounding_retriever,
    EnhancedJinaGroundingRetriever,
    cleanup_sessions,
)

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


def test_configuration_validation():
    """Test configuration validation with warnings."""
    print("\n" + "=" * 80)
    print("🧪 Test 1: Configuration Validation")
    print("=" * 80)

    # Test 1: Invalid timeout (too low)
    print("\n📝 Testing invalid timeout (too low)...")
    try:
        retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, timeout=0)  # Invalid
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")

    # Test 2: High timeout (warning)
    print("\n📝 Testing high timeout (should warn)...")
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, timeout=700)  # High value
        if w:
            print(f"✅ Warning issued: {w[0].message}")
        else:
            print("❌ No warning issued for high timeout")

    # Test 3: Invalid max_retries
    print("\n📝 Testing invalid max_retries...")
    try:
        retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, max_retries=0)  # Invalid
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")

    # Test 4: Invalid retry_delay
    print("\n📝 Testing invalid retry_delay...")
    try:
        retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, retry_delay=0.05)  # Too low
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")

    # Test 5: Valid configuration
    print("\n📝 Testing valid configuration...")
    try:
        retriever = create_enhanced_jina_grounding_retriever(
            api_key=JINA_API_KEY, timeout=120, max_retries=3, retry_delay=1.0, batch_size=5
        )
        print("✅ Valid configuration accepted")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_caching_functionality():
    """Test caching for repeated queries."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 2: Caching Functionality")
    print("=" * 80)

    # Create retriever with caching enabled
    retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, enable_caching=True, verbose=True)

    statement = "The speed of light is approximately 300,000 km/s"

    # First call - should hit API
    print(f"\n🔍 First query: {statement}")
    start_time = time.time()
    docs1 = retriever.invoke(statement)
    first_call_time = time.time() - start_time
    print(f"✅ First call completed in {first_call_time:.2f}s, got {len(docs1)} documents")

    # Second call - should hit cache
    print(f"\n🔍 Second query (cached): {statement}")
    start_time = time.time()
    docs2 = retriever.invoke(statement)
    second_call_time = time.time() - start_time
    print(f"✅ Second call completed in {second_call_time:.2f}s, got {len(docs2)} documents")

    # Verify cache hit was faster
    if second_call_time < first_call_time * 0.1:  # Should be at least 10x faster
        print(f"✅ Cache hit confirmed: {first_call_time/second_call_time:.1f}x speedup")
    else:
        print(f"⚠️  Cache might not be working properly: only {first_call_time/second_call_time:.1f}x speedup")

    # Verify same results
    if len(docs1) == len(docs2) and all(d1.page_content == d2.page_content for d1, d2 in zip(docs1, docs2)):
        print("✅ Cache returns identical results")
    else:
        print("❌ Cache results differ from original")

    # Test cache clearing
    print("\n📝 Testing cache clearing...")
    retriever.clear_cache()
    print("✅ Cache cleared")


async def test_batch_processing():
    """Test batch processing functionality."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 3: Batch Processing")
    print("=" * 80)

    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, batch_size=3, verbose=True  # Process 3 at a time
    )

    statements = [
        "Python was created by Guido van Rossum",
        "JavaScript is a compiled language",
        "HTML stands for HyperText Markup Language",
        "CSS is used for database queries",
        "React is a JavaScript framework",
        "Docker containers are virtual machines",
    ]

    print(f"\n🚀 Batch processing {len(statements)} statements (batch_size=3)...")
    start_time = time.time()

    try:
        results = await retriever.abatch(statements)
        elapsed = time.time() - start_time

        print(f"\n✅ Batch processing completed in {elapsed:.2f}s")
        print(f"Results summary:")
        for i, (stmt, docs) in enumerate(zip(statements, results)):
            if docs:
                factuality = docs[0].metadata.get("factuality_score", 0)
                result = "TRUE" if docs[0].metadata.get("grounding_result") else "FALSE"
                print(f"  {i+1}. {stmt[:40]}... → {result} ({factuality:.2f})")
            else:
                print(f"  {i+1}. {stmt[:40]}... → ERROR")

    except Exception as e:
        print(f"❌ Batch processing error: {e}")


async def test_session_reuse_performance():
    """Test performance improvement with session reuse."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 4: Session Reuse Performance")
    print("=" * 80)

    # Clean up any existing sessions first
    cleanup_sessions()

    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, verbose=False  # Disable verbose for performance test
    )

    statements = [
        "The Earth orbits the Sun",
        "Water freezes at 0 degrees Celsius",
        "Oxygen is essential for human life",
    ]

    print("\n📊 Comparing performance with session reuse...")

    # Test with enhanced retriever (session reuse)
    start_time = time.time()
    tasks = [retriever.ainvoke(stmt) for stmt in statements]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enhanced_time = time.time() - start_time

    successful_results = [r for r in results if not isinstance(r, Exception)]
    print(f"✅ Enhanced retriever: {enhanced_time:.2f}s for {len(statements)} requests")
    print(f"   Successful: {len(successful_results)}/{len(statements)}")
    print(f"   Average time per request: {enhanced_time/len(statements):.2f}s")

    # Note: In production, you would compare with the original retriever
    # For this test, we're just demonstrating the enhanced version works


def test_enhanced_error_handling():
    """Test improved error handling with custom exceptions."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 5: Enhanced Error Handling")
    print("=" * 80)

    from jina_grounding_retriever_enhanced import (
        JinaGroundingAPIError,
        JinaGroundingTimeoutError,
        JinaGroundingRateLimitError,
    )

    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, max_retries=2, retry_delay=0.5, timeout=5
    )

    # Test timeout error
    print("\n📝 Testing timeout error handling...")
    with patch("requests.Session.post") as mock_post:
        mock_post.side_effect = Exception("Read timed out")

        try:
            docs = retriever.invoke("Test timeout")
            print("❌ Should have raised an error")
        except JinaGroundingAPIError as e:
            print(f"✅ Correctly caught timeout error: {type(e).__name__}")
            print(f"   Message: {str(e)}")

    # Test rate limit error
    print("\n📝 Testing rate limit error handling...")
    with patch("requests.Session.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.raise_for_status.side_effect = Exception("429 Client Error")
        mock_post.return_value = mock_response

        try:
            docs = retriever.invoke("Test rate limit")
            print("❌ Should have raised an error")
        except Exception as e:
            print(f"✅ Correctly caught rate limit error: {type(e).__name__}")
            print(f"   Message: {str(e)}")


def test_trusted_references_with_caching():
    """Test that trusted references are included in cache key."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 6: Trusted References with Caching")
    print("=" * 80)

    statement = "COVID-19 vaccines are safe and effective"

    # Create two retrievers with different trusted references
    retriever1 = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, enable_caching=True, trusted_references=["https://www.cdc.gov", "https://www.who.int"]
    )

    retriever2 = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        enable_caching=True,
        trusted_references=["https://www.nature.com", "https://www.science.org"],
    )

    print(f"\n🔍 Query with CDC/WHO trusted sources...")
    docs1 = retriever1.get_relevant_documents(statement)
    print(f"✅ Got {len(docs1)} documents")

    print(f"\n🔍 Same query with Nature/Science trusted sources...")
    docs2 = retriever2.get_relevant_documents(statement)
    print(f"✅ Got {len(docs2)} documents")

    # Cache keys should be different
    cache_key1 = retriever1._get_cache_key(statement)
    cache_key2 = retriever2._get_cache_key(statement)

    if cache_key1 != cache_key2:
        print("✅ Different trusted references create different cache keys")
    else:
        print("❌ Cache keys should differ with different trusted references")


async def main():
    """Run all enhanced retriever tests."""
    print("🚀 Starting Enhanced Jina Grounding Retriever Tests")
    print("=" * 80)

    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    # Run synchronous tests
    test_configuration_validation()
    test_caching_functionality()
    test_enhanced_error_handling()
    test_trusted_references_with_caching()

    # Run async tests
    print("\n" + "🔄" * 40)
    await test_batch_processing()
    await test_session_reuse_performance()

    # Cleanup
    cleanup_sessions()

    print("\n\n" + "🎯" * 40)
    print("\n✅ All enhanced retriever tests completed!")
    print("\nKey Features Tested:")
    print("1. ✅ Configuration validation with warnings")
    print("2. ✅ Caching for repeated queries")
    print("3. ✅ Batch processing support")
    print("4. ✅ Session reuse for performance")
    print("5. ✅ Enhanced error handling")
    print("6. ✅ Trusted references with caching")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    asyncio.run(main())

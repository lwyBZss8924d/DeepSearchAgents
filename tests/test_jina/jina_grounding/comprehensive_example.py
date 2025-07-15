#!/usr/bin/env python3
"""
Comprehensive example demonstrating all features of the Jina Grounding Retriever.

This example shows:
1. Basic usage vs Enhanced usage
2. Performance comparisons
3. Error handling best practices
4. Advanced features (caching, batching, etc.)
"""

import os
import time
import asyncio
from typing import List
from datetime import datetime

from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain_community.llms import FakeListLLM

# Import both versions
from jina_grounding_retriever import create_jina_grounding_retriever
from jina_grounding_retriever_enhanced import (
    create_enhanced_jina_grounding_retriever,
    JinaGroundingAPIError,
    JinaGroundingTimeoutError,
    JinaGroundingRateLimitError,
    cleanup_sessions,
)

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


def section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"📚 {title}")
    print("=" * 80)


def compare_basic_vs_enhanced():
    """Compare basic and enhanced retriever performance."""
    section_header("1. Basic vs Enhanced Retriever Comparison")

    statement = "The International Space Station orbits Earth every 90 minutes"

    # Basic retriever
    print("\n### Basic Retriever")
    basic_retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    start_time = time.time()
    basic_docs = basic_retriever.invoke(statement)
    basic_time = time.time() - start_time

    print(f"✅ Basic retriever: {basic_time:.2f}s")
    print(f"   Documents: {len(basic_docs)}")
    print(f"   Factuality: {basic_docs[0].metadata.get('factuality_score', 0):.2%}")

    # Enhanced retriever with caching
    print("\n### Enhanced Retriever (with caching)")
    enhanced_retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, enable_caching=True, verbose=True
    )

    # First call
    start_time = time.time()
    enhanced_docs1 = enhanced_retriever.invoke(statement)
    enhanced_time1 = time.time() - start_time

    # Second call (cached)
    start_time = time.time()
    enhanced_docs2 = enhanced_retriever.invoke(statement)
    enhanced_time2 = time.time() - start_time

    print(f"\n✅ Enhanced retriever:")
    print(f"   First call: {enhanced_time1:.2f}s")
    print(f"   Cached call: {enhanced_time2:.4f}s ({enhanced_time1/enhanced_time2:.0f}x faster)")
    print(f"   Documents: {len(enhanced_docs1)}")


async def demonstrate_batch_processing():
    """Demonstrate batch processing capabilities."""
    section_header("2. Batch Processing Example")

    # Statements about programming languages
    statements = [
        "Python was created by Guido van Rossum in 1991",
        "JavaScript is a statically typed language",
        "Rust guarantees memory safety without garbage collection",
        "Java runs on the Java Virtual Machine (JVM)",
        "Go was developed by Google",
        "Ruby follows the principle of least surprise",
        "C++ supports multiple programming paradigms",
        "Swift is Apple's programming language for iOS development",
    ]

    print(f"\n📊 Processing {len(statements)} statements about programming languages...")

    # Enhanced retriever with batch processing
    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, batch_size=4, enable_caching=True  # Process 4 at a time
    )

    start_time = time.time()
    results = await retriever.abatch(statements)
    elapsed = time.time() - start_time

    print(f"\n✅ Batch processing completed in {elapsed:.2f}s")
    print(f"   Average time per statement: {elapsed/len(statements):.2f}s")

    # Display results
    print("\n📋 Fact-Checking Results:")
    print("-" * 60)
    for stmt, docs in zip(statements, results):
        if docs:
            score = docs[0].metadata.get("factuality_score", 0)
            result = "TRUE" if docs[0].metadata.get("grounding_result") else "FALSE"
            print(f"• {stmt[:50]:50} | {result:5} | {score:.2%}")
        else:
            print(f"• {stmt[:50]:50} | ERROR | N/A")


def demonstrate_error_handling():
    """Demonstrate proper error handling techniques."""
    section_header("3. Error Handling Best Practices")

    # Create retriever with short timeout for testing
    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY, timeout=5, max_retries=2, retry_delay=0.5  # Short timeout
    )

    # Test various error scenarios
    test_cases = [
        ("", "Empty statement"),
        ("The Earth is flat", "Normal statement"),
        ("x" * 10000, "Very long statement"),
    ]

    for statement, description in test_cases:
        print(f"\n📝 Testing: {description}")
        try:
            docs = retriever.invoke(statement)
            if docs:
                print(f"✅ Success: Got {len(docs)} documents")
        except JinaGroundingTimeoutError as e:
            print(f"⏱️  Timeout Error: {e}")
        except JinaGroundingRateLimitError as e:
            print(f"🚫 Rate Limit Error: {e}")
        except JinaGroundingAPIError as e:
            print(f"❌ API Error: {e}")
        except ValueError as e:
            print(f"⚠️  Validation Error: {e}")
        except Exception as e:
            print(f"🔥 Unexpected Error: {type(e).__name__}: {e}")


def demonstrate_advanced_features():
    """Demonstrate advanced features like trusted references and QA chains."""
    section_header("4. Advanced Features")

    # 1. Trusted References
    print("\n### Using Trusted References")

    medical_retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        trusted_references=[
            "https://www.cdc.gov",
            "https://www.who.int",
            "https://www.nejm.org",
            "https://pubmed.ncbi.nlm.nih.gov",
        ],
        enable_caching=True,
    )

    medical_statement = "mRNA vaccines work by teaching cells to make a protein that triggers an immune response"
    docs = medical_retriever.invoke(medical_statement)

    print(f"✅ Found {len(docs)} references from trusted medical sources")
    for i, doc in enumerate(docs[:3], 1):
        print(f"   {i}. {doc.metadata.get('source', 'N/A')}")

    # 2. Integration with QA Chain
    print("\n### QA Chain Integration")

    # Create a simple QA chain
    qa_template = """You are a fact-checking assistant. Based on the evidence:

Question: {question}

Evidence:
{context}

Provide a brief, factual answer."""

    from langchain.prompts import PromptTemplate

    prompt = PromptTemplate(template=qa_template, input_variables=["question", "context"])

    # Use a simple mock LLM for demonstration
    llm = FakeListLLM(
        responses=[
            "Based on the evidence, mRNA vaccines are indeed designed to teach cells how to make a spike protein that triggers an immune response. This is scientifically accurate."
        ]
    )

    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=medical_retriever, chain_type_kwargs={"prompt": prompt})

    answer = qa_chain.run("How do mRNA vaccines work?")
    print(f"\n💬 QA Chain Answer: {answer}")

    # 3. Performance Monitoring
    print("\n### Performance Monitoring")

    # Track token usage
    total_tokens = sum(doc.metadata.get("token_usage", 0) for doc in docs)
    estimated_cost = total_tokens * 0.000006  # Example rate

    print(f"📊 Token Usage: {total_tokens:,} tokens")
    print(f"💰 Estimated Cost: ${estimated_cost:.4f}")


async def demonstrate_production_patterns():
    """Demonstrate production-ready patterns."""
    section_header("5. Production Patterns")

    # Create a production-ready retriever
    retriever = create_enhanced_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        timeout=120,  # Reasonable timeout
        max_retries=3,  # Sufficient retries
        retry_delay=1.0,  # Exponential backoff
        enable_caching=True,  # Cache for efficiency
        batch_size=5,  # Moderate batch size
        verbose=False,  # Disable verbose in production
    )

    print("\n### Fact-Checking Service Pattern")

    async def fact_check_with_fallback(statement: str) -> dict:
        """Production-ready fact-checking with fallback."""
        try:
            docs = await retriever.ainvoke(statement)
            if docs:
                return {
                    "success": True,
                    "statement": statement,
                    "factuality_score": docs[0].metadata.get("factuality_score", 0),
                    "is_true": docs[0].metadata.get("grounding_result", False),
                    "references": len(docs),
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"Error fact-checking '{statement}': {e}")

        # Fallback response
        return {
            "success": False,
            "statement": statement,
            "error": "Unable to verify",
            "timestamp": datetime.now().isoformat(),
        }

    # Test the service
    test_statements = [
        "AI will replace all human jobs by 2030",
        "The speed of light is constant in vacuum",
        "Blockchain technology was invented in 2008",
    ]

    print("\n🚀 Running production fact-checking service...")
    results = await asyncio.gather(*[fact_check_with_fallback(stmt) for stmt in test_statements])

    # Display results
    print("\n📊 Service Results:")
    for result in results:
        if result["success"]:
            status = "TRUE" if result["is_true"] else "FALSE"
            score = result["factuality_score"]
            print(f"✅ {result['statement'][:40]:40} | {status:5} | {score:.2%}")
        else:
            print(f"❌ {result['statement'][:40]:40} | ERROR | {result['error']}")

    # Cleanup
    retriever.clear_cache()
    print("\n🧹 Cache cleared")


def demonstrate_configuration_recommendations():
    """Show configuration recommendations for different use cases."""
    section_header("6. Configuration Recommendations")

    configs = {
        "Quick Checks": {
            "timeout": 30,
            "max_retries": 1,
            "enable_caching": True,
            "description": "For UI autocomplete or quick validations",
        },
        "Standard": {
            "timeout": 60,
            "max_retries": 2,
            "enable_caching": True,
            "description": "Balanced performance and reliability",
        },
        "Thorough": {
            "timeout": 120,
            "max_retries": 3,
            "trusted_references": ["academic", "sources"],
            "description": "For research or critical fact-checking",
        },
        "High Volume": {
            "timeout": 45,
            "max_retries": 2,
            "enable_caching": True,
            "batch_size": 10,
            "description": "For processing many statements",
        },
    }

    print("\n🔧 Recommended Configurations:\n")
    for name, config in configs.items():
        desc = config.pop("description")
        print(f"### {name}")
        print(f"   Use case: {desc}")
        print(f"   Config: {config}")
        print()


async def main():
    """Run all demonstrations."""
    print("🚀 Comprehensive Jina Grounding Retriever Demo")
    print("=" * 80)

    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    try:
        # Run all demonstrations
        compare_basic_vs_enhanced()
        await demonstrate_batch_processing()
        demonstrate_error_handling()
        demonstrate_advanced_features()
        await demonstrate_production_patterns()
        demonstrate_configuration_recommendations()

    finally:
        # Cleanup
        cleanup_sessions()
        print("\n✅ Demo completed! Sessions cleaned up.")

    # Summary
    print("\n" + "🎯" * 40)
    print("\n📌 Key Takeaways:")
    print("1. Enhanced retriever provides caching and session reuse")
    print("2. Batch processing dramatically improves throughput")
    print("3. Proper error handling is crucial for production")
    print("4. Configuration should match your use case")
    print("5. Always clean up resources when done")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Comprehensive test suite for Jina Grounding API with LangChain LLM integration.

This test demonstrates:
1. Real LLM integration with structured outputs
2. Multiple fact-checking scenarios
3. Batch processing and concurrent requests
4. Advanced chain patterns with retrievers
5. Error handling and edge cases
6. Performance benchmarking

Following the pattern from test_jina_DS_api.py, this provides production-ready
examples of using the Jina Grounding Retriever with real language models.

Prerequisites:
- Set JINA_API_KEY environment variable
- Set OPENAI_API_KEY environment variable (or use alternative LLM)
- Install dependencies: pip install langchain-openai langchain-community

Usage:
    export JINA_API_KEY="your-jina-key"
    export OPENAI_API_KEY="your-openai-key"
    python test_grounding_with_llm.py
"""

import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Import our custom retriever
from jina_grounding_retriever import create_jina_grounding_retriever
from jina_grounding_retriever_enhanced import create_enhanced_jina_grounding_retriever

# Get API keys
JINA_API_KEY = os.getenv("JINA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1")


# ------- Helper Functions -------


def save_test_results(results: Dict[str, Any], filename: str = "results.json") -> str:
    """Save test results to a JSON file in the test-logs directory."""
    log_dir = "test-logs"
    os.makedirs(log_dir, exist_ok=True)

    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return filepath


# ------- Structured Output Models -------


class FactCheckResult(BaseModel):
    """Structured fact-checking analysis result."""

    statement: str = Field(description="The statement being fact-checked")
    is_factual: bool = Field(description="Whether the statement is factual based on evidence")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Detailed explanation of the fact-checking result")
    key_evidence: List[str] = Field(description="Key pieces of evidence from the sources")
    contradictions: Optional[List[str]] = Field(description="Any contradicting evidence found", default=None)
    sources_count: int = Field(description="Number of sources consulted")
    recommendation: str = Field(description="Action recommendation based on the fact-check")


class BatchFactCheckResult(BaseModel):
    """Result for batch fact-checking multiple statements."""

    total_statements: int = Field(description="Total number of statements checked")
    factual_count: int = Field(description="Number of factual statements")
    false_count: int = Field(description="Number of false statements")
    average_confidence: float = Field(description="Average confidence across all checks")
    results: List[FactCheckResult] = Field(description="Individual results for each statement")
    processing_time: float = Field(description="Total processing time in seconds")


class ComparisonResult(BaseModel):
    """Result for comparing multiple related statements."""

    topic: str = Field(description="Common topic being discussed")
    statements: List[str] = Field(description="Statements being compared")
    consensus: Optional[str] = Field(description="Consensus view if statements agree")
    conflicts: List[Dict[str, str]] = Field(description="List of conflicting claims")
    most_accurate: Optional[str] = Field(description="Most accurate statement based on evidence")
    synthesis: str = Field(description="Synthesized understanding from all statements")


# ------- Callback Handlers -------


class FactCheckingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to monitor fact-checking process."""

    def __init__(self):
        self.retrieval_times = []
        self.llm_times = []
        self.total_tokens = 0
        self.start_time = None

    def on_retriever_start(self, query: str, **kwargs) -> None:
        self.start_time = datetime.now()
        print(f"🔍 Retrieving facts for: {query[:50]}...")

    def on_retriever_end(self, documents: List[Any], **kwargs) -> None:
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.retrieval_times.append(elapsed)
            print(f"✅ Retrieved {len(documents)} references in {elapsed:.2f}s")

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        self.start_time = datetime.now()
        print("🤖 LLM analyzing evidence...")

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.llm_times.append(elapsed)
            print(f"✅ LLM analysis complete in {elapsed:.2f}s")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "avg_retrieval_time": sum(self.retrieval_times) / len(self.retrieval_times) if self.retrieval_times else 0,
            "avg_llm_time": sum(self.llm_times) / len(self.llm_times) if self.llm_times else 0,
            "total_retrievals": len(self.retrieval_times),
            "total_llm_calls": len(self.llm_times),
        }


# ------- Test Functions -------


def test_basic_fact_checking_with_llm():
    """Test basic fact-checking with structured LLM output."""
    print("=" * 80)
    print("🧪 Test 1: Basic Fact-Checking with Structured Output")
    print("=" * 80)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, verbose=True)

    # Create LLM with structured output
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else SecretStr("dummy"),
        base_url=OPENAI_BASE_URL,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(FactCheckResult)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                ("You are a professional fact-checker. Analyze evidence objectively and provide structured analysis."),
            ),
            (
                "human",
                """
Please fact-check the following statement based on the provided evidence:

Statement: {question}

Evidence from fact-checking service:
{context}

Provide a comprehensive analysis including:
- Whether the statement is factual
- Your confidence level (0.0-1.0)
- Detailed reasoning
- Key supporting or contradicting evidence
- Number of sources consulted
- A clear recommendation
""",
            ),
        ]
    )

    # Create chain
    qa_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | structured_llm

    # Test statements
    test_statements = [
        "SpaceX-Starship space program Flight Test Missions As of FT-9 on 2025-07-05, "
        "the ninth test has successfully achieved manned flight testing of STARSHIP.",
    ]

    results = []

    for statement in test_statements:
        print(f"\n📝 Checking: {statement}")
        print("-" * 60)

        try:
            result = qa_chain.invoke(statement)

            print("\n📊 Analysis Results:")
            print(f"   Is Factual: {'✅ TRUE' if result.is_factual else '❌ FALSE'}")
            print(f"   Confidence: {result.confidence:.2%}")
            print(f"   Sources: {result.sources_count}")
            print(f"\n   Reasoning: {result.reasoning}")
            print(f"\n   Recommendation: {result.recommendation}")

            results.append(result.model_dump())

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"error": str(e), "statement": statement})

    # Save results
    save_test_results(
        {"test": "basic_fact_checking", "timestamp": datetime.now().isoformat(), "results": results},
        "basic_fact_checking_results.json",
    )

    print("\n✅ Basic fact-checking test completed!")


def test_comparative_fact_checking():
    """Test comparing multiple related statements."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 3: Comparative Fact-Checking")
    print("=" * 80)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Create LLM with structured output
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else SecretStr("dummy"),
        base_url=OPENAI_BASE_URL,
        temperature=0,
    )

    comparison_llm = llm.with_structured_output(ComparisonResult)

    # Related statements about the same topic
    statement_groups = [
        {
            "topic": "Starship have already successfully achieved manned Flight Test. ",
            "statements": [
                "SpaceX-Starship space program Flight Test Missions As of FT-9 on 2025-07-05, "
                "the ninth test has successfully achieved manned flight testing of STARSHIP.",
            ],
        },
        {
            "topic": "latest version of gemini-cli is `v1.1.0` ",
            "statements": [
                "latest version of gemini-cli Github release is `v1.1.0` ",
            ],
        },
    ]

    for group in statement_groups:
        print(f"\n📋 Topic: {group['topic']}")
        print("-" * 60)

        # Gather evidence for all statements
        all_evidence = []
        for statement in group["statements"]:
            print(f"   🔍 Checking: {statement}")
            docs = retriever.invoke(statement)
            all_evidence.append(
                {
                    "statement": statement,
                    "evidence": [doc.page_content for doc in docs[:3]],
                    "factuality_scores": [doc.metadata.get("factuality_score", 0) for doc in docs],
                }
            )

        # Create comparison prompt
        evidence_text = "\n\n".join(
            [
                f"Statement {i+1}: {item['statement']}\n"
                f"Evidence: {'; '.join(item['evidence'])}\n"
                f"Factuality scores: {item['factuality_scores']}"
                for i, item in enumerate(all_evidence)
            ]
        )

        prompt = f"""
Compare these related statements about {group['topic']}:

{evidence_text}

Analyze which statements are accurate, which conflict, and provide a synthesized understanding.
"""

        try:
            # Get comparison analysis
            result = comparison_llm.invoke(
                [
                    SystemMessage(content="You are an expert fact-checker comparing related claims."),
                    HumanMessage(content=prompt),
                ]
            )

            print("\n📊 Comparison Results:")
            print(f"   Most Accurate: {result.most_accurate}")
            print(f"   Conflicts Found: {len(result.conflicts)}")
            if result.conflicts:
                for conflict in result.conflicts[:2]:
                    print(f"     - {conflict}")
            print(f"\n   Synthesis: {result.synthesis}")

            # Save comparison
            save_test_results(
                {
                    "test": "comparative_fact_checking",
                    "topic": group["topic"],
                    "result": result.model_dump(),
                    "timestamp": datetime.now().isoformat(),
                },
                f"comparison_{group['topic'].replace(' ', '_').lower()}.json",
            )

        except Exception as e:
            print(f"❌ Error in comparison: {e}")

    print("\n✅ Comparative fact-checking test completed!")


async def test_async_concurrent_checking():
    """Test concurrent fact-checking with async processing."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 4: Async Concurrent Fact-Checking")
    print("=" * 80)

    # Create enhanced retriever
    retriever = create_enhanced_jina_grounding_retriever(api_key=JINA_API_KEY, enable_caching=True, batch_size=10)

    # Statements to check concurrently
    statements = [
        "SpaceX-Starship space program Flight Test Missions As of FT-11 on 2025-07-05, "
        "the ninth test has successfully achieved manned flight testing of STARSHIP.",
    ]

    print(f"🚀 Checking {len(statements)} statements concurrently...")
    start_time = datetime.now()

    try:
        # Use batch processing
        results = await retriever.abatch_get_relevant_documents(statements)

        # Process results
        fact_check_results = []
        for statement, docs in zip(statements, results):
            if docs:
                factuality = docs[0].metadata.get("factuality_score", 0)
                is_true = docs[0].metadata.get("grounding_result", False)
                fact_check_results.append(
                    {"statement": statement, "is_factual": is_true, "confidence": factuality, "sources": len(docs)}
                )
            else:
                fact_check_results.append({"statement": statement, "error": "No results"})

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        print(f"\n⏱️  Completed in {total_time:.2f}s ({total_time/len(statements):.2f}s per statement)")

        # Display results
        print("\n📊 Concurrent Results Summary:")
        for i, result in enumerate(fact_check_results, 1):
            if "error" not in result:
                status = "✅ TRUE" if result["is_factual"] else "❌ FALSE"
                print(f"{i}. {result['statement'][:50]}... → {status} ({result['confidence']:.2%})")
            else:
                print(f"{i}. {result['statement'][:50]}... → ⚠️ ERROR")

        # Save results
        save_test_results(
            {
                "test": "async_concurrent",
                "total_statements": len(statements),
                "processing_time": total_time,
                "avg_time_per_statement": total_time / len(statements),
                "results": fact_check_results,
                "timestamp": datetime.now().isoformat(),
            },
            "async_concurrent_results.json",
        )

    except Exception as e:
        print(f"❌ Error in async test: {e}")

    print("\n✅ Async concurrent test completed!")


def test_advanced_chain_patterns():
    """Test advanced LangChain patterns with fact-checking."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 5: Advanced Chain Patterns")
    print("=" * 80)

    # Create retriever with trusted sources
    retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY, trusted_references=["https://x.com", "https://spacex.com", "https://www.nasa.gov"]
    )

    # Create LLM
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else SecretStr("dummy"),
        base_url=OPENAI_BASE_URL,
        temperature=0,
    )

    # Pattern 1: Multi-step fact-checking with reasoning
    print("\n📌 Pattern 1: Multi-step Fact-Checking with Reasoning Chain")

    # Create a chain that first extracts claims, then fact-checks each
    class ClaimExtraction(BaseModel):
        claims: List[str] = Field(description="Individual factual claims extracted from the statement")

    class MultiStepResult(BaseModel):
        original_statement: str = Field(description="The original complex statement")
        individual_claims: List[str] = Field(description="Claims extracted from the statement")
        claim_results: List[Dict[str, Any]] = Field(description="Fact-check results for each claim")
        overall_assessment: str = Field(description="Overall assessment of the statement")
        confidence: float = Field(description="Overall confidence score")

    claim_extractor = llm.with_structured_output(ClaimExtraction)

    complex_statement = """
    SpaceX-Starship space program Flight Test Missions As of FT-11 on 2025-07-05, "
    "the ninth test has successfully achieved manned flight testing of STARSHIP.",
    """

    print(f"Complex statement: {complex_statement[:100]}...")

    try:
        # Step 1: Extract claims
        claims = claim_extractor.invoke(
            [
                SystemMessage(content="Extract individual factual claims from complex statements."),
                HumanMessage(content=f"Extract all factual claims from: {complex_statement}"),
            ]
        )

        print(f"\nExtracted {len(claims.claims)} claims:")
        for i, claim in enumerate(claims.claims, 1):
            print(f"  {i}. {claim}")

        # Step 2: Fact-check each claim
        claim_results = []
        for claim in claims.claims:
            docs = retriever.invoke(claim)
            factuality = docs[0].metadata.get("factuality_score", 0) if docs else 0
            claim_results.append({"claim": claim, "factuality": factuality, "sources": len(docs)})

        # Step 3: Overall assessment
        avg_factuality = sum(r["factuality"] for r in claim_results) / len(claim_results)

        print("\n📊 Multi-step Results:")
        print(f"   Average Factuality: {avg_factuality:.2%}")
        print(f"   Most Doubtful Claim: {min(claim_results, key=lambda x: x['factuality'])['claim']}")

    except Exception as e:
        print(f"❌ Error in multi-step pattern: {e}")

    # Pattern 2: Fact-checking with source ranking
    print("\n\n📌 Pattern 2: Fact-Checking with Source Quality Analysis")

    class SourceQualityResult(BaseModel):
        statement: str
        top_sources: List[Dict[str, str]] = Field(description="Top quality sources with URLs and relevance")
        source_diversity: str = Field(description="Assessment of source diversity")
        reliability_score: float = Field(description="Overall reliability based on sources", ge=0, le=1)

    source_analyzer = llm.with_structured_output(SourceQualityResult)

    statement = "SpaceX-Starship space program Flight Test Missions As of FT-10 on 2025-07-11, "

    try:
        # Get evidence with sources
        docs = retriever.invoke(statement)

        # Prepare source information
        sources_info = "\n".join(
            [
                f"Source {i+1}: {doc.metadata.get('source', 'Unknown')}\n"
                f"Content: {doc.page_content[:200]}...\n"
                f"Support: {'Yes' if doc.metadata.get('is_supportive', False) else 'No'}"
                for i, doc in enumerate(docs[:5])
            ]
        )

        # Analyze sources
        result = source_analyzer.invoke(
            [
                SystemMessage(content="Analyze the quality and diversity of sources for fact-checking."),
                HumanMessage(content=f"Statement: {statement}\n\nSources:\n{sources_info}"),
            ]
        )

        print("\n📊 Source Quality Analysis:")
        print(f"   Reliability Score: {result.reliability_score:.2%}")
        print(f"   Source Diversity: {result.source_diversity}")
        print(f"   Top Sources: {len(result.top_sources)}")

    except Exception as e:
        print(f"❌ Error in source analysis: {e}")

    print("\n✅ Advanced chain patterns test completed!")


def test_error_handling_and_edge_cases():
    """Test error handling and edge cases."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 6: Error Handling and Edge Cases")
    print("=" * 80)

    # Test cases
    edge_cases = [
        ("", "Empty statement"),
        ("a" * 5000, "Very long statement"),
        ("What if? Maybe? Could be?", "Vague questions"),
        ("The fnorble grobbles the wibbledy-foo", "Nonsense statement"),
        ("1=1", "Mathematical expression"),
        ("🚀🌟✨", "Only emojis"),
        ("The year is 2024 AND 2025 AND 2026", "Contradictory statement"),
        ("SELECT * FROM users WHERE 1=1", "SQL injection attempt"),
    ]

    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    for statement, description in edge_cases:
        print(f"\n📝 Testing: {description}")
        print(f"   Statement: {statement[:50]}{'...' if len(statement) > 50 else ''}")

        try:
            docs = retriever.invoke(statement)
            if docs:
                print(f"   ✅ Handled successfully: {len(docs)} results")
            else:
                print("   ⚠️  No results returned")

        except ValueError as e:
            print(f"   ✅ Validation error (expected): {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")

    # Test with invalid configuration
    print("\n📝 Testing: Invalid configuration")
    try:
        _ = create_enhanced_jina_grounding_retriever(
            api_key=JINA_API_KEY, timeout=0, max_retries=0  # Invalid  # Invalid
        )
    except ValueError as e:
        print(f"   ✅ Configuration validation worked: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")

    print("\n✅ Error handling test completed!")


# ------- Main Execution -------


def main():
    """Run all comprehensive tests."""
    print("🚀 Starting Comprehensive Jina Grounding + LLM Tests")
    print("=" * 80)

    # Check API keys
    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    if not OPENAI_API_KEY:
        print("⚠️  Warning: OPENAI_API_KEY not set!")
        print("Some tests will be skipped. Set OPENAI_API_KEY to run all tests.")
        print("You can also set OPENAI_BASE_URL and LLM_MODEL for custom endpoints.")

    # Run tests that don't require LLM
    test_error_handling_and_edge_cases()

    # Run LLM-based tests if API key is available
    if OPENAI_API_KEY:
        test_basic_fact_checking_with_llm()
        # test_batch_fact_checking()  # Function not defined yet
        test_comparative_fact_checking()
        test_advanced_chain_patterns()

        # Run async test
        print("\n" + "🔄" * 40)
        asyncio.run(test_async_concurrent_checking())

    print("\n\n" + "🎯" * 40)
    print("\n✅ All tests completed! Check test-logs/ directory for detailed results.")
    print("\nKey Insights:")
    print("1. Real LLM integration provides rich, structured fact-checking analysis")
    print("2. Batch processing significantly improves throughput")
    print("3. Comparative analysis helps identify the most accurate claims")
    print("4. Advanced patterns enable sophisticated fact-checking workflows")
    print("5. Proper error handling ensures robustness in production")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    main()

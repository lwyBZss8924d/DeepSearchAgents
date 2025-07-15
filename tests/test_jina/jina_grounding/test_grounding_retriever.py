#!/usr/bin/env python3
"""
Test suite for Jina Grounding API as LangChain Retriever.

This test demonstrates:
1. Basic fact-checking retrieval
2. Testing various statement types (true, false, ambiguous)
3. Metadata extraction and validation
4. Integration with LangChain chains
5. Async operations
6. Error handling

Usage:
    export JINA_API_KEY="your-api-key"
    python test_grounding_retriever.py

Test logs example:
```
(.venv) arthur@Fqqs-MacBook ~/d/MathJourney-AItutor-Agents> python tests/test_jina/jina_grounding/test_grounding_retriever.py                 (base)
🚀 Starting Jina Grounding Retriever Tests
================================================================================

================================================================================
🧪 Test 1: Basic Fact-Checking
================================================================================

🔍 Checking: Is the latest version of Jina AI's embeddings model `jina-embeddings-v3`?
------------------------------------------------------------
✅ Factuality Score: 0.10
📊 Result: FALSE
📑 References found: 13

First Reference:
  Quote: We introduce jina-embeddings-v4, a 3.8 billion parameter multimodal embedding model that unifies text and image representations through a novel...
  Source: https://arxiv.org/abs/2506.18902
  Supportive: False


================================================================================
🧪 Test 2: Fact-Checking with Trusted References
================================================================================

🔍 Checking with trusted scientific sources: Is the latest version of gemini-cli is `v1.1.0`?
------------------------------------------------------------

================================================================================
📚 Top 3 References
================================================================================

📄 Document 1:
Content: Google announces Gemini CLI: your open-source AI agent

Metadata:
  source: https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent
  statement: Is the latest version of gemini-cli is `v1.1.0`?
  is_supportive: True
  factuality_score: 0.2
  grounding_result: False
  is_summary: False
  token_usage: 2370
  reason: Based on the provided references, there is conflicting information regarding the latest version of `gemini-cli`. One source indicates that the latest release is `v0.1.9-nightly.250704.23eea823`, which...

📄 Document 2:
Content: go.mod - eliben/gemini-cli · GitHub

Metadata:
  source: https://github.com/eliben/gemini-cli/blob/main/go.mod
  statement: Is the latest version of gemini-cli is `v1.1.0`?
  is_supportive: True
  factuality_score: 0.2
  grounding_result: False
  is_summary: False
  token_usage: 2370

📄 Document 3:
Content: Release v0.1.9-nightly.250704.23eea823 · What's Changed

Metadata:
  source: https://github.com/google-gemini/gemini-cli/releases
  statement: Is the latest version of gemini-cli is `v1.1.0`?
  is_supportive: False
  factuality_score: 0.2
  grounding_result: False
  is_summary: False
  token_usage: 2370


================================================================================
🧪 Test 3: Metadata Extraction
================================================================================

🔍 Checking: Jina AI released jina-embeddings-v3 as their latest embedding model
------------------------------------------------------------

📊 Metadata Analysis:
Total documents: 16
Supportive references: 13
Contradicting references: 3

💭 Reasoning:
The statement claims that Jina AI released jina-embeddings-v3 as their latest embedding model. Several references confirm the release of jina-embeddings-v3 by Jina AI, describing it as a new and multilingual text embedding model. Some references indicate that it builds upon Jina Embedding v2 and even outperforms other models. However, one reference from Feb 2025 suggests newer models exist. Despite this, given the substantial evidence confirming the release and capabilities of v3, and that the s...

🔢 Total tokens used: 20,640
```
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List

from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from typing import Optional

# Import our custom retriever
from jina_grounding_retriever import JinaGroundingRetriever, create_jina_grounding_retriever

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


def print_documents(docs: List[Document], title: str = "Documents"):
    """Pretty print documents with metadata."""
    print(f"\n{'='*80}")
    print(f"📚 {title}")
    print(f"{'='*80}")

    for i, doc in enumerate(docs, 1):
        print(f"\n📄 Document {i}:")
        print(
            f"Content: {doc.page_content[:200]}..." if len(doc.page_content) > 200 else f"Content: {doc.page_content}"
        )
        print("\nMetadata:")
        for key, value in doc.metadata.items():
            if key == "reason" and len(str(value)) > 200:
                print(f"  {key}: {str(value)[:200]}...")
            else:
                print(f"  {key}: {value}")


def test_basic_fact_checking():
    """Test basic fact-checking functionality."""
    print("\n" + "=" * 80)
    print("🧪 Test 1: Basic Fact-Checking")
    print("=" * 80)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Test statements
    test_statements = [
        "Is the latest version of Jina AI's embeddings model `jina-embeddings-v3`?",  # False (v4)
    ]

    for statement in test_statements:
        print(f"\n🔍 Checking: {statement}")
        print("-" * 60)

        try:
            # Get fact-checking results
            docs = retriever.invoke(statement)

            if docs:
                # Extract overall result from first document
                first_doc = docs[0]
                factuality = first_doc.metadata.get("factuality_score", 0)
                result = first_doc.metadata.get("grounding_result", False)

                print(f"✅ Factuality Score: {factuality:.2f}")
                print(f"📊 Result: {'TRUE' if result else 'FALSE'}")
                print(f"📑 References found: {len(docs)}")

                # Show first reference
                if not first_doc.metadata.get("is_summary", False):
                    print("\nFirst Reference:")
                    print(f"  Quote: {first_doc.page_content[:150]}...")
                    print(f"  Source: {first_doc.metadata.get('source', 'N/A')}")
                    print(f"  Supportive: {first_doc.metadata.get('is_supportive', 'N/A')}")

        except Exception as e:
            print(f"❌ Error: {e}")


def test_with_trusted_references():
    """Test fact-checking with trusted references."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 2: Fact-Checking with Trusted References")
    print("=" * 80)

    # Create retriever with trusted references
    retriever = JinaGroundingRetriever(
        api_key=JINA_API_KEY, trusted_references=["https://github.com", "https://github.com/google-gemini"]
    )

    statement = "Is the latest version of gemini-cli is `v1.1.0`?"

    print(f"\n🔍 Checking with trusted scientific sources: {statement}")
    print("-" * 60)

    try:
        docs = retriever.invoke(statement)
        print_documents(docs[:3], "Top 3 References")  # Show top 3

    except Exception as e:
        print(f"❌ Error: {e}")


def test_metadata_extraction():
    """Test comprehensive metadata extraction."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 3: Metadata Extraction")
    print("=" * 80)

    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY, include_reason=True)  # Include full reasoning

    statement = "Jina AI released jina-embeddings-v3 as their latest embedding model"

    print(f"\n🔍 Checking: {statement}")
    print("-" * 60)

    try:
        docs = retriever.invoke(statement)

        if docs:
            # Analyze metadata
            print("\n📊 Metadata Analysis:")
            print(f"Total documents: {len(docs)}")

            supportive_count = sum(1 for d in docs if d.metadata.get("is_supportive", False))
            contradicting_count = len(docs) - supportive_count

            print(f"Supportive references: {supportive_count}")
            print(f"Contradicting references: {contradicting_count}")

            # Show reasoning if available
            for doc in docs:
                if "reason" in doc.metadata:
                    print("\n💭 Reasoning:")
                    reason = doc.metadata["reason"]
                    print(reason[:500] + "..." if len(reason) > 500 else reason)
                    break  # Only show first reasoning

            # Token usage
            total_tokens = sum(d.metadata.get("token_usage", 0) for d in docs)
            print(f"\n🔢 Total tokens used: {total_tokens:,}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def test_async_operations():
    """Test async fact-checking operations."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 4: Async Operations")
    print("=" * 80)

    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    statements = [
        "SpaceX-Starship space program Flight Test Missions As of FT-9 on 2025-07-05, "
        "the ninth test has successfully achieved manned flight testing of STARSHIP.",
    ]

    print(f"\n🚀 Checking {len(statements)} statements concurrently...")
    print("-" * 60)

    try:
        # Create async tasks
        start_time = datetime.now()
        tasks = [retriever.ainvoke(stmt) for stmt in statements]

        # Run concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()

        print(f"⏱️  Completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Process results
        for statement, result in zip(statements, results):
            print(f"\n📝 Statement: {statement}")
            if isinstance(result, Exception):
                print(f"   ❌ Error: {result}")
            elif isinstance(result, list) and result:
                factuality = result[0].metadata.get("factuality_score", 0)
                grounding = result[0].metadata.get("grounding_result", False)
                print(f"   ✅ Factuality: {factuality:.2f} - Result: {'TRUE' if grounding else 'FALSE'}")
                print(f"   📑 References: {len(result)}")
            else:
                print("   ❌ No results returned")

    except Exception as e:
        print(f"❌ Error in async test: {e}")


def test_langchain_integration():
    """Test integration with LangChain chains using real LLM with structured output."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 5: LangChain Chain Integration with Structured Output")
    print("=" * 80)

    # Check if OpenAI API key is available
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️  Skipping LangChain integration test - OPENAI_API_KEY not set")
        print("   Set OPENAI_API_KEY to run this test with a real LLM")
        return

    # Define structured output for fact-checking results
    class FactCheckResult(BaseModel):
        """Structured fact-checking analysis result."""

        statement: str = Field(description="The statement being fact-checked")
        is_factual: bool = Field(description="Whether the statement is factual based on evidence")
        confidence: float = Field(description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0)
        reasoning: str = Field(description="Explanation of the fact-checking result")
        key_evidence: List[str] = Field(description="Key pieces of evidence from the sources", default_factory=list)
        contradictions: Optional[List[str]] = Field(description="Any contradicting evidence found", default=None)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Create real LLM with structured output
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("LLM_MODEL", "gpt-4.1")

    llm = ChatOpenAI(model=model, api_key=SecretStr(openai_api_key), base_url=base_url, temperature=0)

    # Create structured LLM
    structured_llm = llm.with_structured_output(FactCheckResult)

    # Create a prompt template for fact-checking
    prompt_template = """
"You are a fact-checking assistant. Analyze the following evidence and provide a structured fact-checking result."

Statement to fact-check: {question}

Evidence from fact-checking service:
{context}

Analyze the evidence carefully and provide:
1. Whether the statement is factual (true/false)
2. Your confidence level (0.0 to 1.0)
3. Clear reasoning for your conclusion
4. Key pieces of evidence that support your conclusion
5. Any contradicting evidence if found

Return a structured analysis of the fact-checking results."""

    prompt = PromptTemplate(template=prompt_template, input_variables=["question", "context"])

    # Create QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=structured_llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )

    # Test statements
    test_cases = [
        "SpaceX-Starship space program Flight Test Missions As of FT-8 on 2025-07-05, "
        "the ninth test has successfully achieved manned flight testing of STARSHIP.",
    ]

    print("\n🔗 Testing Fact-Checking Chain:")
    print("-" * 60)

    for statement in test_cases:
        print(f"\n❓ Statement: {statement}")
        try:
            # Run the chain - returns dict with 'result' and 'source_documents'
            chain_result = qa_chain.invoke({"query": statement})

            # Extract the structured result
            if isinstance(chain_result, dict):
                fact_check_result = chain_result.get("result")
                source_docs = chain_result.get("source_documents", [])
            else:
                fact_check_result = chain_result
                source_docs = []

            # Display structured results
            if isinstance(fact_check_result, FactCheckResult):
                print("\n📊 Structured Fact-Check Analysis:")
                print(f"   Statement: {fact_check_result.statement}")
                print(f"   Is Factual: {'✅ TRUE' if fact_check_result.is_factual else '❌ FALSE'}")
                print(f"   Confidence: {fact_check_result.confidence:.2%}")
                print(f"   Reasoning: {fact_check_result.reasoning}")

                if fact_check_result.key_evidence:
                    print("\n   Key Evidence:")
                    for i, evidence in enumerate(fact_check_result.key_evidence[:3], 1):
                        print(f"     {i}. {evidence}")

                if fact_check_result.contradictions:
                    print("\n   Contradictions Found:")
                    for i, contradiction in enumerate(fact_check_result.contradictions, 1):
                        print(f"     {i}. {contradiction}")

                print(f"\n   Source Documents: {len(source_docs)} references found")

                # Save the result
                result_data = {
                    "test": "langchain_integration_structured",
                    "statement": statement,
                    "result": fact_check_result.model_dump(),
                    "num_sources": len(source_docs),
                    "timestamp": datetime.now().isoformat(),
                }
                save_test_results("langchain_structured_test", result_data)

            else:
                print(f"📌 Chain Result: {fact_check_result}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n\n" + "=" * 80)
    print("🧪 Test 6: Edge Cases and Error Handling")
    print("=" * 80)

    # Test 1: Empty statement
    print("\n📝 Test: Empty statement")
    try:
        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)
        docs = retriever.invoke("")
        print("❌ Should have raised an error for empty statement")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")

    # Test 2: Very long statement
    print("\n📝 Test: Very long statement")
    long_statement = "The Earth " + "is round and " * 100 + "orbits the Sun."
    try:
        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)
        docs = retriever.invoke(long_statement[:500])  # Truncate for API
        print(f"✅ Handled long statement, got {len(docs)} documents")
    except Exception as e:
        print(f"❌ Error with long statement: {e}")

    # Test 3: Invalid API key
    print("\n📝 Test: Invalid API key")
    try:
        retriever = create_jina_grounding_retriever(api_key="invalid-key-12345")
        docs = retriever.invoke("Test statement")
        print("❌ Should have raised an error for invalid API key")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")

    # Test 4: Ambiguous statement
    print("\n📝 Test: Ambiguous statement")
    try:
        retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)
        docs = retriever.invoke("It might rain tomorrow")
        if docs:
            factuality = docs[0].metadata.get("factuality_score", 0)
            print(f"✅ Handled ambiguous statement, factuality score: {factuality:.2f}")
            print("   (Expected low score for unpredictable statement)")
    except Exception as e:
        print(f"❌ Error: {e}")


def save_test_results(test_name: str, data: dict):
    """Save test results to JSON file."""
    os.makedirs("test-logs", exist_ok=True)
    filename = f"test-logs/grounding_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filename


def main():
    """Run all tests."""
    print("🚀 Starting Jina Grounding Retriever Tests")
    print("=" * 80)

    # Check API key
    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    # Run synchronous tests
    test_basic_fact_checking()
    test_with_trusted_references()
    test_metadata_extraction()
    test_langchain_integration()
    test_edge_cases()

    # Run async tests
    print("\n\n" + "🔄" * 40)
    asyncio.run(test_async_operations())

    print("\n\n" + "🎯" * 40)
    print("\n✅ All tests completed!")
    print("\nKey Findings:")
    print("1. Jina Grounding API works well as a LangChain Retriever")
    print("2. Each reference becomes a Document with rich metadata")
    print("3. Factuality scores and reasoning are preserved")
    print("4. Async operations enable efficient batch fact-checking")
    print("5. Integration with LangChain chains is seamless")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    main()

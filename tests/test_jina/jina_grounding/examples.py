#!/usr/bin/env python3
"""
Usage examples for Jina Grounding API as LangChain Retriever.

This file demonstrates various ways to use the JinaGroundingRetriever
in real-world scenarios with LangChain.

Examples included:
1. Simple fact-checking
2. Integration with QA chains
3. Multi-statement fact-checking
4. Combining with other retrievers
5. Building a fact-checking chatbot

Usage:
    export JINA_API_KEY="your-api-key"
    python examples.py
"""

import os
from typing import List
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import FakeListLLM
from langchain.retrievers import EnsembleRetriever

# Import our custom retriever
from jina_grounding_retriever import create_jina_grounding_retriever

# Get API key
JINA_API_KEY = os.getenv("JINA_API_KEY")


def example_simple_fact_checking():
    """Example 1: Simple fact-checking usage."""
    print("\n" + "=" * 80)
    print("📚 Example 1: Simple Fact-Checking")
    print("=" * 80)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Fact-check a statement
    statement = "The James Webb Space Telescope was launched on December 25, 2021"

    print(f"\n🔍 Checking: {statement}")
    docs = retriever.invoke(statement)

    # Display results
    if docs:
        factuality = docs[0].metadata.get("factuality_score", 0)
        result = docs[0].metadata.get("grounding_result", False)

        print("\n📊 Results:")
        print(f"  Factuality Score: {factuality:.2%}")
        print(f"  Verdict: {'✅ TRUE' if result else '❌ FALSE'}")
        print(f"  References Found: {len(docs)}")

        print("\n📑 Supporting Evidence:")
        for i, doc in enumerate(docs[:3], 1):  # Show top 3
            print(f"\n  {i}. {doc.metadata['source']}")
            print(f'     "{doc.page_content[:100]}..."')
            print(f"     Supportive: {'Yes' if doc.metadata['is_supportive'] else 'No'}")


def example_qa_chain_integration():
    """Example 2: Integration with QA chains for fact-aware responses."""
    print("\n\n" + "=" * 80)
    print("📚 Example 2: QA Chain Integration")
    print("=" * 80)

    # Create retriever
    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Create a prompt template
    prompt_template = """You are a fact-checking assistant. Based on the evidence provided, 
give a detailed answer about the truthfulness of the statement.

Statement: {question}

Evidence from fact-checking:
{context}

Please provide:
1. Whether the statement is true or false
2. A brief explanation based on the evidence
3. Confidence level in your assessment

Answer:"""

    prompt = PromptTemplate(template=prompt_template, input_variables=["question", "context"])

    # For demo, use a simple fake LLM that formats the response
    # In production, use a real LLM like ChatOpenAI
    fake_responses = [
        """Based on the evidence provided:

1. **Verdict**: TRUE ✅
2. **Explanation**: The evidence confirms that the James Webb Space Telescope was indeed launched on December 25, "
   "2021. Multiple credible sources including NASA's official website and news outlets corroborate this date.
3. **Confidence Level**: Very High (95%) - The factuality score of 0.95 and consistent references strongly "
   "support this conclusion."""
    ]

    llm = FakeListLLM(responses=fake_responses)

    # Create QA chain
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, chain_type_kwargs={"prompt": prompt})

    # Test the chain
    statement = "The James Webb Space Telescope was launched on December 25, 2021"

    print(f"\n🔍 Analyzing: {statement}")
    result = qa_chain.run(statement)

    print("\n📋 Fact-Checking Report:")
    print(result)


def example_batch_fact_checking():
    """Example 3: Batch fact-checking multiple statements."""
    print("\n\n" + "=" * 80)
    print("📚 Example 3: Batch Fact-Checking")
    print("=" * 80)

    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Multiple statements to check
    statements = [
        "COVID-19 vaccines alter human DNA",
        "The Amazon rainforest produces 20% of Earth's oxygen",
        "Mount Everest is growing taller each year",
        "Goldfish have a 3-second memory span",
        "The Great Pacific Garbage Patch is visible from space",
    ]

    print("\n🔍 Batch Fact-Checking Results:\n")

    results = []
    for statement in statements:
        try:
            docs = retriever.invoke(statement)
            if docs:
                factuality = docs[0].metadata.get("factuality_score", 0)
                result = docs[0].metadata.get("grounding_result", False)
                results.append({"statement": statement, "factuality": factuality, "result": result, "refs": len(docs)})
        except Exception as e:
            print(f"Error checking: {statement} - {e}")

    # Display results in a table format
    print("Statement                                           | Factuality | Result | Refs")
    print("-" * 80)
    for r in results:
        statement_short = r["statement"][:50] + "..." if len(r["statement"]) > 50 else r["statement"].ljust(50)
        result_str = "✅ TRUE " if r["result"] else "❌ FALSE"
        print(f"{statement_short} | {r['factuality']:.2f}      | {result_str} | {r['refs']}")


def example_hybrid_retriever():
    """Example 4: Combining Grounding with other retrievers."""
    print("\n\n" + "=" * 80)
    print("📚 Example 4: Hybrid Retriever (Grounding + Other Sources)")
    print("=" * 80)

    # Create grounding retriever
    grounding_retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    # Create a mock knowledge base retriever
    # In production, this could be a vector store, BM25, etc.
    class MockKnowledgeRetriever:
        def get_relevant_documents(self, query: str) -> List[Document]:
            # Simulate retrieving from a knowledge base
            return [
                Document(
                    page_content=(
                        "The James Webb Space Telescope is a space telescope "
                        "designed primarily to conduct infrared astronomy."
                    ),
                    metadata={"source": "internal_kb", "doc_id": "jwst_001"},
                ),
                Document(
                    page_content="JWST was developed by NASA with contributions from ESA and CSA.",
                    metadata={"source": "internal_kb", "doc_id": "jwst_002"},
                ),
            ]

    kb_retriever = MockKnowledgeRetriever()

    # Create ensemble retriever
    # Note: EnsembleRetriever requires retrievers to have proper inheritance
    # For demo purposes, we'll combine results manually

    statement = "The James Webb Space Telescope can see further than Hubble"

    print(f"\n🔍 Query: {statement}")

    # Get results from both retrievers
    print("\n📑 Fact-Checking Results:")
    grounding_docs = grounding_retriever.invoke(statement)
    if grounding_docs:
        factuality = grounding_docs[0].metadata.get("factuality_score", 0)
        print(f"  Factuality Score: {factuality:.2%}")
        print(f"  External References: {len(grounding_docs)}")

    print("\n📚 Knowledge Base Results:")
    kb_docs = kb_retriever.get_relevant_documents(statement)
    print(f"  Internal Documents: {len(kb_docs)}")

    # Combine results
    all_docs = grounding_docs + kb_docs
    print(f"\n📊 Combined Results: {len(all_docs)} total documents")
    print("  - Fact-checked external sources")
    print("  - Internal knowledge base entries")


def example_fact_checking_chatbot():
    """Example 5: Building a simple fact-checking chatbot."""
    print("\n\n" + "=" * 80)
    print("📚 Example 5: Fact-Checking Chatbot")
    print("=" * 80)

    retriever = create_jina_grounding_retriever(api_key=JINA_API_KEY)

    print("\n🤖 Fact-Checking Chatbot")
    print("Type 'quit' to exit\n")

    # Simulate a chatbot interaction
    test_queries = ["Is it true that vaccines cause autism?", "Can you verify if the Earth is flat?", "quit"]

    for i, query in enumerate(test_queries):
        if i < len(test_queries) - 1:  # Skip the 'quit' in output
            print(f"👤 User: {query}")

            if query.lower() == "quit":
                break

            try:
                # Get fact-checking results
                docs = retriever.invoke(query)

                if docs:
                    factuality = docs[0].metadata.get("factuality_score", 0)
                    result = docs[0].metadata.get("grounding_result", False)

                    # Generate bot response
                    if factuality > 0.8 and result:
                        response = f"✅ This statement appears to be TRUE with {factuality:.0%} confidence."
                    elif factuality < 0.3 and not result:
                        response = f"❌ This statement appears to be FALSE with {(1-factuality):.0%} confidence."
                    else:
                        response = f"🤔 This statement has mixed evidence. Factuality score: {factuality:.0%}"

                    print(f"🤖 Bot: {response}")

                    # Show top evidence
                    if docs[0].page_content:
                        print(f'    📌 Evidence: "{docs[0].page_content[:100]}..."')
                        print(f"    🔗 Source: {docs[0].metadata.get('source', 'N/A')}")

            except Exception as e:
                print(f"🤖 Bot: Sorry, I encountered an error: {e}")

            print()  # Empty line between interactions


def example_custom_trusted_sources():
    """Example 6: Using custom trusted sources for fact-checking."""
    print("\n\n" + "=" * 80)
    print("📚 Example 6: Custom Trusted Sources")
    print("=" * 80)

    # Create retriever with specific trusted sources
    academic_retriever = create_jina_grounding_retriever(
        api_key=JINA_API_KEY,
        trusted_references=[
            "https://www.nature.com",
            "https://www.science.org",
            "https://www.nejm.org",
            "https://arxiv.org",
            "https://pubmed.ncbi.nlm.nih.gov",
        ],
    )

    statement = "mRNA vaccines use lipid nanoparticles for delivery"

    print(f"\n🔍 Checking with academic sources: {statement}")
    docs = academic_retriever.invoke(statement)

    if docs:
        print("\n📊 Results from trusted academic sources:")
        print(f"  Factuality: {docs[0].metadata.get('factuality_score', 0):.2%}")
        print(f"  Verdict: {'✅ TRUE' if docs[0].metadata.get('grounding_result') else '❌ FALSE'}")

        print("\n📑 Academic References:")
        for i, doc in enumerate(docs[:3], 1):
            source = doc.metadata.get("source", "N/A")
            # Check if it's from our trusted sources
            is_trusted = any(trusted in source for trusted in academic_retriever.trusted_references or [])
            trust_badge = "🏆" if is_trusted else "📄"

            print(f"\n  {i}. {trust_badge} {source}")
            print(f'     "{doc.page_content[:100]}..."')


def main():
    """Run all examples."""
    print("🚀 Jina Grounding Retriever Examples")
    print("=" * 80)

    if not JINA_API_KEY:
        print("❌ Error: JINA_API_KEY environment variable not set!")
        print("Get your free API key at: https://jina.ai/?sui=apikey")
        return

    # Run examples
    example_simple_fact_checking()
    example_qa_chain_integration()
    example_batch_fact_checking()
    example_hybrid_retriever()
    example_fact_checking_chatbot()
    example_custom_trusted_sources()

    print("\n\n" + "🎯" * 40)
    print("\n✅ All examples completed!")
    print("\nKey Takeaways:")
    print("1. JinaGroundingRetriever integrates seamlessly with LangChain")
    print("2. Can be used in QA chains for fact-aware responses")
    print("3. Supports batch processing for multiple statements")
    print("4. Can be combined with other retrievers for hybrid search")
    print("5. Enables building fact-checking applications easily")
    print("\n" + "🎯" * 40)


if __name__ == "__main__":
    main()

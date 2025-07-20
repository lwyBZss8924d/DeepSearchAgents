#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_academic_tookit/demo_paper_retrieval.py

"""
Demonstration script for academic paper retrieval functionality.

This script demonstrates the key functionality of the academic toolkit:
1. Searching for papers about ReAct agent methodology
2. Reading a specific paper (ReAct)
3. Detecting HTML availability for papers
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.academic_tookit import PaperRetriever
from src.core.academic_tookit.models import SearchParams, PaperSource


async def demo_search_react_papers():
    """Example 1: Search AI-LLM Agent papers about ReAct agent methodology."""
    print("\n" + "=" * 60)
    print("Demo 1: Search AI-LLM Agent papers about ReAct methodology")
    print("=" * 60)
    
    # Initialize retriever
    retriever = PaperRetriever()
    
    # Search for ReAct papers
    params = SearchParams(
        query="AI LLM Agent papers ReAct agent methodology derived methods",
        max_results=5,  # Limit for demo
        categories=["cs.AI", "cs.CL"],
        sort_by="relevance"
    )
    
    print(f"\nSearching for: {params.query}")
    papers = await retriever.search(
        query=params.query,
        max_results=params.max_results,
        categories=params.categories,
        sort_by=params.sort_by
    )
    
    print(f"\nFound {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.title}")
        print(f"   ID: {paper.paper_id}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        if len(paper.authors) > 3:
            print(f"            ... and {len(paper.authors) - 3} more")
        print(f"   Published: {paper.published_date.strftime('%Y-%m-%d')}")
        print(f"   URL: {paper.url}")
        if paper.html_url:
            print(f"   HTML: {paper.html_url}")
    
    return papers


async def demo_read_specific_paper():
    """Example 2: Read specific ReAct paper."""
    print("\n" + "=" * 60)
    print("Demo 2: Read ReAct paper (arXiv:2210.03629)")
    print("=" * 60)
    
    retriever = PaperRetriever()
    
    # First get the paper object
    paper_id = "2210.03629"
    print(f"\nGetting paper: {paper_id}")
    
    # Get paper from ArXiv
    paper = await retriever.sources[PaperSource.ARXIV].get_paper(paper_id)
    
    if not paper:
        print(f"Paper {paper_id} not found")
        return None
    
    # Read the paper content
    print(f"Reading paper content...")
    try:
        content = await retriever.read_paper(paper)
        print(f"Successfully read paper in {content.get('content_format', 'unknown')} format")
    except Exception as e:
        print(f"Note: Full content reading requires API keys")
        content = None
    
    if paper:
        print(f"\nPaper details:")
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(paper.authors)}")
        print(f"Published: {paper.published_date.strftime('%Y-%m-%d')}")
        print(f"\nAbstract (first 500 chars):")
        print(paper.abstract[:500] + "...")
        print(f"\nPDF URL: {paper.pdf_url}")
        print(f"HTML URL: {paper.html_url or 'Not available'}")
    else:
        print(f"Failed to read paper {paper_id}")
    
    return paper


async def demo_html_availability():
    """Example 3: Demonstrate HTML availability detection."""
    print("\n" + "=" * 60)
    print("Demo 3: HTML availability detection (ReAct vs CodeAct)")
    print("=" * 60)
    
    retriever = PaperRetriever()
    
    # Check ReAct paper (no HTML)
    react_id = "2210.03629"
    print(f"\nChecking ReAct paper: {react_id}")
    react_paper = await retriever.sources[PaperSource.ARXIV].get_paper(react_id)
    
    if react_paper:
        print(f"Title: {react_paper.title}")
        print(f"HTML URL: {react_paper.html_url or 'Not available'}")
        print(f"Expected: No HTML (paper from 2022)")
    
    # Add delay for rate limiting
    await asyncio.sleep(3)
    
    # Check CodeAct paper (has HTML)
    codeact_id = "2402.01030"
    print(f"\nChecking CodeAct paper: {codeact_id}")
    codeact_paper = await retriever.sources[PaperSource.ARXIV].get_paper(codeact_id)
    
    if codeact_paper:
        print(f"Title: {codeact_paper.title}")
        print(f"HTML URL: {codeact_paper.html_url or 'Not available'}")
        print(f"Expected: Has HTML (paper from 2024)")
    
    # Demonstrate the decision logic
    print("\n" + "-" * 40)
    print("HTML Availability Logic:")
    print("- Papers from 2024+ are assumed to have HTML versions")
    print("- Older papers typically only have PDF versions")
    print("- The toolkit automatically selects the best format")
    
    return react_paper, codeact_paper


async def main():
    """Run all demos."""
    print("\nAcademic Paper Retrieval System Demo")
    print("=====================================")
    
    # Check for API keys
    has_mistral = bool(os.getenv("MISTRAL_API_KEY"))
    has_jina = bool(os.getenv("JINA_API_KEY"))
    
    print(f"\nAPI Keys Configured:")
    print(f"- Mistral: {'✓' if has_mistral else '✗ (PDF reading limited)'}")
    print(f"- Jina: {'✓' if has_jina else '✗ (HTML reading limited)'}")
    
    try:
        # Demo 1: Search for papers
        papers = await demo_search_react_papers()
        await asyncio.sleep(3)  # Rate limit
        
        # Demo 2: Read specific paper
        paper = await demo_read_specific_paper()
        await asyncio.sleep(3)  # Rate limit
        
        # Demo 3: HTML availability
        react_paper, codeact_paper = await demo_html_availability()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        
        # Summary
        print("\nKey Features Demonstrated:")
        print("✓ Natural language search converted to ArXiv queries")
        print("✓ Category filtering (cs.AI, cs.CL)")
        print("✓ Reading papers by ID")
        print("✓ Automatic HTML availability detection")
        print("✓ Metadata extraction from search results")
        
        if not (has_mistral and has_jina):
            print("\n⚠️  Note: Full paper content extraction requires API keys")
            print("   Set MISTRAL_API_KEY for PDF parsing")
            print("   Set JINA_API_KEY for HTML parsing")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
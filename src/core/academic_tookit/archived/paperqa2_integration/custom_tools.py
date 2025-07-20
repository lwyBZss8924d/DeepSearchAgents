#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/custom_tools.py
# code style: PEP 8

"""
Custom tools for PaperQA2 agent that use our search infrastructure.

This module provides replacements for PaperQA2's built-in tools to integrate
with our ArXiv search and other academic sources.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

from paperqa.agents.tools import NamedTool, EnvironmentState
from paperqa import Settings, Docs
from paperqa.utils import ImpossibleParsingError

from src.core.academic_tookit.paper_retrievaler import PaperRetriever

logger = logging.getLogger(__name__)


class ArxivPaperSearch(NamedTool):
    """
    Custom paper search tool that uses our ArXiv search.
    
    Replaces PaperQA2's file-based search with API-based paper retrieval.
    """
    
    TOOL_FN_NAME = "paper_search"
    
    def __init__(self, settings: Settings, docs: Docs, **kwargs):
        """Initialize with settings and docs reference."""
        super().__init__()
        # Initialize all fields after parent init
        self.settings = settings
        self.docs = docs
        self.paper_retriever = PaperRetriever()
        self.previous_searches: Dict[tuple[str, str | None], int] = {}
        
    async def paper_search(
        self,
        query: str,
        min_year: int | None,
        max_year: int | None,
        state: EnvironmentState,
    ) -> str:
        """
        Search for papers using our ArXiv API.
        
        This replaces the file-based search with API-based retrieval.
        
        Args:
            query: Search query
            min_year: Minimum publication year
            max_year: Maximum publication year
            state: Current environment state
            
        Returns:
            Status message describing search results
        """
        # Check if this is a continuation
        year_range = f"{min_year or ''}-{max_year or ''}" if (min_year or max_year) else None
        search_key = (query, year_range)
        offset = self.previous_searches.get(search_key, 0)
        
        logger.info(f"Searching ArXiv for '{query}' (offset: {offset})")
        
        try:
            # Search using our retriever
            papers = await self.paper_retriever.search(
                query=query,
                sources=["arxiv"],
                max_results=10
            )
            
            # Skip papers we've already seen
            new_papers = papers[offset:offset + 5]  # Process 5 at a time
            
            if not new_papers:
                return "No new papers found for this query. Try a different search."
            
            # Add papers to docs
            added_count = 0
            paper_titles = []
            
            for paper in new_papers:
                try:
                    # Download PDF if available
                    if paper.pdf_url:
                        # Create a temporary file path for the PDF
                        import tempfile
                        index_dir = getattr(self.settings, 'index_directory', None) or tempfile.gettempdir()
                        pdf_path = Path(index_dir) / f"{paper.paper_id}.pdf"
                        
                        # Download PDF content
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(paper.pdf_url) as response:
                                if response.status == 200:
                                    pdf_content = await response.read()
                                    pdf_path.write_bytes(pdf_content)
                                    
                                    # Add to docs
                                    await self.docs.aadd(
                                        pdf_path,
                                        docname=paper.title,
                                        settings=self.settings,
                                        disable_doc_details_retrieval=True,  # Don't fetch metadata
                                        metadata={
                                            "paper_id": paper.paper_id,
                                            "authors": paper.authors,
                                            "year": paper.published_date.year if paper.published_date else None,
                                            "source": "arxiv",
                                            "url": paper.url,
                                            "abstract": paper.abstract
                                        }
                                    )
                                    added_count += 1
                                    paper_titles.append(paper.title)
                                    
                except Exception as e:
                    logger.warning(f"Failed to add paper {paper.title}: {e}")
                    continue
            
            # Update offset for continuation
            self.previous_searches[search_key] = offset + len(new_papers)
            
            # Build status message
            if added_count == 0:
                return f"Found {len(new_papers)} papers but could not add any. Try searching again."
            
            status = f"Added {added_count} new papers:\n"
            for i, title in enumerate(paper_titles, 1):
                status += f"{i}. {title}\n"
            
            status += f"\nTotal papers in collection: {len(self.docs.docs)}"
            
            if len(new_papers) == 5:
                status += "\nMore papers available - search again to continue."
                
            return status
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search failed with error: {str(e)}. Please try a different query."


def create_custom_tools(settings: Settings, docs: Docs) -> List[NamedTool]:
    """
    Create custom tools for PaperQA2 agent.
    
    Args:
        settings: PaperQA2 settings
        docs: Docs object to populate
        
    Returns:
        List of custom tools
    """
    # Create our custom search tool
    arxiv_search = ArxivPaperSearch(settings=settings, docs=docs)
    
    # For now, return only our custom search tool
    # The agent will get other default tools automatically
    return [arxiv_search]
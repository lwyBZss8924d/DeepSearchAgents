#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/academic_retrieval.py
# code style: PEP 8

"""
Academic Retrieval Tool for DeepSearchAgents.

This tool provides academic paper search capabilities using the new
direct API implementation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from smolagents import Tool
from src.core.academic_tookit import PaperRetriever, Paper

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


class AcademicRetrieval(Tool):
    """
    Search academic papers from multiple sources.

    This tool provides academic paper search using direct APIs for:
    - ArXiv (Default Source)

    Example usage:
        # Search for papers
        results = academic_retrieval(
            query="machine learning in drug discovery",
            operation="search",
            num_results=20
        )

        # Get specific paper
        paper = academic_retrieval(
            query="2301.12345",
            operation="get_paper",
            source="arxiv"
        )

        # Find related papers
        related = academic_retrieval(
            query="2301.12345",
            operation="related",
            source="arxiv",
            num_results=10
        )
    """

    name = "academic_retrieval"
    description = (
        "Search academic papers from ArXiv and other sources. "
        "Operations: 'search' (find papers), 'get_paper' (get by ID), "
        "'related' (find similar papers). "
        "Returns structured results with titles, URLs, abstracts, "
        "and metadata."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": (
                "Search query for 'search' operation, "
                "or paper ID for 'get_paper'/'related' operations"
            ),
        },
        "operation": {
            "type": "string",
            "description": (
                "Operation type: 'search' (default), 'get_paper', "
                "or 'related'"
            ),
            "default": "search",
            "nullable": True,
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return",
            "default": 20,
            "nullable": True,
        },
        "sources": {
            "type": "array",
            "description": (
                "List of sources to search. "
                "Available: ['arxiv']. Default: all available"
            ),
            "nullable": True,
        },
        "categories": {
            "type": "array",
            "description": (
                "Filter by categories (e.g., ['cs.LG', 'cs.AI'])"
            ),
            "nullable": True,
        },
        "start_date": {
            "type": "string",
            "description": "Filter papers after this date (YYYY-MM-DD)",
            "nullable": True,
        },
        "end_date": {
            "type": "string",
            "description": "Filter papers before this date (YYYY-MM-DD)",
            "nullable": True,
        },
        "author": {
            "type": "string",
            "description": "Filter by author name",
            "nullable": True,
        },
        "source": {
            "type": "string",
            "description": (
                "Source for get_paper/related operations "
                "(default: 'arxiv')"
            ),
            "default": "arxiv",
            "nullable": True,
        }
    }
    output_type = "array"

    def __init__(self, cli_console: Optional["Console"] = None, verbose: bool = False):
        """
        Initialize the academic retrieval tool.

        Args:
            cli_console: Optional Rich console for formatted output
            verbose: Enable verbose logging
        """
        super().__init__()
        self.cli_console = cli_console
        self.verbose = verbose
        self._retriever = None
        self._loop = None

    @property
    def retriever(self) -> PaperRetriever:
        """Get or create the paper retriever."""
        if self._retriever is None:
            self._retriever = PaperRetriever()
        return self._retriever

    def forward(
        self,
        query: str,
        operation: str = "search",
        num_results: int = 20,
        sources: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        author: Optional[str] = None,
        source: str = "arxiv"
    ) -> List[Dict[str, Any]]:
        """
        Execute the academic retrieval operation.

        Args:
            query: Search query or paper ID
            operation: Operation type
            num_results: Number of results
            sources: Sources to search
            categories: Category filters
            start_date: Start date filter
            end_date: End date filter
            author: Author filter
            source: Source for get_paper/related

        Returns:
            List of paper results in standardized format
        """
        try:
            # Build kwargs for internal methods
            kwargs = {
                "query": query,
                "operation": operation,
                "num_results": num_results,
                "sources": sources,
                "categories": categories,
                "start_date": start_date,
                "end_date": end_date,
                "author": author,
                "source": source
            }

            # Setup event loop if needed
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

            # Execute operation
            if operation == "search":
                papers = self._loop.run_until_complete(
                    self._search_papers(**kwargs)
                )
            elif operation == "get_paper":
                papers = self._loop.run_until_complete(
                    self._get_paper(**kwargs)
                )
            elif operation == "related":
                papers = self._loop.run_until_complete(
                    self._find_related_papers(**kwargs)
                )
            else:
                raise ValueError(
                    f"Unknown operation: {operation}. "
                    f"Use 'search', 'get_paper', or 'related'"
                )

            # Format results
            return self._format_results(papers)

        except Exception as e:
            logger.error(f"Academic retrieval failed: {e}")

            # Return error in expected format
            return [{
                "title": "Error",
                "url": "",
                "snippet": f"Academic retrieval failed: {str(e)}",
                "error": True
            }]

    async def _search_papers(self, **kwargs) -> List[Paper]:
        """Execute paper search."""
        # Extract search parameters
        query = kwargs.get("query", "")
        if not query:
            raise ValueError("Query is required for search operation")

        # Parse dates if provided
        from datetime import datetime

        start_date = None
        if kwargs.get("start_date"):
            try:
                start_date = datetime.strptime(
                    kwargs["start_date"], "%Y-%m-%d"
                )
            except ValueError:
                logger.warning(
                    f"Invalid start_date format: {kwargs['start_date']}"
                )

        end_date = None
        if kwargs.get("end_date"):
            try:
                end_date = datetime.strptime(
                    kwargs["end_date"], "%Y-%m-%d"
                )
            except ValueError:
                logger.warning(
                    f"Invalid end_date format: {kwargs['end_date']}"
                )

        # Execute search
        papers = await self.retriever.search(
            query=query,
            sources=kwargs.get("sources"),
            max_results=kwargs.get("num_results", 20),
            categories=kwargs.get("categories", []),
            start_date=start_date,
            end_date=end_date,
            author_filter=kwargs.get("author"),
            deduplicate=True
        )

        return papers

    async def _get_paper(self, **kwargs) -> List[Paper]:
        """Get specific paper by ID."""
        paper_id = kwargs.get("query", "")
        if not paper_id:
            raise ValueError("Paper ID is required for get_paper operation")

        source = kwargs.get("source", "arxiv")

        paper = await self.retriever.get_paper(paper_id, source)

        if paper:
            return [paper]
        else:
            return []

    async def _find_related_papers(self, **kwargs) -> List[Paper]:
        """Find papers related to a reference paper."""
        paper_id = kwargs.get("query", "")
        if not paper_id:
            raise ValueError("Paper ID is required for related operation")

        source = kwargs.get("source", "arxiv")

        # First get the reference paper
        ref_paper = await self.retriever.get_paper(paper_id, source)
        if not ref_paper:
            raise ValueError(f"Reference paper {paper_id} not found")

        # Find related papers
        related = await self.retriever.find_related_papers(
            ref_paper,
            max_results=kwargs.get("num_results", 10)
        )

        return related

    def _format_results(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """
        Format papers into standardized output format.

        Args:
            papers: List of Paper objects

        Returns:
            List of formatted paper dictionaries
        """
        results = []

        for paper in papers:
            # Create snippet from abstract
            snippet = paper.abstract
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."

            # Build result entry
            result = {
                "title": paper.title,
                "url": paper.url,
                "snippet": snippet,
                "authors": paper.authors,
                "published_date": (
                    paper.published_date.isoformat()
                    if paper.published_date else None
                ),
                "source": paper.source,
                "categories": paper.categories,
                "paper_id": paper.paper_id,
            }

            # Add optional fields if available
            if paper.pdf_url:
                result["pdf_url"] = paper.pdf_url
            if paper.doi:
                result["doi"] = paper.doi
            if paper.venue:
                result["venue"] = paper.venue
            if paper.citations_count > 0:
                result["citations"] = paper.citations_count

            # Add source-specific metadata
            if paper.extra:
                if "primary_category" in paper.extra:
                    result["primary_category"] = (
                        paper.extra["primary_category"]
                    )
                if "all_sources" in paper.extra:
                    result["found_in_sources"] = paper.extra["all_sources"]

            results.append(result)

        return results

    def __repr__(self) -> str:
        """String representation."""
        sources = []
        if self._retriever:
            sources = self.retriever.get_available_sources()

        return (
            f"<AcademicRetrieval "
            f"sources={sources} "
            f"status={'active' if sources else 'initializing'}>"
        )

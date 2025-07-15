#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_retrievaler.py
# code style: PEP 8

"""
Main paper retriever interface for searching academic papers.

This module provides a unified interface for searching papers across
multiple academic sources with deduplication and ranking.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from .models import Paper, SearchParams, PaperSource
from .paper_search.arxiv import ArxivClient
from .ranking import PaperDeduplicator

logger = logging.getLogger(__name__)


class PaperRetriever:
    """
    Unified interface for paper retrieval from multiple sources.

    This class:
    - Manages multiple paper search clients
    - Handles concurrent searches across sources
    - Deduplicates results
    - Provides caching (future enhancement)
    - Supports reranking (future enhancement)
    """

    def __init__(self):
        """Initialize the paper retriever with available sources."""
        # Initialize available sources
        self.sources: Dict[str, Any] = {}

        # Always initialize ArXiv
        try:
            self.sources[PaperSource.ARXIV] = ArxivClient()
            logger.info("Initialized ArXiv client")
        except Exception as e:
            logger.error(f"Failed to initialize ArXiv client: {e}")

        # Future: Add other sources as they're implemented
        # try:
        #     self.sources[PaperSource.PUBMED] = PubMedClient()
        # except Exception as e:
        #     logger.error(f"Failed to initialize PubMed client: {e}")

        # Initialize utilities
        self.deduplicator = PaperDeduplicator()

        # Cache placeholder (future enhancement)
        self._cache = None

        logger.info(
            f"PaperRetriever initialized with sources: "
            f"{list(self.sources.keys())}"
        )

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_results: int = 20,
        deduplicate: bool = True,
        **kwargs
    ) -> List[Paper]:
        """
        Search for papers across multiple sources.

        Args:
            query: Search query (natural language or structured)
            sources: List of sources to search (None = all available)
            max_results: Maximum results to return
            deduplicate: Whether to deduplicate results
            **kwargs: Additional parameters for SearchParams

        Returns:
            List of papers sorted by relevance

        Raises:
            ValueError: If no sources are available
        """
        # Build search parameters
        params = SearchParams(
            query=query,
            max_results=max_results,
            sources=sources or list(self.sources.keys()),
            **kwargs
        )

        # Validate sources
        available_sources = self._get_available_sources(params.sources)
        if not available_sources:
            raise ValueError(
                f"No available sources found. Requested: {params.sources}, "
                f"Available: {list(self.sources.keys())}"
            )

        # Log search
        logger.info(
            f"Searching for '{query}' in sources: {available_sources} "
            f"(max_results={max_results})"
        )

        # Search all sources concurrently
        papers = await self._search_concurrent(params, available_sources)

        # Deduplicate if requested
        if deduplicate and len(available_sources) > 1:
            papers = self.deduplicator.deduplicate(papers)

        # Limit results
        papers = papers[:max_results]

        logger.info(
            f"Search completed: {len(papers)} papers returned"
        )

        return papers

    async def get_paper(
        self,
        paper_id: str,
        source: str
    ) -> Optional[Paper]:
        """
        Get a specific paper by ID from a source.

        Args:
            paper_id: Paper identifier
            source: Source name

        Returns:
            Paper if found, None otherwise
        """
        if source not in self.sources:
            logger.error(f"Source {source} not available")
            return None

        try:
            client = self.sources[source]
            paper = await client.get_paper(paper_id)
            return paper
        except Exception as e:
            logger.error(
                f"Failed to get paper {paper_id} from {source}: {e}"
            )
            return None

    async def get_paper_by_doi(
        self,
        doi: str,
        sources: Optional[List[str]] = None
    ) -> Optional[Paper]:
        """
        Get paper by DOI from any available source.

        Args:
            doi: Digital Object Identifier
            sources: Sources to check (None = all)

        Returns:
            Paper if found, None otherwise
        """
        sources_to_check = sources or list(self.sources.keys())

        # Try each source
        for source_name in sources_to_check:
            if source_name not in self.sources:
                continue

            try:
                client = self.sources[source_name]
                paper = await client.get_paper_by_doi(doi)
                if paper:
                    return paper
            except NotImplementedError:
                logger.debug(f"{source_name} doesn't support DOI lookup")
            except Exception as e:
                logger.error(
                    f"Error getting paper by DOI from {source_name}: {e}"
                )

        return None

    async def find_related_papers(
        self,
        reference_paper: Paper,
        max_results: int = 10,
        sources: Optional[List[str]] = None
    ) -> List[Paper]:
        """
        Find papers related to a reference paper.

        Args:
            reference_paper: The reference paper
            max_results: Maximum related papers to find
            sources: Sources to search (None = same as reference)

        Returns:
            List of related papers
        """
        # Default to the source of the reference paper
        if sources is None:
            sources = [reference_paper.source]

        # Use ArXiv client's related paper feature if available
        if (PaperSource.ARXIV in sources and
                PaperSource.ARXIV in self.sources):
            client = self.sources[PaperSource.ARXIV]
            if hasattr(client, 'find_related_papers'):
                try:
                    related = await client.find_related_papers(
                        reference_paper,
                        max_results
                    )
                    return related
                except Exception as e:
                    logger.error(f"Error finding related papers: {e}")

        # Fallback: Search using keywords from title/abstract
        keywords = reference_paper.title.split()[:5]
        return await self.search(
            query=" ".join(keywords),
            sources=sources,
            max_results=max_results,
            categories=reference_paper.categories
        )

    def get_available_sources(self) -> List[str]:
        """
        Get list of available sources.

        Returns:
            List of source names
        """
        return list(self.sources.keys())

    async def validate_sources(self) -> Dict[str, bool]:
        """
        Validate connectivity to all sources.

        Returns:
            Dictionary mapping source names to validation status
        """
        results = {}

        for source_name, client in self.sources.items():
            try:
                is_valid = await client.validate_connection()
                results[source_name] = is_valid
            except Exception as e:
                logger.error(f"Failed to validate {source_name}: {e}")
                results[source_name] = False

        return results

    def _get_available_sources(
        self,
        requested_sources: List[str]
    ) -> List[str]:
        """
        Get intersection of requested and available sources.

        Args:
            requested_sources: Sources requested by user

        Returns:
            List of available sources from the requested list
        """
        available = []

        for source in requested_sources:
            if source in self.sources:
                available.append(source)
            else:
                logger.warning(
                    f"Source {source} requested but not available"
                )

        return available

    async def _search_concurrent(
        self,
        params: SearchParams,
        sources: List[str]
    ) -> List[Paper]:
        """
        Search multiple sources concurrently.

        Args:
            params: Search parameters
            sources: Sources to search

        Returns:
            Combined list of papers from all sources
        """
        # Create tasks for each source
        tasks = []

        for source_name in sources:
            if source_name in self.sources:
                client = self.sources[source_name]
                task = self._search_with_timeout(
                    client,
                    params,
                    source_name
                )
                tasks.append(task)

        # Execute all searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_papers = []

        for i, result in enumerate(results):
            source_name = sources[i]

            if isinstance(result, Exception):
                logger.error(
                    f"Search failed for {source_name}: {result}"
                )
            elif isinstance(result, list):
                logger.info(
                    f"Got {len(result)} papers from {source_name}"
                )
                all_papers.extend(result)
            else:
                logger.warning(
                    f"Unexpected result type from {source_name}: "
                    f"{type(result)}"
                )

        return all_papers

    async def _search_with_timeout(
        self,
        client: Any,
        params: SearchParams,
        source_name: str,
        timeout: float = 30.0
    ) -> List[Paper]:
        """
        Search a source with timeout.

        Args:
            client: Source client
            params: Search parameters
            source_name: Name of the source
            timeout: Timeout in seconds

        Returns:
            List of papers

        Raises:
            asyncio.TimeoutError: If search times out
        """
        try:
            return await asyncio.wait_for(
                client.search(params),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Search timeout for {source_name} after {timeout}s"
            )
            raise

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PaperRetriever sources={list(self.sources.keys())}>"
        )

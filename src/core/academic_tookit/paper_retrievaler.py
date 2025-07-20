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
from typing import List, Dict, Any, Optional, Tuple

from .models import Paper, SearchParams, PaperSource
from .paper_search.arxiv import ArxivClient
from .ranking import PaperDeduplicator
from .paper_reader import PaperReader, PaperReaderConfig

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

    def __init__(self, reader_config: Optional[PaperReaderConfig] = None):
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

        # Initialize paper reader
        self.paper_reader = PaperReader(reader_config)
        logger.info("Initialized paper reader with PDF and HTML support")

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

    async def read_paper(
        self,
        paper: Paper,
        force_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read full paper content with automatic format selection.

        Args:
            paper: Paper object to read
            force_format: Force specific format ('html' or 'pdf')

        Returns:
            Dictionary containing:
                - paper_id: Paper identifier
                - content_format: Format used ('html' or 'pdf')
                - full_text: Full paper text in markdown
                - sections: List of paper sections
                - figures: List of figures
                - tables: List of tables
                - references: List of references
                - equations: List of equations (if extracted)
                - metadata: Additional metadata
                - processing_info: Processing details

        Raises:
            ValueError: If paper has no readable URLs
            Exception: If reading fails
        """
        logger.info(
            f"Reading paper: {paper.paper_id} - {paper.title[:50]}..."
        )

        try:
            result = await self.paper_reader.read_paper(
                paper=paper,
                force_format=force_format
            )

            # Enhance result with paper's original metadata if available
            if result and 'metadata' in result:
                # Merge paper object data with extracted metadata
                result['metadata']['paper_id'] = paper.paper_id
                result['metadata']['source'] = paper.source
                result['metadata']['url'] = paper.url

                # Use paper's metadata if extraction failed
                if not result['metadata'].get('title') and paper.title:
                    result['metadata']['title'] = paper.title
                if not result['metadata'].get('authors') and paper.authors:
                    result['metadata']['authors'] = paper.authors
                if not result['metadata'].get('abstract') and paper.abstract:
                    result['metadata']['abstract'] = paper.abstract
                if not result['metadata'].get('doi') and paper.doi:
                    result['metadata']['doi'] = paper.doi

            logger.info(
                f"Successfully read paper {paper.paper_id} using "
                f"{result['content_format']} format"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to read paper {paper.paper_id}: {e}")
            raise

    async def read_papers_batch(
        self,
        papers: List[Paper],
        max_concurrent: int = 3
    ) -> Dict[str, Dict[str, Any]]:
        """
        Read multiple papers concurrently.

        Args:
            papers: List of papers to read
            max_concurrent: Maximum concurrent reads

        Returns:
            Dictionary mapping paper_id to content dictionary
        """
        logger.info(f"Reading {len(papers)} papers in batch")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def read_with_semaphore(paper: Paper) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                try:
                    content = await self.read_paper(paper)
                    return paper.paper_id, content
                except Exception as e:
                    logger.error(
                        f"Failed to read paper {paper.paper_id}: {e}"
                    )
                    return paper.paper_id, {
                        "error": str(e),
                        "paper_id": paper.paper_id,
                        "title": paper.title
                    }

        # Read all papers concurrently
        results = await asyncio.gather(
            *[read_with_semaphore(paper) for paper in papers]
        )

        # Convert to dictionary
        content_dict = dict(results)

        # Log summary
        successful = sum(
            1 for content in content_dict.values()
            if "error" not in content
        )
        logger.info(
            f"Batch reading complete: {successful}/{len(papers)} "
            f"papers read successfully"
        )

        return content_dict

    async def search_and_read(
        self,
        query: str,
        max_papers: int = 5,
        sources: Optional[List[str]] = None,
        deduplicate: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for papers and read their full content.

        Args:
            query: Search query
            max_papers: Maximum papers to read
            sources: List of sources to search
            deduplicate: Whether to deduplicate results
            **kwargs: Additional search parameters

        Returns:
            List of paper content dictionaries with harmonized metadata
        """
        logger.info(
            f"Searching and reading papers for query: '{query}' "
            f"(max_papers={max_papers})"
        )

        # First search for papers
        papers = await self.search(
            query=query,
            sources=sources,
            max_results=max_papers * 2,  # Get extra for filtering
            deduplicate=deduplicate,
            **kwargs
        )

        if not papers:
            logger.warning(f"No papers found for query: '{query}'")
            return []

        # Limit to requested number
        papers_to_read = papers[:max_papers]

        # Read papers in batch
        content_dict = await self.read_papers_batch(papers_to_read)

        # Combine paper metadata with content
        results = []
        for paper in papers_to_read:
            content = content_dict.get(paper.paper_id, {})

            # Add search metadata to content
            if "error" not in content:
                # Create harmonized metadata structure
                content['harmonized_metadata'] = {
                    'paper_id': paper.paper_id,
                    'title': content['metadata'].get('title') or paper.title,
                    'authors': content['metadata'].get('authors') or paper.authors,
                    'abstract': content['metadata'].get('abstract') or paper.abstract,
                    'source': paper.source,
                    'published_date': paper.published_date.isoformat() if paper.published_date else None,
                    'doi': content['metadata'].get('doi') or paper.doi,
                    'venue': content['metadata'].get('venue') or paper.venue,
                    'keywords': content['metadata'].get('keywords') or paper.keywords,
                    'categories': paper.categories,
                    'urls': {
                        'main': paper.url,
                        'pdf': paper.pdf_url,
                        'html': paper.html_url
                    },
                    'extraction_info': {
                        'format': content.get('content_format'),
                        'parser': content.get('processing_info', {}).get('parser'),
                        'sections_count': len(content.get('sections', [])),
                        'references_count': len(content.get('references', [])),
                        'figures_count': len(content.get('figures', [])),
                        'tables_count': len(content.get('tables', []))
                    },
                    'search_info': {
                        'query': query,
                        'relevance_rank': papers_to_read.index(paper) + 1,
                        'citations_count': paper.citations_count
                    }
                }

                results.append(content)
            else:
                logger.warning(
                    f"Skipping paper {paper.paper_id} due to read error"
                )

        logger.info(
            f"Search and read complete: {len(results)} papers "
            f"successfully processed"
        )

        return results

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PaperRetriever sources={list(self.sources.keys())}>"
        )

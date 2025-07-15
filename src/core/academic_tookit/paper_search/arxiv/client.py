#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_search/arxiv/client.py
# code style: PEP 8

"""
ArXiv client implementation using hybrid approach.

This client combines the reliability of the arxiv SDK with async support
and advanced features from the demo implementations.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..base import BasePaperSearchClient
from ...models import Paper, SearchParams, PaperSource
from .arxiv_sdk import Client, Search, Result, SortCriterion, SortOrder
from .query_parser import ArxivQueryParser
from .features import ArxivFeatureExtractor

logger = logging.getLogger(__name__)


class ArxivClient(BasePaperSearchClient):
    """
    ArXiv client using SDK with async wrapper and advanced features.

    This implementation:
    - Uses the proven arxiv SDK for core API interactions
    - Adds async support via ThreadPoolExecutor
    - Incorporates natural language query parsing
    - Provides advanced features like trend analysis
    """

    def __init__(self, page_size: int = 100, delay_seconds: float = 3.0):
        """
        Initialize the ArXiv client.

        Args:
            page_size: Number of results per API request (max 2000)
            delay_seconds: Delay between API requests (min 3.0)
        """
        super().__init__()

        # Core SDK client with conservative defaults
        self._sdk_client = Client(
            page_size=min(page_size, 2000),  # API limit
            delay_seconds=max(delay_seconds, 3.0),  # API requirement
            num_retries=3
        )

        # Enhancement modules
        self._query_parser = ArxivQueryParser()
        self._feature_extractor = ArxivFeatureExtractor()

        # Async support - single thread to maintain rate limiting
        self._executor = ThreadPoolExecutor(max_workers=1)

        logger.info(
            f"Initialized ArxivClient with page_size={page_size}, "
            f"delay_seconds={delay_seconds}"
        )

    async def search(self, params: SearchParams) -> List[Paper]:
        """
        Search for papers on ArXiv.

        Args:
            params: Search parameters

        Returns:
            List of Paper objects matching the search

        Raises:
            Exception: If search fails
        """
        try:
            # Build ArXiv query
            if params.use_natural_language:
                arxiv_query = self._query_parser.parse_natural_language(
                    query=params.query,
                    categories=params.categories,
                    start_date=params.start_date,
                    end_date=params.end_date,
                    author=params.author_filter
                )
                logger.debug(
                    f"Parsed natural language query '{params.query}' "
                    f"to ArXiv query: {arxiv_query}"
                )
            else:
                arxiv_query = self._build_structured_query(params)

            # Create SDK search object
            search = Search(
                query=arxiv_query,
                max_results=params.max_results,
                sort_by=self._get_sort_criterion(params.sort_by),
                sort_order=(
                    SortOrder.Descending
                    if params.sort_order == "desc"
                    else SortOrder.Ascending
                )
            )

            # Execute search asynchronously
            results = await self._run_async(
                lambda: list(self._sdk_client.results(search))
            )

            # Convert to Paper models
            papers = []
            for result in results:
                paper = self._convert_to_paper(result)

                # Apply filters
                if params.require_doi and not paper.doi:
                    continue
                if params.require_pdf and not paper.pdf_url:
                    continue

                papers.append(paper)

            # Update statistics
            self._increment_stats(papers_count=len(papers))

            logger.info(
                f"ArXiv search for '{params.query}' returned "
                f"{len(papers)} papers"
            )

            return papers

        except Exception as e:
            self._increment_stats(error=True)
            logger.error(f"ArXiv search failed: {e}")
            raise

    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get detailed information about a specific paper.

        Args:
            paper_id: ArXiv ID (e.g., '2301.12345' or 'cs/0501001')

        Returns:
            Paper object if found, None otherwise
        """
        try:
            # Use SDK id_list search
            search = Search(id_list=[paper_id])
            results = await self._run_async(
                lambda: list(self._sdk_client.results(search))
            )

            if results:
                paper = self._convert_to_paper(results[0])
                self._increment_stats(papers_count=1)
                return paper

            return None

        except Exception as e:
            self._increment_stats(error=True)
            logger.error(f"Failed to get paper {paper_id}: {e}")
            raise

    async def get_paper_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get paper by DOI.

        Note: ArXiv doesn't have a direct DOI search, so we search
        for the DOI in all fields and filter results.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object if found, None otherwise
        """
        try:
            # Search for DOI in all fields
            search = Search(
                query=f'all:"{doi}"',
                max_results=10
            )

            results = await self._run_async(
                lambda: list(self._sdk_client.results(search))
            )

            # Find exact DOI match
            for result in results:
                if result.doi and result.doi.lower() == doi.lower():
                    paper = self._convert_to_paper(result)
                    self._increment_stats(papers_count=1)
                    return paper

            return None

        except Exception as e:
            self._increment_stats(error=True)
            logger.error(f"Failed to get paper by DOI {doi}: {e}")
            raise

    async def validate_connection(self) -> bool:
        """
        Test if the ArXiv API is accessible.

        Returns:
            True if connection successful
        """
        try:
            # Simple test query
            search = Search(query="test", max_results=1)
            results = await self._run_async(
                lambda: list(self._sdk_client.results(search))
            )

            return True

        except Exception as e:
            logger.error(f"ArXiv connection validation failed: {e}")
            return False

    def _convert_to_paper(self, result: Result) -> Paper:
        """
        Convert SDK Result to our Paper model.

        Args:
            result: ArXiv SDK Result object

        Returns:
            Paper object
        """
        # Extract paper ID
        paper_id = result.get_short_id()

        # Build HTML URL if available (ArXiv added HTML in 2024)
        html_url = None
        if self._has_html_version(paper_id):
            html_url = f"https://arxiv.org/html/{paper_id}"

        # Extract author names
        authors = [author.name for author in result.authors]

        # Build extra metadata
        extra = {}
        if result.comment:
            extra["comment"] = result.comment
        if result.journal_ref:
            extra["journal_ref"] = result.journal_ref
        if result.primary_category:
            extra["primary_category"] = result.primary_category

        return Paper(
            paper_id=paper_id,
            title=result.title,
            authors=authors,
            abstract=result.summary,
            source=PaperSource.ARXIV,
            published_date=result.published,
            updated_date=result.updated,
            url=result.entry_id,
            pdf_url=result.pdf_url,
            html_url=html_url,
            doi=result.doi,
            categories=result.categories,
            extra=extra
        )

    def _build_structured_query(self, params: SearchParams) -> str:
        """
        Build structured ArXiv query from parameters.

        Args:
            params: Search parameters

        Returns:
            ArXiv query string
        """
        query_parts = []

        # Add base query
        if params.query:
            query_parts.append(params.query)

        # Add category filter
        if params.categories:
            cat_queries = [f"cat:{cat}" for cat in params.categories]
            query_parts.append(f"({' OR '.join(cat_queries)})")

        # Add author filter
        if params.author_filter:
            query_parts.append(f'au:"{params.author_filter}"')

        # Add date filter
        if params.start_date or params.end_date:
            date_query = self._build_date_query(
                params.start_date,
                params.end_date
            )
            if date_query:
                query_parts.append(date_query)

        return " AND ".join(query_parts) if query_parts else ""

    def _build_date_query(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """
        Build ArXiv date range query.

        Args:
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Date query string
        """
        if not start_date and not end_date:
            return ""

        # ArXiv date format: YYYYMMDD
        start = "19910814"  # ArXiv launch date
        if start_date:
            start = start_date.strftime("%Y%m%d")

        end = datetime.now().strftime("%Y%m%d")
        if end_date:
            end = end_date.strftime("%Y%m%d")

        return f"submittedDate:[{start} TO {end}]"

    def _get_sort_criterion(self, sort_by: str) -> SortCriterion:
        """
        Convert our sort parameter to SDK SortCriterion.

        Args:
            sort_by: Our sort parameter (relevance, date, citations)

        Returns:
            SDK SortCriterion
        """
        mapping = {
            "relevance": SortCriterion.Relevance,
            "date": SortCriterion.SubmittedDate,
            "citations": SortCriterion.Relevance  # ArXiv doesn't sort by citations
        }
        return mapping.get(sort_by, SortCriterion.Relevance)

    def _has_html_version(self, paper_id: str) -> bool:
        """
        Check if paper likely has HTML version.

        ArXiv started providing HTML versions in 2024 for new papers.
        This is a heuristic check.

        Args:
            paper_id: ArXiv paper ID

        Returns:
            True if HTML version likely exists
        """
        # Extract year from paper ID if possible
        if '.' in paper_id:
            # New format: YYMM.NNNNN
            try:
                year_month = paper_id.split('.')[0]
                year = int("20" + year_month[:2])
                return year >= 2024
            except (ValueError, IndexError):
                pass

        # Conservative default
        return False

    async def _run_async(self, func):
        """
        Run synchronous function in thread pool.

        Args:
            func: Synchronous function to run

        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)

    # Advanced features from demo implementation

    async def find_related_papers(
        self,
        reference_paper: Paper,
        max_results: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Paper]:
        """
        Find papers related to a reference paper.

        This uses the feature extractor to find similar papers
        based on title and abstract similarity.

        Args:
            reference_paper: The reference paper
            max_results: Maximum related papers to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of related papers
        """
        # Extract keywords from reference
        keywords = self._feature_extractor.extract_keywords(
            reference_paper.title + " " + reference_paper.abstract
        )

        # Search for papers with similar keywords
        params = SearchParams(
            query=" OR ".join(keywords[:5]),  # Top 5 keywords
            max_results=max_results * 3,  # Get extra for filtering
            categories=reference_paper.categories,
            use_natural_language=False
        )

        candidates = await self.search(params)

        # Find similar papers
        related = self._feature_extractor.find_similar_papers(
            reference_paper,
            candidates,
            similarity_threshold
        )

        return related[:max_results]

    async def analyze_trends(
        self,
        papers: List[Paper],
        analysis_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Analyze trends in a collection of papers.

        Args:
            papers: Papers to analyze
            analysis_type: Type of analysis (all, authors, timeline, etc.)

        Returns:
            Analysis results
        """
        return await self._run_async(
            lambda: self._feature_extractor.analyze_trends(
                papers,
                analysis_type
            )
        )

    def __del__(self):
        """Cleanup when client is destroyed."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

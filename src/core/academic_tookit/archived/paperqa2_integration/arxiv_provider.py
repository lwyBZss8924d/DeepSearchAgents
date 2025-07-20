#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/arxiv_provider.py
# code style: PEP 8

"""
ArXiv provider adapter for PaperQA2.

This module provides a PaperQA2-compatible provider that uses our
ArxivClient to fetch paper metadata.
"""

import logging
from typing import List, Optional, AsyncIterator, Union

from paperqa.clients.client_models import (
    MetadataProvider,
    DOIOrTitleBasedProvider,
    DocDetails,
    DOIQuery,
    TitleAuthorQuery
)

from ..paper_search.arxiv import ArxivClient
from ..models import Paper

logger = logging.getLogger(__name__)


class ArxivPaperQA2Provider(DOIOrTitleBasedProvider):
    """
    ArXiv provider for PaperQA2 metadata system.

    This provider:
    - Implements PaperQA2's DOIOrTitleBasedProvider interface
    - Uses our existing ArxivClient for searches
    - Converts our Paper model to PaperQA2's DocDetails
    - Supports both DOI and title/author queries
    """

    def __init__(self, client: Optional[ArxivClient] = None):
        """
        Initialize ArXiv provider.

        Args:
            client: ArxivClient instance (creates new if None)
        """
        self.client = client or ArxivClient()
        self.name = "arxiv"
        logger.info("Initialized ArxivPaperQA2Provider")

    async def _query(
        self, query: Union[TitleAuthorQuery, DOIQuery]
    ) -> Optional[DocDetails]:
        """
        Query for paper metadata.

        Args:
            query: Either a TitleAuthorQuery or DOIQuery

        Returns:
            DocDetails if found, None otherwise
        """
        if isinstance(query, DOIQuery):
            return await self._get_by_doi(query)
        else:
            # For title queries, get first match
            async for doc_details in self._get_by_title(query):
                return doc_details
            return None

    async def _get_by_doi(self, doi_query: DOIQuery) -> Optional[DocDetails]:
        """
        Get paper details by DOI.

        Args:
            doi_query: Query containing DOI

        Returns:
            DocDetails if found, None otherwise
        """
        try:
            # Try to get paper by DOI
            paper = await self.client.get_paper_by_doi(doi_query.doi)
            if paper:
                return self._paper_to_docdetails(paper)
        except Exception as e:
            logger.error(f"Error fetching by DOI {doi_query.doi}: {e}")

        return None

    async def _get_by_title(
        self,
        title_author_query: TitleAuthorQuery
    ) -> AsyncIterator[DocDetails]:
        """
        Get papers by title and optionally authors.

        Args:
            title_author_query: Query with title and optional authors

        Yields:
            DocDetails for matching papers
        """
        # Build search query
        query_parts = [f'"{title_author_query.title}"']

        if title_author_query.authors:
            # Add author names to query
            for author in title_author_query.authors[:3]:  # Limit authors
                if author:
                    query_parts.append(f'"{author}"')

        query = " ".join(query_parts)

        try:
            # Search ArXiv
            from ..models import SearchParams
            params = SearchParams(
                query=query,
                max_results=10  # Get more to find best match
            )

            papers = await self.client.search(params)

            # Convert and yield results
            for paper in papers:
                # Check if title is similar enough
                if self._is_title_match(
                    paper.title,
                    title_author_query.title
                ):
                    yield self._paper_to_docdetails(paper)

        except Exception as e:
            logger.error(f"Error searching by title: {e}")

    def _paper_to_docdetails(self, paper: Paper) -> DocDetails:
        """
        Convert our Paper model to PaperQA2's DocDetails.

        Args:
            paper: Our Paper model instance

        Returns:
            PaperQA2 DocDetails instance
        """
        # Extract authors
        authors = []
        for author in paper.authors:
            if isinstance(author, str):
                authors.append(author)
            else:
                authors.append(author.name)

        # Get publication year
        year = None
        if paper.published_date:
            year = paper.published_date.year

        # Get journal/venue
        journal = paper.venue or "arXiv preprint"
        if paper.extra and "journal_ref" in paper.extra:
            journal = paper.extra["journal_ref"]

        # Build citation string
        citation = self._build_citation(paper, authors, year, journal)

        # Generate BibTeX
        bibtex = self._generate_bibtex(paper, authors, year, journal)

        # Get URLs
        pdf_url = paper.pdf_url
        other_urls = []

        if paper.url:
            other_urls.append(paper.url)
        if paper.html_url:
            other_urls.append(paper.html_url)

        # Create DocDetails
        doc_details = DocDetails(
            # Required fields
            docname=paper.title,

            # Bibliographic info
            title=paper.title,
            authors=authors,
            year=year,
            journal=journal,
            volume=paper.volume,
            issue=paper.issue,
            pages=paper.pages,
            doi=paper.doi,

            # Citation info
            citation_count=paper.citations_count,
            bibkey=paper.get_bibtex_key(),
            citation=citation,
            bibtex=bibtex,

            # URLs
            url=other_urls[0] if other_urls else None,
            pdf_url=pdf_url,

            # Source info
            source_type="arxiv",

            # Quality indicators
            is_oa=True,  # ArXiv is always open access

            # Metadata
            key=f"arxiv:{paper.paper_id}",

            # Optional fields we can set
            abstract=paper.abstract,
            keywords=paper.keywords,
        )

        return doc_details

    def _build_citation(
        self,
        paper: Paper,
        authors: List[str],
        year: Optional[int],
        journal: str
    ) -> str:
        """
        Build citation string for paper.

        Args:
            paper: Paper model
            authors: List of author names
            year: Publication year
            journal: Journal/venue name

        Returns:
            Formatted citation string
        """
        # Format authors
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        else:
            author_str = f"{authors[0]} et al."

        # Build citation
        parts = [author_str]

        if year:
            parts.append(f"({year})")

        parts.append(f'"{paper.title}"')
        parts.append(journal)

        if paper.paper_id:
            parts.append(f"arXiv:{paper.paper_id}")

        return " ".join(parts) + "."

    def _generate_bibtex(
        self,
        paper: Paper,
        authors: List[str],
        year: Optional[int],
        journal: str
    ) -> str:
        """
        Generate BibTeX entry for paper.

        Args:
            paper: Paper model
            authors: List of author names
            year: Publication year
            journal: Journal/venue name

        Returns:
            BibTeX entry string
        """
        # Determine entry type
        entry_type = "article" if paper.doi else "misc"

        # Generate key
        key = paper.get_bibtex_key()

        # Build BibTeX
        lines = [f"@{entry_type}{{{key},"]

        # Add fields
        lines.append(f'  title = {{{paper.title}}},')
        lines.append(f'  author = {{{" and ".join(authors)}}},')

        if year:
            lines.append(f'  year = {{{year}}},')

        if entry_type == "article" and journal != "arXiv preprint":
            lines.append(f'  journal = {{{journal}}},')

            if paper.volume:
                lines.append(f'  volume = {{{paper.volume}}},')
            if paper.issue:
                lines.append(f'  number = {{{paper.issue}}},')
            if paper.pages:
                lines.append(f'  pages = {{{paper.pages}}},')
        else:
            lines.append(f'  howpublished = {{arXiv preprint}},')

        if paper.doi:
            lines.append(f'  doi = {{{paper.doi}}},')

        if paper.paper_id:
            lines.append(f'  eprint = {{{paper.paper_id}}},')
            lines.append('  archivePrefix = {arXiv},')

            # Try to extract primary class
            if paper.categories:
                primary_class = paper.categories[0]
                lines.append(f'  primaryClass = {{{primary_class}}},')

        if paper.abstract:
            # Clean abstract for BibTeX
            abstract = paper.abstract.replace('\n', ' ').strip()
            lines.append(f'  abstract = {{{abstract}}},')

        # Add URL
        if paper.url:
            lines.append(f'  url = {{{paper.url}}},')

        lines.append('}')

        return '\n'.join(lines)

    def _is_title_match(self, title1: str, title2: str) -> bool:
        """
        Check if two titles are similar enough.

        Args:
            title1: First title
            title2: Second title

        Returns:
            True if titles match
        """
        # Normalize titles
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()

        # Exact match
        if t1 == t2:
            return True

        # One contains the other
        if t1 in t2 or t2 in t1:
            return True

        # Simple fuzzy match - check word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())

        # Remove common words
        stopwords = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to',
                     'for', 'and', 'or', 'with', 'by', 'from'}
        words1 -= stopwords
        words2 -= stopwords

        # Calculate overlap
        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        # Require high overlap
        return (overlap / total) >= 0.7

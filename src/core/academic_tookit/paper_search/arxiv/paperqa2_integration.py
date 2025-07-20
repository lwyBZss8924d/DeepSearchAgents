#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_search/arxiv/paperqa2_integration.py
# code style: PEP 8

"""
ArXiv integration for PaperQA2.

This module provides a custom ArXiv client that implements PaperQA2's
MetadataProvider interface to fetch paper metadata from ArXiv.
"""

import logging
from typing import Any

from paperqa.clients.client_models import (
    DOIOrTitleBasedProvider,
    DOIQuery,
    TitleAuthorQuery
)
from paperqa.types import DocDetails, BibTeXSource
from paperqa.utils import (
    create_bibtex_key,
    strings_similarity
)
from .client import ArxivClient
from ...models.search_params import SearchParams

logger = logging.getLogger(__name__)


class ArxivPaperQA2Provider(DOIOrTitleBasedProvider):
    """
    PaperQA2 metadata provider for ArXiv papers.

    This provider integrates our ArxivClient with PaperQA2's metadata
    system, allowing ArXiv papers to be automatically enriched with
    metadata when added to a Docs collection.

    Example usage:
        ```python
        from paperqa import Docs
        from paperqa.clients import DocMetadataClient

        # Create client with ArXiv provider
        arxiv_provider = ArxivPaperQA2Provider()
        client = DocMetadataClient(clients=[arxiv_provider])

        # Use with Docs
        docs = Docs()
        await docs.aadd("paper.pdf", client=client)
        ```
    """

    def __init__(self):
        """Initialize the ArXiv provider."""
        self._arxiv_client = ArxivClient()
        self._session_owner = False
        logger.info("Initialized ArxivPaperQA2Provider")

    async def _query(
        self,
        query: DOIQuery | TitleAuthorQuery
    ) -> DocDetails | None:
        """
        Query ArXiv for paper metadata.

        Args:
            query: Either a DOI or title/author query

        Returns:
            DocDetails if paper found, None otherwise
        """
        try:
            # Handle DOI query
            if isinstance(query, DOIQuery):
                return await self._query_by_doi(query)

            # Handle title/author query
            elif isinstance(query, TitleAuthorQuery):
                return await self._query_by_title(query)

        except Exception as e:
            logger.error(f"ArXiv query failed: {e}")
            return None

    async def _query_by_doi(self, query: DOIQuery) -> DocDetails | None:
        """
        Query ArXiv by DOI.

        Args:
            query: DOI query

        Returns:
            DocDetails if found
        """
        paper = await self._arxiv_client.get_paper_by_doi(query.doi)

        if paper:
            return self._convert_to_doc_details(paper, query.fields)

        return None

    async def _query_by_title(
        self,
        query: TitleAuthorQuery
    ) -> DocDetails | None:
        """
        Query ArXiv by title and optional authors.

        Args:
            query: Title/author query

        Returns:
            DocDetails if found
        """
        # Build search parameters
        params = SearchParams(
            query=f'ti:"{query.title}"',
            max_results=10,
            author_filter=(
                query.authors[0] if query.authors else None
            ),
            use_natural_language=False,
            sort_by="relevance",
            sort_order="desc",
            include_preprints=True,
            require_doi=False,
            require_pdf=True,
            start_date=None,
            end_date=None,
            categories=None,
            venue_filter=None,
            min_citations=None
        )

        # Search ArXiv
        papers = await self._arxiv_client.search(params)

        # Find best match
        for paper in papers:
            # Check title similarity
            title_sim = strings_similarity(
                paper.title.lower(),
                query.title.lower()
            )

            if title_sim < query.title_similarity_threshold:
                continue

            # Check author match if provided
            if query.authors:
                paper_authors = [a.lower() for a in paper.authors]
                query_authors = [a.lower() for a in query.authors]

                # At least one author must match
                if not any(
                    any(qa in pa for pa in paper_authors)
                    for qa in query_authors
                ):
                    continue

            # Found a match
            return self._convert_to_doc_details(paper, query.fields)

        return None

    def _convert_to_doc_details(
        self,
        paper: Any,  # Paper from our models
        fields: list[str] | None = None
    ) -> DocDetails:
        """
        Convert our Paper model to PaperQA2's DocDetails.

        Args:
            paper: Paper object from our models
            fields: Optional list of fields to populate

        Returns:
            DocDetails object
        """
        # Extract publication date
        pub_date = paper.published_date
        year = pub_date.year if pub_date else None

        # Create author list
        authors = paper.authors if paper.authors else []

        # Generate bibtex key
        key = create_bibtex_key(
            authors or ["Unknown"],
            year or "Unknown",
            paper.title or "Unknown"
        )

        # Build bibtex entry
        bibtex_data = {
            "title": paper.title,
            "author": " and ".join(authors),
            "year": str(year) if year else None,
            "eprint": paper.paper_id,
            "archivePrefix": "arXiv",
            "primaryClass": (
                paper.categories[0] if paper.categories else None
            ),
            "url": paper.url,
            "doi": paper.doi,
            "abstract": paper.abstract[:500] + "..."
                if len(paper.abstract) > 500 else paper.abstract
        }

        # Filter out None values
        bibtex_data = {k: v for k, v in bibtex_data.items() if v}

        # Generate bibtex string
        bibtex_lines = ["@article{" + key + ","]
        for field, value in bibtex_data.items():
            # Escape special characters
            value = value.replace('"', '\\"')
            value = value.replace('\n', ' ')
            bibtex_lines.append(f'  {field} = "{value}",')
        bibtex_lines[-1] = bibtex_lines[-1].rstrip(',')  # Remove last comma
        bibtex_lines.append("}")
        bibtex = "\n".join(bibtex_lines)

        # Build DocDetails
        doc_details_data = {
            "key": key,
            "bibtex": bibtex,
            "authors": authors,
            "publication_date": pub_date,
            "year": year,
            "title": paper.title,
            "journal": "arXiv",
            "volume": None,
            "issue": None,
            "pages": None,
            "doi": paper.doi,
            "doi_url": f"https://doi.org/{paper.doi}" if paper.doi else None,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "citation_count": paper.citations_count or 0,
            "bibtex_type": "article",
            "is_retracted": False,
            "other": {
                "bibtex_source": [BibTeXSource.SELF_GENERATED],
                "client_source": ["ArxivPaperQA2Provider"],
                "arxiv_id": paper.paper_id,
                "categories": paper.categories,
                "abstract": paper.abstract,
                "html_url": paper.html_url,
                "comment": paper.extra.get("comment") if paper.extra else None,
                "journal_ref": paper.extra.get("journal_ref")
                    if paper.extra else None
            }
        }

        # Only include requested fields if specified
        if fields:
            doc_details_data = {
                k: v for k, v in doc_details_data.items()
                if k in fields or k in ["key", "doi", "title", "authors"]
            }

        return DocDetails(**doc_details_data)


# Example usage function
async def example_usage():
    """
    Example of using ArxivPaperQA2Provider with PaperQA2.

    This shows how to:
    1. Create a custom client with ArXiv support
    2. Query for papers by title or DOI
    3. Add ArXiv papers to a Docs collection
    """
    from paperqa import Docs, Settings
    from paperqa.clients import DocMetadataClient

    # Create client with ArXiv provider
    arxiv_provider = ArxivPaperQA2Provider()
    client = DocMetadataClient(clients=[arxiv_provider])

    # Example 1: Query by title
    paper_details = await client.query(
        title="Attention is All You Need",
        authors=["Vaswani"]
    )
    if paper_details:
        print(f"Found paper: {paper_details.formatted_citation}")

    # Example 2: Query by DOI
    paper_details = await client.query(
        doi="10.48550/arXiv.1706.03762"
    )
    if paper_details:
        print(f"Found paper by DOI: {paper_details.title}")

    # Example 3: Use with Docs
    docs = Docs()
    settings = Settings(use_doc_details=True)

    # Add a local PDF with automatic metadata retrieval
    # The provider will be called automatically to enrich metadata
    await docs.aadd(
        "path/to/attention_paper.pdf",
        settings=settings,
        # The DocMetadataClient will be used internally
    )

    # Query the docs
    answer = await docs.aquery(
        "What is the transformer architecture?",
        settings=settings
    )
    print(answer.formatted_answer)


if __name__ == "__main__":
    # Run example
    import asyncio
    asyncio.run(example_usage())

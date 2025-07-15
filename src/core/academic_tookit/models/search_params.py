#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/models/search_params.py
# code style: PEP 8

"""
Search parameters model for academic paper searches.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class SearchParams(BaseModel):
    """
    Unified search parameters for all paper sources.

    This model provides a consistent interface for search parameters
    across different academic sources, with sensible defaults and
    validation.
    """

    # Core search parameters
    query: str = Field(
        ...,
        description="Search query (natural language or structured)",
        min_length=1
    )
    max_results: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )

    # Date filtering
    start_date: Optional[datetime] = Field(
        None,
        description="Filter papers published after this date"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter papers published before this date"
    )

    # Categorization
    categories: List[str] = Field(
        default_factory=list,
        description="Filter by categories (e.g., ['cs.AI', 'cs.LG'])"
    )

    # Sorting
    sort_by: str = Field(
        "relevance",
        pattern="^(relevance|date|citations)$",
        description="Sort criterion: relevance, date, or citations"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order: ascending or descending"
    )

    # Filtering options
    include_preprints: bool = Field(
        True,
        description="Include preprint papers in results"
    )
    require_doi: bool = Field(
        False,
        description="Only return papers with DOI"
    )
    require_pdf: bool = Field(
        False,
        description="Only return papers with available PDF"
    )

    # Query processing
    use_natural_language: bool = Field(
        True,
        description="Parse query as natural language vs structured syntax"
    )

    # Source selection
    sources: List[str] = Field(
        default_factory=lambda: ["arxiv"],
        description="List of sources to search (e.g., ['arxiv', 'pubmed'])"
    )

    # Advanced options
    author_filter: Optional[str] = Field(
        None,
        description="Filter by author name"
    )
    venue_filter: Optional[str] = Field(
        None,
        description="Filter by venue (journal/conference)"
    )
    min_citations: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum citation count"
    )

    @validator('sources')
    def validate_sources(cls, v):
        """Ensure at least one source is specified."""
        if not v:
            return ["arxiv"]  # Default to arxiv
        return v

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date if both are provided."""
        start_date = values.get('start_date')
        if start_date and v and v < start_date:
            raise ValueError('end_date must be after start_date')
        return v

    @validator('categories', pre=True)
    def normalize_categories(cls, v):
        """Normalize category formats."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [cat.strip() for cat in v.split(',')]
        return v or []

    def to_source_params(self, source: str) -> dict:
        """
        Convert to source-specific parameters.

        Different sources may have different parameter names and formats.
        This method provides source-specific conversions.

        Args:
            source: The source name (e.g., 'arxiv', 'pubmed')

        Returns:
            Dictionary of source-specific parameters
        """
        base_params = {
            'query': self.query,
            'max_results': self.max_results,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order
        }

        if source == 'arxiv':
            params = base_params.copy()
            if self.categories:
                # ArXiv uses 'cat:' prefix
                params['categories'] = self.categories
            if self.start_date:
                params['start_date'] = self.start_date.strftime('%Y-%m-%d')
            if self.end_date:
                params['end_date'] = self.end_date.strftime('%Y-%m-%d')
            if self.author_filter:
                params['author'] = self.author_filter

        elif source == 'pubmed':
            params = base_params.copy()
            if self.start_date:
                params['mindate'] = self.start_date.strftime('%Y/%m/%d')
            if self.end_date:
                params['maxdate'] = self.end_date.strftime('%Y/%m/%d')
            # PubMed uses different field names
            params['retmax'] = params.pop('max_results')

        else:
            # Default mapping
            params = base_params.copy()

        return params

    def get_cache_key(self) -> str:
        """
        Generate a cache key for these search parameters.

        This creates a unique string that can be used as a cache key
        for storing search results.
        """
        import hashlib
        import json

        # Create a sorted dictionary of parameters
        params_dict = {
            'query': self.query,
            'max_results': self.max_results,
            'sources': sorted(self.sources),
            'categories': sorted(self.categories),
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'start_date': (
                self.start_date.isoformat()
                if self.start_date else None
            ),
            'end_date': (
                self.end_date.isoformat()
                if self.end_date else None
            ),
            'author_filter': self.author_filter,
            'venue_filter': self.venue_filter,
            'min_citations': self.min_citations,
            'include_preprints': self.include_preprints,
            'require_doi': self.require_doi,
            'require_pdf': self.require_pdf
        }

        # Remove None values
        params_dict = {k: v for k, v in params_dict.items() if v is not None}

        # Create hash
        params_str = json.dumps(params_dict, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "query": "machine learning in drug discovery",
                "max_results": 20,
                "sources": ["arxiv", "pubmed"],
                "categories": ["cs.LG", "cs.AI"],
                "sort_by": "relevance",
                "sort_order": "desc",
                "start_date": "2023-01-01T00:00:00",
                "include_preprints": True,
                "use_natural_language": True
            }
        }

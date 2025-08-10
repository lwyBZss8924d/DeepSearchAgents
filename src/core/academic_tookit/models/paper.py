#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/models/paper.py
# code style: PEP 8

"""
Unified paper model for all academic sources.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, validator


class PaperSource(str, Enum):
    """Supported academic paper sources."""

    ARXIV = "arxiv"
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    BIORXIV = "biorxiv"
    MEDRXIV = "medrxiv"
    GOOGLE_SCHOLAR = "google_scholar"


class Paper(BaseModel):
    """
    Unified paper model for all academic sources.

    This model provides a consistent interface for papers from different
    sources while allowing source-specific metadata in the 'extra' field.
    """

    # Core fields (required)
    paper_id: str = Field(
        ...,
        description="Unique identifier within source (e.g., arXiv ID, PMID)"
    )
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(..., description="List of author names")
    abstract: str = Field(..., description="Paper abstract")
    source: PaperSource = Field(..., description="Source platform")
    published_date: datetime = Field(..., description="Publication date")

    # URLs (at least one required)
    url: str = Field(..., description="Main paper page URL")
    pdf_url: Optional[str] = Field(None, description="Direct PDF download URL")
    html_url: Optional[str] = Field(
        None,
        description="HTML version URL (if available)"
    )

    # Optional metadata
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    venue: Optional[str] = Field(
        None,
        description="Publication venue (conference/journal)"
    )
    volume: Optional[str] = Field(None, description="Journal volume")
    issue: Optional[str] = Field(None, description="Journal issue")
    pages: Optional[str] = Field(None, description="Page numbers")

    # Categorization
    categories: List[str] = Field(
        default_factory=list,
        description="Subject categories (e.g., cs.AI, cs.LG)"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords or tags"
    )

    # Metrics
    citations_count: int = Field(
        0,
        description="Number of citations (if available)"
    )
    references: List[str] = Field(
        default_factory=list,
        description="List of reference IDs/DOIs"
    )

    # Source-specific extras
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific metadata"
    )

    # Timestamps
    updated_date: Optional[datetime] = Field(
        None,
        description="Last update date (if different from published)"
    )

    @validator('pdf_url', 'html_url', 'url')
    def validate_urls(cls, v):
        """Ensure URLs are properly formatted."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @validator('doi')
    def validate_doi(cls, v):
        """Basic DOI validation."""
        if v and not v.startswith('10.'):
            # Some sources prefix DOI with "doi:"
            if v.startswith('doi:'):
                return v[4:]
            raise ValueError('DOI must start with "10."')
        return v

    @validator('authors', pre=True)
    def ensure_authors_list(cls, v):
        """Ensure authors is always a list."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [a.strip() for a in v.split(',')]
        return v or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert paper to dictionary format for serialization.

        This method provides a standardized dictionary representation
        suitable for JSON serialization or database storage.
        """
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': '; '.join(self.authors) if self.authors else '',
            'abstract': self.abstract,
            'source': self.source,
            'published_date': (
                self.published_date.isoformat()
                if self.published_date else ''
            ),
            'url': self.url,
            'pdf_url': self.pdf_url or '',
            'html_url': self.html_url or '',
            'doi': self.doi or '',
            'venue': self.venue or '',
            'volume': self.volume or '',
            'issue': self.issue or '',
            'pages': self.pages or '',
            'categories': '; '.join(self.categories)
            if self.categories else '',
            'keywords': '; '.join(self.keywords)
            if self.keywords else '',
            'citations_count': self.citations_count,
            'references': '; '.join(self.references)
            if self.references else '',
            'extra': self.extra,
            'updated_date': (
                self.updated_date.isoformat()
                if self.updated_date else ''
            )
        }

    def get_bibtex_key(self) -> str:
        """
        Generate a BibTeX-friendly key for this paper.

        Format: FirstAuthorLastName_Year_FirstWordOfTitle
        """
        # Get first author's last name
        if self.authors:
            first_author = self.authors[0]
            # Simple heuristic: last word is usually last name
            last_name = first_author.split()[-1] if first_author else "Unknown"
        else:
            last_name = "Unknown"

        # Get year
        year = self.published_date.year if self.published_date else "0000"

        # Get first meaningful word from title
        title_words = self.title.split()
        first_word = "Unknown"
        for word in title_words:
            if len(word) > 3 and word.lower() not in ['the', 'and', 'for']:
                first_word = word
                break

        # Clean and combine
        import re
        last_name = re.sub(r'[^a-zA-Z0-9]', '', last_name)
        first_word = re.sub(r'[^a-zA-Z0-9]', '', first_word)

        return f"{last_name}{year}{first_word}"

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        schema_extra = {
            "example": {
                "paper_id": "2301.12345",
                "title": "Deep Learning for Scientific Discovery",
                "authors": ["John Doe", "Jane Smith"],
                "abstract": "We present a novel approach...",
                "source": "arxiv",
                "published_date": "2023-01-15T00:00:00",
                "url": "https://arxiv.org/abs/2301.12345",
                "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
                "html_url": "https://arxiv.org/html/2301.12345",
                "categories": ["cs.LG", "cs.AI"],
                "keywords": ["deep learning", "scientific computing"]
            }
        }

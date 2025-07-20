#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_reader/metadata_merger.py
# code style: PEP 8

"""
Metadata merger for intelligent combination of search and extracted metadata.

This module provides functionality to merge metadata from paper search results
with metadata extracted during PDF/HTML parsing, using confidence scores and
source tracking.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..models import Paper, PaperSource

logger = logging.getLogger(__name__)


class MetadataMerger:
    """
    Intelligently merge search metadata with extracted content.

    This class implements a priority-based merging strategy where:
    - Bibliographic metadata from search results is preferred (more reliable)
    - Content structure from extraction is preserved (sections, figures, etc.)
    - Confidence scores help resolve conflicts
    - Source tracking enables debugging
    """

    # Field priority configuration
    # Higher priority means prefer search metadata over extracted
    FIELD_PRIORITIES = {
        # Bibliographic fields - trust search results
        'paper_id': 1.0,
        'source': 1.0,
        'url': 1.0,
        'pdf_url': 1.0,
        'html_url': 1.0,
        'doi': 0.9,  # High priority but sometimes extraction finds it
        'published_date': 0.9,
        'updated_date': 0.9,
        'venue': 0.8,
        'volume': 0.8,
        'issue': 0.8,
        'pages': 0.8,
        'citations_count': 1.0,
        'categories': 0.9,

        # Content fields - may vary in quality
        'title': 0.7,  # Usually good from search but check extraction
        'authors': 0.7,  # Same as title
        'abstract': 0.6,  # Sometimes truncated in search results
        'keywords': 0.5,  # Often better from extraction

        # Structure fields - always from extraction
        'sections': 0.0,
        'figures': 0.0,
        'tables': 0.0,
        'references': 0.0,
        'equations': 0.0,
        'full_text': 0.0,
    }

    def __init__(self):
        """Initialize the metadata merger."""
        self.merge_stats = {
            'fields_from_search': 0,
            'fields_from_extraction': 0,
            'conflicts_resolved': 0
        }

    def merge_metadata(
        self,
        search_paper: Optional[Paper],
        extracted_metadata: Dict[str, Any],
        extraction_confidence: Optional[Dict[str, float]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Merge metadata from search and extraction with intelligent priority.

        Args:
            search_paper: Paper object from search results
            extracted_metadata: Metadata extracted from PDF/HTML
            extraction_confidence: Optional confidence scores for extracted fields

        Returns:
            Tuple of:
                - merged_metadata: Combined metadata dictionary
                - metadata_sources: Source tracking for each field
        """
        merged = {}
        sources = {}

        # Reset stats
        self.merge_stats = {
            'fields_from_search': 0,
            'fields_from_extraction': 0,
            'conflicts_resolved': 0
        }

        # Start with search metadata if available
        if search_paper:
            search_dict = self._paper_to_dict(search_paper)
        else:
            search_dict = {}

        # Default confidence scores if not provided
        if extraction_confidence is None:
            extraction_confidence = {}

        # Get all unique fields
        all_fields = set(search_dict.keys()) | set(extracted_metadata.keys())

        # Merge each field
        for field in all_fields:
            search_value = search_dict.get(field)
            extracted_value = extracted_metadata.get(field)

            # Determine which value to use
            if search_value is not None and extracted_value is not None:
                # Both have values - need to decide
                use_search = self._should_use_search_value(
                    field,
                    search_value,
                    extracted_value,
                    extraction_confidence.get(field, 0.5)
                )

                if use_search:
                    merged[field] = search_value
                    sources[field] = 'search'
                    self.merge_stats['fields_from_search'] += 1
                else:
                    merged[field] = extracted_value
                    sources[field] = 'extracted'
                    self.merge_stats['fields_from_extraction'] += 1

                if search_value != extracted_value:
                    self.merge_stats['conflicts_resolved'] += 1
                    logger.debug(
                        f"Resolved conflict for field '{field}': "
                        f"chose {'search' if use_search else 'extracted'} value"
                    )

            elif search_value is not None:
                # Only search has value
                merged[field] = search_value
                sources[field] = 'search'
                self.merge_stats['fields_from_search'] += 1

            elif extracted_value is not None:
                # Only extraction has value
                merged[field] = extracted_value
                sources[field] = 'extracted'
                self.merge_stats['fields_from_extraction'] += 1

        # Add extraction-specific fields that should always be included
        for field in ['sections', 'figures', 'tables', 'references', 
                      'equations', 'full_text']:
            if field in extracted_metadata and field not in merged:
                merged[field] = extracted_metadata[field]
                sources[field] = 'extracted'
                self.merge_stats['fields_from_extraction'] += 1

        # Log merge statistics
        logger.info(
            f"Metadata merge complete: {self.merge_stats['fields_from_search']} "
            f"fields from search, {self.merge_stats['fields_from_extraction']} "
            f"from extraction, {self.merge_stats['conflicts_resolved']} conflicts resolved"
        )

        return merged, sources

    def _should_use_search_value(
        self,
        field: str,
        search_value: Any,
        extracted_value: Any,
        extraction_confidence: float
    ) -> bool:
        """
        Determine whether to use search or extracted value for a field.

        Args:
            field: Field name
            search_value: Value from search results
            extracted_value: Value from extraction
            extraction_confidence: Confidence score for extraction (0-1)

        Returns:
            True to use search value, False to use extracted value
        """
        # Get field priority (default to 0.5 if not configured)
        field_priority = self.FIELD_PRIORITIES.get(field, 0.5)

        # If field strongly prefers search (priority >= 0.9), use search
        if field_priority >= 0.9:
            return True

        # If field strongly prefers extraction (priority <= 0.1), use extraction
        if field_priority <= 0.1:
            return False

        # For fields with moderate priority, consider confidence and quality

        # Special handling for specific fields
        if field == 'title':
            # Prefer longer, more complete title
            if isinstance(search_value, str) and isinstance(extracted_value, str):
                # If extraction confidence is high and title is longer, use it
                if extraction_confidence > 0.8 and len(extracted_value) > len(search_value):
                    return False

        elif field == 'authors':
            # Prefer list with more authors (likely more complete)
            if isinstance(search_value, list) and isinstance(extracted_value, list):
                if len(extracted_value) > len(search_value) and extraction_confidence > 0.7:
                    return False

        elif field == 'abstract':
            # Prefer longer abstract (search results often truncate)
            if isinstance(search_value, str) and isinstance(extracted_value, str):
                if len(extracted_value) > len(search_value) * 1.2:  # 20% longer
                    return False

        elif field == 'doi':
            # DOI format validation
            if isinstance(extracted_value, str) and extracted_value.startswith('10.'):
                if extraction_confidence > 0.6:
                    return False

        # Default: use field priority weighted by extraction confidence
        # If extraction confidence is high, it can override moderate priority
        threshold = field_priority - (extraction_confidence - 0.5) * 0.3
        return threshold > 0.5

    def _paper_to_dict(self, paper: Paper) -> Dict[str, Any]:
        """
        Convert Paper object to dictionary for merging.

        Args:
            paper: Paper object from search

        Returns:
            Dictionary representation of paper
        """
        return {
            'paper_id': paper.paper_id,
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract,
            'source': paper.source,
            'published_date': paper.published_date,
            'updated_date': paper.updated_date,
            'url': paper.url,
            'pdf_url': paper.pdf_url,
            'html_url': paper.html_url,
            'doi': paper.doi,
            'venue': paper.venue,
            'volume': paper.volume,
            'issue': paper.issue,
            'pages': paper.pages,
            'categories': paper.categories,
            'keywords': paper.keywords,
            'citations_count': paper.citations_count,
            'references': paper.references,
            'extra': paper.extra
        }

    def create_harmonized_metadata(
        self,
        merged_metadata: Dict[str, Any],
        metadata_sources: Dict[str, str],
        content_format: str
    ) -> Dict[str, Any]:
        """
        Create a harmonized metadata structure with all information organized.

        Args:
            merged_metadata: Merged metadata dictionary
            metadata_sources: Source tracking for each field
            content_format: Format used for content extraction ('pdf' or 'html')

        Returns:
            Harmonized metadata structure
        """
        # Ensure date serialization
        def serialize_date(date_val):
            if isinstance(date_val, datetime):
                return date_val.isoformat()
            return date_val

        harmonized = {
            'bibliographic': {
                'paper_id': merged_metadata.get('paper_id'),
                'title': merged_metadata.get('title'),
                'authors': merged_metadata.get('authors', []),
                'abstract': merged_metadata.get('abstract'),
                'doi': merged_metadata.get('doi'),
                'venue': merged_metadata.get('venue'),
                'published_date': serialize_date(merged_metadata.get('published_date')),
                'updated_date': serialize_date(merged_metadata.get('updated_date')),
                'source': merged_metadata.get('source'),
                'categories': merged_metadata.get('categories', []),
                'keywords': merged_metadata.get('keywords', []),
                'citations_count': merged_metadata.get('citations_count', 0)
            },
            'urls': {
                'main': merged_metadata.get('url'),
                'pdf': merged_metadata.get('pdf_url'),
                'html': merged_metadata.get('html_url')
            },
            'content': {
                'format': content_format,
                'full_text': merged_metadata.get('full_text'),
                'sections': merged_metadata.get('sections', []),
                'figures': merged_metadata.get('figures', []),
                'tables': merged_metadata.get('tables', []),
                'references': merged_metadata.get('references', []),
                'equations': merged_metadata.get('equations', [])
            },
            'metadata_info': {
                'sources': metadata_sources,
                'merge_stats': self.merge_stats.copy(),
                'extraction_format': content_format
            }
        }

        return harmonized

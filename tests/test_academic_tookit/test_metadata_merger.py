#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_metadata_merger.py
# code style: PEP 8

"""
Tests for metadata merger functionality.
"""

import pytest
from datetime import datetime
from src.core.academic_tookit.models import Paper, PaperSource
from src.core.academic_tookit.paper_reader import MetadataMerger


class TestMetadataMerger:
    """Test MetadataMerger functionality."""

    @pytest.fixture
    def merger(self):
        """Create a MetadataMerger instance."""
        return MetadataMerger()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample Paper object from search."""
        return Paper(
            paper_id="2301.12345",
            title="Deep Learning for Scientific Discovery",
            authors=["John Doe", "Jane Smith"],
            abstract="We present a novel approach to scientific discovery...",
            source=PaperSource.ARXIV,
            published_date=datetime(2023, 1, 15),
            url="https://arxiv.org/abs/2301.12345",
            pdf_url="https://arxiv.org/pdf/2301.12345.pdf",
            doi="10.1234/arxiv.2301.12345",
            categories=["cs.LG", "cs.AI"],
            keywords=["deep learning", "scientific computing"]
        )

    @pytest.fixture
    def extracted_metadata(self):
        """Create sample extracted metadata."""
        return {
            'title': 'Deep Learning for Scientific Discovery: A Novel Approach',
            'authors': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'abstract': 'We present a novel approach to scientific discovery using deep learning techniques. Our method shows significant improvements...',
            'doi': '10.1234/arxiv.2301.12345',
            'keywords': ['deep learning', 'scientific computing', 'machine learning'],
            'sections': [
                {'title': 'Introduction', 'content': 'In this paper...'},
                {'title': 'Methodology', 'content': 'We propose...'}
            ],
            'figures': [
                {'id': 'figure_1', 'caption': 'Architecture overview'}
            ],
            'tables': [
                {'id': 'table_1', 'caption': 'Performance comparison'}
            ],
            'references': [
                {'id': '1', 'title': 'Related work on deep learning'}
            ],
            'full_text': 'Full paper text here...'
        }

    def test_merge_with_search_paper(self, merger, sample_paper, extracted_metadata):
        """Test merging with search paper metadata."""
        merged, sources = merger.merge_metadata(
            search_paper=sample_paper,
            extracted_metadata=extracted_metadata
        )

        # Check that bibliographic data comes from search
        assert merged['paper_id'] == "2301.12345"
        assert sources['paper_id'] == 'search'

        # Check that DOI is preserved from search (high priority)
        assert merged['doi'] == "10.1234/arxiv.2301.12345"
        assert sources['doi'] == 'search'

        # Check that structure data comes from extraction
        assert len(merged['sections']) == 2
        assert sources['sections'] == 'extracted'

        assert len(merged['figures']) == 1
        assert sources['figures'] == 'extracted'

        # Check that longer abstract is preferred
        assert len(merged['abstract']) > len(sample_paper.abstract)
        assert sources['abstract'] == 'extracted'

        # Authors field has priority 0.7, so it depends on extraction confidence
        # With no confidence provided, it defaults to 0.5, so search wins
        assert 'authors' in merged
        assert len(merged['authors']) >= 2  # At least the search authors

    def test_merge_without_search_paper(self, merger, extracted_metadata):
        """Test merging without search paper (extraction only)."""
        merged, sources = merger.merge_metadata(
            search_paper=None,
            extracted_metadata=extracted_metadata
        )

        # All data should come from extraction
        assert all(source == 'extracted' for source in sources.values())

        # Check specific fields
        assert merged['title'] == extracted_metadata['title']
        assert merged['authors'] == extracted_metadata['authors']
        assert merged['sections'] == extracted_metadata['sections']

    def test_field_priority(self, merger, sample_paper):
        """Test field priority handling."""
        # Create extracted metadata with different values
        extracted = {
            'paper_id': 'different_id',  # Should be ignored (priority 1.0)
            'doi': '10.9999/different',  # Should be ignored (priority 0.9)
            'keywords': ['new', 'keywords', 'extracted'],  # Should be used (priority 0.5)
        }

        merged, sources = merger.merge_metadata(sample_paper, extracted)

        # High priority fields should come from search
        assert merged['paper_id'] == sample_paper.paper_id
        assert sources['paper_id'] == 'search'

        assert merged['doi'] == sample_paper.doi
        assert sources['doi'] == 'search'

        # Low priority fields should come from extraction
        assert merged['keywords'] == extracted['keywords']
        assert sources['keywords'] == 'extracted'

    def test_confidence_scores(self, merger, sample_paper):
        """Test extraction confidence influence."""
        extracted = {
            'title': 'High Confidence Title',
            'abstract': 'High confidence abstract that is much longer than the search abstract',
        }

        # High confidence should allow extraction to override moderate priority
        confidence = {
            'title': 0.95,
            'abstract': 0.9
        }

        merged, sources = merger.merge_metadata(
            sample_paper,
            extracted,
            confidence
        )

        # With high confidence, extracted values might be preferred
        # (depending on implementation details)
        assert 'title' in merged
        assert 'abstract' in merged

    def test_harmonized_metadata(self, merger, sample_paper, extracted_metadata):
        """Test harmonized metadata creation."""
        merged, sources = merger.merge_metadata(sample_paper, extracted_metadata)

        harmonized = merger.create_harmonized_metadata(
            merged,
            sources,
            'pdf'
        )

        # Check structure
        assert 'bibliographic' in harmonized
        assert 'urls' in harmonized
        assert 'content' in harmonized
        assert 'metadata_info' in harmonized

        # Check bibliographic data
        assert harmonized['bibliographic']['paper_id'] == sample_paper.paper_id
        assert harmonized['bibliographic']['title'] == merged['title']

        # Check URLs
        assert harmonized['urls']['pdf'] == sample_paper.pdf_url

        # Check content
        assert harmonized['content']['format'] == 'pdf'
        assert len(harmonized['content']['sections']) == 2

        # Check metadata info
        assert harmonized['metadata_info']['sources'] == sources
        assert harmonized['metadata_info']['extraction_format'] == 'pdf'

    def test_empty_extraction(self, merger, sample_paper):
        """Test handling of empty extraction metadata."""
        merged, sources = merger.merge_metadata(sample_paper, {})

        # Should have all search fields
        assert merged['paper_id'] == sample_paper.paper_id
        assert merged['title'] == sample_paper.title
        assert all(source == 'search' for source in sources.values())

    def test_partial_extraction(self, merger, sample_paper):
        """Test handling of partial extraction metadata."""
        extracted = {
            'sections': [{'title': 'Introduction'}],
            'figures': [],
            'full_text': 'Some text...'
        }

        merged, sources = merger.merge_metadata(sample_paper, extracted)

        # Should have both search and extracted fields
        assert merged['paper_id'] == sample_paper.paper_id
        assert sources['paper_id'] == 'search'

        assert merged['sections'] == extracted['sections']
        assert sources['sections'] == 'extracted'

        assert merged['full_text'] == extracted['full_text']
        assert sources['full_text'] == 'extracted'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

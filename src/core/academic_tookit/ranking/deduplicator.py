#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/ranking/deduplicator.py
# code style: PEP 8

"""
Paper deduplication across multiple sources.

This module handles:
- DOI-based deduplication
- Title similarity matching
- Author and year matching
- Source priority ranking
"""

import re
import logging
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher

from ..models import Paper, PaperSource

logger = logging.getLogger(__name__)


class PaperDeduplicator:
    """
    Deduplicate papers from multiple sources.

    Papers are considered duplicates if they have:
    - Same DOI
    - Very similar titles and same year
    - Same arXiv ID across sources
    """

    # Source priority (higher number = higher priority)
    SOURCE_PRIORITY = {
        PaperSource.SEMANTIC_SCHOLAR: 3,  # Often has citation counts
        PaperSource.ARXIV: 2,             # Authoritative for preprints
        PaperSource.PUBMED: 2,            # Authoritative for biomedical
        PaperSource.BIORXIV: 1,
        PaperSource.MEDRXIV: 1,
        PaperSource.GOOGLE_SCHOLAR: 0     # Often incomplete metadata
    }

    def __init__(self, title_similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator.

        Args:
            title_similarity_threshold: Minimum similarity for title matching
        """
        self.title_similarity_threshold = title_similarity_threshold

    def deduplicate(self, papers: List[Paper]) -> List[Paper]:
        """
        Remove duplicate papers from the list.

        When duplicates are found, the paper from the highest
        priority source is kept, with metadata merged from other sources.

        Args:
            papers: List of papers to deduplicate

        Returns:
            Deduplicated list of papers
        """
        if not papers:
            return []

        # Group papers by potential duplicates
        groups = self._group_duplicates(papers)

        # Select best paper from each group
        deduplicated = []
        for group in groups:
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                best_paper = self._select_best_paper(group)
                merged_paper = self._merge_metadata(best_paper, group)
                deduplicated.append(merged_paper)

        logger.info(
            f"Deduplicated {len(papers)} papers to {len(deduplicated)} "
            f"unique papers"
        )

        return deduplicated

    def _group_duplicates(self, papers: List[Paper]) -> List[List[Paper]]:
        """
        Group papers that are likely duplicates.

        Args:
            papers: Papers to group

        Returns:
            List of paper groups
        """
        # Build indices for fast lookup
        doi_index: Dict[str, List[Paper]] = {}
        arxiv_index: Dict[str, List[Paper]] = {}

        for paper in papers:
            # Index by DOI
            if paper.doi:
                doi_key = paper.doi.lower().strip()
                if doi_key not in doi_index:
                    doi_index[doi_key] = []
                doi_index[doi_key].append(paper)

            # Index by arXiv ID
            if paper.source == PaperSource.ARXIV:
                arxiv_index[paper.paper_id] = [paper]
            # Check if paper from other source references arXiv
            elif paper.extra and "arxiv_id" in paper.extra:
                arxiv_id = paper.extra["arxiv_id"]
                if arxiv_id not in arxiv_index:
                    arxiv_index[arxiv_id] = []
                arxiv_index[arxiv_id].append(paper)

        # Track which papers have been grouped
        grouped_papers: Set[int] = set()
        groups: List[List[Paper]] = []

        # Group by DOI first (most reliable)
        for doi_papers in doi_index.values():
            if len(doi_papers) > 1:
                group_ids = {id(p) for p in doi_papers}
                if not group_ids & grouped_papers:
                    groups.append(doi_papers)
                    grouped_papers.update(group_ids)

        # Group by arXiv ID
        for arxiv_papers in arxiv_index.values():
            if len(arxiv_papers) > 1:
                group_ids = {id(p) for p in arxiv_papers}
                if not group_ids & grouped_papers:
                    groups.append(arxiv_papers)
                    grouped_papers.update(group_ids)

        # Group by title similarity
        remaining_papers = [p for p in papers if id(p) not in grouped_papers]
        title_groups = self._group_by_title(remaining_papers)

        for group in title_groups:
            if len(group) > 1:
                groups.append(group)
                grouped_papers.update(id(p) for p in group)

        # Add ungrouped papers as single-item groups
        for paper in papers:
            if id(paper) not in grouped_papers:
                groups.append([paper])

        return groups

    def _group_by_title(self, papers: List[Paper]) -> List[List[Paper]]:
        """
        Group papers with similar titles from the same year.

        Args:
            papers: Papers to group by title

        Returns:
            List of paper groups
        """
        groups = []
        used = set()

        for i, paper1 in enumerate(papers):
            if i in used:
                continue

            group = [paper1]
            used.add(i)

            for j, paper2 in enumerate(papers[i+1:], i+1):
                if j in used:
                    continue

                # Check year match
                if (paper1.published_date and paper2.published_date and
                        paper1.published_date.year !=
                        paper2.published_date.year):
                    continue

                # Check title similarity
                similarity = self._calculate_title_similarity(
                    paper1.title,
                    paper2.title
                )

                if similarity >= self.title_similarity_threshold:
                    group.append(paper2)
                    used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score (0-1)
        """
        # Normalize titles
        norm1 = self._normalize_title(title1)
        norm2 = self._normalize_title(title2)

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _normalize_title(self, title: str) -> str:
        """
        Normalize title for comparison.

        Args:
            title: Title to normalize

        Returns:
            Normalized title
        """
        # Convert to lowercase
        title = title.lower()

        # Remove punctuation
        title = re.sub(r'[^\w\s]', ' ', title)

        # Remove extra whitespace
        title = ' '.join(title.split())

        # Remove common variations
        title = re.sub(r'\b(a|an|the)\b', '', title)

        return title.strip()

    def _select_best_paper(self, group: List[Paper]) -> Paper:
        """
        Select the best paper from a group of duplicates.

        Selection criteria:
        1. Source priority
        2. Completeness of metadata
        3. Recency of update

        Args:
            group: Group of duplicate papers

        Returns:
            Best paper from the group
        """
        def score_paper(paper: Paper) -> Tuple[int, int, float]:
            # Source priority
            source_score = self.SOURCE_PRIORITY.get(paper.source, 0)

            # Metadata completeness
            metadata_score = 0
            if paper.doi:
                metadata_score += 2
            if paper.pdf_url:
                metadata_score += 1
            if paper.venue:
                metadata_score += 1
            if paper.citations_count > 0:
                metadata_score += 2
            if paper.categories:
                metadata_score += 1
            if paper.keywords:
                metadata_score += 1

            # Recency (use timestamp as tiebreaker)
            recency = paper.updated_date or paper.published_date
            timestamp = recency.timestamp() if recency else 0

            return (source_score, metadata_score, timestamp)

        # Sort by score (descending)
        sorted_papers = sorted(group, key=score_paper, reverse=True)
        return sorted_papers[0]

    def _merge_metadata(
        self,
        primary_paper: Paper,
        group: List[Paper]
    ) -> Paper:
        """
        Merge metadata from duplicate papers.

        Args:
            primary_paper: The selected best paper
            group: All papers in the duplicate group

        Returns:
            Paper with merged metadata
        """
        # Create a copy to avoid modifying the original
        merged = primary_paper.copy()

        # Track which sources provided this paper
        sources_list = list(set(p.source for p in group))
        merged.extra["all_sources"] = sources_list

        # Merge missing fields
        for paper in group:
            if paper.paper_id == primary_paper.paper_id:
                continue

            # Fill in missing basic fields
            if not merged.doi and paper.doi:
                merged.doi = paper.doi
            if not merged.pdf_url and paper.pdf_url:
                merged.pdf_url = paper.pdf_url
            if not merged.html_url and paper.html_url:
                merged.html_url = paper.html_url
            if not merged.venue and paper.venue:
                merged.venue = paper.venue

            # Merge categories and keywords
            if paper.categories:
                existing = set(merged.categories)
                for cat in paper.categories:
                    if cat not in existing:
                        merged.categories.append(cat)
                        existing.add(cat)

            if paper.keywords:
                existing = set(merged.keywords)
                for kw in paper.keywords:
                    if kw not in existing:
                        merged.keywords.append(kw)
                        existing.add(kw)

            # Take maximum citation count
            if paper.citations_count > merged.citations_count:
                merged.citations_count = paper.citations_count

            # Store alternative IDs
            if paper.source != merged.source:
                merged.extra[f"{paper.source}_id"] = paper.paper_id
                merged.extra[f"{paper.source}_url"] = paper.url

        return merged

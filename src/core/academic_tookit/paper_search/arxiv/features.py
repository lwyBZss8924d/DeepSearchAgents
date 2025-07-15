#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_search/arxiv/features.py
# code style: PEP 8

"""
Advanced features for ArXiv paper analysis.

This module provides functionality for:
- Finding related papers
- Analyzing research trends
- Keyword extraction
- Paper similarity computation
"""

import re
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Any

from ...models import Paper

logger = logging.getLogger(__name__)


class ArxivFeatureExtractor:
    """
    Advanced features ported from arxiv_client_demo.py.

    This class provides:
    - Related paper finding
    - Trend analysis
    - Keyword extraction
    - Author collaboration analysis
    """

    # Common stop words for academic text
    ACADEMIC_STOP_WORDS = {
        "a", "an", "and", "the", "of", "in", "for", "to", "with", "on",
        "is", "are", "was", "were", "it", "we", "our", "this", "that",
        "these", "those", "which", "where", "when", "what", "how", "why",
        "from", "into", "through", "during", "including", "across",
        "after", "above", "below", "between", "under", "over", "however",
        "therefore", "moreover", "furthermore", "although", "though",
        "thus", "hence", "since", "because", "due", "despite", "while",
        "paper", "papers", "work", "works", "study", "studies", "research",
        "approach", "method", "methods", "results", "result", "show",
        "shows", "shown", "demonstrate", "demonstrates", "present",
        "presents", "presented", "propose", "proposes", "proposed",
        "introduce", "introduces", "introduced", "describe", "describes",
        "described", "discuss", "discusses", "discussed", "abstract",
        "introduction", "conclusion", "section", "figure", "table",
        "equation", "theorem", "proof", "lemma", "definition", "example"
    }

    def __init__(self):
        """Initialize the feature extractor."""
        self._stop_words = self.ACADEMIC_STOP_WORDS

    def find_similar_papers(
        self,
        reference_paper: Paper,
        candidate_papers: List[Paper],
        similarity_threshold: float = 0.7
    ) -> List[Paper]:
        """
        Find papers similar to a reference paper.

        Args:
            reference_paper: The reference paper
            candidate_papers: Papers to compare against
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar papers sorted by similarity
        """
        if not candidate_papers:
            return []

        # Extract keywords from reference
        ref_keywords = self.extract_keywords(
            reference_paper.title + " " + reference_paper.abstract,
            max_keywords=20
        )
        ref_keyword_set = set(ref_keywords)

        # Calculate similarities
        similarities = []

        for paper in candidate_papers:
            # Skip self
            if paper.paper_id == reference_paper.paper_id:
                continue

            # Calculate keyword overlap
            paper_text = paper.title + " " + paper.abstract
            paper_keywords = set(
                self.extract_keywords(paper_text, max_keywords=20)
            )

            # Jaccard similarity
            intersection = ref_keyword_set & paper_keywords
            union = ref_keyword_set | paper_keywords

            if union:
                similarity = len(intersection) / len(union)

                # Boost similarity for category overlap
                category_overlap = (
                    set(reference_paper.categories) & set(paper.categories)
                )
                if category_overlap:
                    similarity *= 1.2  # 20% boost

                # Boost for author overlap
                author_overlap = (
                    set(reference_paper.authors) & set(paper.authors)
                )
                if author_overlap:
                    similarity *= 1.3  # 30% boost

                # Cap at 1.0
                similarity = min(similarity, 1.0)

                if similarity >= similarity_threshold:
                    similarities.append((paper, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [paper for paper, _ in similarities]

    def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10
    ) -> List[str]:
        """
        Extract keywords from text using simple TF-IDF-like approach.

        Args:
            text: Input text
            max_keywords: Maximum keywords to return

        Returns:
            List of keywords
        """
        # Clean text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        # Tokenize
        words = text.split()

        # Filter stop words and short words
        words = [
            w for w in words
            if w not in self._stop_words and len(w) > 2 and not w.isdigit()
        ]

        # Count word frequencies
        word_freq = Counter(words)

        # Get top keywords
        keywords = [word for word, _ in word_freq.most_common(max_keywords)]

        return keywords

    def analyze_trends(
        self,
        papers: List[Paper],
        analysis_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Analyze trends in a collection of papers.

        Args:
            papers: Papers to analyze
            analysis_type: Type of analysis
                          ('all', 'authors', 'timeline', 'categories',
                          'keywords')

        Returns:
            Analysis results
        """
        if not papers:
            return {"error": "No papers to analyze"}

        analysis = {
            "total_papers": len(papers),
            "date_range": self._get_date_range(papers)
        }

        if analysis_type in ["all", "authors"]:
            analysis["author_analysis"] = self._analyze_authors(papers)

        if analysis_type in ["all", "timeline"]:
            analysis["timeline_analysis"] = self._analyze_timeline(papers)

        if analysis_type in ["all", "categories"]:
            analysis["category_analysis"] = self._analyze_categories(papers)

        if analysis_type in ["all", "keywords"]:
            analysis["keyword_analysis"] = self._analyze_keywords(papers)

        return analysis

    def _analyze_authors(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze author trends."""
        author_counts = Counter()
        collaboration_sizes = []
        author_papers = defaultdict(list)

        for paper in papers:
            # Count authors
            for author in paper.authors:
                author_counts[author] += 1
                author_papers[author].append(paper.title)

            # Track collaboration size
            collaboration_sizes.append(len(paper.authors))

        # Find frequent collaborators
        collaborations = defaultdict(int)
        for paper in papers:
            if len(paper.authors) > 1:
                # Count pairwise collaborations
                for i in range(len(paper.authors)):
                    for j in range(i + 1, len(paper.authors)):
                        pair = tuple(sorted([paper.authors[i],
                                             paper.authors[j]]))
                        collaborations[pair] += 1

        return {
            "total_unique_authors": len(author_counts),
            "most_prolific_authors": author_counts.most_common(10),
            "average_authors_per_paper": (
                sum(collaboration_sizes) / len(collaboration_sizes)
                if collaboration_sizes else 0
            ),
            "single_author_papers": sum(1 for s in collaboration_sizes
                                        if s == 1),
            "collaborative_papers": sum(1 for s in collaboration_sizes
                                        if s > 1),
            "top_collaborations": sorted(
                collaborations.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def _analyze_timeline(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze publication timeline."""
        # Group by year and month
        yearly_counts = Counter()
        monthly_counts = defaultdict(Counter)

        for paper in papers:
            if paper.published_date:
                year = paper.published_date.year
                month = paper.published_date.strftime("%Y-%m")

                yearly_counts[year] += 1
                monthly_counts[year][month] += 1

        # Calculate growth rate
        years = sorted(yearly_counts.keys())
        growth_rates = []
        if len(years) > 1:
            for i in range(1, len(years)):
                prev_count = yearly_counts[years[i-1]]
                curr_count = yearly_counts[years[i]]
                if prev_count > 0:
                    growth_rate = (curr_count - prev_count) / prev_count * 100
                    growth_rates.append((years[i], growth_rate))

        return {
            "papers_by_year": dict(sorted(yearly_counts.items())),
            "most_active_year": (
                yearly_counts.most_common(1)[0]
                if yearly_counts else None
            ),
            "year_range": (min(years), max(years)) if years else (None, None),
            "average_papers_per_year": (
                sum(yearly_counts.values()) / len(yearly_counts)
                if yearly_counts else 0
            ),
            "growth_rates": growth_rates,
            "recent_trend": self._calculate_recent_trend(yearly_counts)
        }

    def _analyze_categories(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze category distribution."""
        category_counts = Counter()
        category_combinations = Counter()
        primary_categories = Counter()

        for paper in papers:
            # Count individual categories
            for cat in paper.categories:
                category_counts[cat] += 1

            # Track category combinations
            if len(paper.categories) > 1:
                cat_tuple = tuple(sorted(paper.categories[:2]))  # Top 2
                category_combinations[cat_tuple] += 1

            # Primary category from extra data
            if paper.extra and "primary_category" in paper.extra:
                primary_categories[paper.extra["primary_category"]] += 1

        return {
            "total_categories": len(category_counts),
            "most_common_categories": category_counts.most_common(15),
            "category_distribution": dict(category_counts),
            "common_category_pairs": category_combinations.most_common(10),
            "primary_categories": primary_categories.most_common(10),
            "interdisciplinary_papers": sum(
                1 for p in papers if len(p.categories) > 1
            )
        }

    def _analyze_keywords(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze keyword trends."""
        # Combine all text
        all_text = []
        title_keywords = Counter()

        for paper in papers:
            # Full text for general keywords
            all_text.append(paper.title + " " + paper.abstract)

            # Title keywords (more important)
            title_words = self.extract_keywords(paper.title, max_keywords=5)
            for word in title_words:
                title_keywords[word] += 1

        # Extract keywords from all text
        combined_text = " ".join(all_text)
        top_keywords = self.extract_keywords(combined_text, max_keywords=50)

        # Find trending keywords (appear in recent papers)
        recent_papers = sorted(
            papers,
            key=lambda p: p.published_date,
            reverse=True
        )[:min(20, len(papers))]

        recent_text = " ".join(
            p.title + " " + p.abstract for p in recent_papers
        )
        trending_keywords = self.extract_keywords(recent_text, max_keywords=20)

        return {
            "top_keywords": top_keywords[:20],
            "title_keywords": title_keywords.most_common(20),
            "trending_keywords": trending_keywords,
            "keyword_diversity": (
                len(set(top_keywords)) / len(papers) if papers else 0
            )
        }

    def _get_date_range(self, papers: List[Paper]) -> Dict[str, Any]:
        """Get date range statistics."""
        dates = [p.published_date for p in papers if p.published_date]

        if not dates:
            return {"start": None, "end": None, "span_days": 0}

        start_date = min(dates)
        end_date = max(dates)
        span = (end_date - start_date).days

        return {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "span_days": span
        }

    def _calculate_recent_trend(self, yearly_counts: Counter) -> str:
        """Calculate recent publication trend."""
        if not yearly_counts:
            return "no_data"

        years = sorted(yearly_counts.keys())
        if len(years) < 2:
            return "insufficient_data"

        # Look at last 3 years
        recent_years = years[-3:]
        recent_counts = [yearly_counts[y] for y in recent_years]

        # Simple trend detection
        if all(recent_counts[i] <= recent_counts[i+1]
               for i in range(len(recent_counts)-1)):
            return "increasing"
        elif all(recent_counts[i] >= recent_counts[i+1]
                 for i in range(len(recent_counts)-1)):
            return "decreasing"
        else:
            return "stable"

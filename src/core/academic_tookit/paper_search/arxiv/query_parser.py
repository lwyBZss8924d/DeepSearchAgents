#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_search/arxiv/query_parser.py
# code style: PEP 8

"""
Query parser for converting natural language to ArXiv API queries.

This module extracts keywords, dates, authors, and categories from
natural language queries and converts them to ArXiv search syntax.
"""

import re
import logging
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class ArxivQueryParser:
    """
    Parse natural language queries into ArXiv API format.

    This parser handles:
    - Keyword extraction
    - Date extraction and parsing
    - Author name detection
    - Category inference
    - Query structure building
    """

    # Common stop words to filter out
    STOP_WORDS = {
        "a", "an", "and", "the", "of", "in", "for", "to", "with", "on",
        "is", "are", "was", "were", "it", "about", "how", "what", "when",
        "where", "which", "who", "why", "can", "could", "would", "should",
        "may", "might", "must", "shall", "will", "do", "does", "did",
        "has", "have", "had", "be", "been", "being", "that", "this",
        "these", "those", "from", "into", "through", "during", "before",
        "after", "above", "below", "between", "under", "over", "out",
        "off", "up", "down", "as", "at", "by", "or", "nor", "but", "so",
        "if", "then", "else", "all", "any", "both", "each", "few",
        "more", "most", "other", "some", "such", "no", "not", "only",
        "own", "same", "than", "too", "very", "just", "papers", "paper",
        "research", "study", "studies", "work", "works", "recent", "latest",
        "new", "novel", "current", "find", "search", "show", "give", "get"
    }

    # Common author name patterns
    AUTHOR_PATTERNS = [
        r"\b(?:by|from|author)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'s\s+(?:work|papers?|research)\b",
        r"\b(?:papers?\s+by|works?\s+by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
    ]

    # Category keywords mapping
    CATEGORY_KEYWORDS = {
        "cs.AI": ["artificial intelligence", "ai", "intelligent systems"],
        "cs.LG": ["machine learning", "deep learning", "neural network",
                  "neural networks", "transformer", "transformers"],
        "cs.CV": ["computer vision", "image processing", "object detection",
                  "image recognition", "visual"],
        "cs.CL": ["natural language", "nlp", "language processing", "text",
                  "linguistics", "language model", "llm"],
        "cs.RO": ["robotics", "robot", "robots", "autonomous"],
        "cs.CR": ["cryptography", "security", "encryption", "privacy"],
        "cs.DB": ["database", "databases", "data management", "sql"],
        "cs.SE": ["software engineering", "software development",
                  "programming", "software"],
        "cs.IR": ["information retrieval", "search engine", "ranking"],
        "cs.HC": ["human computer interaction", "hci", "user interface",
                  "ui", "ux"],
        "math.NA": ["numerical analysis", "numerical methods",
                    "computational"],
        "physics": ["physics", "quantum", "particle", "relativity"],
        "q-bio": ["biology", "biological", "genomics", "bioinformatics"],
        "stat.ML": ["statistical learning", "statistics", "statistical"],
    }

    def __init__(self):
        """Initialize the query parser."""
        # Compile regex patterns for efficiency
        self._author_patterns = [re.compile(p) for p in self.AUTHOR_PATTERNS]
        self._year_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        self._date_range_pattern = re.compile(
            r'\b(?:from|between|since)\s+'
            r'(19\d{2}|20\d{2})\s*(?:to|and|-|until)?\s*(19\d{2}|20\d{2})?\b',
            re.IGNORECASE
        )

    def parse_natural_language(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        author: Optional[str] = None
    ) -> str:
        """
        Convert natural language query to ArXiv search syntax.

        Args:
            query: Natural language query
            categories: Optional category filters
            start_date: Optional start date filter
            end_date: Optional end date filter
            author: Optional author filter

        Returns:
            ArXiv formatted query string
        """
        logger.debug(f"Parsing natural language query: {query}")

        # Extract components from query
        extracted_authors = self._extract_authors(query) if not author else []
        extracted_dates = self._extract_dates(query)
        inferred_categories = self._infer_categories(query)
        keywords = self._extract_keywords(query)

        # Build query parts
        query_parts = []

        # Add keyword search
        if keywords:
            keyword_query = self._build_keyword_query(keywords)
            if keyword_query:
                query_parts.append(keyword_query)

        # Add author filter
        authors_to_use = [author] if author else extracted_authors
        if authors_to_use:
            author_queries = [f'au:"{a}"' for a in authors_to_use]
            if len(author_queries) == 1:
                query_parts.append(author_queries[0])
            else:
                query_parts.append(f"({' OR '.join(author_queries)})")

        # Add category filter
        categories_to_use = categories or inferred_categories
        if categories_to_use:
            cat_queries = [f"cat:{cat}" for cat in categories_to_use]
            if len(cat_queries) == 1:
                query_parts.append(cat_queries[0])
            else:
                query_parts.append(f"({' OR '.join(cat_queries)})")

        # Add date filter
        date_query = self._build_date_query(
            start_date or extracted_dates.get('start'),
            end_date or extracted_dates.get('end')
        )
        if date_query:
            query_parts.append(date_query)

        # Combine all parts
        final_query = " AND ".join(query_parts) if query_parts else query

        logger.info(
            f"Parsed query '{query}' to ArXiv syntax: {final_query}"
        )

        return final_query

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Remove author patterns and dates first
        cleaned_text = text

        # Remove author mentions
        for pattern in self._author_patterns:
            cleaned_text = pattern.sub('', cleaned_text)

        # Remove dates
        cleaned_text = self._year_pattern.sub('', cleaned_text)
        cleaned_text = self._date_range_pattern.sub('', cleaned_text)

        # Extract words
        words = re.findall(r'\b\w+\b', cleaned_text.lower())

        # Filter keywords
        keywords = []
        seen = set()

        for word in words:
            # Skip if already seen, too short, or stop word
            if (word in seen or len(word) <= 2 or word in self.STOP_WORDS or
                    word.isdigit()):
                continue

            keywords.append(word)
            seen.add(word)

        # Also extract important phrases
        phrases = self._extract_phrases(cleaned_text)
        keywords.extend(phrases)

        return keywords[:10]  # Limit to top 10 keywords

    def _extract_phrases(self, text: str) -> List[str]:
        """
        Extract important multi-word phrases.

        Args:
            text: Input text

        Returns:
            List of phrases
        """
        phrases = []

        # Common ML/AI phrases
        phrase_patterns = [
            r"(?:deep|machine|reinforcement|transfer)\s+learning",
            r"neural\s+networks?",
            r"natural\s+language\s+processing",
            r"computer\s+vision",
            r"artificial\s+intelligence",
            r"large\s+language\s+models?",
            r"transformer\s+models?",
            r"convolutional\s+neural\s+networks?",
            r"generative\s+adversarial\s+networks?",
            r"graph\s+neural\s+networks?",
            r"attention\s+mechanisms?",
            r"knowledge\s+graphs?",
            r"quantum\s+computing",
            r"federated\s+learning",
            r"meta\s+learning"
        ]

        text_lower = text.lower()
        for pattern in phrase_patterns:
            matches = re.findall(pattern, text_lower)
            phrases.extend(matches)

        return list(set(phrases))  # Remove duplicates

    def _extract_authors(self, text: str) -> List[str]:
        """
        Extract author names from text.

        Args:
            text: Input text

        Returns:
            List of author names
        """
        authors = []

        for pattern in self._author_patterns:
            matches = pattern.findall(text)
            authors.extend(matches)

        # Clean up authors
        cleaned_authors = []
        for author in authors:
            # Remove trailing possessives
            author = re.sub(r"'s$", "", author)
            # Ensure proper capitalization
            author = " ".join(word.capitalize() for word in author.split())
            if author and author not in cleaned_authors:
                cleaned_authors.append(author)

        return cleaned_authors

    def _extract_dates(self, text: str) -> Dict[str, datetime]:
        """
        Extract date information from text.

        Args:
            text: Input text

        Returns:
            Dictionary with 'start' and 'end' dates
        """
        dates = {}

        # Look for date ranges
        range_match = self._date_range_pattern.search(text)
        if range_match:
            start_year = range_match.group(1)
            end_year = range_match.group(2) or str(datetime.now().year)

            dates['start'] = datetime(int(start_year), 1, 1)
            dates['end'] = datetime(int(end_year), 12, 31)
            return dates

        # Look for single years
        year_matches = self._year_pattern.findall(text)
        if year_matches:
            # Keywords indicating recency
            if any(word in text.lower() for word in
                   ['recent', 'latest', 'new', 'current', 'since', 'after']):
                # Use the year as start date
                dates['start'] = datetime(int(year_matches[0]), 1, 1)
            elif any(word in text.lower() for word in
                     ['before', 'until', 'prior']):
                # Use the year as end date
                dates['end'] = datetime(int(year_matches[0]), 12, 31)
            else:
                # Single year - search within that year
                year = int(year_matches[0])
                dates['start'] = datetime(year, 1, 1)
                dates['end'] = datetime(year, 12, 31)

        return dates

    def _infer_categories(self, text: str) -> List[str]:
        """
        Infer ArXiv categories from query text.

        Args:
            text: Input text

        Returns:
            List of inferred category codes
        """
        categories = []
        text_lower = text.lower()

        # Score each category based on keyword matches
        category_scores = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # Longer keywords get higher scores
                    score += len(keyword.split())

            if score > 0:
                category_scores[category] = score

        # Return top categories
        if category_scores:
            sorted_categories = sorted(
                category_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            categories = [cat for cat, score in sorted_categories[:3]]

        return categories

    def _build_keyword_query(self, keywords: List[str]) -> str:
        """
        Build keyword search query.

        Args:
            keywords: List of keywords

        Returns:
            ArXiv keyword query string
        """
        if not keywords:
            return ""

        # Use OR for broader results
        # Search in both title and abstract
        keyword_queries = []
        for keyword in keywords:
            # Quote multi-word phrases
            if ' ' in keyword:
                keyword_queries.append(f'(ti:"{keyword}" OR abs:"{keyword}")')
            else:
                keyword_queries.append(f'(ti:{keyword} OR abs:{keyword})')

        return f"({' OR '.join(keyword_queries)})"

    def _build_date_query(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """
        Build ArXiv date range query.

        Args:
            start_date: Start date
            end_date: End date

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

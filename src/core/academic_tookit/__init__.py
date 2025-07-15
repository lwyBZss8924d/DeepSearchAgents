#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/__init__.py
# code style: PEP 8

"""
Academic Toolkit for DeepSearchAgents.

This module provides client interfaces to FutureHouse Platform API
for academic paper search and research capabilities.
"""

# TODO: Temporarily disabled due to FutureHouse API rate limiting
# from .scholar_search_client import ScholarSearchClient
# from .academic_research_client import AcademicResearchClient

# New implementation using direct APIs
from .paper_retrievaler import PaperRetriever
from .models import Paper, PaperSource, SearchParams

__all__ = [
    # Legacy (temporarily disabled)
    # "ScholarSearchClient",
    # "AcademicResearchClient",
    # New implementation
    "PaperRetriever",
    "Paper",
    "PaperSource",
    "SearchParams",
]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/__init__.py
# code style: PEP 8

"""
Search Engines API for web search tools.
"""

from .base import BaseSearchClient, RateLimiter

from .search_serper import (
    SerperAPIException,
    SearchResult,
    SerperAPI,
    GoogleSerperClient,
)

from .search_xcom import (
    XAISearchClient,
    detect_x_query,
    extract_x_handles,
)

from .search_jina import (
    JinaSearchClient,
    JinaSearchException,
)

from .search_exa import (
    ExaSearchClient,
    ExaSearchException,
)

from .search_hybrid import (
    HybridSearchEngine,
    hybrid_search,
)

__all__ = [
    # Base classes
    "BaseSearchClient",
    "RateLimiter",
    # Serper/Google
    "SerperAPIException",
    "SearchResult",
    "SerperAPI",
    "GoogleSerperClient",
    # X.com
    "XAISearchClient",
    "detect_x_query",
    "extract_x_handles",
    # Jina
    "JinaSearchClient",
    "JinaSearchException",
    # Exa
    "ExaSearchClient",
    "ExaSearchException",
    # Hybrid
    "HybridSearchEngine",
    "hybrid_search",
]

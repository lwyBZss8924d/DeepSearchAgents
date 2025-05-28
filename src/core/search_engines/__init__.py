#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/__init__.py
# code style: PEP 8

"""
Search Engines API for web search tools.
"""

from .search_serper import (
    SerperAPIException,
    SearchResult,
    SerperAPI,
    SerperConfig,
)

from .search_xcom import (
    XAISearchClient,
    detect_x_query,
    extract_x_handles,
)

__all__ = [
    "SerperAPIException",
    "SearchResult",
    "SerperAPI",
    "SerperConfig",
    "XAISearchClient",
    "detect_x_query",
    "extract_x_handles",
]

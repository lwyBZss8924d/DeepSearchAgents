#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/__init__.py
# code style: PEP 8

"""
Search Engines API for web search tools.
"""

from .serper import (
    SerperAPIException,
    SearchResult,
    SerperAPI,
    SerperConfig,
)

__all__ = [
    "SerperAPIException",
    "SearchResult",
    "SerperAPI",
    "SerperConfig",
]

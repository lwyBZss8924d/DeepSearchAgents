#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_xcom.py
# code style: PEP 8

"""
[XAI] for (x.com), (twitter.com) live search API
specialized search engine using xAI's Grok LLM for x.com social network client for "HybridSearchEngine"
API Base URL: (api.x.ai)

This module now uses the xai-sdk for cleaner implementation.
"""

# Re-export everything from the SDK implementation
from .search_xcom_sdk import (
    XAISearchClient,
    detect_x_query,
    extract_x_handles,
)

__all__ = [
    "XAISearchClient",
    "detect_x_query",
    "extract_x_handles",
]

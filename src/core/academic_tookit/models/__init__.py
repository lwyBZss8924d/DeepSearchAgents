#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/models/__init__.py
# code style: PEP 8

"""
Models for the academic toolkit.
"""

from .paper import Paper, PaperSource
from .search_params import SearchParams

__all__ = [
    "Paper",
    "PaperSource",
    "SearchParams",
]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/ranking/__init__.py
# code style: PEP 8

"""
Ranking and deduplication utilities for academic papers.
"""

from .deduplicator import PaperDeduplicator

__all__ = ["PaperDeduplicator"]

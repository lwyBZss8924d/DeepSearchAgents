#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/__init__.py
# code style: PEP 8

"""
PaperQA2 integration for the academic toolkit.

This module provides bridges between our academic toolkit and PaperQA2:
- Custom ArXiv provider for PaperQA2's metadata system
- Mistral OCR reader for enhanced PDF processing
- Manager class for orchestrating searches and Q&A
- High-level API for academic research workflows
"""

from .arxiv_provider import ArxivPaperQA2Provider
from .manager import PaperQA2Manager
from .mistral_ocr_parser import create_mistral_ocr_parser
from .config import PaperQA2Config, SearchConfig, load_config_from_env
from .academic_qa import AcademicQASystem, ResearchResult

__all__ = [
    'ArxivPaperQA2Provider',
    'PaperQA2Manager',
    'create_mistral_ocr_parser',
    'PaperQA2Config',
    'SearchConfig',
    'load_config_from_env',
    'AcademicQASystem',
    'ResearchResult',
]

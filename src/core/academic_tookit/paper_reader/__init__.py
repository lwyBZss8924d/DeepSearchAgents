#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_reader/__init__.py
# code style: PEP 8

"""
Paper reader module for academic paper parsing.

This module provides enhanced paper parsing capabilities including:
- PDF parsing with Mistral OCR
- HTML parsing with Jina Reader
- Figure and table extraction
- Reference parsing
- Unified paper reading interface
"""

from .paper_parser_pdf import (
    PDFParserConfig,
    parse_pdf_with_ocr,
    extract_assets_from_mistral_response
)

from .paper_parser_html import (
    HTMLParserConfig,
    HTMLPaperParser,
    parse_paper_html
)

from .reader import (
    PaperReader,
    PaperReaderConfig
)

from .metadata_merger import MetadataMerger

__all__ = [
    # PDF parser exports
    "PDFParserConfig",
    "parse_pdf_with_ocr",
    "extract_assets_from_mistral_response",
    # HTML parser exports
    "HTMLParserConfig",
    "HTMLPaperParser",
    "parse_paper_html",
    # Unified reader exports
    "PaperReader",
    "PaperReaderConfig",
    # Metadata merger
    "MetadataMerger"
]

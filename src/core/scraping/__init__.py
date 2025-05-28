#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/__init__.py
# code style: PEP 8

from .scraper import JinaReaderScraper
from .xcom_scraper import XcomScraper
from .result import ExtractionResult, print_extraction_result
from .utils import get_wikipedia_content

__all__ = [
    "JinaReaderScraper",
    "XcomScraper",
    "ExtractionResult",
    "print_extraction_result",
    "get_wikipedia_content",
]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_reader/reader.py
# code style: PEP 8

"""
Unified paper reader interface for academic papers.

This module provides a unified interface for reading academic papers from
various sources (HTML, PDF URL, PDF file) with automatic format detection
and priority handling.
"""

import logging
import tempfile
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .paper_parser_pdf import PDFParserConfig, parse_pdf_with_ocr
from .paper_parser_html import HTMLParserConfig, HTMLPaperParser
from .metadata_merger import MetadataMerger
from ..models import Paper, PaperSource

logger = logging.getLogger(__name__)


@dataclass
class PaperReaderConfig:
    """Configuration for unified paper reader."""

    # Parser configurations
    pdf_config: Optional[PDFParserConfig] = None
    html_config: Optional[HTMLParserConfig] = None

    # Priority settings
    prefer_html: bool = True  # Prefer HTML over PDF when both available

    # Cache settings
    cache_dir: Optional[Path] = None
    cache_pdfs: bool = True

    # Processing options
    extract_references: bool = True
    extract_figures: bool = True
    extract_equations: bool = True
    extract_tables: bool = True


class PaperReader:
    """
    Unified interface for reading academic papers.

    Priority order:
    1. HTML URL (if available and preferred)
    2. PDF URL (direct download)
    3. PDF file (local file)

    This reader automatically selects the best available format and
    returns standardized paper content.
    """

    def __init__(self, config: Optional[PaperReaderConfig] = None):
        """
        Initialize paper reader.

        Args:
            config: Optional reader configuration
        """
        self.config = config or PaperReaderConfig()

        # Initialize parsers
        self.pdf_config = self.config.pdf_config or PDFParserConfig()
        self.html_config = self.config.html_config or HTMLParserConfig()
        self.html_parser = HTMLPaperParser(self.html_config)

        # Initialize metadata merger
        self.metadata_merger = MetadataMerger()

        # Setup cache directory
        if self.config.cache_dir:
            self.cache_dir = Path(self.config.cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "paper_reader_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def read_paper(
        self,
        paper: Optional[Paper] = None,
        paper_id: Optional[str] = None,
        html_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
        pdf_path: Optional[str] = None,
        force_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read academic paper with automatic format selection.

        Args:
            paper: Paper object containing URLs
            paper_id: Paper ID for caching/logging
            html_url: Direct HTML URL
            pdf_url: Direct PDF URL
            pdf_path: Local PDF file path
            force_format: Force specific format ('html' or 'pdf')

        Returns:
            Dictionary containing:
                - paper_id: Paper identifier
                - content_format: Format used ('html' or 'pdf')
                - full_text: Full paper text in markdown
                - sections: List of paper sections
                - figures: List of figures
                - tables: List of tables
                - references: List of references
                - equations: List of equations (if extracted)
                - metadata: Additional metadata
                - processing_info: Processing details
        """
        # Extract URLs from paper object if provided
        if paper:
            paper_id = paper_id or paper.paper_id
            html_url = html_url or paper.html_url
            pdf_url = pdf_url or paper.pdf_url

        if not any([html_url, pdf_url, pdf_path]):
            raise ValueError("No paper source provided (HTML URL, PDF URL, or PDF path)")

        # Determine format to use based on priority
        format_to_use = self._determine_format(
            html_url, pdf_url, pdf_path, force_format
        )

        logger.info(
            f"Reading paper {paper_id or 'unknown'} using format: {format_to_use}"
        )

        try:
            if format_to_use == 'html':
                return await self._read_html(html_url, paper_id, paper)
            else:
                # For PDF, check if we can use direct URL
                if pdf_url and self.pdf_config.use_direct_url:
                    # Try direct URL processing first
                    try:
                        return await self._read_pdf(pdf_url=pdf_url, paper_id=paper_id, paper=paper)
                    except Exception as e:
                        logger.warning(
                            f"Direct URL processing failed: {e}. "
                            f"Falling back to download."
                        )
                        if self.pdf_config.download_fallback:
                            pdf_path = await self._download_pdf(pdf_url, paper_id)
                            return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)
                        else:
                            raise
                elif pdf_url and not pdf_path:
                    # Download PDF if direct URL is disabled
                    pdf_path = await self._download_pdf(pdf_url, paper_id)
                    return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)
                else:
                    # Use local file
                    return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)

        except Exception as e:
            logger.error(f"Failed to read paper with {format_to_use}: {e}")

            # Try fallback format if available
            if format_to_use == 'html' and (pdf_url or pdf_path):
                logger.info("Falling back to PDF format")
                if pdf_url and self.pdf_config.use_direct_url:
                    try:
                        return await self._read_pdf(pdf_url=pdf_url, paper_id=paper_id, paper=paper)
                    except Exception:
                        if self.pdf_config.download_fallback:
                            pdf_path = await self._download_pdf(pdf_url, paper_id)
                            return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)
                        else:
                            raise
                elif pdf_url and not pdf_path:
                    pdf_path = await self._download_pdf(pdf_url, paper_id)
                    return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)
                else:
                    return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id, paper=paper)
            elif format_to_use == 'pdf' and html_url:
                logger.info("Falling back to HTML format")
                return await self._read_html(html_url, paper_id, paper)
            else:
                raise

    async def read_pdf(
        self,
        pdf_path: Optional[str] = None,
        pdf_url: Optional[str] = None,
        paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read paper from PDF source.

        Args:
            pdf_path: Local PDF file path
            pdf_url: PDF URL (can be processed directly or downloaded)
            paper_id: Paper ID for caching/logging

        Returns:
            Standardized paper content dictionary
        """
        if pdf_url and self.pdf_config.use_direct_url:
            # Try direct URL processing
            try:
                return await self._read_pdf(pdf_url=pdf_url, paper_id=paper_id)
            except Exception as e:
                logger.warning(f"Direct URL processing failed: {e}")
                if self.pdf_config.download_fallback and not pdf_path:
                    pdf_path = await self._download_pdf(pdf_url, paper_id)
                else:
                    raise
        elif pdf_url and not pdf_path:
            pdf_path = await self._download_pdf(pdf_url, paper_id)
        elif not pdf_path and not pdf_url:
            raise ValueError("No PDF source provided")

        return await self._read_pdf(pdf_path=pdf_path, paper_id=paper_id)

    async def read_html(
        self,
        html_url: str,
        paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read paper from HTML source.

        Args:
            html_url: HTML URL
            paper_id: Paper ID for logging

        Returns:
            Standardized paper content dictionary
        """
        return await self._read_html(html_url, paper_id)

    def _determine_format(
        self,
        html_url: Optional[str],
        pdf_url: Optional[str],
        pdf_path: Optional[str],
        force_format: Optional[str]
    ) -> str:
        """Determine which format to use based on availability and preference."""
        if force_format:
            if force_format == 'html' and not html_url:
                raise ValueError("Forced HTML format but no HTML URL provided")
            elif force_format == 'pdf' and not (pdf_url or pdf_path):
                raise ValueError("Forced PDF format but no PDF source provided")
            return force_format

        # Follow priority order
        if self.config.prefer_html and html_url:
            return 'html'
        elif pdf_url or pdf_path:
            return 'pdf'
        elif html_url:
            return 'html'
        else:
            raise ValueError("No valid paper source available")

    async def _read_html(
        self,
        html_url: str,
        paper_id: Optional[str] = None,
        paper: Optional[Paper] = None
    ) -> Dict[str, Any]:
        """Read paper from HTML source."""
        # Parse HTML
        metadata, content, figures, tables = await self.html_parser.parse_paper_html(
            html_url, paper_id
        )

        # Build extracted metadata
        extracted_metadata = {
            'title': metadata.get('title', ''),
            'authors': metadata.get('authors', []),
            'abstract': metadata.get('abstract', ''),
            'keywords': metadata.get('keywords', []),
            'url': html_url,
            'sections': metadata.get('sections', []),
            'figures': figures,
            'tables': tables,
            'references': metadata.get('references', []),
            'equations': metadata.get('equations', []),
            'full_text': content
        }

        # Merge with search metadata if available
        if paper:
            merged_metadata, metadata_sources = self.metadata_merger.merge_metadata(
                search_paper=paper,
                extracted_metadata=extracted_metadata,
                extraction_confidence=None  # TODO: Add confidence scores
            )
        else:
            merged_metadata = extracted_metadata
            metadata_sources = {k: 'extracted' for k in extracted_metadata.keys()}

        # Build standardized response
        result = {
            'paper_id': merged_metadata.get('paper_id', paper_id or metadata.get('url', '')),
            'content_format': 'html',
            'full_text': merged_metadata.get('full_text', content),
            'sections': merged_metadata.get('sections', []),
            'figures': merged_metadata.get('figures', figures),
            'tables': merged_metadata.get('tables', tables),
            'references': merged_metadata.get('references', []),
            'equations': merged_metadata.get('equations', []),
            'metadata': merged_metadata,
            'metadata_sources': metadata_sources,
            'processing_info': {
                'parser': 'jina_reader',
                'source_url': html_url
            }
        }

        return result

    async def _read_pdf(
        self,
        pdf_path: Optional[str] = None,
        pdf_url: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper: Optional[Paper] = None
    ) -> Dict[str, Any]:
        """Read paper from PDF source (file or URL)."""
        # Parse PDF - returns 5-element tuple
        if pdf_url and self.pdf_config.use_direct_url:
            # Use direct URL processing
            raw_response, markdown_text, images_list, tables_list, pdf_metadata = await parse_pdf_with_ocr(
                pdf_url=pdf_url,
                config=self.pdf_config,
                filename_for_logging=paper_id or pdf_url.split('/')[-1],
                extract_metadata=True
            )
        else:
            # Use file-based processing
            if not pdf_path:
                raise ValueError("PDF path required when not using direct URL")
            raw_response, markdown_text, images_list, tables_list, pdf_metadata = await parse_pdf_with_ocr(
                pdf_path=pdf_path,
                config=self.pdf_config,
                filename_for_logging=paper_id or Path(pdf_path).name,
                extract_metadata=True
            )

        # Use sections and references from PDF parser
        sections = pdf_metadata.get('sections', [])
        references = pdf_metadata.get('references', [])

        # Build extracted metadata
        extracted_metadata = {
            'title': pdf_metadata.get('title', ''),
            'authors': pdf_metadata.get('authors', []),
            'abstract': pdf_metadata.get('abstract', ''),
            'keywords': pdf_metadata.get('keywords', []),
            'doi': pdf_metadata.get('doi'),
            'arxiv_id': pdf_metadata.get('arxiv_id'),
            'venue': pdf_metadata.get('venue'),
            'publication_date': pdf_metadata.get('publication_date'),
            'sections': sections,
            'figures': images_list,
            'tables': tables_list,
            'references': references,
            'full_text': markdown_text
        }

        # Merge with search metadata if available
        if paper:
            merged_metadata, metadata_sources = self.metadata_merger.merge_metadata(
                search_paper=paper,
                extracted_metadata=extracted_metadata,
                extraction_confidence=None  # TODO: Add confidence scores
            )
        else:
            merged_metadata = extracted_metadata
            metadata_sources = {k: 'extracted' for k in extracted_metadata.keys()}

        # Build standardized response
        if pdf_url:
            source_id = paper_id or pdf_url.split('/')[-1].replace('.pdf', '')
            source_info = {'source_url': pdf_url}
        else:
            source_id = paper_id or Path(pdf_path).stem
            source_info = {'source_file': pdf_path}

        result = {
            'paper_id': merged_metadata.get('paper_id', source_id),
            'content_format': 'pdf',
            'full_text': merged_metadata.get('full_text', markdown_text),
            'sections': merged_metadata.get('sections', sections),
            'figures': merged_metadata.get('figures', images_list),
            'tables': merged_metadata.get('tables', tables_list),
            'references': merged_metadata.get('references', references),
            'equations': merged_metadata.get('equations', []),
            'metadata': merged_metadata,
            'metadata_sources': metadata_sources,
            'processing_info': {
                'parser': 'mistral_ocr',
                **source_info,
                'pages': len(raw_response.get('pages', [])) if isinstance(raw_response, dict) else 0
            }
        }

        return result

    async def _download_pdf(
        self,
        pdf_url: str,
        paper_id: Optional[str] = None
    ) -> str:
        """Download PDF to cache directory."""
        # Generate filename
        if paper_id:
            filename = f"{paper_id}.pdf"
        else:
            # Extract from URL
            filename = pdf_url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename = f"{hash(pdf_url)}.pdf"

        pdf_path = self.cache_dir / filename

        # Check if already cached
        if pdf_path.exists() and self.config.cache_pdfs:
            logger.info(f"Using cached PDF: {pdf_path}")
            return str(pdf_path)

        # Download PDF
        logger.info(f"Downloading PDF from: {pdf_url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as response:
                response.raise_for_status()

                # Save to file
                with open(pdf_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        logger.info(f"PDF downloaded to: {pdf_path}")
        return str(pdf_path)

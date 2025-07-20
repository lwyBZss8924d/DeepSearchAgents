#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/mistral_ocr_parser.py
# code style: PEP 8

"""
Mistral OCR parser for PaperQA2.

This module provides a PDF parser function that uses Mistral's OCR API
for enhanced document processing, compatible with PaperQA2's PDF parsing
interface.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from paperqa.types import ParsedText, ParsedMetadata
from paperqa.version import __version__ as pqa_version
from mistralai import Mistral

# Import from paper_reader
from ..paper_reader.mistral_ocr import (
    MistralOCRConfig,
    process_pdf_with_mistral
)

logger = logging.getLogger(__name__)


def create_mistral_ocr_parser(
    config: Optional[MistralOCRConfig] = None,
    extract_references: bool = True,
    extract_figures: bool = True,
    fallback_parser: Optional[Callable] = None
) -> Callable[[str | Path, int | None], ParsedText]:
    """
    Create a PDF parser function that uses Mistral OCR.

    This factory function returns a parser compatible with PaperQA2's
    PDFParserFn protocol.

    Args:
        config: Mistral OCR configuration
        extract_references: Whether to extract references
        extract_figures: Whether to extract figures/tables
        fallback_parser: Optional fallback parser if Mistral fails

    Returns:
        A PDF parser function compatible with PaperQA2
    """
    if config is None:
        config = MistralOCRConfig()

    # Initialize Mistral client
    client = Mistral(api_key=config.api_key)

    def parse_pdf_with_mistral_ocr(
        path: str | Path,
        page_size_limit: int | None = None,
        **kwargs
    ) -> ParsedText:
        """
        Parse PDF using Mistral OCR.

        Args:
            path: Path to PDF file
            page_size_limit: Maximum characters per page
            **kwargs: Additional arguments (ignored)

        Returns:
            ParsedText object for PaperQA2
        """
        path = Path(path)
        logger.info(f"Parsing PDF with Mistral OCR: {path}")

        try:
            # Process with Mistral OCR
            result = process_pdf_with_mistral(
                pdf_path=str(path),
                client=client,
                config=config
            )
            raw_response, markdown_text, images, tables = result

            if (not markdown_text or
                    len(markdown_text) < config.min_markdown_length):
                logger.warning(
                    f"Mistral OCR output too short: {len(markdown_text)} chars"
                )
                if fallback_parser:
                    logger.info("Falling back to alternative parser")
                    return fallback_parser(path, page_size_limit, **kwargs)
                else:
                    raise ValueError("Mistral OCR output insufficient")

            # Process into pages if possible
            pages_dict = _split_markdown_into_pages(
                markdown_text,
                raw_response,
                page_size_limit
            )

            # Extract metadata
            metadata_extras = {}

            # Extract references if requested
            if extract_references:
                references = _extract_references(markdown_text)
                if references:
                    metadata_extras["references"] = references
                    logger.info(f"Extracted {len(references)} references")

            # Add figure/table metadata if requested
            if extract_figures:
                if images:
                    metadata_extras["figures"] = images
                    logger.info(f"Extracted {len(images)} figures")
                if tables:
                    metadata_extras["tables"] = tables
                    logger.info(f"Extracted {len(tables)} tables")

            # Calculate total length
            total_length = sum(len(text) for text in pages_dict.values())

            # Create metadata
            metadata = ParsedMetadata(
                parsing_libraries=[f"mistral-ocr ({config.model})"],
                paperqa_version=pqa_version,
                total_parsed_text_length=total_length,
                parse_type="mistral_ocr_pdf",
                **metadata_extras
            )

            return ParsedText(content=pages_dict, metadata=metadata)

        except Exception as e:
            logger.error(f"Error in Mistral OCR parsing: {e}")
            if fallback_parser:
                logger.info("Falling back to alternative parser")
                return fallback_parser(path, page_size_limit, **kwargs)
            else:
                raise

    return parse_pdf_with_mistral_ocr


def _split_markdown_into_pages(
    markdown_text: str,
    raw_response: Dict[str, Any],
    page_size_limit: int | None
) -> Dict[str, str]:
    """
    Split markdown text into pages based on response structure.

    Args:
        markdown_text: Combined markdown text
        raw_response: Raw Mistral OCR response
        page_size_limit: Maximum characters per page

    Returns:
        Dictionary mapping page numbers to text
    """
    pages_dict = {}

    # Try to use page structure from response
    if "pages" in raw_response:
        for i, page_data in enumerate(raw_response["pages"]):
            page_text = page_data.get("markdown", "")

            if page_size_limit and len(page_text) > page_size_limit:
                raise ValueError(
                    f"Page {i+1} exceeds size limit: "
                    f"{len(page_text)} > {page_size_limit}"
                )

            pages_dict[str(i + 1)] = page_text
    else:
        # Fallback: treat entire text as one page
        if page_size_limit and len(markdown_text) > page_size_limit:
            # Split into chunks if needed
            chunk_size = page_size_limit
            for i in range(0, len(markdown_text), chunk_size):
                chunk = markdown_text[i:i + chunk_size]
                pages_dict[str(i // chunk_size + 1)] = chunk
        else:
            pages_dict["1"] = markdown_text

    return pages_dict


def _extract_references(text: str) -> List[Dict[str, str]]:
    """
    Extract references from paper text.

    Args:
        text: Paper text

    Returns:
        List of reference dictionaries
    """
    references = []

    # Look for references section
    ref_patterns = [
        r"(?i)\n\s*references\s*\n",
        r"(?i)\n\s*bibliography\s*\n",
        r"(?i)\n\s*works cited\s*\n"
    ]

    ref_start = -1
    for pattern in ref_patterns:
        match = re.search(pattern, text)
        if match:
            ref_start = match.end()
            break

    if ref_start == -1:
        logger.debug("No references section found")
        return references

    # Extract reference text
    ref_text = text[ref_start:]

    # Split into individual references
    ref_lines = ref_text.split('\n')
    current_ref = []

    for line in ref_lines:
        line = line.strip()
        if not line:
            continue

        # Check if this starts a new reference
        if re.match(r'^(\[\d+\]|\d+\.|\d+\))', line):
            if current_ref:
                # Save previous reference
                ref_text = ' '.join(current_ref)
                references.append({
                    "text": ref_text,
                    "type": "reference"
                })
            current_ref = [line]
        else:
            # Continue current reference
            current_ref.append(line)

    # Don't forget the last reference
    if current_ref:
        ref_text = ' '.join(current_ref)
        references.append({
            "text": ref_text,
            "type": "reference"
        })

    return references


# For backward compatibility, create a default parser
default_mistral_parser = create_mistral_ocr_parser()

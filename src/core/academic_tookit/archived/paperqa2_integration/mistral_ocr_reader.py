#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/mistral_ocr_reader.py
# code style: PEP 8

"""
Mistral OCR reader for PaperQA2.

This module provides a custom PDF reader that uses Mistral's OCR API
for enhanced document processing, including reference extraction and
figure/table analysis.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
import fitz  # PyMuPDF

from paperqa import Doc, Text
from mistralai import Mistral

from ..paper_reader.mistral_ocr import (
    MistralOCRConfig,
    process_pdf_with_mistral
)

logger = logging.getLogger(__name__)


class MistralOCRReader:
    """
    Custom PDF reader using Mistral OCR for PaperQA2.

    This reader:
    - Uses Mistral OCR for accurate text extraction
    - Extracts references and citations
    - Identifies figures and tables with annotations
    - Provides structured document analysis
    - Falls back to standard PDF parsing if needed
    """

    def __init__(
        self,
        config: Optional[MistralOCRConfig] = None,
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        extract_references: bool = True,
        extract_figures: bool = True
    ):
        """
        Initialize Mistral OCR reader.

        Args:
            config: Mistral OCR configuration
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            extract_references: Whether to extract references
            extract_figures: Whether to extract figures/tables
        """
        self.config = config or MistralOCRConfig()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.extract_references = extract_references
        self.extract_figures = extract_figures

        # Initialize Mistral client
        self.client = Mistral(api_key=self.config.api_key)

        logger.info("Initialized MistralOCRReader")

    async def parse(
        self,
        doc_path: Path,
        doc: Doc,
        **kwargs
    ) -> List[Text]:
        """
        Parse PDF using Mistral OCR.

        Args:
            doc_path: Path to PDF file
            doc: PaperQA2 Doc object
            **kwargs: Additional arguments

        Returns:
            List of Text chunks for PaperQA2
        """
        logger.info(f"Parsing PDF with Mistral OCR: {doc_path}")

        try:
            # Process PDF with Mistral
            result = await self._process_with_mistral(doc_path)

            if not result:
                logger.warning(
                    "Mistral OCR returned no content, "
                    "falling back to standard parsing"
                )
                return await self._fallback_parse(doc_path, doc)

            # Extract components
            markdown_text = result.get("markdown", "")
            metadata = result.get("metadata", {})

            # Process references if requested
            if self.extract_references:
                references = await self._extract_references(
                    markdown_text,
                    metadata
                )
                # Store references in doc metadata
                if references:
                    doc.metadata = doc.metadata or {}
                    doc.metadata["references"] = references

            # Process figures/tables if requested
            if self.extract_figures:
                figures = metadata.get("images", [])
                tables = metadata.get("tables", [])
                if figures or tables:
                    doc.metadata = doc.metadata or {}
                    doc.metadata["figures"] = figures
                    doc.metadata["tables"] = tables

            # Chunk the text
            chunks = self._chunk_text(markdown_text)

            # Convert to PaperQA2 Text objects
            texts = []
            for i, chunk in enumerate(chunks):
                text_obj = Text(
                    text=chunk,
                    doc=doc,
                    chunk_id=i,
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "source": "mistral_ocr"
                    }
                )
                texts.append(text_obj)

            logger.info(
                f"Successfully parsed PDF into {len(texts)} chunks"
            )

            return texts

        except Exception as e:
            logger.error(f"Error in Mistral OCR parsing: {e}")
            # Fall back to standard parsing
            return await self._fallback_parse(doc_path, doc)

    async def parse_url(
        self,
        url: str,
        doc: Doc,
        **kwargs
    ) -> List[Text]:
        """
        Parse PDF from URL using Mistral OCR.

        Args:
            url: URL to PDF or HTML paper
            doc: PaperQA2 Doc object
            **kwargs: Additional arguments

        Returns:
            List of Text chunks
        """
        # Download to temporary file
        temp_path = await self._download_to_temp(url)

        try:
            # Parse the downloaded file
            return await self.parse(temp_path, doc, **kwargs)
        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()

    async def _process_with_mistral(
        self,
        pdf_path: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Process PDF with Mistral OCR.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Processing result or None if failed
        """
        try:
            # Use the existing Mistral OCR function
            raw_response, markdown, images, tables = await process_pdf_with_mistral(
                pdf_path=str(pdf_path),
                client=self.client,
                config=self.config
            )

            # Validate output
            if not markdown or len(markdown) < self.config.min_markdown_length:
                logger.warning(
                    f"Mistral OCR output too short: {len(markdown)} chars"
                )
                return None

            return {
                "markdown": markdown,
                "metadata": {
                    "images": images,
                    "tables": tables,
                    "raw_response": raw_response
                }
            }

        except Exception as e:
            logger.error(f"Mistral OCR processing failed: {e}")
            return None

    async def _extract_references(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Extract references from paper text.

        Args:
            text: Paper text
            metadata: OCR metadata

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
            import re
            match = re.search(pattern, text)
            if match:
                ref_start = match.end()
                break

        if ref_start == -1:
            logger.info("No references section found")
            return references

        # Extract reference text
        ref_text = text[ref_start:]

        # Split into individual references
        # Look for patterns like [1], 1., or similar
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

        logger.info(f"Extracted {len(references)} references")

        return references

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # If paragraph is too large, split it
            if para_size > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split large paragraph
                words = para.split()
                temp_chunk = []
                temp_size = 0

                for word in words:
                    word_size = len(word) + 1  # +1 for space
                    if temp_size + word_size > self.chunk_size:
                        if temp_chunk:
                            chunks.append(' '.join(temp_chunk))
                        temp_chunk = [word]
                        temp_size = word_size
                    else:
                        temp_chunk.append(word)
                        temp_size += word_size

                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))

            # Normal paragraph
            elif current_size + para_size > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for \n\n

        # Don't forget the last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Get overlap from previous chunk
                    prev_words = chunks[i-1].split()
                    overlap_words = prev_words[-self.chunk_overlap:]
                    chunk = ' '.join(overlap_words) + '\n\n' + chunk
                overlapped_chunks.append(chunk)
            chunks = overlapped_chunks

        return chunks

    async def _fallback_parse(
        self,
        doc_path: Path,
        doc: Doc
    ) -> List[Text]:
        """
        Fallback to standard PDF parsing.

        Args:
            doc_path: Path to PDF
            doc: Doc object

        Returns:
            List of Text chunks
        """
        logger.info("Using fallback PDF parsing with PyMuPDF")

        try:
            # Use PyMuPDF directly
            pdf_doc = fitz.open(doc_path)

            texts = []
            for page_num, page in enumerate(pdf_doc):
                # Extract text from page
                page_text = page.get_text()

                if page_text.strip():
                    # Create Text object for page
                    text_obj = Text(
                        text=page_text,
                        doc=doc,
                        chunk_id=page_num,
                        metadata={
                            "page": page_num + 1,
                            "source": "pymupdf_fallback"
                        }
                    )
                    texts.append(text_obj)

            pdf_doc.close()

            return texts

        except Exception as e:
            logger.error(f"Fallback parsing also failed: {e}")
            # Return empty list as last resort
            return []

    async def _download_to_temp(self, url: str) -> Path:
        """
        Download URL content to temporary file.

        Args:
            url: URL to download

        Returns:
            Path to temporary file
        """
        # Create temporary file
        suffix = ".pdf" if url.endswith('.pdf') else ".html"
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        )
        temp_path = Path(temp_file.name)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    # Write content
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

            return temp_path

        except Exception as e:
            # Clean up on error
            if temp_path.exists():
                temp_path.unlink()
            raise

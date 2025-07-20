#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_reader/paper_parser_pdf.py
# code style: PEP 8

"""
PDF Parser using Mistral OCR API.

This module provides PDF parsing capabilities specifically designed for
academic papers, using Mistral OCR API for structured extraction.
"""

import os
import logging
import base64
import re
import mimetypes
import fitz  # PyMuPDF pymupdf library
import aiohttp
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional

from pydantic import BaseModel, Field
from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type
)


@dataclass
class PDFParserConfig:
    """Configuration for PDF parsing using Mistral OCR."""

    api_key: str = field(
        default_factory=lambda: os.getenv("MISTRAL_API_KEY", "")
    )
    model: str = "mistral-ocr-latest"
    max_pages: int = 1000
    timeout: int = 1000
    include_image_base64: bool = True
    retry_attempts: int = 3
    fallback_to_docling: bool = True
    min_markdown_length: int = 500
    min_token_ratio: float = 0.05
    use_direct_url: bool = True  # Use direct URL when available
    download_fallback: bool = True  # Fall back to download if URL fails
    max_pages_with_annotations: int = 8  # Mistral API limit for document annotations
    use_bbox_only_for_large_docs: bool = True  # Use only bbox annotations for docs > 8 pages
    check_page_count_for_urls: bool = True  # Check page count before processing URLs


# Comprehensive schema definitions for Mistral OCR structured extraction

class Author(BaseModel):
    """Author information schema."""
    name: str = Field(description="Author full name")
    affiliation: str = Field(
        default="", description="Author's institution or organization"
    )
    email: str = Field(
        default="", description="Author's email address if available"
    )


class Section(BaseModel):
    """Paper section schema."""
    level: int = Field(
        description="Heading level (1-6, where 1 is top-level)"
    )
    title: str = Field(description="Section title")
    content: str = Field(description="Section content text")
    subsections: List['Section'] = Field(
        default_factory=list,
        description="Nested subsections"
    )


class Reference(BaseModel):
    """Bibliography reference schema."""
    id: str = Field(description="Reference ID or number")
    title: str = Field(description="Paper or book title")
    authors: str = Field(description="Author names as a string")
    year: str = Field(default="", description="Publication year")
    venue: str = Field(
        default="", description="Journal, conference, or publisher"
    )
    doi: str = Field(default="", description="DOI if available")
    url: str = Field(default="", description="URL if available")
    arxiv_id: str = Field(default="", description="arXiv ID if available")


class Figure(BaseModel):
    """Figure information schema."""
    id: str = Field(description="Figure number or ID (e.g., 'Figure 1')")
    caption: str = Field(description="Complete figure caption")
    referenced_in_sections: List[str] = Field(
        default_factory=list,
        description="Section titles where this figure is referenced"
    )


class Table(BaseModel):
    """Table information schema."""
    id: str = Field(description="Table number or ID (e.g., 'Table 1')")
    caption: str = Field(description="Complete table caption")
    headers: List[str] = Field(
        default_factory=list,
        description="Column headers"
    )
    rows: List[List[str]] = Field(
        default_factory=list,
        description="Table data rows"
    )


class Equation(BaseModel):
    """Mathematical equation schema."""
    id: str = Field(description="Equation number or ID")
    latex: str = Field(description="LaTeX representation of the equation")
    description: str = Field(
        default="",
        description="Description or context of the equation"
    )


class PublicationInfo(BaseModel):
    """Publication metadata schema."""
    venue: str = Field(
        default="", description="Publication venue (journal/conference)"
    )
    year: str = Field(default="", description="Publication year")
    volume: str = Field(default="", description="Volume number")
    issue: str = Field(default="", description="Issue number")
    pages: str = Field(default="", description="Page numbers")
    doi: str = Field(default="", description="Digital Object Identifier")
    arxiv_id: str = Field(default="", description="arXiv identifier")
    pmid: str = Field(default="", description="PubMed ID if applicable")


class DocumentAnnotation(BaseModel):
    """Comprehensive document-level annotation schema for academic papers."""
    title: str = Field(description="Paper title")
    authors: List[Author] = Field(
        description="List of authors with their details"
    )
    abstract: str = Field(description="Paper abstract")
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords or key phrases"
    )
    sections: List[Section] = Field(
        description="All paper sections with hierarchical structure"
    )
    references: List[Reference] = Field(
        default_factory=list,
        description="Bibliography references"
    )
    figures: List[Figure] = Field(
        default_factory=list,
        description="All figures in the paper"
    )
    tables: List[Table] = Field(
        default_factory=list,
        description="All tables in the paper"
    )
    equations: List[Equation] = Field(
        default_factory=list,
        description="Key mathematical equations"
    )
    publication_info: PublicationInfo = Field(
        default_factory=PublicationInfo,
        description="Publication metadata"
    )


# Enable forward references for nested models
Section.model_rebuild()


class BBoxAnnotation(BaseModel):
    """Unified bounding box annotation for all visual elements."""
    bbox_type: str = Field(
        description="Type: figure|table|equation|chart|diagram|algorithm"
    )
    caption: str = Field(description="Caption or title of the element")
    number: str = Field(
        default="",
        description="Element number (e.g., '1', '2a', 'A.1')"
    )
    # Table-specific fields
    headers: List[str] = Field(
        default_factory=list,
        description="Column headers if bbox_type is table"
    )
    data_summary: str = Field(
        default="",
        description="Brief description of the content"
    )
    # Equation-specific fields
    latex: str = Field(
        default="",
        description="LaTeX representation if bbox_type is equation"
    )


logger = logging.getLogger(__name__)


class PDFParserError(Exception):
    """Custom exception for PDF parsing errors."""
    pass


class MistralAPIError(Exception):
    """Custom exception for Mistral API errors."""
    pass


async def _download_and_check_pdf_page_count(
    pdf_url: str,
    timeout: int = 30
) -> Tuple[bytes, int]:
    """
    Download PDF and check page count.
    
    Args:
        pdf_url: URL of the PDF to download
        timeout: Download timeout in seconds
        
    Returns:
        Tuple of (pdf_bytes, page_count)
        
    Raises:
        ConnectionError: If download fails
        PDFParserError: If PDF cannot be parsed
    """
    logger.info(f"Downloading PDF from {pdf_url} to check page count")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                pdf_url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                response.raise_for_status()
                pdf_bytes = await response.read()
        
        # Check page count using PyMuPDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        logger.info(f"PDF from {pdf_url} has {page_count} pages")
        return pdf_bytes, page_count
        
    except aiohttp.ClientError as e:
        logger.error(f"Failed to download PDF from {pdf_url}: {e}")
        raise ConnectionError(f"Failed to download PDF: {e}")
    except (fitz.FileDataError, fitz.EmptyFileError) as e:
        logger.error(f"Failed to parse PDF from {pdf_url}: {e}")
        raise PDFParserError(f"Failed to parse PDF: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading PDF from {pdf_url}: {e}")
        raise


@retry(
    wait=wait_exponential(min=4, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((MistralAPIError, ConnectionError))
)
async def parse_pdf_with_ocr(
    pdf_path: Optional[str] = None,
    pdf_url: Optional[str] = None,
    pdf_base64: Optional[str] = None,
    client: Optional[Mistral] = None,
    config: Optional[PDFParserConfig] = None,
    filename_for_logging: str = "unnamed_pdf",
    extract_metadata: bool = True
) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse PDF document using Mistral OCR API with chunking support.

    Args:
        pdf_path: Path to the PDF file
        pdf_url: Direct URL to the PDF (avoids download)
        pdf_base64: Base64 encoded PDF string
        client: Optional Mistral client instance
        config: Optional PDFParserConfig instance
        filename_for_logging: Filename for logging purposes
        extract_metadata: Whether to extract structured metadata

    Returns:
        Tuple containing:
            - raw_response: The raw JSON response from Mistral API
            - markdown_text: Combined markdown from all pages
            - images_list: List of extracted image metadata
            - tables_list: List of extracted table metadata
            - metadata: Document metadata (title, authors, etc.)

    Raises:
        ValueError: If none of pdf_path, pdf_url, or pdf_base64 is provided
        PDFParserError: If PDF parsing fails after retries
    """
    if not config:
        config = PDFParserConfig()

    if not client:
        if not config.api_key:
            logger.warning(
                "MISTRAL_API_KEY not set. PDF parsing requires Mistral API. "
                "Get your API key from https://mistral.ai/"
            )
            raise ValueError(
                "MISTRAL_API_KEY must be set in PDFParserConfig "
                "or as environment variable. Get your API key from "
                "https://mistral.ai/"
            )
        client = Mistral(api_key=config.api_key)

    if not pdf_path and not pdf_url and not pdf_base64:
        raise ValueError(
            "At least one of pdf_path, pdf_url, or pdf_base64 "
            "must be provided."
        )

    pdf_doc: Optional[fitz.Document] = None
    pdf_bytes_from_url: Optional[bytes] = None
    page_count_from_url: Optional[int] = None
    
    try:
        # If URL is provided and direct URL is enabled
        if pdf_url and config.use_direct_url:
            filename_for_logging = (
                pdf_url.split('/')[-1] or filename_for_logging
            )
            
            # Check if we should download to check page count
            if config.check_page_count_for_urls and extract_metadata:
                try:
                    pdf_bytes_from_url, page_count_from_url = (
                        await _download_and_check_pdf_page_count(pdf_url)
                    )
                    logger.info(
                        f"PDF from URL has {page_count_from_url} pages. "
                        f"Will process with appropriate annotation settings."
                    )
                    # Process with known page count
                    pdf_doc = fitz.open(
                        stream=pdf_bytes_from_url, filetype="pdf"
                    )
                    # Convert bytes to base64 for processing
                    pdf_base64_from_url = base64.b64encode(
                        pdf_bytes_from_url
                    ).decode('utf-8')
                    return await _process_single_pdf(
                        pdf_doc, None, None, pdf_base64_from_url, client, config,
                        filename_for_logging, extract_metadata,
                        page_count_override=page_count_from_url
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to check page count for URL {pdf_url}: {e}. "
                        f"Falling back to direct URL processing without "
                        f"document annotations."
                    )
                    # Fall back to direct URL without document annotations
                    return await _process_single_pdf(
                        None, None, pdf_url, None, client, config,
                        filename_for_logging, extract_metadata,
                        force_bbox_only=True
                    )
            else:
                # Direct URL processing without page count check
                logger.info(
                    f"Processing PDF directly from URL: {pdf_url}"
                )
                # Default to bbox-only for safety when not checking page count
                return await _process_single_pdf(
                    None, None, pdf_url, None, client, config,
                    filename_for_logging, extract_metadata,
                    force_bbox_only=(not config.check_page_count_for_urls)
                )

        # Otherwise, we need PyMuPDF to process the PDF
        if pdf_path:
            filename_for_logging = pdf_path
            pdf_doc = fitz.open(pdf_path)
        elif pdf_base64:
            filename_for_logging = filename_for_logging or "base64_pdf"
            pdf_doc = fitz.open(
                stream=base64.b64decode(pdf_base64), filetype="pdf"
            )
        else:
            raise ValueError(
                "Either pdf_path or pdf_base64 must be provided "
                "when not using direct URL."
            )

        page_count = len(pdf_doc)

        # Determine max pages per chunk based on whether we need annotations
        effective_max_pages = min(config.max_pages, config.max_pages_with_annotations) if extract_metadata else config.max_pages

        logger.info(
            f"PDF '{filename_for_logging}' has {page_count} pages. "
            f"Max pages per chunk: {effective_max_pages}."
        )

        if page_count > effective_max_pages:
            return await _process_large_pdf_chunks(
                pdf_doc, page_count, client, config, filename_for_logging,
                extract_metadata
            )
        else:
            return await _process_single_pdf(
                pdf_doc, pdf_path, None, pdf_base64, client, config,
                filename_for_logging, extract_metadata
            )

    except (fitz.FileDataError, fitz.FileNotFoundError,
            fitz.EmptyFileError) as f_err:
        logger.error(
            f"PyMuPDF (fitz) error while processing "
            f"'{filename_for_logging}': {f_err}"
        )
        raise PDFParserError(
            f"PyMuPDF error processing '{filename_for_logging}': {f_err}"
        )
    except Exception as fitz_err:
        # Catch any other fitz-related errors
        if ('fitz' in str(type(fitz_err)).lower() or
                'mupdf' in str(fitz_err).lower()):
            logger.error(
                f"PyMuPDF (fitz) error while processing "
                f"'{filename_for_logging}': {fitz_err}"
            )
            raise PDFParserError(
                f"PyMuPDF error processing "
                f"'{filename_for_logging}': {fitz_err}"
            )
        # Re-raise if not a fitz error
        raise
    except Exception as e:
        logger.error(
            f"Error during Mistral OCR processing "
            f"for '{filename_for_logging}': {e}"
        )
        if "timeout" in str(e).lower():
            raise ConnectionError(
                f"Mistral API request timed out "
                f"for '{filename_for_logging}': {e}"
            )
        elif not isinstance(e, (
            MistralAPIError, PDFParserError, ConnectionError, ValueError
        )):
            raise MistralAPIError(
                f"Mistral API call failed for '{filename_for_logging}': {e}"
            )
        raise
    finally:
        if pdf_doc:
            pdf_doc.close()


async def _process_large_pdf_chunks(
    pdf_doc: fitz.Document,
    page_count: int,
    client: Mistral,
    config: PDFParserConfig,
    filename_for_logging: str,
    extract_metadata: bool = True
) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process large PDF by splitting into chunks with intelligent
    metadata extraction.

    Returns:
        Tuple containing:
            - raw_response: Combined response dict with chunks
            - markdown_text: Combined markdown from all pages
            - images_list: List of all extracted images
            - tables_list: List of all extracted tables
            - metadata: Combined document metadata
    """
    logger.info(
        f"PDF '{filename_for_logging}' has {page_count} pages. "
        f"Processing in chunks of {config.max_pages} pages."
    )

    all_raw_responses = []
    all_markdown_parts = []

    # Initialize combined metadata structure
    combined_metadata = {
        'title': '',
        'authors': [],
        'abstract': '',
        'keywords': [],
        'sections': [],
        'references': [],
        'figures': [],
        'tables': [],
        'equations': [],
        'publication_info': {}
    }

    # Determine strategic chunks for metadata extraction
    # First pages: title, authors, abstract, introduction
    # Last pages: references, appendices
    # Middle chunks: main content sections

    # Use annotation limit for chunk size
    chunk_size = config.max_pages_with_annotations if extract_metadata else config.max_pages

    chunks_to_process = []

    # First chunk (up to chunk_size pages)
    first_chunk_end = min(chunk_size - 1, page_count - 1)
    chunks_to_process.append((0, first_chunk_end, 'first'))

    # Last chunk (last chunk_size pages) if document is large enough
    if page_count > chunk_size:
        last_chunk_start = max(page_count - chunk_size, first_chunk_end + 1)
        if last_chunk_start > first_chunk_end:
            chunks_to_process.append(
                (last_chunk_start, page_count - 1, 'last')
            )

    # Middle chunks if needed
    if page_count > chunk_size * 2:
        # Process middle sections
        middle_start = first_chunk_end + 1
        middle_end = page_count - chunk_size - 1
        for i in range(middle_start, middle_end, chunk_size):
            chunk_end = min(i + chunk_size - 1, middle_end)
            chunks_to_process.append((i, chunk_end, 'middle'))

    # Process each chunk
    for chunk_idx, (start_page, end_page, chunk_type) in enumerate(
        chunks_to_process
    ):
        logger.info(
            f"Processing {chunk_type} chunk {chunk_idx + 1}/"
            f"{len(chunks_to_process)} for '{filename_for_logging}': "
            f"pages {start_page + 1}-{end_page + 1}"
        )

        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(pdf_doc, from_page=start_page, to_page=end_page)

        chunk_base64 = base64.b64encode(chunk_doc.tobytes()).decode('utf-8')
        chunk_doc.close()

        chunk_filename = (
            f"{filename_for_logging}_chunk_{start_page+1}-"
            f"{end_page+1}_{chunk_type}"
        )

        # Note: parse_pdf_with_ocr can be called recursively
        # Ensure we handle the response properly
        result = await parse_pdf_with_ocr(
            pdf_base64=chunk_base64,
            client=client,
            config=config,
            filename_for_logging=chunk_filename,
            extract_metadata=True  # Always extract for all chunks
        )

        if len(result) == 5:
            raw_res_chunk, md_chunk, images_chunk, tables_chunk, meta_chunk = result
        else:
            logger.error(
                f"Unexpected result format from parse_pdf_with_ocr for "
                f"{chunk_filename}: {len(result)} elements"
            )
            continue

        all_raw_responses.append(raw_res_chunk)
        all_markdown_parts.append(md_chunk)

        # Merge metadata based on chunk type
        if chunk_type == 'first':
            # First chunk has title, authors, abstract, introduction
            combined_metadata['title'] = meta_chunk.get('title', '')
            combined_metadata['authors'] = meta_chunk.get('authors', [])
            combined_metadata['abstract'] = meta_chunk.get('abstract', '')
            combined_metadata['keywords'] = meta_chunk.get('keywords', [])
            combined_metadata['publication_info'] = meta_chunk.get(
                'publication_info', {}
            )

            # Add early sections
            for section in meta_chunk.get('sections', []):
                section_title = section.get('title', '').lower()
                if section_title in [
                    'introduction', 'background', 'related work'
                ]:
                    combined_metadata['sections'].append(section)

        elif chunk_type == 'last':
            # Last chunk has references and appendices
            combined_metadata['references'].extend(
                meta_chunk.get('references', [])
            )

            # Add concluding sections
            for section in meta_chunk.get('sections', []):
                section_title = section.get('title', '').lower()
                if section_title in [
                    'conclusion', 'references', 'appendix', 'acknowledgments'
                ]:
                    combined_metadata['sections'].append(section)

        else:
            # Middle chunks have main content sections
            combined_metadata['sections'].extend(
                meta_chunk.get('sections', [])
            )

        # Always merge figures and tables (adjust page numbers)
        for fig in meta_chunk.get('figures', []):
            if 'page_number' in fig:
                fig['page_number'] += start_page
            combined_metadata['figures'].append(fig)

        for tbl in meta_chunk.get('tables', []):
            if 'page_number' in tbl:
                tbl['page_number'] += start_page
            combined_metadata['tables'].append(tbl)

        # Merge equations
        combined_metadata['equations'].extend(meta_chunk.get('equations', []))

    combined_markdown = "\n\n".join(all_markdown_parts)
    logger.info(
        f"Finished processing all chunks for '{filename_for_logging}'. "
        f"Extracted {len(combined_metadata['sections'])} sections, "
        f"{len(combined_metadata['references'])} references."
    )

    # Extract figures and tables lists from combined metadata
    figures_list = combined_metadata.get('figures', [])
    tables_list = combined_metadata.get('tables', [])

    return (
        {"chunks": all_raw_responses},
        combined_markdown,
        figures_list,
        tables_list,
        combined_metadata
    )


async def _process_single_pdf(
    pdf_doc: Optional[fitz.Document],
    pdf_path: Optional[str],
    pdf_url: Optional[str],
    pdf_base64: Optional[str],
    client: Mistral,
    config: PDFParserConfig,
    filename_for_logging: str,
    extract_metadata: bool = True,
    page_count_override: Optional[int] = None,
    force_bbox_only: bool = False
) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process a single PDF using Mistral's structured extraction.

    Args:
        pdf_doc: PyMuPDF document object (optional)
        pdf_path: Path to PDF file (optional)
        pdf_url: Direct URL to PDF (optional)
        pdf_base64: Base64 encoded PDF (optional)
        client: Mistral API client
        config: Parser configuration
        filename_for_logging: Filename for logging
        extract_metadata: Whether to extract metadata (always True currently)
        page_count_override: Override page count (used when already known)
        force_bbox_only: Force using bbox-only annotations

    Returns:
        Tuple containing:
            - response_dict: The raw JSON response from Mistral API
            - markdown_text: Combined markdown from all pages
            - images_list: List of extracted image metadata
            - tables_list: List of extracted table metadata
            - metadata: Document metadata (title, authors, etc.)
    """
    # Prepare document input
    if pdf_url:
        logger.info(
            f"Processing PDF '{filename_for_logging}' directly from URL: "
            f"{pdf_url}"
        )
        document_input = {
            "type": "document_url",
            "document_url": pdf_url
        }
    else:
        # Handle base64 or file path
        if pdf_base64:
            logger.info(
                f"Processing PDF '{filename_for_logging}' from base64 string."
            )
            current_pdf_base64 = pdf_base64
            current_content_type = "application/pdf"
        elif pdf_path and pdf_doc:
            logger.info(f"Processing PDF from path: {pdf_path}")
            pdf_bytes = pdf_doc.tobytes()
            current_pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            current_content_type = (
                mimetypes.guess_type(pdf_path)[0] or "application/pdf"
            )
        else:
            raise ValueError(
                "No PDF input available for processing."
            )

        document_input = {
            "type": "document_url",
            "document_url": (
                f"data:{current_content_type};base64,{current_pdf_base64}"
            )
        }

    logger.info(
        f"Sending request to Mistral OCR API for '{filename_for_logging}' "
        f"(model: {config.model}, timeout: {config.timeout}s)"
    )

    # Determine if we should use document annotations based on page count
    # For direct URL processing, we can't know page count in advance
    use_document_annotations = extract_metadata and not force_bbox_only

    # Use override page count if provided, otherwise check PDF doc
    if page_count_override is not None:
        page_count = page_count_override
    elif pdf_doc:
        page_count = len(pdf_doc)
    else:
        page_count = None

    # Check if we should use bbox only based on page count
    if page_count is not None and extract_metadata:
        if page_count > config.max_pages_with_annotations and config.use_bbox_only_for_large_docs:
            logger.info(
                f"PDF has {page_count} pages, exceeding Mistral annotation limit of "
                f"{config.max_pages_with_annotations}. Using bbox annotations only."
            )
            use_document_annotations = False
    elif force_bbox_only:
        logger.info(
            f"Using bbox annotations only for '{filename_for_logging}' "
            f"(forced due to unknown page count or configuration)."
        )
        use_document_annotations = False

    request_params = {
        "model": config.model,
        "document": document_input,
        "include_image_base64": config.include_image_base64,
        "timeout_ms": config.timeout * 1000,
    }

    # Add structured extraction formats based on page count
    if extract_metadata:
        request_params["bbox_annotation_format"] = (
            response_format_from_pydantic_model(BBoxAnnotation)
        )
        if use_document_annotations:
            request_params["document_annotation_format"] = (
                response_format_from_pydantic_model(DocumentAnnotation)
            )

    response = client.ocr.process(**request_params)

    if not response or not response.pages:
        logger.error(
            f"Mistral OCR response is empty or invalid "
            f"for '{filename_for_logging}'."
        )
        raise MistralAPIError("Mistral OCR response is empty or invalid.")

    logger.info(
        f"Successfully received response from Mistral OCR "
        f"for '{filename_for_logging}'."
    )

    # Extract markdown text
    markdown_text = "\n\n".join([
        page.markdown for page in response.pages if page.markdown
    ])

    # Validate response
    if not _is_mistral_response_valid(
        response, markdown_text, config, filename_for_logging
    ):
        raise MistralAPIError(
            f"Mistral OCR output failed validation "
            f"for '{filename_for_logging}'."
        )

    # Extract structured metadata from document annotation
    metadata: Dict[str, Any] = {}
    if (hasattr(response, 'document_annotation') and
            response.document_annotation):
        doc_ann = response.document_annotation

        # Handle different possible types for document_annotation
        if isinstance(doc_ann, dict):
            # Ensure it's a proper Dict[str, Any]
            metadata = {str(k): v for k, v in doc_ann.items()}
        elif isinstance(doc_ann, DocumentAnnotation):
            # It's our Pydantic model
            metadata = doc_ann.model_dump()
        elif hasattr(doc_ann, 'model_dump') and callable(getattr(doc_ann, 'model_dump', None)):
            # It's some other Pydantic model
            metadata = doc_ann.model_dump()
        elif hasattr(doc_ann, 'dict') and callable(getattr(doc_ann, 'dict', None)):
            # Older Pydantic model
            metadata = doc_ann.dict()
        else:
            # Try to convert to dict if it's a different type
            try:
                if hasattr(doc_ann, '__dict__'):
                    # Object with attributes
                    metadata = vars(doc_ann)
                else:
                    # Try dict conversion
                    temp_dict = dict(doc_ann)  # type: ignore
                    # Ensure string keys
                    metadata = {str(k): v for k, v in temp_dict.items()}
            except (TypeError, ValueError):
                logger.warning(
                    f"Could not convert document annotation to dict for "
                    f"'{filename_for_logging}'. Type: {type(doc_ann)}"
                )
                metadata = {}

        if metadata:
            logger.info(
                f"Extracted structured metadata for '{filename_for_logging}': "
                f"title='{metadata.get('title', 'N/A')}', "
                f"authors={len(metadata.get('authors', []))}, "
                f"sections={len(metadata.get('sections', []))}, "
                f"references={len(metadata.get('references', []))}"
            )
    else:
        logger.warning(
            f"No document annotation found for '{filename_for_logging}'. "
            "Metadata will be empty."
        )

    # Process bbox annotations to enhance figures and tables
    if hasattr(response, 'pages'):
        enhanced_figures, enhanced_tables = process_bbox_annotations(response)

        # Merge bbox data into metadata
        if 'figures' in metadata:
            # Enhance existing figures with bbox data
            figures_list = metadata.get('figures', [])
            if isinstance(figures_list, list):
                for fig in figures_list:
                    if isinstance(fig, dict):
                        for bbox_fig in enhanced_figures:
                            if similar_caption(
                                fig.get('caption', ''),
                                bbox_fig.get('caption', '')
                            ):
                                fig.update(bbox_fig)
                                break
        else:
            metadata['figures'] = enhanced_figures

        if 'tables' in metadata:
            # Enhance existing tables with bbox data
            tables_list = metadata.get('tables', [])
            if isinstance(tables_list, list):
                for tbl in tables_list:
                    if isinstance(tbl, dict):
                        for bbox_tbl in enhanced_tables:
                            if similar_caption(
                                tbl.get('caption', ''),
                                bbox_tbl.get('caption', '')
                            ):
                                tbl.update(bbox_tbl)
                                break
        else:
            metadata['tables'] = enhanced_tables

    # Convert response to dict
    response_dict: Dict[str, Any] = {}
    if hasattr(response, 'model_dump'):
        response_dict = response.model_dump()
    elif hasattr(response, 'dict'):
        # Fallback for older versions
        response_dict = response.dict()
    else:
        # If response is already a dict or has pages attribute
        if isinstance(response, dict):
            response_dict = response
        elif hasattr(response, 'pages'):
            # Create a minimal response dict with pages
            response_dict = {
                'pages': [
                    {
                        'markdown': page.markdown if hasattr(page, 'markdown') else '',
                        'images': getattr(page, 'images', [])
                    }
                    for page in response.pages
                ]
            }

    # Extract figures and tables lists from metadata
    figures_list = metadata.get('figures', [])
    tables_list = metadata.get('tables', [])

    return response_dict, markdown_text, figures_list, tables_list, metadata


# Asset adjustment functions removed - handled in structured extraction


def process_bbox_annotations(
    response: Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process bbox annotations from Mistral response to extract enhanced
    figure and table information.
    """
    figures = []
    tables = []

    if not hasattr(response, 'pages'):
        return figures, tables

    for page_idx, page in enumerate(response.pages):
        if not hasattr(page, 'images'):
            continue

        for img in page.images:
            # Get the bbox annotation if available
            bbox_ann = getattr(img, 'bbox_annotation', None)
            if not bbox_ann:
                continue

            # Extract base64 image data if available
            image_data = None
            if hasattr(img, 'image_base64') and img.image_base64:
                try:
                    image_data = base64.b64decode(img.image_base64)
                except Exception as e:
                    logger.warning(f"Failed to decode image base64: {e}")

            # Calculate dimensions
            width = img.bottom_right_x - img.top_left_x
            height = img.bottom_right_y - img.top_left_y

            # Create base entry
            entry = {
                "page_number": page_idx + 1,
                "bbox": [
                    img.top_left_x,
                    img.top_left_y,
                    img.bottom_right_x,
                    img.bottom_right_y
                ],
                "width": width,
                "height": height,
                "data": image_data
            }

            # Process based on bbox type
            if bbox_ann.bbox_type == "table":
                entry.update({
                    "id": (f"Table {bbox_ann.number}" if bbox_ann.number
                           else f"Table {len(tables) + 1}"),
                    "caption": bbox_ann.caption,
                    "headers": bbox_ann.headers if bbox_ann.headers else [],
                    "data_summary": bbox_ann.data_summary
                })
                tables.append(entry)
            elif bbox_ann.bbox_type in ["figure", "chart", "diagram"]:
                entry.update({
                    "id": (f"Figure {bbox_ann.number}" if bbox_ann.number
                            else f"Figure {len(figures) + 1}"),
                    "caption": bbox_ann.caption,
                    "type": bbox_ann.bbox_type,
                    "data_summary": bbox_ann.data_summary
                })
                figures.append(entry)
            elif bbox_ann.bbox_type == "equation":
                # Store equation separately if needed
                entry.update({
                    "id": (f"Equation {bbox_ann.number}" if bbox_ann.number
                             else f"Equation {page_idx + 1}"),
                    "latex": bbox_ann.latex,
                    "caption": bbox_ann.caption
                })
                # Could add to a separate equations list if needed

    return figures, tables


def similar_caption(cap1: str, cap2: str, threshold: float = 0.8) -> bool:
    """
    Check if two captions are similar enough to be the same element.
    Simple implementation - can be enhanced with better similarity metrics.
    """
    if not cap1 or not cap2:
        return False

    # Normalize captions
    cap1_norm = cap1.lower().strip()
    cap2_norm = cap2.lower().strip()

    # Exact match
    if cap1_norm == cap2_norm:
        return True

    # Check if one is substring of the other
    if cap1_norm in cap2_norm or cap2_norm in cap1_norm:
        return True

    # Simple word overlap check
    words1 = set(cap1_norm.split())
    words2 = set(cap2_norm.split())
    if len(words1) > 0 and len(words2) > 0:
        overlap = len(words1.intersection(words2))
        min_len = min(len(words1), len(words2))
        if overlap / min_len >= threshold:
            return True

    return False


def _is_mistral_response_valid(
    response: Any,
    extracted_markdown: str,
    config: PDFParserConfig,
    file_description: str = "processed PDF"
) -> bool:
    """Validates the Mistral OCR API response based on thresholds."""
    if not response or not hasattr(response, 'pages') or not response.pages:
        logger.warning(
            f"Validation failed for {file_description}: "
            f"Response is empty or has no pages."
        )
        return False

    if len(extracted_markdown) < config.min_markdown_length:
        logger.warning(
            f"Validation failed for {file_description}: "
            f"Markdown length ({len(extracted_markdown)}) is less than "
            f"min_markdown_length ({config.min_markdown_length})."
        )
        return False

    # Token ratio validation (simplified)
    num_chars = len(extracted_markdown)
    if num_chars > 0:
        num_pseudo_tokens = num_chars / 4.5
        token_char_ratio = num_pseudo_tokens / num_chars
        logger.debug(
            f"For {file_description}: Pseudo-token count: "
            f"{num_pseudo_tokens:.0f}, Char count: {num_chars}, "
            f"Pseudo-token/char ratio: {token_char_ratio:.4f}"
        )

    logger.info(
        f"Mistral OCR response for {file_description} passed basic validation."
    )
    return True


# Quality check functions removed - handled by validation


def extract_assets_from_mistral_response(
    api_response: Dict[str, Any],
    output_dir: str
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Extract markdown text, images, and tables from Mistral response.

    Returns:
        - markdown_text: Combined markdown content
        - images_meta: List of image metadata dicts
        - tables_meta: List of table metadata dicts
    """
    pages = api_response.get("pages", [])
    markdown_text = "\n\n".join(p.get("markdown", "") for p in pages)

    images_meta = []
    tables_meta = []
    fig_count = 1
    table_count = 1

    for page_idx, page in enumerate(pages):
        for img in page.get("images", []):
            # Extract image metadata
            caption = img.get("image_annotation", "")
            width = img.get("bottom_right_x", 0) - img.get("top_left_x", 0)
            height = img.get("bottom_right_y", 0) - img.get("top_left_y", 0)

            # Save image to file
            image_id = f"img_{page_idx}_{len(images_meta)}"
            image_filename = f"{image_id}.png"
            image_path = os.path.join(output_dir, image_filename)

            # Decode and save base64 image
            if img.get("image_base64"):
                image_data = base64.b64decode(img["image_base64"])
                os.makedirs(output_dir, exist_ok=True)
                with open(image_path, "wb") as f:
                    f.write(image_data)

            # Determine if it's a table or figure
            fig_match = re.match(
                r"^(Figure\s*\d+):?\s*(.*)", caption, re.IGNORECASE
            )
            tbl_match = re.match(
                r"^(Table\s*\d+):?\s*(.*)", caption, re.IGNORECASE
            )

            entry = {
                "id": image_id,
                "caption": caption,
                "width": width,
                "height": height,
                "file_path": image_path,
                "page_number": page_idx,
                "bbox": [
                    img.get("top_left_x", 0),
                    img.get("top_left_y", 0),
                    img.get("bottom_right_x", 0),
                    img.get("bottom_right_y", 0)
                ],
                "data": image_data if img.get("image_base64") else None
            }

            if tbl_match:
                entry["table_id"] = tbl_match.group(1)
                entry["clean_caption"] = tbl_match.group(2)
                entry["index"] = table_count
                tables_meta.append(entry)
                table_count += 1
            else:
                if fig_match:
                    entry["figure_id"] = fig_match.group(1)
                    entry["clean_caption"] = fig_match.group(2)
                else:
                    entry["figure_id"] = f"Figure {fig_count}"
                    entry["clean_caption"] = caption
                entry["index"] = fig_count
                images_meta.append(entry)
                fig_count += 1

    return markdown_text, images_meta, tables_meta


def save_assets_to_files(
    images: List[Dict[str, Any]],
    tables: List[Dict[str, Any]],
    output_dir: str,
    doc_filename: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Save image and table data to files and return file paths."""
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Process images
    processed_images = []
    for i, img in enumerate(images):
        img_filename = f"{doc_filename}-picture-{i+1}.png"
        img_path = output_path / img_filename

        # Save image data to file
        if img.get("data"):
            try:
                with img_path.open("wb") as f:
                    f.write(img["data"])

                # Create compatible entry for Paper2Poster
                processed_img = {
                    "id": img.get("id", f"Image {i+1}"),
                    "caption": img.get("caption", ""),
                    "image_path": str(img_path),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "figure_size": img.get("width", 0) * img.get("height", 0),
                    "figure_aspect": (
                        img.get("width", 1) / max(img.get("height", 1), 1)
                    ),
                    "page_number": img.get("page_number", 0),
                    "bbox": img.get("bbox", [0, 0, 0, 0])
                }
                processed_images.append(processed_img)

            except Exception as e:
                logger.error(f"Failed to save image {img_filename}: {e}")

    # Process tables
    processed_tables = []
    for i, tbl in enumerate(tables):
        tbl_filename = f"{doc_filename}-table-{i+1}.png"
        tbl_path = output_path / tbl_filename

        # Save table data to file
        if tbl.get("data"):
            try:
                with tbl_path.open("wb") as f:
                    f.write(tbl["data"])

                # Create compatible entry for Paper2Poster
                processed_tbl = {
                    "id": tbl.get("id", f"Table {i+1}"),
                    "caption": tbl.get("caption", ""),
                    "table_path": str(tbl_path),
                    "width": tbl.get("width", 0),
                    "height": tbl.get("height", 0),
                    "figure_size": tbl.get("width", 0) * tbl.get("height", 0),
                    "figure_aspect": (
                        tbl.get("width", 1) / max(tbl.get("height", 1), 1)
                    ),
                    "page_number": tbl.get("page_number", 0),
                    "bbox": tbl.get("bbox", [0, 0, 0, 0])
                }
                processed_tables.append(processed_tbl)

            except Exception as e:
                logger.error(f"Failed to save table {tbl_filename}: {e}")

    return processed_images, processed_tables

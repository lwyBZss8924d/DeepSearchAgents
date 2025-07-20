#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paper_reader/paper_parser_html.py
# code style: PEP 8

"""
Enhanced HTML Paper Parser using Jina Reader LM v2.

This module provides HTML parsing capabilities specifically designed for
academic papers, using Jina's readerlm-v2 model for structured extraction.
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from src.core.scraping.scraper_jinareader import JinaReaderScraper
from src.core.scraping.result import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class HTMLParserConfig:
    """Configuration for HTML paper parsing."""

    api_key: str = field(
        default_factory=lambda: os.getenv("JINA_API_KEY", "")
    )
    output_format: str = "markdown"
    extract_references: bool = True
    extract_figures: bool = True
    extract_equations: bool = True
    extract_tables: bool = True
    with_links_summary: bool = False
    with_images_summary: bool = True
    timeout: int = 120
    max_retries: int = 3
    use_readerlm_v2: bool = True


# JSON Schema for academic paper extraction
PAPER_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "The title of the academic paper"
        },
        "authors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "affiliation": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name"]
            },
            "description": "List of paper authors"
        },
        "abstract": {
            "type": "string",
            "description": "The paper abstract"
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Keywords or key phrases"
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "subsections": {"type": "array"}
                },
                "required": ["title", "content"]
            },
            "description": "Paper sections with hierarchy"
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "authors": {"type": "string"},
                    "year": {"type": "string"},
                    "venue": {"type": "string"},
                    "doi": {"type": "string"},
                    "url": {"type": "string"}
                }
            },
            "description": "Bibliography references"
        },
        "figures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "caption": {"type": "string"},
                    "url": {"type": "string"},
                    "referenced_in_sections": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "description": "Figures with captions"
        },
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "caption": {"type": "string"},
                    "headers": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "description": "Tables with structured data"
        },
        "equations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "latex": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "description": "Mathematical equations"
        },
        "publication_info": {
            "type": "object",
            "properties": {
                "venue": {"type": "string"},
                "year": {"type": "string"},
                "volume": {"type": "string"},
                "pages": {"type": "string"},
                "doi": {"type": "string"},
                "arxiv_id": {"type": "string"}
            },
            "description": "Publication details"
        }
    },
    "required": ["title", "authors", "abstract", "sections"]
}


class HTMLPaperParser:
    """
    Enhanced parser for academic papers using Jina Reader LM v2.

    This parser uses Jina's readerlm-v2 model for structured extraction,
    providing more accurate and consistent results than regex-based parsing.
    """

    def __init__(self, config: Optional[HTMLParserConfig] = None):
        """
        Initialize HTML paper parser.

        Args:
            config: Optional parser configuration
        """
        self.config = config or HTMLParserConfig()

        # Check for API key
        if not self.config.api_key:
            logger.warning(
                "JINA_API_KEY not set. HTML parsing with structured extraction "
                "requires Jina API. Get your free API key from "
                "https://jina.ai/?sui=apikey"
            )

        try:
            self.scraper = JinaReaderScraper(
                api_key=self.config.api_key,
                output_format=self.config.output_format,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        except Exception as e:
            if "No API key provided" in str(e):
                logger.error(
                    "Failed to initialize Jina Reader. Please set JINA_API_KEY "
                    "environment variable or provide it in config. "
                    "Get your free API key from https://jina.ai/?sui=apikey"
                )
            raise

    async def parse_paper_html(
        self,
        html_url: str,
        paper_id: Optional[str] = None,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse academic paper from HTML URL using structured extraction.

        Args:
            html_url: URL of the HTML paper
            paper_id: Optional paper ID for logging
            custom_schema: Optional custom JSON schema for extraction

        Returns:
            Tuple containing:
                - metadata: Paper metadata and structure
                - content: Full paper content in markdown
                - figures: List of figure metadata
                - tables: List of table metadata
        """
        logger.info(f"Parsing HTML paper from: {html_url}")

        try:
            # Prepare extraction schema
            schema = custom_schema or PAPER_EXTRACTION_SCHEMA

            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(schema)

            # Fetch and extract using readerlm-v2
            if self.config.use_readerlm_v2:
                result = await self._extract_with_readerlm(
                    html_url,
                    extraction_prompt,
                    schema
                )
            else:
                # Fallback to original extraction
                result = await self._extract_with_regex(html_url)

            if not result['success']:
                raise Exception(f"Failed to parse paper: {result.get('error')}")

            metadata = result['metadata']
            content = result['content']
            figures = metadata.get('figures', [])
            tables = metadata.get('tables', [])

            # Post-process extracted data
            metadata = self._post_process_metadata(metadata)

            return metadata, content, figures, tables

        except Exception as e:
            logger.error(f"Error parsing HTML paper {html_url}: {e}")
            raise

    async def _extract_with_readerlm(
        self,
        html_url: str,
        extraction_prompt: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract paper data using Jina Reader LM v2."""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Respond-With": "readerlm-v2",
            "X-Return-Format": "markdown",
            "X-With-Images-Summary": "true" if self.config.with_images_summary else "false",
            "X-Engine": "browser",
            "X-Timeout": str(self.config.timeout)
        }

        # Request body with extraction instructions
        body = {
            "url": html_url,
            "injectPageScript": f"""
            // Add extraction instructions as a comment
            /* EXTRACTION_INSTRUCTIONS:
            {extraction_prompt}

            JSON_SCHEMA:
            {json.dumps(schema, indent=2)}
            */
            """
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://r.jina.ai/",
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    response_data = await response.json()

                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f"API error: {response_data}"
                        }

                    # Extract content and metadata
                    content = response_data['data']['content']

                    # Parse structured data from content
                    # Look for JSON block in the response
                    json_match = re.search(
                        r'```json\n(.*?)\n```',
                        content,
                        re.DOTALL
                    )

                    if json_match:
                        try:
                            metadata = json.loads(json_match.group(1))
                        except json.JSONDecodeError:
                            # Fallback to regex extraction
                            return await self._extract_with_regex(html_url)
                    else:
                        # Try to find inline JSON
                        metadata = self._extract_json_from_content(content)
                        if not metadata:
                            # Fallback to regex extraction
                            return await self._extract_with_regex(html_url)

                    # Add image metadata if available
                    if 'images' in response_data['data']:
                        metadata['image_metadata'] = response_data['data']['images']

                    return {
                        'success': True,
                        'content': content,
                        'metadata': metadata
                    }

        except Exception as e:
            logger.error(f"ReadLM extraction failed: {e}")
            # Fallback to regex extraction
            return await self._extract_with_regex(html_url)

    async def _extract_with_regex(self, html_url: str) -> Dict[str, Any]:
        """Fallback regex-based extraction (original method)."""
        result = await self.scraper.scrape_async(
            html_url,
            with_links_summary=self.config.with_links_summary,
            with_images_summary=self.config.with_images_summary,
            engine="browser",
            timeout_seconds=self.config.timeout
        )

        if not result.success:
            return {
                'success': False,
                'error': result.error
            }

        content = result.content

        # Use original parser methods (converted to standalone functions)
        metadata = self._extract_metadata_regex(content, result.metadata)

        # Extract sections
        metadata['sections'] = self._extract_sections_regex(content)

        # Extract other components
        if self.config.extract_references:
            metadata['references'] = self._extract_references_regex(content)

        if self.config.extract_figures:
            metadata['figures'] = self._extract_figures_regex(
                content,
                result.metadata.get('images', [])
            )

        if self.config.extract_tables:
            metadata['tables'] = self._extract_tables_regex(content)

        if self.config.extract_equations:
            metadata['equations'] = self._extract_equations_regex(content)

        return {
            'success': True,
            'content': content,
            'metadata': metadata
        }

    def _build_extraction_prompt(self, schema: Dict[str, Any]) -> str:
        """Build extraction prompt for readerlm-v2."""
        return f"""
        Extract the following information from this academic paper and return it as a JSON object
        that matches the provided schema. Be thorough and accurate in your extraction.

        Focus on:
        1. Complete author information including affiliations
        2. Full abstract without truncation
        3. All section titles and their complete content
        4. All references with complete citation information
        5. Figure and table captions with their IDs
        6. Mathematical equations in LaTeX format
        7. Publication metadata (venue, year, DOI, etc.)

        Return the data as a valid JSON object matching this schema:
        {json.dumps(schema, indent=2)}

        Important: Return ONLY the JSON object, no additional text.
        """

    def _extract_json_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from content."""
        # Try various JSON patterns
        patterns = [
            r'\{[\s\S]*\}',  # Full JSON object
            r'```json\n(.*?)\n```',  # JSON code block
            r'```\n(.*?)\n```'  # Generic code block
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    # Try to parse as JSON
                    data = json.loads(match)
                    # Validate it has expected fields
                    if 'title' in data or 'authors' in data:
                        return data
                except json.JSONDecodeError:
                    continue

        return None

    def _post_process_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process extracted metadata for consistency."""
        # Ensure all required fields exist
        metadata.setdefault('title', '')
        metadata.setdefault('authors', [])
        metadata.setdefault('abstract', '')
        metadata.setdefault('sections', [])
        metadata.setdefault('keywords', [])

        # Normalize author format
        if isinstance(metadata['authors'], list):
            normalized_authors = []
            for author in metadata['authors']:
                if isinstance(author, str):
                    normalized_authors.append({'name': author})
                elif isinstance(author, dict):
                    normalized_authors.append(author)
            metadata['authors'] = normalized_authors

        # Add IDs to sections if missing
        for i, section in enumerate(metadata.get('sections', [])):
            if 'id' not in section:
                section['id'] = f"section_{i+1}"

        # Add IDs to references if missing
        for i, ref in enumerate(metadata.get('references', [])):
            if 'id' not in ref:
                ref['id'] = str(i + 1)

        return metadata

    # Regex-based extraction methods (from original parser)
    def _extract_metadata_regex(
        self,
        content: str,
        jina_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract paper metadata from content using regex."""
        metadata = {
            'title': jina_metadata.get('title', ''),
            'url': jina_metadata.get('url', ''),
            'description': jina_metadata.get('description', '')
        }

        if not metadata['title']:
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata['title'] = title_match.group(1).strip()

        return metadata

    def _extract_sections_regex(self, content: str) -> List[Dict[str, str]]:
        """Extract paper sections using regex."""
        sections = []
        header_pattern = r'^(#{1,6})\s+(.+)$'

        current_section = None
        section_content = []

        for line in content.split('\n'):
            header_match = re.match(header_pattern, line)

            if header_match:
                if current_section:
                    current_section['content'] = '\n'.join(section_content).strip()
                    sections.append(current_section)
                    section_content = []

                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                current_section = {
                    'level': level,
                    'title': title,
                    'content': ''
                }
            elif current_section:
                section_content.append(line)

        if current_section:
            current_section['content'] = '\n'.join(section_content).strip()
            sections.append(current_section)

        return sections

    def _extract_references_regex(self, content: str) -> List[Dict[str, str]]:
        """Extract references using regex."""
        references = []

        ref_pattern = r'(?i)(?:^|\n)#+\s*(?:references?|bibliography)\s*\n+([\\s\\S]+?)(?=\n#+|$)'
        match = re.search(ref_pattern, content)

        if not match:
            return references

        ref_section = match.group(1)
        ref_items = re.split(r'\n\s*(?:\[\d+\]|\d+[.)])', ref_section)

        for i, ref_text in enumerate(ref_items[1:], 1):
            ref_text = ref_text.strip()
            if not ref_text:
                continue

            ref_entry = {
                'id': str(i),
                'text': ref_text
            }

            title_match = re.search(r'"([^"]+)"', ref_text)
            if title_match:
                ref_entry['title'] = title_match.group(1)

            year_match = re.search(r'\b(19|20)\d{2}\b', ref_text)
            if year_match:
                ref_entry['year'] = year_match.group(0)

            doi_match = re.search(r'(?:doi:|https://doi.org/)(10\.\d+/[^\s]+)', ref_text)
            if doi_match:
                ref_entry['doi'] = doi_match.group(1)

            references.append(ref_entry)

        return references

    def _extract_figures_regex(
        self,
        content: str,
        image_metadata: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Extract figure information using regex."""
        figures = []
        caption_pattern = r'(?i)(?:figure|fig\.?)\s*(\d+)[:\s]*([^\n]+)'

        for match in re.finditer(caption_pattern, content):
            fig_num = match.group(1)
            caption = match.group(2).strip()

            figure = {
                'id': f'figure_{fig_num}',
                'figure_number': fig_num,
                'caption': caption
            }

            for img in image_metadata:
                if f'fig{fig_num}' in img.get('alt', '').lower():
                    figure['url'] = img.get('src', '')
                    break

            figures.append(figure)

        return figures

    def _extract_tables_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract table information using regex."""
        tables = []
        caption_pattern = r'(?i)(?:table)\s*(\d+)[:\s]*([^\n]+)'

        for match in re.finditer(caption_pattern, content):
            table_num = match.group(1)
            caption = match.group(2).strip()

            table = {
                'id': f'table_{table_num}',
                'table_number': table_num,
                'caption': caption
            }

            # Try to find markdown table
            table_start = match.end()
            table_lines = []
            lines = content[table_start:].split('\n')

            for line in lines[:20]:
                if '|' in line:
                    table_lines.append(line)
                elif table_lines and not line.strip():
                    break

            if table_lines:
                table['markdown'] = '\n'.join(table_lines)
                # Parse table structure
                if len(table_lines) >= 2:
                    headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
                    table['headers'] = headers

                    rows = []
                    for line in table_lines[2:]:  # Skip header separator
                        row = [cell.strip() for cell in line.split('|') if cell.strip()]
                        if row:
                            rows.append(row)
                    table['rows'] = rows

            tables.append(table)

        return tables

    def _extract_equations_regex(self, content: str) -> List[Dict[str, str]]:
        """Extract equations using regex."""
        equations = []

        patterns = [
            (r'\$\$([^\$]+)\$\$', 'display'),
            (r'\\\[([^\]]+)\\\]', 'display'),
            (r'\\begin\{equation\}([\\s\\S]+?)\\end\{equation\}', 'display'),
            (r'\$([^\$]+)\$', 'inline')
        ]

        equation_id = 1
        seen = set()

        for pattern, eq_type in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                latex = match.strip()
                if latex and latex not in seen:
                    seen.add(latex)
                    equations.append({
                        'id': f'eq_{equation_id}',
                        'latex': latex,
                        'type': eq_type
                    })
                    equation_id += 1

        return equations


def parse_paper_html(
    html_url: str,
    config: Optional[HTMLParserConfig] = None,
    custom_schema: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Synchronous wrapper for parsing HTML papers with enhanced extraction.

    Args:
        html_url: URL of the HTML paper
        config: Optional parser configuration
        custom_schema: Optional custom extraction schema

    Returns:
        Tuple of (metadata, content, figures, tables)
    """
    import asyncio

    parser = HTMLPaperParser(config)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    parser.parse_paper_html(html_url, custom_schema=custom_schema)
                )
                return future.result()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        parser.parse_paper_html(html_url, custom_schema=custom_schema)
    )

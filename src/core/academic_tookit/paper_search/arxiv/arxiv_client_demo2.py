"""
arXiv API client with rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import feedparser
import httpx
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


def arxiv_client_demo2():
    arxiv_client = ArxivClient()
    """
            annotations={
                "title": "Search arXiv Papers",
                "readOnlyHint": True,
                "openWorldHint": True,
            }
        )
    """
    async def search_papers(query: str, max_results: int = 10) -> str:
        """
        Search for papers on arXiv by title and abstract content.

        You can use advanced search syntax:
        - Search in title: ti:"search terms"
        - Search in abstract: abs:"search terms"
        - Search by author: au:"author name"
        - Combine terms with: AND, OR, ANDNOT
        - Filter by category: cat:cs.AI (use list_categories tool to see available categories)

        Examples:
        - "machine learning"  (searches all fields)
        - ti:"neural networks" AND cat:cs.AI  (title with category)
        - au:bengio AND ti:"deep learning"  (author and title)
        """
        max_results = min(max_results, 50)
        papers = await arxiv_client.search(query, max_results)

        # Format results in a readable way
        result = "Search Results:\n\n"
        for i, paper in enumerate(papers, 1):
            result += f"{i}. {paper['title']}\n"
            result += f"   Authors: {', '.join(paper['authors'])}\n"
            result += f"   ID: {paper['id']}\n"
            result += f"   Categories: "
            if paper['primary_category']:
                result += f"Primary: {paper['primary_category']}"
            if paper['categories']:
                result += f", Additional: {', '.join(paper['categories'])}"
            result += f"\n   Published: {paper['published']}\n"

            # Add first sentence of abstract
            abstract_preview = get_first_sentence(paper['summary'])
            result += f"   Preview: {abstract_preview}\n"
            result += "\n"

        return result

    async def get_paper_data(paper_id: str) -> str:
        """
                annotations={
                    "title": "Get arXiv Paper Data",
                    "readOnlyHint": True,
                    "openWorldHint": True
                }
            )
        """
        """Get detailed information about a specific paper including abstract and available formats."""
        paper = await arxiv_client.get_paper(paper_id)

        # Format paper details in a readable way with clear sections
        result = f"Title: {paper['title']}\n\n"

        # Metadata section
        result += "Metadata:\n"
        result += f"- Authors: {', '.join(paper['authors'])}\n"
        result += f"- Published: {paper['published']}\n"
        result += f"- Last Updated: {paper['updated']}\n"
        result += "- Categories: "
        if paper['primary_category']:
            result += f"Primary: {paper['primary_category']}"
        if paper['categories']:
            result += f", Additional: {', '.join(paper['categories'])}"
        result += "\n"

        if paper['doi']:
            result += f"- DOI: {paper['doi']}\n"
        if paper["journal_ref"]:
            result += f"- Journal Reference: {paper['journal_ref']}\n"

        # Abstract section
        result += "\nAbstract:\n"
        result += paper["summary"]
        result += "\n"

        # Access options section
        result += "\nAccess Options:\n"
        result += "- Abstract page: " + paper["abstract_url"] + "\n"
        if paper["html_url"]:  # Add HTML version if available
            result += "- Full text HTML version: " + paper["html_url"] + "\n"
        result += "- PDF version: " + paper["pdf_url"] + "\n"

        # Additional information section
        if paper["comment"] or "code" in paper["comment"].lower():
            result += "\nAdditional Information:\n"
            if paper["comment"]:
                result += "- Comment: " + paper["comment"] + "\n"

        return result

    def list_categories(primary_category: str = None) -> str:
        """
        annotations={
            "title": "List arXiv Categories",
            "readOnlyHint": True,
            "openWorldHint": False
        }
    )
    """
        """List all available arXiv categories and how to use them in search."""
        try:
            taxonomy = load_taxonomy()
        except Exception as e:
            logger.error(f"Error loading taxonomy: {e}")
            return f"Error loading category taxonomy. Try using update_categories tool to refresh it."

        result = "arXiv Categories:\n\n"

        for primary, data in taxonomy.items():
            if primary_category and primary != primary_category:
                continue

            result += f"{primary}: {data['name']}\n"
            for code, desc in data['subcategories'].items():
                result += f"  {primary}.{code}: {desc}\n"
            result += "\n"

        result += "\nUsage in search:\n"
        result += '- Search in specific category: cat:cs.AI\n'
        result += '- Combine with other terms: "neural networks" AND cat:cs.AI\n'
        result += '- Multiple categories: (cat:cs.AI OR cat:cs.LG)\n'
        result += '\nNote: If categories seem outdated, use the update_categories tool to refresh them.\n'

        return result

    def update_categories() -> str:
        """
        Update the stored category taxonomy by fetching the latest version from arxiv.org
        """
        """
            annotations={
                "title": "Update arXiv Categories",
                "readOnlyHint": False,
                "openWorldHint": True
            }
        )
        """
        try:
            taxonomy = update_taxonomy_file()
            result = "Successfully updated category taxonomy.\n\n"
            result += f"Found {len(taxonomy)} primary categories:\n"
            for primary, data in taxonomy.items():
                result += f"- {primary}: {data['name']} ({len(data['subcategories'])} subcategories)\n"
            return result
        except Exception as e:
            logger.error(f"Error updating taxonomy: {e}")
            # FastMCP will handle raising this as a proper JSON-RPC error
            raise e

    return {
        "search_papers": search_papers,
        "get_paper_data": get_paper_data,
        "list_categories": list_categories,
        "update_categories": update_categories,
    }


class ArxivClient:
    """
    arXiv API client with built-in rate limiting.
    Ensures no more than 1 request every 3 seconds.
    """

    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self._last_request: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def _wait_for_rate_limit(self) -> None:
        """Ensures we respect arXiv's rate limit of 1 request every 3 seconds."""
        async with self._lock:
            if self._last_request is not None:
                elapsed = datetime.now() - self._last_request
                if elapsed < timedelta(seconds=3):
                    await asyncio.sleep(3 - elapsed.total_seconds())
            self._last_request = datetime.now()

    def _clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace and newlines."""
        return " ".join(text.split())

    def _get_html_url(self, arxiv_id: str) -> str:
        """
        Construct HTML version URL for a paper.

        The HTML version URL is not provided by the API but can be constructed
        by modifying the PDF URL pattern.
        """
        # Remove version suffix if present (e.g., v1, v2)
        base_id = arxiv_id.split('v')[0]
        return f"https://arxiv.org/html/{arxiv_id}"

    def _parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a feed entry into a paper dictionary."""
        # Extract PDF and HTML links
        pdf_url = None
        abstract_url = None  # This is the URL to the abstract page
        for link in entry.get('links', []):
            if isinstance(link, dict):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href')
                elif link.get('type') == 'text/html':
                    abstract_url = link.get('href')

        # Get paper ID
        paper_id = entry.get('id', '').split("/abs/")[-1].rstrip()

        # Create HTML version URL
        html_url = self._get_html_url(paper_id) if paper_id else None

        # Get authors
        authors = []
        for author in entry.get('authors', []):
            if isinstance(author, dict) and 'name' in author:
                authors.append(author['name'])
            elif hasattr(author, 'name'):
                authors.append(author.name)

        # Get categories
        categories = []
        primary_category = None

        # Get primary category
        if 'arxiv_primary_category' in entry:
            if isinstance(entry['arxiv_primary_category'], dict):
                primary_category = entry['arxiv_primary_category'].get('term')
            elif hasattr(entry['arxiv_primary_category'], 'term'):
                primary_category = entry['arxiv_primary_category'].term

        # Get all categories
        for category in entry.get('tags', []):
            if isinstance(category, dict) and 'term' in category:
                categories.append(category['term'])
            elif hasattr(category, 'term'):
                categories.append(category.term)

        # Remove primary category from regular categories if it's there
        if primary_category and primary_category in categories:
            categories.remove(primary_category)

        return {
            "id": paper_id,
            "title": self._clean_text(entry.get('title', '')),
            "authors": authors,
            "primary_category": primary_category,
            "categories": categories,
            "published": entry.get('published', ''),
            "updated": entry.get('updated', ''),
            "summary": self._clean_text(entry.get('summary', '')),
            "comment": self._clean_text(entry.get('arxiv_comment', '')),
            "journal_ref": entry.get('arxiv_journal_ref', ''),
            "doi": entry.get('arxiv_doi', ''),
            "pdf_url": pdf_url,
            "abstract_url": abstract_url,  # URL to abstract page
            "html_url": html_url  # URL to HTML version if available
        }

    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search arXiv papers.

        The query string supports arXiv's advanced search syntax:
        - Search in title: ti:"search terms"
        - Search in abstract: abs:"search terms"
        - Search by author: au:"author name"
        - Combine terms with: AND, OR, ANDNOT
        - Filter by category: cat:cs.AI

        Examples:
        - "machine learning"  (searches all fields)
        - ti:"neural networks" AND cat:cs.AI  (title with category)
        - au:bengio AND ti:"deep learning"  (author and title)
        """
        await self._wait_for_rate_limit()

        # Ensure max_results is within API limits
        max_results = min(max_results, 2000)  # API limit: 2000 per request

        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": "submittedDate",  # Default to newest papers first
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status() # Raise an exception for bad status codes

                # Parse the Atom feed response
                feed = feedparser.parse(response.text)

                if not isinstance(feed, dict) or 'entries' not in feed:
                    logger.error("Invalid response from arXiv API")
                    logger.debug(f"Response text: {response.text[:1000]}...")
                    raise ValueError("Invalid response from arXiv API")

                if not feed.get('entries'):
                    # Empty results are ok - return empty list
                    return []

                return [self._parse_entry(entry) for entry in feed.entries]

            except httpx.HTTPError as e:
                logger.error(f"HTTP error while searching: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")

    async def get_paper(self, paper_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific paper.

        Args:
            paper_id: arXiv paper ID (e.g., "2103.08220")

        Returns:
            Dictionary containing paper metadata, including:
            - Basic metadata (title, authors, dates)
            - Categories (primary and others)
            - Abstract and comments
            - URLs (abstract page, PDF version, HTML version if available)
            - DOI if available
        """
        await self._wait_for_rate_limit()

        params = {
            "id_list": paper_id,
            "max_results": 1
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                feed = feedparser.parse(response.text)
                if not isinstance(feed, dict) or 'entries' not in feed:
                    logger.error("Invalid response from arXiv API")
                    logger.debug(f"Response text: {response.text[:1000]}...")
                    raise ValueError("Invalid response from arXiv API")

                if not feed.get('entries'):
                    raise ValueError(f"Paper not found: {paper_id}")

                return self._parse_entry(feed.entries[0])

            except httpx.HTTPError as e:
                logger.error(f"HTTP error while fetching paper: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")

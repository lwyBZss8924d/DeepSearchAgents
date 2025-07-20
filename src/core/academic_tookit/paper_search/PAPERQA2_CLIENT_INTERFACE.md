# PaperQA2 Client Interface Guide

This guide explains how to implement custom metadata providers for PaperQA2 to integrate new paper sources like ArXiv, bioRxiv, or custom databases.

## Overview

PaperQA2 uses a flexible metadata system that allows you to:
1. Automatically fetch paper metadata when adding PDFs
2. Enrich papers with citation counts, DOIs, and bibliographic data
3. Support multiple metadata sources with fallback chains

## Core Concepts

### 1. DocDetails Model

The `DocDetails` class is the central data model for paper metadata in PaperQA2:

```python
from paperqa.types import DocDetails

# Key fields in DocDetails:
doc_details = DocDetails(
    # Required identification
    key="Smith2023Neural",           # BibTeX key
    docname="Smith2023Neural",       # Document name
    dockey="unique_doc_id",          # Unique document key
    citation="Smith et al. (2023)",  # Formatted citation
    
    # Bibliographic data
    title="Neural Networks for NLP",
    authors=["John Smith", "Jane Doe"],
    year=2023,
    publication_date=datetime(2023, 3, 15),
    journal="Nature Machine Intelligence",
    volume="5",
    issue="3",
    pages="123-145",
    
    # Identifiers
    doi="10.1038/s42256-023-00000-0",
    doi_url="https://doi.org/10.1038/s42256-023-00000-0",
    doc_id="encoded_doi_hash",
    
    # Access URLs
    url="https://arxiv.org/abs/2303.12345",
    pdf_url="https://arxiv.org/pdf/2303.12345.pdf",
    
    # Quality indicators
    citation_count=42,
    source_quality=2,  # 0-3 scale
    is_retracted=False,
    
    # BibTeX
    bibtex="@article{Smith2023Neural, ...}",
    bibtex_type="article",
    
    # Additional metadata
    other={
        "client_source": ["ArxivProvider"],
        "abstract": "Full abstract text...",
        "categories": ["cs.CL", "cs.AI"]
    }
)
```

### 2. MetadataProvider Interface

All custom providers must inherit from either:
- `MetadataProvider`: Base interface
- `DOIOrTitleBasedProvider`: Convenient base for DOI/title searches

```python
from paperqa.clients.client_models import DOIOrTitleBasedProvider

class MyCustomProvider(DOIOrTitleBasedProvider):
    async def _query(
        self, 
        query: DOIQuery | TitleAuthorQuery
    ) -> DocDetails | None:
        # Implement your search logic
        pass
```

### 3. Query Types

PaperQA2 supports two primary query types:

```python
# DOI Query
from paperqa.clients.client_models import DOIQuery

doi_query = DOIQuery(
    doi="10.1038/nature12373",
    fields=["title", "authors", "year"],  # Optional field filter
    session=aiohttp_session
)

# Title/Author Query
from paperqa.clients.client_models import TitleAuthorQuery

title_query = TitleAuthorQuery(
    title="Attention is All You Need",
    authors=["Vaswani", "Shazeer"],  # Optional
    title_similarity_threshold=0.75,   # Fuzzy matching threshold
    fields=["doi", "pdf_url"],        # Optional field filter
    session=aiohttp_session
)
```

## Implementation Guide

### Step 1: Create Your Provider Class

```python
from paperqa.clients.client_models import DOIOrTitleBasedProvider
from paperqa.types import DocDetails
import aiohttp

class ArxivProvider(DOIOrTitleBasedProvider):
    """
    Custom provider for ArXiv papers.
    """
    
    def __init__(self):
        # Initialize your client/API connections
        self._api_client = YourAPIClient()
    
    async def _query(
        self, 
        query: DOIQuery | TitleAuthorQuery
    ) -> DocDetails | None:
        """
        Main query method - routes to appropriate handler.
        """
        if isinstance(query, DOIQuery):
            return await self._query_by_doi(query)
        else:
            return await self._query_by_title(query)
```

### Step 2: Implement DOI Search

```python
async def _query_by_doi(self, query: DOIQuery) -> DocDetails | None:
    """Search by DOI."""
    try:
        # Call your API
        paper_data = await self._api_client.get_by_doi(query.doi)
        
        if not paper_data:
            return None
            
        # Convert to DocDetails
        return self._convert_to_doc_details(paper_data, query.fields)
        
    except Exception as e:
        logger.error(f"DOI search failed: {e}")
        return None
```

### Step 3: Implement Title Search

```python
async def _query_by_title(
    self, 
    query: TitleAuthorQuery
) -> DocDetails | None:
    """Search by title and optional authors."""
    
    # Search your source
    results = await self._api_client.search(
        title=query.title,
        authors=query.authors
    )
    
    # Find best match
    for result in results:
        # Check title similarity
        from paperqa.utils import strings_similarity
        
        similarity = strings_similarity(
            result.title.lower(),
            query.title.lower()
        )
        
        if similarity < query.title_similarity_threshold:
            continue
            
        # Optional: Check author match
        if query.authors and not self._authors_match(
            result.authors, 
            query.authors
        ):
            continue
            
        # Found match - convert and return
        return self._convert_to_doc_details(result, query.fields)
    
    return None
```

### Step 4: Convert to DocDetails

```python
def _convert_to_doc_details(
    self, 
    paper_data: dict,
    fields: list[str] | None = None
) -> DocDetails:
    """Convert API response to DocDetails."""
    
    from paperqa.utils import create_bibtex_key
    from paperqa.types import BibTeXSource
    
    # Generate BibTeX key
    key = create_bibtex_key(
        paper_data.get("authors", ["Unknown"]),
        paper_data.get("year", "Unknown"),
        paper_data.get("title", "Unknown")
    )
    
    # Build DocDetails
    doc_details = DocDetails(
        key=key,
        docname=key,
        title=paper_data.get("title"),
        authors=paper_data.get("authors", []),
        year=paper_data.get("year"),
        doi=paper_data.get("doi"),
        journal=paper_data.get("journal", "arXiv"),
        pdf_url=paper_data.get("pdf_url"),
        # ... other fields ...
        other={
            "bibtex_source": [BibTeXSource.SELF_GENERATED],
            "client_source": ["MyCustomProvider"],
            # ... custom fields ...
        }
    )
    
    # Filter to requested fields if specified
    if fields:
        # Implementation depends on your needs
        pass
        
    return doc_details
```

## Integration with PaperQA2

### Using Your Provider

```python
from paperqa import Docs, Settings
from paperqa.clients import DocMetadataClient

# Method 1: Create custom client
arxiv_provider = ArxivProvider()
client = DocMetadataClient(clients=[arxiv_provider])

# Query directly
details = await client.query(
    title="Neural Networks for NLP",
    authors=["Smith"]
)

# Method 2: Use with Docs
docs = Docs()
settings = Settings()

# The metadata will be fetched automatically
await docs.aadd(
    "paper.pdf",
    settings=settings,
    # Custom client can be passed here
)
```

### Combining Multiple Providers

```python
from paperqa.clients import (
    CrossrefProvider,
    SemanticScholarProvider
)

# Create chain of providers
client = DocMetadataClient(
    clients=[
        # Try ArXiv first
        [ArxivProvider()],
        # Then try Crossref and Semantic Scholar
        [CrossrefProvider(), SemanticScholarProvider()],
        # Post-processors can be added too
        [JournalQualityPostProcessor()]
    ]
)
```

## Best Practices

### 1. Error Handling

```python
async def _query(self, query) -> DocDetails | None:
    try:
        # Your implementation
        pass
    except DOINotFoundError:
        logger.warning(f"DOI not found: {query.doi}")
        return None
    except aiohttp.ClientError:
        logger.error("Network error")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### 2. Rate Limiting

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def _api_call(self, endpoint: str) -> dict:
    # Your API call with retries
    pass
```

### 3. Caching

Consider caching results to avoid repeated API calls:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def _cached_doi_lookup(self, doi: str) -> dict:
    # Cache DOI lookups
    pass
```

### 4. Field Filtering

Respect the `fields` parameter to avoid fetching unnecessary data:

```python
if fields and "full_text" not in fields:
    # Skip expensive full-text retrieval
    pass
```

## Testing Your Provider

```python
import pytest
from paperqa.clients.client_models import DOIQuery, TitleAuthorQuery

@pytest.mark.asyncio
async def test_doi_query():
    provider = MyCustomProvider()
    
    query = DOIQuery(
        doi="10.1234/test",
        session=aiohttp.ClientSession()
    )
    
    result = await provider._query(query)
    assert result is not None
    assert result.doi == "10.1234/test"

@pytest.mark.asyncio
async def test_title_query():
    provider = MyCustomProvider()
    
    query = TitleAuthorQuery(
        title="Test Paper",
        authors=["Smith"],
        session=aiohttp.ClientSession()
    )
    
    result = await provider._query(query)
    assert result is not None
    assert "Smith" in result.authors
```

## Advanced Features

### MetadataPostProcessor

For additional processing after initial metadata retrieval:

```python
from paperqa.clients.client_models import MetadataPostProcessor

class CitationCountProcessor(MetadataPostProcessor):
    async def _process(
        self, 
        query: ClientQuery,
        doc_details: DocDetails
    ) -> DocDetails:
        # Add citation counts from another source
        count = await self._get_citation_count(doc_details.doi)
        doc_details.citation_count = count
        return doc_details
```

### Custom BibTeX Generation

```python
from pybtex.database import Entry, Person

def generate_bibtex(doc_details: DocDetails) -> str:
    entry = Entry(
        doc_details.bibtex_type or "article",
        fields={
            "title": doc_details.title,
            "year": str(doc_details.year),
            "doi": doc_details.doi,
            # ... other fields ...
        }
    )
    
    # Add authors
    for author_name in doc_details.authors:
        entry.add_person(Person(author_name), "author")
    
    # Convert to string
    from pybtex.database import BibliographyData
    bib_data = BibliographyData(entries={doc_details.key: entry})
    return bib_data.to_string("bibtex")
```

## Conclusion

Implementing a custom PaperQA2 client allows you to:
- Integrate any paper source with PaperQA2
- Automatically enrich PDFs with metadata
- Build powerful paper Q&A systems with custom sources

The key is to properly implement the `DOIOrTitleBasedProvider` interface and convert your data to the `DocDetails` format that PaperQA2 expects.
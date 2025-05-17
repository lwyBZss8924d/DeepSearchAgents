# TODO: Optimizing Scheduling Requirements for Agent-Tools Search

> **NOTE**: This optimization REQUIRES the implementation of [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md) component first.

Our current `serper.py` and `search.py` implementations require updates to match the efficiency and flexibility of the TypeScript version:

## 1. Enhanced Query Interface

```python
# Add support for direct object-based query parameters
def get_sources(
    self,
    query: Union[str, Dict[str, Any]],  # Allow either string or parameter object
    num_results: int = 8,
    stored_location: Optional[str] = None
) -> SearchResult[Dict[str, Any]]:
    """
    Fetch search results from Serper API.
    
    Args:
        query: Search query string or a complete query parameters object
        num_results: Number of results to return (ignored if query is a dict)
        stored_location: Optional location string (ignored if query is a dict)
        
    Returns:
        SearchResult containing the search results or error information
    """
    try:
        # Handle query as either string or full parameter object
        if isinstance(query, str):
            if not query.strip():
                return SearchResult(error="Query cannot be empty")
                
            search_location = (
                stored_location or self.config.default_location
            ).lower()
            
            payload = {
                "q": query,
                "num": min(max(1, num_results), 10),
                "gl": search_location,
                "autocorrect": False  # Add autocorrect flag from TS implementation
            }
        else:
            # Allow passing a complete parameters object
            payload = {
                **query,
                "autocorrect": query.get("autocorrect", False)
            }
```

## 2. Optimized Timeout Settings

```python
@dataclass
class SerperConfig:
    """Configuration for Serper API"""
    api_key: str
    api_url: str = "https://google.serper.dev/search"
    default_location: str = 'us'
    timeout: int = 10  # Reduced from 100 to 10 seconds to match TS implementation
```

## 3. Improved Error Handling

```python
# Simplify error handling and add better error messages
def get_sources(
    self,
    query: Union[str, Dict[str, Any]],
    num_results: int = 8,
    stored_location: Optional[str] = None
) -> SearchResult[Dict[str, Any]]:
    # ...existing code...
    
    try:
        # ...request code...
        response = requests.post(
            self.config.api_url,
            headers=self.headers,
            json=payload,
            timeout=self.config.timeout
        )
        
        # Add explicit status code checking like in TS implementation
        if response.status_code != 200:
            error_msg = f"Serper search failed: {response.status_code} {response.reason}"
            return SearchResult(error=error_msg)
            
        response.raise_for_status()
        data = response.json()
        
        # ...continue with processing...
```

## 4. SearchLinksTool Interface Update

```python
# Update the SearchLinksTool inputs to support more query parameters
inputs = {
    "query": {
        "type": "string",
        "description": "The search query string.",
    },
    "num_results": {
        "type": "integer",
        "description": "The desired number of search results.",
        "default": 10,
        "nullable": True,
    },
    "location": {
        "type": "string",
        "description": "The geographic location for the search (e.g., 'us', 'cn').",
        "default": "us",
        "nullable": True,
    },
    "autocorrect": {
        "type": "boolean", 
        "description": "Whether to enable search query autocorrection.",
        "default": False,
        "nullable": True,
    },
    "search_type": {
        "type": "string",
        "description": "Type of search to perform ('search', 'images', 'news', 'places').",
        "default": "search",
        "nullable": True,
    }
}

# Update forward method to support new parameters
def forward(
    self,
    query: str,
    num_results: Optional[int] = 10,
    location: Optional[str] = "us",
    autocorrect: Optional[bool] = False,
    search_type: Optional[str] = "search"
) -> str:
    """
    Performs a search and returns a JSON string containing a list of
    Search Engine Results Page (SERP) results.

    Args:
        query (str): The search query.
        num_results (int, optional): The number of results to return. Default: 10.
        location (str, optional): The search location. Default: 'us'.
        autocorrect (bool, optional): Whether to enable query autocorrection. Default: False.
        search_type (str, optional): Type of search to perform. Default: 'search'.

    Returns:
        str: A JSON string containing a list of Search Engine Results Page (SERP) results.
            If the search fails or returns no results, return a JSON string of an empty list ('[]').
    """
    # Support both direct string queries and parameter objects
    if search_type and search_type != "search":
        # Create a parameter object for non-standard search types
        query_params = {
            "q": query,
            "gl": location if location else "us",
            "num": num_results if num_results else 10,
            "autocorrect": autocorrect if autocorrect is not None else False,
            "type": search_type
        }
        search_result = self.serp_search_api.get_sources(query_params)
    else:
        # Use standard search with individual parameters
        search_result = self.serp_search_api.get_sources(
            query,
            num_results=num_results if num_results is not None else 10,
            stored_location=location if location is not None else "us"
        )
```

## 5. Retry Mechanism

Add a robust retry mechanism for transient errors:

```python
def get_sources(
    self,
    query: Union[str, Dict[str, Any]],
    num_results: int = 8,
    stored_location: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> SearchResult[Dict[str, Any]]:
    # ...existing code...
    
    retry_count = 0
    while retry_count <= max_retries:
        try:
            # ...request code...
            response = requests.post(
                self.config.api_url,
                headers=self.headers,
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 429:  # Rate limit error
                retry_count += 1
                if retry_count <= max_retries:
                    sleep_time = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    print(f"Rate limit hit, retrying in {sleep_time} seconds...")
                    import time
                    time.sleep(sleep_time)
                    continue
                    
            # ...continue with normal processing...
```

## 6. Progress Reporting

Enhance progress reporting for better visibility:

```python
def forward(
    self,
    query: str,
    num_results: Optional[int] = 10,
    location: Optional[str] = "us",
    autocorrect: Optional[bool] = False,
    search_type: Optional[str] = "search"
) -> str:
    # ...existing code...
    
    log_func(
        f"[bold blue]Performing {search_type} search[/bold blue]: {query}"
    )
    log_func(
        f"[dim]Parameters: num_results={num_results}, location={location}, "
        f"autocorrect={autocorrect}[/dim]"
    )
    
    start_time = time.time()
    # ...search code...
    
    end_time = time.time()
    search_time = end_time - start_time
    
    if search_result.failed:
        log_func(
            f"[bold red]Web search failed ({search_time:.2f}s)[/bold red]: "
            f"{search_result.error}"
        )
    else:
        log_func(
            f"[bold green]Web search completed in {search_time:.2f}s, found "
            f"{len(results_list)} results.[/bold green]"
        )
```

## 7. Support for Different Search Types

Add support for different search types (images, news, places):

```python
class SerperAPI:
    # ...existing code...
    
    def get_images(self, query: str, num_results: int = 10) -> SearchResult[Dict[str, Any]]:
        """Special search method for images"""
        return self.get_sources(
            {"q": query, "num": num_results, "type": "images"},
        )
    
    def get_news(self, query: str, num_results: int = 10) -> SearchResult[Dict[str, Any]]:
        """Special search method for news"""
        return self.get_sources(
            {"q": query, "num": num_results, "type": "news"},
        )
        
    def get_places(self, query: str, num_results: int = 10) -> SearchResult[Dict[str, Any]]:
        """Special search method for places"""
        return self.get_sources(
            {"q": query, "num": num_results, "type": "places"},
        )
```

## 8. Response Data Enrichment

Add more metadata to enrich the search responses:

```python
def get_sources(
    self,
    query: Union[str, Dict[str, Any]],
    num_results: int = 8,
    stored_location: Optional[str] = None
) -> SearchResult[Dict[str, Any]]:
    # ...existing code...

    results = {
        'organic': self.extract_fields(
            data.get('organic', []),
            ['title', 'link', 'snippet', 'date']
        ),
        'topStories': self.extract_fields(
            data.get('topStories', []),
            ['title', 'imageUrl']
        ),
        'images': self.extract_fields(
            data.get('images', [])[:6],
            ['title', 'imageUrl']
        ),
        'graph': data.get('knowledgeGraph'),
        'answerBox': data.get('answerBox'),
        'peopleAlsoAsk': data.get('peopleAlsoAsk'),
        'relatedSearches': data.get('relatedSearches'),
        'metadata': {
            'searchQuery': query if isinstance(query, str) else query.get('q', ''),
            'searchType': 'search',  # or derive from query type
            'location': stored_location or self.config.default_location,
            'totalResults': len(data.get('organic', [])),
            'timestamp': time.time(),
            'responseTime': response.elapsed.total_seconds()
        }
    }
```

## 9. Performance Optimization

Enhance performance with connection pooling and async processing:

```python
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, TypeVar, Generic, Union
from dataclasses import dataclass
import requests

# Add a connection pool for better performance
class SerperAPI:
    def __init__(
        self,
        config: Optional[SerperConfig] = None
    ):
        self.config = config or SerperConfig.from_env()
        self.headers = {
            'X-API-KEY': self.config.api_key,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()  # Use a session for connection pooling
        
    # Add async version of get_sources
    async def get_sources_async(
        self,
        query: Union[str, Dict[str, Any]],
        num_results: int = 8,
        stored_location: Optional[str] = None
    ) -> SearchResult[Dict[str, Any]]:
        # Similar to get_sources but using aiohttp
        # ...implementation...
        
    def __del__(self):
        """Clean up session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
```

## Iteration Requirements Summary

1. Implement enhanced query interface to support both string queries and parameter objects
2. Optimize timeout settings to match production needs
3. Improve error handling for better debugging and user experience
4. Update SearchLinksTool interface to support more query parameters
5. Add retry mechanism for handling transient errors and rate limits
6. Enhance progress reporting for better visibility
7. Add support for different search types (images, news, places)
8. Standardize result formats for improved downstream processing
9. Optimize performance with connection pooling and async processing

By implementing these improvements, our Search Agent Tools (`serper.py` and `search.py`) will become more flexible, robust, and efficient in handling different search requirements while providing a better developer experience.

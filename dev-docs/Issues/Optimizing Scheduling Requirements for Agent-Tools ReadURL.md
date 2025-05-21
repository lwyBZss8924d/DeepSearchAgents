# TODO: Optimizing Scheduling Requirements for Agent-Tools ReadURL

> **NOTE**: This optimization REQUIRES the implementation of [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md) component first.

Our current `readurl.py` and related scraping components require updates to match the efficiency and flexibility of the TypeScript version:

## 1. Enhanced URL Validation

```python
def forward(
    self,
    url: str,
    output_format: Optional[str] = "markdown"
) -> str:
    """
    Reads the content of a given URL and returns the processed text.
    
    Args:
        url (str): The URL to read content from.
        output_format (str, optional): The output format. Default is 'markdown'.
        
    Returns:
        str: The processed content. If reading fails, return an error message string.
    """
    # Add URL validation like in TypeScript implementation
    if not url.strip():
        return "Error: URL cannot be empty"
        
    if not (url.startswith('http://') or url.startswith('https://')):
        return "Error: Invalid URL, only http and https URLs are supported"
    
    # Continue with existing implementation...
```

## 2. Extended Header Options

```python
class JinaReaderScraper:
    # ...existing code...
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "readerlm-v2",
        output_format: str = "markdown",
        api_base_url: str = "https://r.jina.ai/",
        max_concurrent_requests: int = 5,
        timeout: int = 60,  # Reduced from 600 to 60 seconds to match TS implementation
        retry_attempts: int = 2,
        retain_images: str = "none",
        md_link_style: str = "discarded",
        with_links_summary: Optional[str] = None
    ):
        # ...existing code...
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json',
            'X-Respond-With': model,
            'X-Return-Format': output_format,
            'X-Retain-Images': retain_images,
            'X-Md-Link-Style': md_link_style,
        }
        
        # Add optional headers
        if with_links_summary:
            self.headers['X-With-Links-Summary'] = with_links_summary
```

## 3. Token Usage Tracking Integration

Use the shared TokenUsageTracker component as defined in [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md):

```python
# Import and use shared TokenUsageTracker instead of implementing a new one
from ..core.token_tracking import get_token_tracker, TokenUsageTool

# Example usage in ReadURLTool
def forward(self, url: str, output_format: Optional[str] = "markdown", ...):
    # ...processing logic...
    
    # After successful read, track token usage using the shared component
    if result.success and result.metadata and 'usage' in result.metadata:
        tokens = result.metadata['usage'].get('tokens', 0)
        
        # Use the shared token tracker
        tracker = get_token_tracker()
        tracker.track_usage(
            tool=TokenUsageTool.READ,
            usage_data={
                'prompt_tokens': len(url),
                'completion_tokens': tokens,
                'total_tokens': tokens
            },
            metadata={
                'url': url,
                'format': output_format
            }
        )
```

## 4. Improved Error Handling

```python
async def scrape(
    self,
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    attempt: int = 0
) -> ExtractionResult:
    # ...existing code...
    
    try:
        # ...request code...
        
        async with session.post(
            self.api_base_url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                # Enhanced error handling like in TS implementation
                error_msg = ""
                error_data = None
                
                try:
                    error_data = await response.json()
                except:
                    error_text = await response.text()
                    error_msg = f"Jina Reader API returned HTTP error: {response.status}. Response: {error_text}"
                
                if error_data:
                    readable_message = error_data.get('readableMessage')
                    if response.status == 402:
                        error_msg = readable_message or "Insufficient balance"
                    else:
                        error_msg = readable_message or f"HTTP Error {response.status}"
                
                # If the error is retryable, do exponential backoff retry
                if (response.status in (429, 500, 502, 503, 504) and attempt < self.retry_attempts):
                    wait_time = 2 ** attempt
                    print(f"Waiting {wait_time} seconds before retrying {url}")
                    await asyncio.sleep(wait_time)
                    return await self.scrape(url, session, attempt + 1)
                
                print(error_msg)
                return ExtractionResult(
                    name="jina_reader",
                    success=False,
                    error=error_msg
                )
```

## 5. ReadURLTool Interface Update

```python
# Update the ReadURLTool inputs
inputs = {
    "url": {
        "type": "string",
        "description": "The URL to read content from.",
    },
    "output_format": {
        "type": "string",
        "description": "Desired output format (e.g., 'markdown', 'text').",
        "default": "markdown",
        "nullable": True,
    },
    "with_all_links": {
        "type": "boolean",
        "description": "Whether to include a summary of all links in the page.",
        "default": False,
        "nullable": True,
    },
    "retain_images": {
        "type": "string",
        "description": "Image retention mode ('none', 'all', 'important').",
        "default": "none",
        "nullable": True,
    },
    "md_link_style": {
        "type": "string",
        "description": "Markdown link style ('standard', 'discarded', 'footnote').",
        "default": "discarded",
        "nullable": True,
    }
}

# Update forward method to support new parameters
def forward(
    self,
    url: str,
    output_format: Optional[str] = "markdown",
    with_all_links: Optional[bool] = False,
    retain_images: Optional[str] = "none",
    md_link_style: Optional[str] = "discarded"
) -> str:
    """
    Reads the content of a given URL and returns the processed text.

    Args:
        url (str): The URL to read content from.
        output_format (str, optional): The output format. Default is 'markdown'.
        with_all_links (bool, optional): Whether to include all links. Default is False.
        retain_images (str, optional): Image retention mode. Default is 'none'.
        md_link_style (str, optional): Markdown link style. Default is 'discarded'.

    Returns:
        str: The processed content. If reading fails, return an error message string.
    """
    # Combine parameters to pass to scraper
    with_links_summary = "all" if with_all_links else None
    
    # Configure scraper with new parameters
    self._ensure_scraper(
        output_format=output_format,
        retain_images=retain_images,
        md_link_style=md_link_style,
        with_links_summary=with_links_summary
    )
    
    # Continue with existing implementation...
```

## 6. Enhanced Progress Reporting

```python
# Add to ReadURLTool.forward() method
def forward(
    self,
    url: str,
    output_format: Optional[str] = "markdown",
    with_all_links: Optional[bool] = False,
    retain_images: Optional[str] = "none",
    md_link_style: Optional[str] = "discarded"
) -> str:
    # ...validation and setup...
    
    # Add detailed progress logging
    start_time = time.time()
    log_func(f"[bold blue]Starting URL read[/bold blue]: {url}")
    log_func(f"[dim]Parameters: format={output_format}, links={with_all_links}, "
             f"images={retain_images}, link_style={md_link_style}[/dim]")
    
    # ...processing code...
    
    end_time = time.time()
    read_time = end_time - start_time
    
    if result.success:
        metadata = result.metadata or {}
        log_func(
            f"[bold green]URL read completed in {read_time:.2f}s[/bold green]: "
            f"Title: {metadata.get('title', 'N/A')}, "
            f"Tokens: {metadata.get('usage', {}).get('tokens', 0)}"
        )
    else:
        log_func(
            f"[bold red]URL read failed in {read_time:.2f}s[/bold red]: "
            f"{result.error}"
        )
```

## 7. Wikipedia Specific Enhancements

Integrate Wikipedia-specific handling for better results:

```python
# In ReadURLTool class
def forward(
    self,
    url: str,
    output_format: Optional[str] = "markdown",
    with_all_links: Optional[bool] = False,
    retain_images: Optional[str] = "none",
    md_link_style: Optional[str] = "discarded"
) -> str:
    # ...validation...
    
    # Special handling for Wikipedia URLs
    if 'wikipedia.org/wiki/' in url:
        try:
            from ..core.scraping.utils import get_wikipedia_content
            # Try using the specialized Wikipedia function first
            content = get_wikipedia_content(url)
            if content:
                log_func("[bold blue]Using optimized Wikipedia extraction[/bold blue]")
                # Process content into desired format
                return content
                
        except Exception as e:
            log_func(f"[yellow]Wikipedia extraction failed, falling back to Reader API: {e}[/yellow]")
            # Continue with regular processing if Wikipedia-specific extraction fails
```

## 8. Response Data Enrichment

```python
# In scraper.py - enhance ExtractionResult class
class EnhancedExtractionResult(ExtractionResult):
    """Enhanced extraction result with additional metadata"""
    def __init__(
        self,
        name: str,
        success: bool,
        content: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
        links: Optional[List[tuple]] = None,
        response_time: float = 0.0
    ):
        super().__init__(name, success, content, error, metadata)
        self.links = links or []  # List of [anchor, url] tuples
        self.response_time = response_time
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the extraction result"""
        result = {
            "success": self.success,
            "response_time": self.response_time,
        }
        
        if self.success:
            result.update({
                "title": self.metadata.get("title", ""),
                "content_length": len(self.content or ""),
                "token_count": self.metadata.get("usage", {}).get("tokens", 0),
                "link_count": len(self.links)
            })
        else:
            result["error"] = self.error
            
        return result
```

## 9. Optimized Timeout and Concurrency Settings

```python
# Adjust timeout and connection pooling settings
class JinaReaderScraper:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "readerlm-v2",
        output_format: str = "markdown",
        api_base_url: str = "https://r.jina.ai/",
        max_concurrent_requests: int = 5,
        timeout: int = 60,  # Reduced from 600 to 60 seconds
        retry_attempts: int = 2,
        # ...other parameters...
    ):
        # ...existing code...
        
        # Configure connection pool for better performance
        self.connector = aiohttp.TCPConnector(
            limit=max_concurrent_requests,
            limit_per_host=max_concurrent_requests,
            enable_cleanup_closed=True
        )
```

## 10. Token Budget Management

Use the shared TokenUsageTracker for token budget management:

```python
class ReadURLTool(Tool):
    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        reader_model: str = "readerlm-v2",
        cli_console=None,
        verbose: bool = False,
        token_budget: Optional[int] = None  # Add token budget parameter
    ):
        # ...existing code...
        
        # Use the shared token tracker with the provided budget
        from ..core.token_tracking import get_token_tracker
        self.token_tracker = get_token_tracker(budget=token_budget)
```

## Iteration Requirements Summary

1. Implement enhanced URL validation to catch problematic URLs early
2. Add extended header options for greater configuration flexibility
3. **[DEPENDENCY]** Integrate shared TokenUsageTracker component from [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md)
4. Improve error handling with detailed error types and messages
5. Update ReadURLTool interface to support more configuration options
6. Add enhanced progress reporting for better visibility
7. Implement Wikipedia-specific optimizations for better results
8. Enrich response data with additional metadata and summaries
9. Optimize timeout and concurrency settings for better performance
10. Utilize the shared TokenUsageTracker for global budget management

By implementing these improvements, our ReadURL Agent Tools will become more flexible, robust, and efficient while providing better error handling and monitoring capabilities.

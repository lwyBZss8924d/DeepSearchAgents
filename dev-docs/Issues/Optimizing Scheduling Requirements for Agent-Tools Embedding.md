# TODO: Optimizing Scheduling Requirements for Agent-Tools Embedding

> **NOTE**: This optimization REQUIRES the implementation of [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md) component first.

Our current `jina_embedder.py` and `embed.py` scripts require updates to meet new scheduling optimization needs:

## 1. Batch Processing and Retry Mechanism Optimization

```python
# Current batch processing logic is not robust enough
batches = [inputs[i:i + batch_size] for i in range(0, len(inputs), batch_size)]

# Suggested improvement: Add fixed batch size constant and more robust retry logic
BATCH_SIZE = 128  # Batch size borrowed from TS implementation
MAX_RETRIES = 3  # Maximum retry attempts
```

The batch processing and retry logic implementation needs to be more robust, particularly:

- Use a fixed batch size (128) instead of the current parameterized batch size
- Implement a dedicated retry mechanism for missing embedding indices
- Strictly maintain index mapping to ensure returned results match input order

## 2. Missing Embeddings Handling Mechanism

Add a more elegant handling method for missing embeddings:

```python
# Add similar logic
def _handle_missing_embeddings(
    self,
    received_embeddings: List[Any],
    original_texts: List[str],
    dimensions: int = 512
) -> List[List[float]]:
    """Handle missing embeddings in the response"""
    result = [None] * len(original_texts)  # Pre-allocate result array
    missing_indices = []
    
    # Fill in received embeddings
    for item in received_embeddings:
        if "index" in item and "embedding" in item:
            result[item["index"]] = item["embedding"]
    
    # Detect and handle missing embeddings
    for i, r in enumerate(result):
        if r is None:
            missing_indices.append(i)
            result[i] = [0.0] * dimensions  # Zero vector placeholder
            
    if missing_indices:
        print(f"Warning: {len(missing_indices)} embeddings are missing, replaced with zero vectors")
        
    return result
```

## 3. Token Usage Tracking

Use the shared TokenUsageTracker component as defined in [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md):

```python
# Import shared token tracking component
from ..core.token_tracking import get_token_tracker, TokenUsageTool

# Add to JinaAIEmbedder
def _track_token_usage(self, usage_data: Dict[str, int], metadata: Optional[Dict[str, Any]] = None):
    """Track token usage using shared component"""
    tracker = get_token_tracker()
    tracker.track_usage(
        tool=TokenUsageTool.EMBED,
        usage_data=usage_data,
        metadata=metadata
    )
```

## 4. Support for More Embedding Task Options

Add support for various embedding task types:

```python
# Explicitly support these options in the tool interface
inputs = {
    # ...existing options...
    "task": {
        "type": "string",
        "description": "Embedding task type: text-matching, retrieval.query, retrieval.passage",
        "enum": ["text-matching", "retrieval.query", "retrieval.passage"],
        "default": "text-matching",
    },
    "late_chunking": {
        "type": "boolean",
        "description": "Whether to enable late chunking",
        "default": False,
    }
}
```

## 5. Detailed Embedding Tools Progress Reporting

Add more detailed batch processing progress reporting:

```python
# Add when processing large batches
async def _process_batch_with_progress(
    self, 
    batch: List[str], 
    current_batch: int, 
    total_batches: int,
    **kwargs
):
    """Process a single batch and report progress"""
    print(f"[embedding] Processing batch {current_batch}/{total_batches} ({len(batch)} texts)")
    
    # Batch processing code...
    
    print(f"[embedding] Batch {current_batch} complete. Tokens used: {batch_tokens}")
```

## 6. Improved Error Handling

Optimize for more detailed error handling:

```python
# Add more detailed error handling
async def _process_batch(self, session, data, semaphore):
    """Process a batch of embedding requests"""
    retry_count = 0
    while retry_count <= self.max_retries:
        try:
            # Existing request code...
        except aiohttp.ClientError as e:
            # Existing basic error handling
            
            # Add handling for specific errors
            if isinstance(e, aiohttp.ClientResponseError):
                if e.status == 402:  # Jina API balance insufficient error
                    print("API key quota has been exhausted, cannot continue processing")
                    return []  # Or throw a specific exception
                elif e.status == 429:  # Rate limit
                    wait_time = 2 ** retry_count
                    print(f"Rate limit encountered, waiting {wait_time} seconds before retry")
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue
```

## 7. CodeAct Agent Embedding Tools Optimization

Update the tool description in `codact_prompts.py` to clearly specify new features:

```python
# Update tool description in CODACT_SYSTEM_EXTENSION
*   `embed_texts(texts: List[str], task: str = "text-matching", 
    dimensions: int = 512) -> List[List[float]]:`
    Creates vector embeddings for texts. Supports various task types (text-matching,
    retrieval.query, retrieval.passage) and dimension adjustment.
```

## Iteration Requirements Summary

1. Optimize batch processing and retry mechanism
2. Optimize precise index tracking and missing embedding handling
3. **[DEPENDENCY]** Integrate shared TokenUsageTracker component from [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md)
4. Implement more comprehensive embedding task type support
5. Add detailed batch processing progress tracking and logging
6. Implement specific handling strategies for different error types

By implementing these improvements, our Embedding Agent Tools (`jina_embedder.py` and `embed.py`) will become more robust and feature-complete, especially when handling large-scale embedding requests. 
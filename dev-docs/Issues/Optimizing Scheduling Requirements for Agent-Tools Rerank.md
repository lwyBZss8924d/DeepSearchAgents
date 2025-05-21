# TODO: Optimizing Scheduling Requirements for Agent-Tools Rerank

> **NOTE**: This optimization REQUIRES the implementation of [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md) component first.

Our current `jina_reranker.py` and `rerank.py` scripts require updates to meet new scheduling optimization needs:

## 1. Batch Processing Strategy Enhancement

```python
# Increase batch size from 100 to 2000 for large-scale document reranking
BATCH_SIZE = 2000

# Adjust batch size during class initialization or configuration
def __init__(self, ..., batch_size: int = 2000):
    # Existing code...
    self.batch_size = batch_size
```

## 2. Token Usage Tracking

Use the shared TokenUsageTracker component as defined in [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md):

```python
# Import shared token tracking component
from ..core.token_tracking import get_token_tracker, TokenUsageTool

# Example usage in JinaReranker
def _track_rerank_usage(self, usage_data: Dict[str, int], metadata: Optional[Dict[str, Any]] = None):
    """Track token usage for reranking operations"""
    tracker = get_token_tracker()
    tracker.track_usage(
        tool=TokenUsageTool.RERANK,
        usage_data=usage_data,
        metadata=metadata
    )
```

## 3. Parallel Processing Improvements

Batch parallel processing can be optimized as follows:

```python
# Replace the current batch processing method in rerank_async

async def rerank_async(self, query: str, documents: List[Union[str, Dict[str, Any]]], ...):

# ...existing code...

# Create tasks for all batches

tasks = []

for i, batch in enumerate(batches):

    start_idx = i * self.batch_size

    tasks.append(self._process_batch(

        session, query, batch, top_n, start_idx, query_image_url

    ))

# Execute all batches fully in parallel (without semaphore restrictions)

all_batch_results = await asyncio.gather(*tasks, return_exceptions=True)

# Handle results and errors

all_results = []

for i, result in enumerate(all_batch_results):

    if isinstance(result, Exception):

        print(f"Batch {i+1}/{len(batches)} failed: {str(result)}")

        continue

    all_results.extend(result)

# Sort all results by relevance score

all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

# If top_n results are needed, truncate

if top_n and len(all_results) > top_n:

    return all_results[:top_n]

return all_results
```

## 4. Optimization of Original Index Mapping

Maintain a clearer mapping to the original indices during batch processing:

```python
async def _process_batch(self, session, query, batch, top_n, start_idx, query_image_url=None):
    """Process a single batch and preserve the original index mapping"""

    # ...existing code...

    results = []

    for item in api_result['results']:

        # Preserve the original index mapping

        original_index = start_idx + item.get('index', 0)

        # Extract document content

        # ...existing code...

        results.append({

            "document": doc_content,

            "relevance_score": item.get('relevance_score', 0),

            "index": original_index,  # Use original index

            "batch_index": item.get('index', 0)  # Optional: keep batch-internal index

        })

    return results
```

## 5. Simplified Error Handling

Optimize error handling logic in some scenarios:

```python
# In certain cases, error handling can be simplified

try:

    # Some less critical operations

    result = await self._try_operation()

    return result

except Exception as e:

    print(f"Operation failed: {str(e)}")

    # Simply return an empty result instead of raising an exception

    return []

```

## 6. Tool Interface Extension

Update the `RerankTextsTool` class to support new features:

```python
inputs = {

    # ...existing inputs...

    "batch_size": {

        "type": "integer",

        "description": "Batch size, default is 2000",

        "default": 2000,

        "nullable": True,

    },

    "track_tokens": {

        "type": "boolean",

        "description": "Whether to track token usage",

        "default": True,

        "nullable": True,

    }

}

# Update the forward method to accept new parameters

def forward(

    self,

    query: str,

    texts: str,

    model: Optional[str] = None,

    top_n: Optional[int] = None,

    query_image_url: Optional[str] = None,

    batch_size: Optional[int] = 2000,

    track_tokens: Optional[bool] = True

) -> str:

    # ...existing code...

```

## Iteration Requirements Summary

1. Larger batch size (2000 vs 100)
2. **[DEPENDENCY]** Integrate shared TokenUsageTracker component from [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md)
3. More direct batch parallel processing
4. Clearer original index mapping
5. Optimization for large-scale document sets

By implementing these improvements, our Rerank Agent Tools will be able to better handle large-scale document reranking tasks, while also providing more comprehensive token usage tracking and error handling mechanisms.

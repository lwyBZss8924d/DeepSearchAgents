# TODO: Optimizing Scheduling Requirements for Agent-Tools Chunking

> **NOTE**: This optimization REQUIRES the implementation of [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md) component first.

Our current `segmenter.py` and `chunk.py` require updates to meet new scheduling optimization needs and incorporate Jina AI's latest segmentation improvements:

## 1. Intelligent Large Text Handling

```python
# Implement smart batch handling for large documents
def split_text_into_batches(text: str, max_batch_size: int = 60000) -> List[str]:
    """
    Smart splitting of large texts, preferably at paragraph, newline, or sentence boundaries
    """
    batches = []
    current_index = 0
    
    while current_index < len(text):
        if current_index + max_batch_size >= len(text):
            # If remaining text fits in one batch, add it and complete
            batches.append(text[current_index:])
            break
            
        # Find appropriate split point, preferably at paragraph breaks
        end_index = current_index + max_batch_size
        
        # Try to find paragraph separators (double newline)
        paragraph_break = text.rfind('\n\n', current_index, end_index)
        if paragraph_break > current_index and paragraph_break <= end_index - 10:
            # Found paragraph separator without causing tiny splits at the end
            end_index = paragraph_break + 2  # Include double newline
        else:
            # If no paragraph separator, try single newline
            newline_index = text.rfind('\n', current_index, end_index)
            if newline_index > current_index and newline_index <= end_index - 5:
                end_index = newline_index + 1  # Include newline
            else:
                # Try splitting at sentence boundaries
                sentence_break = _find_last_sentence_break(text, current_index, end_index)
                if sentence_break > current_index:
                    end_index = sentence_break
                # If no good boundaries found, use max batch size
        
        batches.append(text[current_index:end_index])
        current_index = end_index
        
    return batches
```

## 2. Position Tracking & Adjustment

Add detailed position tracking to preserve original text locations:

```python
async def split_large_text_async(
    self,
    text: str,
    max_chunk_length: int = 500,
    return_tokens: bool = False
) -> Dict[str, Any]:
    """Process large text with adjusted chunk positions"""
    # Maximum batch size (slightly under 64KB for safety)
    MAX_BATCH_SIZE = 60000
    
    # Split text into batches
    batches = self.split_text_into_batches(text, MAX_BATCH_SIZE)
    print(f"Split content into {len(batches)} batches")
    
    # Calculate offsets for each batch upfront
    batch_offsets = []
    current_offset = 0
    for batch in batches:
        batch_offsets.append(current_offset)
        current_offset += len(batch)
    
    # Process batches in parallel
    all_chunks = []
    all_chunk_positions = []
    total_tokens = 0
    
    tasks = []
    for i, batch in enumerate(batches):
        tasks.append(self._process_batch_with_position(
            batch, i, len(batches), batch_offsets[i], 
            max_chunk_length, return_tokens
        ))
    
    # Wait for all batches to complete
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Aggregate results
    for i, result in enumerate(batch_results):
        if isinstance(result, Exception):
            print(f"Batch {i+1} processing failed: {str(result)}")
            continue
            
        if 'chunks' in result:
            all_chunks.extend(result['chunks'])
        if 'positions' in result:
            all_chunk_positions.extend(result['positions'])
        if 'tokens' in result:
            total_tokens += result['tokens']
    
    return {
        "chunks": all_chunks,
        "chunk_positions": all_chunk_positions,
        "total_tokens": total_tokens
    }
```

## 3. Token Usage Tracking

Use the shared TokenUsageTracker component as defined in [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md):

```python
# Import shared token tracking component
from ..core.token_tracking import get_token_tracker, TokenUsageTool

# Track segmentation token usage
def _track_segmentation_usage(self, tokens: int, chars: int, chunks: int):
    """Track token usage for segmentation operations"""
    tracker = get_token_tracker()
    
    # Convert character count to approximate prompt tokens
    prompt_tokens = chars // 4  # Rough estimate
    
    tracker.track_usage(
        tool=TokenUsageTool.CHUNK,
        usage_data={
            'prompt_tokens': prompt_tokens,
            'completion_tokens': tokens - prompt_tokens,
            'total_tokens': tokens
        },
        metadata={
            'input_chars': chars,
            'chunk_count': chunks
        }
    )
```

## 4. Enhanced Error Handling

Implement more detailed error handling:

```python
def _handle_segmentation_error(self, error):
    """Handle segmentation API errors"""
    if isinstance(error, aiohttp.ClientResponseError):
        if error.status == 402:
            # Insufficient balance error
            raise ValueError("API balance insufficient, cannot continue processing")
        elif error.status == 429:
            # Rate limit error
            raise ValueError("Rate limit exceeded, please try again later")
        else:
            raise ValueError(f"HTTP Error {error.status}: {error.message}")
    elif isinstance(error, aiohttp.ClientConnectionError):
        raise ConnectionError("Cannot connect to server")
    elif isinstance(error, asyncio.TimeoutError):
        raise TimeoutError("Request timed out")
    else:
        raise error
```

## 5. Advanced Segmentation Models Support

Add support for Jina AI's new text segmentation models:

```python
def __init__(
    self,
    api_key: Optional[str] = None,
    segmentation_method: str = "default",  # "default", "topic", "simple", or "summary"
    tokenizer: str = "o200k_base",
    api_base_url: str = "https://api.jina.ai/v1/segment",
    max_concurrent_requests: int = 3,
    timeout: int = 600,
    retry_attempts: int = 2
):
    """
    Initialize JinaAISegmenter with segmentation method selection.
    
    Available methods:
    - "default": Standard Jina API segmentation
    - "topic": Topic-based segmentation (using topic-qwen-0.5 model)
    - "simple": Structure-based segmentation (using simple-qwen-0.5 model)
    - "summary": Summary-based segmentation (using summary-qwen-0.5 model)
    """
    # Get your Jina AI API key for free: https://jina.ai/?sui=apikey
    if api_key is None:
        load_dotenv()
        api_key = os.getenv('JINA_API_KEY')
        if not api_key:
            raise ValueError(
                "No API key provided, and JINA_API_KEY not found in "
                "environment variables"
            )
            
    self.segmentation_method = segmentation_method
    # Map segmentation methods to appropriate endpoints/parameters
    if self.segmentation_method != "default":
        # Configure for specialized models
        self._configure_advanced_segmentation()
```

## 6. Late Chunking Integration

Implement "late chunking" support using Jina AI's V3 embeddings:

```python
def split_text_with_late_chunking(
    self,
    text: str,
    max_chunk_length: int = 500,
    enable_late_chunking: bool = True
) -> Dict[str, Any]:
    """
    Split text with late chunking support.
    
    Late chunking preserves context during embedding by passing additional
    contextual information to the embedding model, improving performance
    while maintaining semantic coherence.
    
    Args:
        text: Text to segment
        max_chunk_length: Maximum chunk length
        enable_late_chunking: Whether to enable late chunking
        
    Returns:
        Dictionary containing chunks, positions, and metadata
    """
    chunks_data = self.split_large_text(
        text=text,
        max_chunk_length=max_chunk_length
    )
    
    if enable_late_chunking:
        # Add metadata for late chunking
        for i, _ in enumerate(chunks_data["chunks"]):
            # Determine chunk boundaries
            start_pos, end_pos = chunks_data["chunk_positions"][i]
            
            # Add context information (e.g., preceding and following chunks)
            prev_idx = max(0, i-1)
            next_idx = min(len(chunks_data["chunks"])-1, i+1)
            
            chunks_data["context_info"] = {
                "prev_chunk": chunks_data["chunks"][prev_idx] if prev_idx != i else "",
                "next_chunk": chunks_data["chunks"][next_idx] if next_idx != i else "",
                "original_position": (start_pos, end_pos)
            }
    
    return chunks_data
```

## 7. ChunkTextTool Interface Extension

Update the ChunkTextTool class to support new features:

```python
# Update the ChunkTextTool inputs
inputs = {
    "text": {
        "type": "string",
        "description": "The long text to be chunked.",
    },
    "chunk_size": {
        "type": "integer",
        "description": "Target size for each chunk.",
        "default": 150,
        "nullable": True,
    },
    "chunk_overlap": {
        "type": "integer",
        "description": "Number of characters to overlap between chunks.",
        "default": 50,
        "nullable": True,
    },
    "return_positions": {
        "type": "boolean",
        "description": "Whether to return chunk positions in the original text.",
        "default": False,
        "nullable": True,
    },
    "segmentation_method": {
        "type": "string",
        "description": "Segmentation method to use: default, topic, simple, or summary.",
        "default": "default",
        "enum": ["default", "topic", "simple", "summary"],
        "nullable": True,
    },
    "enable_late_chunking": {
        "type": "boolean",
        "description": "Whether to enable late chunking for better context preservation.",
        "default": False,
        "nullable": True,
    }
}

# Update forward method to support new parameters
def forward(
    self,
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    return_positions: Optional[bool] = False,
    segmentation_method: Optional[str] = "default",
    enable_late_chunking: Optional[bool] = False
) -> str:
    """
    Execute text chunking with advanced options.
    
    Args:
        text: Text to be chunked
        chunk_size: Chunk size
        chunk_overlap: Chunk overlap
        return_positions: Whether to return chunk positions
        segmentation_method: Segmentation method to use
        enable_late_chunking: Whether to enable late chunking
        
    Returns:
        JSON string containing the results
    """
```

## 8. Detailed Progress Reporting

Enhance progress reporting for better visibility:

```python
async def _process_batch_with_position(
    self,
    batch: str,
    batch_index: int,
    total_batches: int,
    offset: int,
    max_chunk_length: int,
    return_tokens: bool
) -> Dict[str, Any]:
    """Process batch and report progress"""
    print(f"[segmenter] Processing batch {batch_index + 1}/{total_batches} (size: {len(batch)})")
    
    try:
        # Process batch code...
        
        # Get batch offset and adjust chunk positions
        adjusted_positions = []
        if 'chunk_positions' in api_result:
            for position in api_result['chunk_positions']:
                adjusted_positions.append([
                    position[0] + offset,
                    position[1] + offset
                ])
        
        print(f"Batch {batch_index + 1} results: "
              f"chunks: {len(api_result.get('chunks', []))}, "
              f"tokens: {api_result.get('num_tokens', 0)}")
        
        return {
            'chunks': api_result.get('chunks', []),
            'positions': adjusted_positions,
            'tokens': api_result.get('usage', {}).get('tokens', 0)
        }
    
    except Exception as e:
        self._handle_segmentation_error(e)
```

## 9. Support for Multi-Model Tokenizers

Enhance tokenizer selection and configuration:

```python
def _configure_tokenizer(self, tokenizer: str):
    """Configure tokenizer settings"""
    valid_tokenizers = ["cl100k_base", "o200k_base", "p50k_base", 
                         "r50k_base", "p50k_edit", "gpt2"]
    
    if tokenizer not in valid_tokenizers:
        print(f"Warning: Unknown tokenizer '{tokenizer}'. Falling back to o200k_base")
        self.tokenizer = "o200k_base"
    else:
        self.tokenizer = tokenizer
        
    # Map tokenizers to their approximate token limits
    self.tokenizer_limits = {
        "cl100k_base": 8192,  # OpenAI's cl100k (ChatGPT)
        "o200k_base": 200000, # Jina o200k
        "p50k_base": 50000,   # GPT-3
        "r50k_base": 50000,   # GPT-4 early
        "p50k_edit": 50000,   # Codex
        "gpt2": 1024          # Original GPT-2
    }
    
    # Set approximate token limit for selected tokenizer
    self.token_limit = self.tokenizer_limits.get(self.tokenizer, 8192)
```

## 10. Integration with Jina AI's Latest Segmentation Research

Implement findings from Jina AI's research:

```python
def _configure_advanced_segmentation(self):
    """Configure advanced segmentation based on method"""
    if self.segmentation_method == "topic":
        # Topic-based segmentation (topic-qwen-0.5)
        # Identifies topics within text and creates segments based on topic boundaries
        self.model_id = "jinaai/text-seg-lm-qwen2-0.5b-cot-topic-chunking"
        self.use_external_model = True
    elif self.segmentation_method == "simple":
        # Structure-based segmentation (simple-qwen-0.5)
        # Segments based on structural elements of the document
        self.model_id = "jinaai/text-seg-lm-qwen2-0.5b"
        self.use_external_model = True
    elif self.segmentation_method == "summary":
        # Summary-based segmentation (summary-qwen-0.5)
        # Generates summaries for each segment
        self.model_id = "jinaai/text-seg-lm-qwen2-0.5b-summary-chunking"
        self.use_external_model = True
        self.generate_summaries = True
    else:
        # Default Jina API segmentation
        self.use_external_model = False
        self.generate_summaries = False
```

## Iteration Requirements Summary

1. Implement intelligent large text handling with natural boundary detection
2. Add position tracking to preserve original text locations
3. **[DEPENDENCY]** Integrate shared TokenUsageTracker component from [P1-Optimizing Shared TokenUsageTracker](P1-Optimizing%20Shared%20TokenUsageTracker.md)
4. Enhance error handling for specific error conditions
5. Add support for Jina AI's specialized segmentation models
6. Implement "late chunking" integration for better context preservation
7. Extend ChunkTextTool interface with new options
8. Add detailed progress reporting for visibility
9. Add support for multiple tokenizers with appropriate configurations
10. Integrate Jina AI's latest research findings on optimal text segmentation

By implementing these improvements, our Chunking Agent Tools (`segmenter.py` and `chunk.py`) will significantly improve in handling large documents, preserving context, and providing better segmentation options for different use cases - especially for RAG applications and other downstream tasks.

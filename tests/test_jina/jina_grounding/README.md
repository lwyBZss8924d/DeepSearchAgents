# Jina Grounding API as LangChain Retriever

This directory contains an implementation of Jina's Grounding API (`g.jina.ai`) as a custom LangChain retriever, enabling fact-checking functionality within the LangChain ecosystem.

## Overview

The Jina Grounding API is a fact-checking service that:
- Takes a statement as input
- Cross-references it with current web data
- Returns a factuality score (0-1) and supporting/contradicting references
- Provides detailed reasoning about the statement's truthfulness

By implementing it as a LangChain retriever, we can:
- Use it in retrieval-augmented generation (RAG) pipelines
- Integrate with QA chains for fact-aware responses
- Combine with other retrievers for hybrid search
- Build fact-checking applications using LangChain tools

## Files

- `jina_grounding_retriever.py` - The custom retriever implementation
- `test_grounding_retriever.py` - Comprehensive test suite
- `examples.py` - Usage examples and integration patterns
- `Jina-Grounding-API.md` - Official API documentation

## Installation

```bash
pip install langchain-core langchain-community requests aiohttp pydantic
```

## Quick Start

1. Get a Jina AI API key (free): https://jina.ai/?sui=apikey
2. Set the environment variable:
   ```bash
   export JINA_API_KEY="your-api-key"
   ```
3. Use the retriever:
   ```python
   from jina_grounding_retriever import create_jina_grounding_retriever
   
   retriever = create_jina_grounding_retriever(api_key="your-key")
   docs = retriever.invoke("The Earth is round")  # Use invoke() instead of get_relevant_documents()
   
   # Check results
   factuality = docs[0].metadata["factuality_score"]  # 0.95
   result = docs[0].metadata["grounding_result"]       # True
   ```

## ⚠️ Important: Method Deprecation Notice

As of LangChain v0.1.46, the `get_relevant_documents()` method is deprecated. Use the modern Runnable interface instead:

```python
# ❌ Deprecated (will be removed in LangChain 1.0)
docs = retriever.get_relevant_documents("statement")

# ✅ Recommended
docs = retriever.invoke("statement")

# For async operations:
# ❌ Deprecated
docs = await retriever.aget_relevant_documents("statement")

# ✅ Recommended
docs = await retriever.ainvoke("statement")
```

## How It Works

### Retriever Interface

The `JinaGroundingRetriever` implements LangChain's `BaseRetriever`:
- **Input**: A statement to fact-check (query string)
- **Output**: List of `Document` objects with:
  - `page_content`: Key quote from the reference
  - `metadata`: Rich metadata including URL, factuality score, support status

### Document Structure

Each returned document contains:
```python
Document(
    page_content="The quoted text from the source",
    metadata={
        "source": "https://example.com/article",
        "statement": "Original statement checked",
        "is_supportive": True,  # or False
        "factuality_score": 0.95,  # Overall score (0-1)
        "grounding_result": True,  # Final verdict
        "reason": "Detailed explanation...",  # Optional
        "token_usage": 12345
    }
)
```

## Usage Examples

### 1. Simple Fact-Checking

```python
from jina_grounding_retriever import create_jina_grounding_retriever

retriever = create_jina_grounding_retriever(api_key="your-key")
docs = retriever.invoke("Python was created in 1991")

for doc in docs:
    print(f"Source: {doc.metadata['source']}")
    print(f"Quote: {doc.page_content}")
    print(f"Supports: {doc.metadata['is_supportive']}")
```

### 2. With QA Chains

```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

retriever = create_jina_grounding_retriever(api_key="your-key")
llm = ChatOpenAI()

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

result = qa_chain("Is the Great Wall of China visible from space?")
```

### 3. Async Operations

```python
import asyncio

retriever = create_jina_grounding_retriever(api_key="your-key")

async def check_facts():
    docs = await retriever.ainvoke("AI will replace all jobs")
    return docs

docs = asyncio.run(check_facts())
```

### 4. Custom Trusted Sources

```python
retriever = create_jina_grounding_retriever(
    api_key="your-key",
    trusted_references=[
        "https://www.nature.com",
        "https://www.science.org",
        "https://arxiv.org"
    ]
)
```

## Configuration Options

- `api_key`: Jina AI API key (required)
- `base_url`: API endpoint (default: "https://g.jina.ai")
- `include_reason`: Include full reasoning in metadata (default: True)
- `trusted_references`: List of trusted websites (optional)
- `timeout`: Request timeout in seconds (default: 120)
- `verbose`: Enable verbose logging through callback manager (default: False)
- `max_retries`: Maximum number of retries for API calls (default: 3)
- `retry_delay`: Initial delay between retries in seconds (default: 1.0)

## Enhanced Features

### Verbose Mode and Callback Support
The retriever now supports verbose logging through LangChain's callback system:

```python
from langchain_core.callbacks import StdOutCallbackHandler

retriever = create_jina_grounding_retriever(
    api_key="your-key",
    verbose=True,
    callbacks=[StdOutCallbackHandler()]
)

# Verbose output will show:
# - Statement being fact-checked
# - API calls and retries
# - Response details (factuality score, reference count)
# - Final document count
```

### Retry Logic with Exponential Backoff
Automatic retry for transient failures:

```python
retriever = create_jina_grounding_retriever(
    api_key="your-key",
    max_retries=3,      # Retry up to 3 times
    retry_delay=1.0,    # Start with 1 second delay
    verbose=True        # See retry attempts
)
```

### Enhanced Error Handling
Custom exceptions for better error identification:
- `JinaGroundingAPIError`: Base exception for API errors
- `JinaGroundingTimeoutError`: Request timeout errors
- `JinaGroundingRateLimitError`: Rate limit errors

## Testing

Run the test suite:
```bash
python test_grounding_retriever.py
```

Run the examples:
```bash
python examples.py
```

Test verbose mode and callbacks:
```bash
python test_verbose_callback.py
```

## API Costs

- Jina provides 1M free tokens for initial use
- Each grounding request costs approximately $0.006
- Token usage is included in document metadata

## Limitations

1. **Latency**: Requests can take 30+ seconds for complex fact-checking
2. **Token Usage**: Each request uses 100k-300k tokens
3. **Scope**: Best for factual statements, not opinions or predictions
4. **Rate Limits**: Check Jina's documentation for current limits

## Integration Patterns

### Hybrid Retrieval
Combine fact-checking with other sources:
```python
from langchain.retrievers import EnsembleRetriever

fact_retriever = create_jina_grounding_retriever(api_key="key")
kb_retriever = your_knowledge_base_retriever

ensemble = EnsembleRetriever(
    retrievers=[fact_retriever, kb_retriever],
    weights=[0.7, 0.3]  # Prioritize fact-checking
)
```

### Fact-Aware Chatbot
Build a chatbot that fact-checks its responses:
```python
def fact_check_response(statement):
    docs = retriever.get_relevant_documents(statement)
    factuality = docs[0].metadata["factuality_score"]
    
    if factuality < 0.5:
        return f"⚠️ Low confidence ({factuality:.0%}): {statement}"
    return statement
```

## Troubleshooting

1. **API Key Issues**: Ensure JINA_API_KEY is set correctly
2. **Timeouts**: Increase timeout for complex statements
3. **Empty Results**: Check if statement is too vague or opinion-based
4. **Rate Limits**: Implement retry logic with exponential backoff

## Enhanced Version Available

An enhanced version of the retriever is available with additional features:

### Enhanced Features
- **Session Reuse**: Improved performance through connection pooling
- **Configuration Validation**: Automatic validation with helpful warnings
- **Caching Support**: Optional caching for repeated queries
- **Batch Processing**: Process multiple statements concurrently
- **Better Error Handling**: Custom exceptions for different error types

### Using the Enhanced Retriever

```python
from jina_grounding_retriever_enhanced import create_enhanced_jina_grounding_retriever

# Create enhanced retriever with caching
retriever = create_enhanced_jina_grounding_retriever(
    api_key="your-key",
    enable_caching=True,    # Cache repeated queries
    batch_size=5,           # Process up to 5 queries concurrently
    max_retries=3,          # Retry failed requests
    retry_delay=1.0,        # Initial retry delay
    timeout=120             # Request timeout
)

# Batch process multiple statements
statements = [
    "The Earth is round",
    "Vaccines cause autism",
    "Climate change is real"
]

# Use async batch processing
import asyncio
results = asyncio.run(retriever.abatch(statements))
```

## Performance Tuning Guide

### Optimal Configuration Settings

1. **Timeout Settings**
   ```python
   # For simple fact-checking
   retriever = create_jina_grounding_retriever(
       timeout=60,  # 60 seconds is usually sufficient
       max_retries=2
   )
   
   # For complex statements with many references
   retriever = create_jina_grounding_retriever(
       timeout=120,  # Allow more time
       max_retries=3
   )
   ```

2. **Retry Strategy**
   ```python
   # Conservative retry (recommended)
   retriever = create_jina_grounding_retriever(
       max_retries=3,
       retry_delay=1.0  # Exponential: 1s, 2s, 4s
   )
   
   # Aggressive retry (for critical applications)
   retriever = create_jina_grounding_retriever(
       max_retries=5,
       retry_delay=0.5  # Exponential: 0.5s, 1s, 2s, 4s, 8s
   )
   ```

3. **Batch Processing**
   ```python
   # For high-throughput applications
   retriever = create_enhanced_jina_grounding_retriever(
       batch_size=10,      # Process 10 concurrently
       enable_caching=True # Cache common queries
   )
   ```

### Performance Tips

1. **Use Caching for Repeated Queries**
   - Enable caching when fact-checking similar statements
   - Clear cache periodically with `retriever.clear_cache()`

2. **Session Reuse (Enhanced Version)**
   - The enhanced retriever automatically reuses HTTP sessions
   - Provides 20-30% performance improvement for multiple requests

3. **Batch Processing**
   - Use `abatch_get_relevant_documents()` for multiple statements
   - Processes queries concurrently respecting rate limits

4. **Optimize Trusted References**
   - Fewer trusted references = faster processing
   - Only include highly relevant sources

## Exception Handling Examples

### Basic Error Handling

```python
from jina_grounding_retriever import create_jina_grounding_retriever

retriever = create_jina_grounding_retriever(api_key="your-key")

try:
    docs = retriever.get_relevant_documents("Your statement here")
    # Process results
except ValueError as e:
    print(f"Configuration error: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Enhanced Error Handling

```python
from jina_grounding_retriever_enhanced import (
    create_enhanced_jina_grounding_retriever,
    JinaGroundingAPIError,
    JinaGroundingTimeoutError,
    JinaGroundingRateLimitError
)

retriever = create_enhanced_jina_grounding_retriever(api_key="your-key")

try:
    docs = retriever.get_relevant_documents("Your statement here")
except JinaGroundingTimeoutError as e:
    print(f"Request timed out: {e}")
    # Retry with longer timeout
except JinaGroundingRateLimitError as e:
    print(f"Rate limit hit: {e}")
    # Wait before retrying
except JinaGroundingAPIError as e:
    print(f"API error: {e}")
    # Log and handle gracefully
```

### Async Error Handling

```python
async def safe_fact_check(statement):
    try:
        docs = await retriever.aget_relevant_documents(statement)
        return docs
    except asyncio.TimeoutError:
        print("Async timeout")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

# Handle multiple statements with error recovery
results = await asyncio.gather(
    *[safe_fact_check(stmt) for stmt in statements],
    return_exceptions=False
)
```

## Monitoring and Debugging

### Enable Verbose Logging

```python
# See detailed API interactions
retriever = create_jina_grounding_retriever(
    api_key="your-key",
    verbose=True
)

# With custom callback handler
from langchain_core.callbacks import StdOutCallbackHandler

retriever = create_jina_grounding_retriever(
    api_key="your-key",
    verbose=True,
    callbacks=[StdOutCallbackHandler()]
)
```

### Track Token Usage

```python
docs = retriever.get_relevant_documents("Your statement")

total_tokens = sum(doc.metadata.get("token_usage", 0) for doc in docs)
print(f"Total tokens used: {total_tokens:,}")

# Estimate cost (example rate)
cost = total_tokens * 0.00001  # $0.01 per 1K tokens
print(f"Estimated cost: ${cost:.4f}")
```

## Real-World Integration with LLMs

### Using ChatOpenAI with Structured Output

For production applications, combine the retriever with real LLMs for rich fact-checking analysis:

```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional

# Define structured output
class FactCheckResult(BaseModel):
    statement: str = Field(description="The statement being fact-checked")
    is_factual: bool = Field(description="Whether the statement is factual")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
    reasoning: str = Field(description="Explanation of the result")
    key_evidence: List[str] = Field(description="Key supporting evidence")

# Create LLM with structured output
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_llm = llm.with_structured_output(FactCheckResult)

# Create fact-checking chain
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(
    llm=structured_llm,
    retriever=retriever,
    chain_type="stuff"
)

# Get structured analysis
result = qa_chain.invoke({"query": "Climate change is accelerating"})
print(f"Factual: {result.is_factual} (Confidence: {result.confidence:.0%})")
print(f"Reasoning: {result.reasoning}")
```

### Production Best Practices

1. **Use Real LLMs**: Replace FakeListLLM with ChatOpenAI, Anthropic, or other production LLMs
2. **Implement Structured Output**: Define Pydantic models for consistent fact-checking results
3. **Add Error Handling**: Wrap retriever calls in try-except blocks
4. **Monitor Performance**: Track token usage and API costs
5. **Cache Results**: Use the enhanced retriever with caching for repeated queries

See `test_grounding_with_llm.py` for comprehensive examples of production-ready implementations.

## More Information

- Jina AI Documentation: https://docs.jina.ai
- Get API Key: https://jina.ai/?sui=apikey
- Grounding API Details: See `Jina-Grounding-API.md`
- LangChain Retrievers: https://python.langchain.com/docs/concepts/retrievers/
- Full Examples: See `test_grounding_with_llm.py` for production patterns
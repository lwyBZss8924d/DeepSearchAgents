# Jina DeepSearch API Tests

This directory contains tests and examples for using Jina's DeepSearch API with LangChain.

## Files

- `test_jina_DS_api.py` - Comprehensive LangChain ChatOpenAI test suite for Jina DeepSearch
- `test_langchain_example.py` - Clean examples showing various use cases with LangChain
- `test_langchain_simple.py` - Minimal example for quick testing

## Prerequisites

1. Get a Jina AI API key (free): https://jina.ai/?sui=apikey
2. Set the environment variable:
   ```bash
   export JINA_API_KEY="your-api-key"
   ```
3. Install dependencies:
   ```bash
   pip install langchain-openai requests
   ```

## Running the Tests

### Full Test Suite
```bash
python test_jina_DS_api.py
```

This runs:
- Direct API streaming test
- LangChain basic queries
- Streaming with callbacks
- Structured output with JSON schema
- Advanced search parameters
- Multi-turn conversations
- Async/concurrent queries
- Error handling tests

### LangChain Examples Only
```bash
python test_langchain_example.py
```

This demonstrates:
- Basic queries
- Streaming responses
- Structured outputs
- Advanced search features
- Multi-turn conversations
- Integration with LangChain chains

## Using Jina DeepSearch with LangChain

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Configure ChatOpenAI for Jina DeepSearch
llm = ChatOpenAI(
    model="jina-deepsearch-v2",
    base_url="https://deepsearch.jina.ai/v1",
    api_key="your-jina-api-key",  # type: ignore
    model_kwargs={
        "reasoning_effort": "medium",  # low/medium/high
        "max_returned_urls": 10,      # number of sources
        "no_direct_answer": True,     # force web search
    }
)

# Use it like any LangChain LLM
response = llm.invoke([
    HumanMessage(content="Your question here")
])
print(response.content)
```

## Key Features

### 1. OpenAI-Compatible API
Jina DeepSearch provides an OpenAI-compatible endpoint, making it easy to use with LangChain.

### 2. Advanced Search Parameters
- `reasoning_effort`: Controls search depth (low/medium/high)
- `no_direct_answer`: Forces web search instead of direct answers
- `max_attempts`: Number of search iterations
- `budget_tokens`: Maximum tokens to spend
- `max_returned_urls`: Number of sources to return
- `boost_hostnames`: Prioritize specific domains
- `search_language_code`: Search query language
- `language_code`: Response language

### 3. Structured Output
Use `response_format` with JSON schema for structured responses:

```python
llm = ChatOpenAI(
    model="jina-deepsearch-v2",
    base_url="https://deepsearch.jina.ai/v1",
    api_key=api_key,
    model_kwargs={
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
)
```

### 4. Streaming Support
Enable streaming with callbacks to see responses as they arrive:

```python
from langchain_core.callbacks import BaseCallbackHandler

class StreamHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(token, end='', flush=True)

llm = ChatOpenAI(
    model="jina-deepsearch-v2",
    base_url="https://deepsearch.jina.ai/v1",
    api_key=api_key,
    streaming=True,
    callbacks=[StreamHandler()]
)
```

## Troubleshooting

1. **API Key Issues**: Make sure your JINA_API_KEY is set correctly
2. **Timeouts**: DeepSearch can take time for complex queries. Increase timeout if needed:
   ```python
   llm = ChatOpenAI(..., timeout=600)  # 10 minutes
   ```
3. **Rate Limits**: Check Jina's documentation for rate limits
4. **Type Errors**: Use `# type: ignore` for api_key parameter if you get type errors

## More Information

- Jina AI Documentation: https://docs.jina.ai
- Get API Key: https://jina.ai/?sui=apikey
- DeepSearch API Reference: https://docs.jina.ai/deepsearch
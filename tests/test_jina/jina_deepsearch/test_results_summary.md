# Jina DeepSearch LangChain Test Results Summary

## Test Results Overview

Based on the test execution, here's what works and what doesn't when using Jina DeepSearch through LangChain's ChatOpenAI interface:

### ✅ Working Features

1. **Basic Queries** - Standard question-answering works perfectly
2. **Streaming Responses** - Real-time token streaming with callback handlers
3. **Structured Output** - JSON schema validation for consistent response formats
4. **Multi-turn Conversations** - Context preservation across multiple messages
5. **Async Operations** - Concurrent query execution
6. **Error Handling** - Proper error messages for invalid API keys

### ❌ Limitations

The following DeepSearch-specific parameters are **NOT available** through the OpenAI-compatible endpoint:
- `reasoning_effort` 
- `no_direct_answer`
- `max_attempts`
- `budget_tokens`
- `max_returned_urls`
- `boost_hostnames`
- `search_provider`
- `bad_hostnames`
- `only_hostnames`

These parameters may only be available when using the DeepSearch API directly, not through the OpenAI-compatible interface.

### 💡 Key Insights

1. **DeepSearch Intelligence**: Even without explicit parameters, DeepSearch automatically performs web searches and reasoning when needed based on the query complexity.

2. **Streaming Behavior**: The streaming includes both reasoning tokens (marked with `<think>` tags) and answer tokens, which can be filtered using custom callbacks.

3. **Response Quality**: The responses are comprehensive and include up-to-date information from web searches, demonstrating DeepSearch's real-time capabilities.

### 📝 Recommended Usage

For LangChain integration, use standard ChatOpenAI parameters:

```python
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

chat = ChatOpenAI(
    model="jina-deepsearch-v2",
    base_url="https://deepsearch.jina.ai/v1",
    api_key=SecretStr(your_api_key),
    temperature=0,  # DeepSearch doesn't use temperature but accepts it
    timeout=300,    # Increase for complex queries
    streaming=True  # Enable for real-time responses
)
```

### 🚀 Best Practices

1. **Complex Queries**: Use longer timeouts (300-600 seconds) for research-intensive queries
2. **Structured Output**: Leverage response_format for consistent JSON outputs
3. **Streaming**: Implement custom callbacks to handle reasoning vs answer tokens
4. **Error Handling**: Always wrap API calls in try-except blocks

### 📊 Performance Notes

- Basic queries: ~5-30 seconds
- Complex research queries: ~30-120 seconds
- Streaming provides better UX for long-running queries
- Response sizes can be large (10K-15K characters for comprehensive answers)
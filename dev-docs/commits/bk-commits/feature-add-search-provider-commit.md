# feat: Add hybrid search engine with multiple providers and GitHub repository Q&A tool

## Summary
This feature branch introduces a comprehensive search engine enhancement with multiple provider support, intelligent result aggregation, and GitHub repository analysis capabilities. The implementation provides a unified interface for searching across Google (Serper), X.com (XAI), Jina, and Exa search engines, with automatic deduplication and provider-specific optimizations.

## Key Features

### 1. **Hybrid Search Engine Architecture**
- Created `BaseSearchClient` abstraction for consistent search provider interface
- Implemented `HybridSearchEngine` that aggregates results from multiple providers
- Supports parallel and sequential search execution strategies
- Intelligent URL deduplication and result ranking
- Configurable aggregation strategies: merge, round_robin, priority

### 2. **New Search Providers**
- **JinaSearchClient**: LLM-optimized web search with advanced content extraction
  - Support for markdown/HTML/text content formats
  - Domain-specific search capabilities
  - Enhanced error handling for CloudFlare timeouts (524 errors)
  - Rate limiting: 40 RPM (standard), 400 RPM (premium)
  
- **ExaSearchClient**: Neural search with semantic understanding
  - Supports both keyword and neural search modes
  - Content extraction with autoprompt optimization
  - Domain filtering and date range support
  - Highlights extraction for relevant content snippets

### 3. **GitHub Repository Analysis Tool**
- **GitHubRepoQATool**: AI-powered repository understanding via DeepWiki MCP
  - Three operations: structure, contents, query
  - Repository format validation (owner/repo)
  - Integrated with MCP (Model Context Protocol) server
  - Supports both built-in and MCP configuration modes

### 4. **Search Tool Enhancements**
- **SearchLinksFastTool**: Optimized for speed with simplified interface
- **Search Helper Tools**:
  - `MultiQuerySearchTool`: Execute multiple searches concurrently
  - `DomainSearchTool`: Search within specific domains
  - Convenience functions: `search_code()`, `search_docs()`, `search_recent()`

### 5. **Error Handling Improvements**
- Enhanced HTML error response filtering across all scrapers
- Specific handling for CloudFlare 524 timeout errors
- Clean error messages instead of raw HTML content
- Consistent error response format across providers

## Technical Implementation

### Architecture Changes
```
┌─────────────────────┐
│  HybridSearchEngine │ ← Main aggregator
└──────────┬──────────┘
           │
    ┌──────┴───────┬────────────┬─────────────┐
    │              │            │             │
┌───▼────┐  ┌─────▼─────┐  ┌───▼────┐  ┌────▼────┐
│ Serper │  │    XAI    │  │  Jina  │  │   Exa   │
│(Google)│  │  (X.com)  │  │  (AI)  │  │(Neural) │
└────────┘  └───────────┘  └────────┘  └─────────┘
    ↑              ↑            ↑            ↑
    └──────────────┴────────────┴────────────┘
                BaseSearchClient
```

### New Files Created
1. **Search Engine Core**:
   - `src/core/search_engines/base.py` - BaseSearchClient abstraction and RateLimiter
   - `src/core/search_engines/search_jina.py` - Jina AI search implementation
   - `src/core/search_engines/search_exa.py` - Exa neural search implementation
   - `src/core/search_engines/search_hybrid.py` - Hybrid search aggregator
   - `src/core/search_engines/utils/` - Search utilities and token counting

2. **GitHub Toolkit**:
   - `src/core/github_toolkit/__init__.py` - Package initialization
   - `src/core/github_toolkit/deepwiki.py` - DeepWikiClient wrapper

3. **New Tools**:
   - `src/tools/github_qa.py` - GitHub repository Q&A tool
   - `src/tools/search_fast.py` - Fast search tool implementation
   - `src/tools/search_helpers.py` - Search helper tools

4. **Configuration**:
   - `.cursor/rules/jina-ai-api-rules.mdc` - updated Jina AI API documentation v8

### Modified Files
1. **Search Engine Updates**:
   - `src/core/search_engines/__init__.py` - Added new provider exports
   - `src/core/search_engines/search_serper.py` - Refactored to inherit from BaseSearchClient
   - `src/core/search_engines/search_xcom.py` - Refactored to use xai-sdk
   - `src/core/search_engines/search_xcom_sdk.py` - Split SDK implementation

2. **Tool Registry**:
   - `src/tools/__init__.py` - Added new tool exports
   - `src/tools/toolbox.py` - Added GitHubRepoQATool and icon mapping
   - `src/tools/search.py` - Enhanced with provider selection logic

3. **Agent Updates**:
   - `src/agents/codact_agent.py` - Updated for new tool support
   - `src/agents/prompt_templates/codact_prompts.py` - modified so many things:
      - updated structured code / structured output rules
      - updated Available Advanced Tools overview
      - updated ReAct Planning rules
      - Added GitHub repo analysis rules
      - Added new {CURRENT_TIME} variable
      - more...
   - `src/core/scraping/scraper.py` - Enhanced error handling with HTML cleanup

4. **Configuration**:
   - `config.template.toml` - Added MCP server configuration example
   - `pyproject.toml` - Updated dependencies

## Configuration

### MCP Server Configuration
```toml
[[tools.mcp_servers]]
type = "streamable-http"
url = "https://mcp.deepwiki.com/mcp"
```

### API Keys Required
- `SERPER_API_KEY` - For Google search via Serper
- `XAI_API_KEY` - For X.com search
- `JINA_API_KEY` - For Jina AI search
- `EXA_API_KEY` - For Exa neural search

## Usage Examples

### Hybrid Search
```python
from src.core.search_engines import HybridSearchEngine

# Initialize with API keys
engine = HybridSearchEngine(
    api_keys={
        "serper": "your-serper-key",
        "jina": "your-jina-key",
        "exa": "your-exa-key"
    }
)

# Search across all providers
results = engine.search(
    query="LLM agents",
    num=10,
    aggregation_strategy="priority"
)
```

### GitHub Repository Analysis
```python
# Using the tool directly
tool = GitHubRepoQATool()
result = tool(
    operation="query",
    repository="langchain-ai/langchain",
    question="What are the main components of this project?"
)
```

## Provider Comparison

| Provider | Best For | Rate Limit | Search Type |
|----------|----------|------------|-------------|
| Serper (Google) | General web search | 100/month (free) | Keyword |
| XAI (X.com) | Social media, real-time | 500/day | Keyword + Social |
| Jina | LLM-optimized content | 40 RPM | AI-enhanced |
| Exa | Semantic/research queries | 1000/month | Neural |

## Breaking Changes
None - All changes are additive and maintain backward compatibility.

## Testing
- Added comprehensive test coverage for new search providers
- Validated error handling for various failure scenarios
- Tested deduplication and aggregation strategies
- Verified MCP server integration

## Performance Optimizations
1. Parallel search execution reduces latency
2. Intelligent caching in BaseSearchClient
3. Rate limiting prevents API throttling
4. Efficient deduplication algorithm
5. Optimized token counting for usage tracking

## Future Enhancements
1. Add more search providers (Bing, DuckDuckGo, etc.)
2. Implement search result caching
3. Add search quality scoring
4. Support for image and video search
5. Enhanced filtering and ranking algorithms

## Related Issues
- Implements hybrid search architecture requested in project roadmap
- Addresses CloudFlare timeout issues with proper error handling
- Adds GitHub repository analysis capability as requested

## Files Summary
- **New Files**: 10 core files implementing search providers and tools
- **Modified Files**: 15 files updated for integration
- **Documentation**: Updated prompts and configuration templates
- **Tests**: Comprehensive test coverage for new functionality

This feature significantly enhances DeepSearchAgents' search capabilities by providing multiple search providers, intelligent aggregation, and specialized tools for code and repository analysis.
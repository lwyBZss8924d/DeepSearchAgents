# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-07-13

### Added
- **Hybrid Search Engine with Multiple Providers**
  - New `BaseSearchClient` abstraction for consistent search provider interface
  - `HybridSearchEngine` that aggregates results from multiple providers
  - Parallel and sequential search execution strategies
  - Intelligent URL deduplication and result ranking
  - Configurable aggregation strategies: merge, round_robin, priority

- **New Search Providers**
  - **JinaSearchClient**: LLM-optimized web search with advanced content extraction
    - Support for markdown/HTML/text content formats
    - Domain-specific search capabilities
    - Enhanced error handling for CloudFlare timeouts (524 errors)
  - **ExaSearchClient**: Neural search with semantic understanding
    - Supports both keyword and neural search modes
    - Content extraction with autoprompt optimization
    - Domain filtering and date range support

- **GitHub Repository Q&A Tool**
  - `GitHubRepoQATool`: AI-powered repository analysis via DeepWiki MCP
  - Three operations: structure, contents, query
  - Repository format validation
  - Integration with MCP (Model Context Protocol) server

- **X.com (Twitter) Integration**
  - `XcomDeepQATool`: Deep query and analyze X.com content
  - `XAILiveSearchClient`: Uses xAI's Live Search API
  - Support for searching posts, reading URLs, asking questions

- **Enhanced Scraping Architecture**
  - Modular scraper design with `BaseScraper` abstraction
  - New scrapers: `FirecrawlScraper`, `JinaReaderScraper`, `XcomScraper`
  - Improved error handling and rate limiting
  - Automatic provider selection based on URL type

- **Search Tool Enhancements**
  - `SearchLinksFastTool`: Optimized for speed with simplified interface
  - Helper tools: `MultiQuerySearchTool`, `DomainSearchTool`
  - Convenience functions: `search_code()`, `search_docs()`, `search_recent()`

- **GitHub Actions Workflows**
  - Claude Code review automation
  - Security improvements with author association checks
  - Dual-job architecture for trusted vs external contributors

### Changed
- **Upgraded to smolagents v0.2.9**
  - Support for managed agents with hierarchical agent management
  - Structured output generation for CodeAgent
  - Improved streaming support with `StreamingFormatter`
  - Enhanced token usage tracking

- **Prompt Template Improvements**
  - Updated structured code/output rules
  - Enhanced ReAct planning rules
  - Added GitHub repo analysis rules
  - New `{CURRENT_TIME}` variable support

- **Error Handling Enhancements**
  - HTML error response filtering across all scrapers
  - Specific handling for CloudFlare 524 timeout errors
  - Clean error messages instead of raw HTML content
  - Consistent error response format across providers

### Fixed
- XcomScraper routing issue - now correctly routes only X.com URLs
- Improved URL detection regex for X.com/Twitter URLs
- Fixed scraping API backward compatibility issues

### Configuration
- **New API Keys Required**:
  - `JINA_API_KEY` - For Jina AI search
  - `EXA_API_KEY` - For Exa neural search
  - `FIRECRAWL_API_KEY` - For Firecrawl scraping

- **MCP Server Configuration**:
  ```toml
  [[tools.mcp_servers]]
  type = "streamable-http"
  url = "https://mcp.deepwiki.com/mcp"
  ```

### Breaking Changes
- Scraping API has been refactored
  - Old `scraper.py` and `xcom_scraper.py` removed
  - New modular architecture requires updating import paths
  - Change imports from `src.core.scraping.scraper` to `src.core.scraping.scrape_url`

## [0.2.9] - 2025-05-31

### Added
- Managed agents support for hierarchical agent management
- Streaming support improvements
- Structured generation support for CodeAgent

### Changed
- Upgraded smolagents to v0.2.9 with v1.19.0 compatibility
- Enhanced token usage tracking

## [0.2.8] - 2025-05-28

### Added
- Initial MCP (Model Context Protocol) support
- Enhanced tool management system

### Changed
- Improved agent runtime performance
- Better error handling in tool execution

## [0.2.7] - 2025-05-17

### Added
- Enhanced CLI with streaming output support
- Improved agent step callbacks

### Changed
- Better UI components for agent interactions
- Enhanced console formatting

## [0.2.6] - 2025-04-23

### Added
- Initial DeepSearchAgents implementation
- ReAct and CodeAct agent paradigms
- Basic search and content processing tools
- FastAPI and Gradio interfaces

### Changed
- Core agent architecture established
- Tool interface design implemented

---

For more details on each release, see the [commit history](https://github.com/lwyBZss8924d/DeepSearchAgents/commits/main).
# Release Notes - DeepSearchAgents v0.3.1

**Release Date**: 2025-07-13

## 🎉 Major Release Highlights

DeepSearchAgents v0.3.1 introduces **Hybrid Search Engine** capabilities, bringing together multiple search providers with intelligent aggregation, enhanced scraping architecture, and GitHub repository analysis tools. This release significantly expands the agent's ability to search across diverse sources and understand code repositories.

## 🌟 Key Features

### 1. 🌐 Hybrid Search Engine Architecture
- **Multi-Provider Support**: Seamlessly search across Google (Serper), X.com, Jina AI, and Exa Neural search engines
- **Intelligent Aggregation**: Three strategies available - merge, round_robin, and priority-based aggregation
- **Automatic Deduplication**: Smart URL deduplication prevents duplicate results across providers
- **Parallel Execution**: Concurrent search requests reduce latency and improve performance

### 2. 🔍 New Search Providers

#### JinaSearchClient
- LLM-optimized web search with advanced content extraction
- Support for markdown/HTML/text content formats
- Domain-specific search capabilities
- Enhanced CloudFlare timeout (524) error handling
- Rate limiting: 40 RPM (standard), 400 RPM (premium)

#### ExaSearchClient
- Neural search with semantic understanding
- Keyword and neural search modes
- Autoprompt optimization for better results
- Domain filtering and date range support
- Highlights extraction for relevant snippets

### 3. 📚 GitHub Repository Q&A Tool
- **GitHubRepoQATool**: AI-powered repository understanding via DeepWiki MCP
- Three operations:
  - `structure`: Get repository documentation structure
  - `contents`: Read full repository documentation
  - `query`: Ask specific questions about the repository
- Repository format validation (owner/repo)
- Integrated with MCP (Model Context Protocol) server

### 4. 🐦 X.com (Twitter) Deep Integration
- **XcomDeepQATool**: Analyze X.com content with AI
- **XAILiveSearchClient**: Real-time X.com search using xAI's Live Search API
- Support for:
  - Searching posts and profiles
  - Reading specific tweets
  - Asking questions about X.com content

### 5. 🏗️ Enhanced Scraping Architecture
- **Modular Design**: New `BaseScraper` abstraction for consistent interface
- **Multiple Scrapers**:
  - `FirecrawlScraper`: Advanced web extraction with JavaScript rendering
  - `JinaReaderScraper`: LLM-optimized content extraction
  - `XcomScraper`: Specialized for X.com content
- **Smart Routing**: Automatic provider selection based on URL type
- **Improved Error Handling**: Clean error messages instead of raw HTML

### 6. 🛡️ Security & Workflow Enhancements
- **GitHub Actions**: Claude Code review automation with security checks
- **Author Association**: Dual-job architecture for trusted vs external contributors
- **Secure Execution**: Enhanced security for code execution environments

## 📋 Configuration Requirements

### New API Keys Required
```bash
# Add to your .env file:
JINA_API_KEY=your-jina-key        # For Jina AI search
EXA_API_KEY=your-exa-key          # For Exa neural search
FIRECRAWL_API_KEY=your-firecrawl-key  # For Firecrawl scraping
XAI_API_KEY=your-xai-key          # For X.com search (if not already set)
```

### MCP Server Configuration
```toml
# Add to config.toml:
[[tools.mcp_servers]]
type = "streamable-http"
url = "https://mcp.deepwiki.com/mcp"
```

## 💡 Usage Examples

### Using Hybrid Search
```python
# CLI command with provider selection
python -m src.cli --query "Latest AI research papers" --providers serper,jina,exa

# Using specific aggregation strategy
python -m src.cli --query "OpenAI GPT updates" --aggregation priority
```

### GitHub Repository Analysis
```python
# Analyze a repository structure
python -m src.cli --query "github:langchain-ai/langchain structure"

# Ask questions about a repository
python -m src.cli --query "What are the main components of github:facebook/react?"
```

### X.com Search
```python
# Search X.com for specific topics
python -m src.cli --query "site:x.com AI agents discussion"
```

## 🔄 Migration Guide

### Breaking Changes
1. **Scraping API Refactored**:
   - Old imports: `from src.core.scraping.scraper import Scraper`
   - New imports: `from src.core.scraping.scrape_url import ScrapeUrl`

2. **Tool Registry Updates**:
   - New tools added to toolbox: `github_repo_qa`, `search_fast`
   - Updated tool icons and descriptions

### Backward Compatibility
- All existing search functionality remains intact
- Default behavior unchanged (uses Serper/Google if no providers specified)
- Existing API endpoints continue to work as before

## 🚀 Performance Improvements
- **Parallel Search**: 2-3x faster search results with multiple providers
- **Smart Caching**: Reduced API calls with intelligent result caching
- **Efficient Deduplication**: O(n) deduplication algorithm
- **Token Optimization**: Better token usage tracking across providers

## 🐛 Bug Fixes
- Fixed XcomScraper incorrectly routing non-X.com URLs
- Improved URL detection regex for Twitter/X.com domains
- Enhanced error handling for CloudFlare timeouts
- Fixed HTML content appearing in error messages

## 📊 Provider Comparison

| Provider | Best For | Rate Limit | Search Type | Cost |
|----------|----------|------------|-------------|------|
| Serper (Google) | General web search | 100/month (free) | Keyword | Free tier available |
| XAI (X.com) | Social media, real-time | 500/day | Keyword + Social | API key required |
| Jina | LLM-optimized content | 40 RPM | AI-enhanced | Free tier available |
| Exa | Semantic/research queries | 1000/month | Neural | API key required |

## 🔮 What's Next
- Additional search providers (Bing, DuckDuckGo, Perplexity)
- Enhanced caching and result persistence
- Search quality scoring and ranking improvements
- Support for image and video search
- Advanced filtering and faceted search

## 🙏 Acknowledgments
Special thanks to all contributors and the open-source community for making this release possible. This release builds upon the excellent work from:
- Hugging Face's smolagents framework
- DeepWiki MCP server for GitHub analysis
- Jina AI, Exa, and xAI for their search APIs
- The Model Context Protocol (MCP) community

## 📚 Documentation
For detailed documentation and examples, visit:
- [GitHub Repository](https://github.com/lwyBZss8924d/DeepSearchAgents)
- [Ask DeepWiki](https://deepwiki.com/lwyBZss8924d/DeepSearchAgents)

---

**Note**: This is a significant feature release. While we've thoroughly tested all new functionality, please report any issues to our [GitHub Issues](https://github.com/lwyBZss8924d/DeepSearchAgents/issues) page.
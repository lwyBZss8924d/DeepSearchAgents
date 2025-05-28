# Pull Request: Upgrade DeepSearchAgents to v0.2.8

## Summary
This PR upgrades DeepSearchAgents from v0.2.6/v0.2.7.dev to v0.2.8, adding multiple search engine support with XCom integration and enhancing the MCP server capabilities.

## Changes Overview
- Add support for XCom search engine and specialized content scraping
- Refactor search engine infrastructure to support multiple providers
- Improve FastMCP server implementation and MCP tool response handling
- Update agent prompts and tool descriptions for multi-provider support
- Enhance configuration system for search engine selection

## Major Features
- **Multi-Provider Search**: Added XCom search engine alongside Serper
- **Content Extraction**: New specialized scrapers for different content formats
- **MCP Integration**: Enhanced FastMCP server with streaming support
- **Configuration**: Extended settings for provider selection while maintaining backward compatibility

## Technical Implementation
- Architecture changes follow factory pattern for search provider selection
- Search engines now use consistent naming convention (search_*.py)
- Content extraction handled by specialized scrapers for each provider
- All changes maintain backward compatibility with previous configurations

## Testing Performed
- Verified search capabilities with both Serper and XCom providers
- Tested MCP server integration with streaming responses
- Confirmed backward compatibility with existing configurations
- Validated all agent modes (ReAct and CodeAct) with new search providers

## Documentation
- Updated README.md with FastMCP server documentation
- Created version upgrade notes in dev-docs/version-upgrade-0.2.8.md
- Added detailed commit logs with technical implementation details

## Future Work
- Explore additional search providers integration
- Enhance search strategy optimization based on provider capabilities
- Improve content ranking with provider-specific optimizations
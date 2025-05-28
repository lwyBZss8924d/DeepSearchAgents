# DeepSearchAgents v0.2.6/v0.2.7.dev to v0.2.8 Release

## Major Features and Improvements

### 1. Multiple Search Engine Support
- **XCom Search Engine Integration**: Added support for XCom search engine alongside existing Serper
- **Configurable Provider Selection**: Users can now choose between search providers through settings
- **Search Engine Architecture Refactor**: Redesigned search engine infrastructure to support multiple providers
  - Renamed `serper.py` to `search_serper.py` for consistent naming
  - Added `search_xcom.py` for XCom search implementation
  - Modified search engine initialization in affected modules

### 2. Enhanced Web Content Handling
- **XCom Scraper**: Added specialized scraper for XCom search results
  - New module `xcom_scraper.py` for extracting content from XCom results
  - Custom URL reading capabilities for XCom in `xcom_readurl.py`
- **Improved Content Processing**: Better handling of different content formats across search providers

### 3. MCP (Model Context Protocol) Server Integration
- **FastMCP Server Implementation**: Added FastMCP server supporting Streamable HTTP protocol
  - New module `run_fastmcp.py` for MCP server implementation
  - Integration with main FastAPI application
- **DeepSearchAgents as MCP Tool**: Exposed DeepSearch capabilities as an MCP tool via `deepsearch_tool`
- **Real-time Progress Reporting**: Enhanced streaming support for MCP clients

### 4. Agent Prompts Enhancement
- **Updated Prompt Templates**: Modified agent prompts to support multiple search engines
- **Improved Tool Descriptions**: Enhanced tool descriptions for better agent understanding

### 5. Configuration and Settings
- **Upgraded Version**: From v0.2.7.dev to v0.2.8.dev
- **Enhanced Settings Management**: Extended configuration options for search engine selection
- **Backward Compatibility**: Maintained compatibility with existing configurations

## Architectural Changes
- Search engine operations now use a factory pattern for selecting appropriate provider
- Added modular support for different search and scraping implementations
- Enhanced the project structure documentation

## Development & Documentation
- Updated README.md with FastMCP server documentation
- Added detailed architecture diagrams
- Improved project structure documentation
- Created comprehensive commit logs with technical details

## Technical Notes
- All changes maintain backward compatibility with previous versions
- Search engine selection is configurable through settings
- Requires Python 3.13+ (unchanged from previous version)
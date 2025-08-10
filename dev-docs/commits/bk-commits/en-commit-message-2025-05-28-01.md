# Commit Message 2025-05-28-01

## Summary
- Add support for XCom search engine and scraper integration
- Refactor search engine infrastructure to support multiple providers
- Upgrade project version to v0.2.8.dev

## Details
- Added `xcom_scraper.py` for XCom search result content extraction
- Added `search_xcom.py` and refactored `search_serper.py` (renamed from serper.py)
- Added `xcom_readurl.py` for specialized XCom URL reading
- Updated configuration and tool integration for XCom search engine
- Modified agent prompts to support XCom search capabilities

## Technical Notes
- This version maintains backward compatibility with existing search providers
- Search engine selection is configurable through settings
- Updated relevant imports and initialization in affected modules
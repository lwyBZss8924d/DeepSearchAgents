# PaperQA2 Integration - Archived

This module contains the experimental PaperQA2 integration that was developed but temporarily archived due to integration challenges.

## Why Archived?

1. **Tight Coupling**: PaperQA2's architecture is tightly coupled with its file-based search and metadata providers
2. **Model Configuration**: Difficulty in overriding default model settings (`gpt-4o-2024-11-20`)
3. **Directory Indexing**: PaperQA2 agent attempts to index local codebase files instead of focusing on academic papers
4. **Metadata Providers**: Default providers (SemanticScholarProvider, CrossrefProvider) are invoked even when disabled

## What Was Implemented

- Custom ArXiv provider for PaperQA2
- Agent-based search refinement
- Custom tools to replace file-based search
- Integration with our paper retrieval system
- Advanced Q&A capabilities with evidence gathering

## Future Plans

This integration will be revisited after:
1. Further understanding of PaperQA2 source code
2. Potential upstream contributions to make PaperQA2 more modular
3. Development of custom agent system tailored to our needs

## Key Files

- `manager.py` - Core orchestration logic
- `academic_qa.py` - High-level Q&A API
- `arxiv_provider.py` - Custom ArXiv metadata provider
- `custom_tools.py` - Replacement tools for agent
- `config.py` - Configuration management

## Lessons Learned

1. Need for more modular architecture in external dependencies
2. Importance of understanding third-party tool assumptions
3. Value of incremental integration approach

For now, academic paper search functionality is available through the `academic_retrieval` tool.
feat(agents): v0.2.4.dev Upgrade text chunking tools and optimize prompt template system

## Major Changes

### 1. Implement Jina AI Segmenter API for Text Chunking
- Created new `src/agents/core/chunk/segmenter.py` implementing intelligent text segmentation based on Jina AI Segment API
- Maintained backward compatibility with `Chunker` class
- Updated `chunk.py` Agent tool to utilize the new text segmenter
- Optimized error handling and asynchronous processing logic

### 2. Refactor and Standardize Prompt Template System
- Refactored `codact_prompts.py` file, introducing modular prompt template structure
- Updated tool descriptions to reflect new Jina AI chunker capabilities
- Enhanced template merging logic for improved extensibility
- Ensured prompt templates remain consistent with latest tool implementations

### 3. Unify and Enhance Final Answer Generation Tool
- Optimized `final_answer.py` extension tool to support multiple output formats
- Added intelligent JSON processing logic and unified result formatting
- Improved source link extraction and formatting capabilities
- Ensured consistency in output formatting across streaming and non-streaming modes
- Fixed JSON and Markdown rendering issues in CLI

### 4. Optimize CLI Logging and Fix Tool Naming
- Improved CLI logging configuration in `cli.py` to simplify LiteLLM logs output
- Added strict filtering for redundant cost calculation and token counter logs
- Fixed bug in `wolfram.py` tool naming (changed from "calculate" to "wolfram")
- Ensured consistent tool naming across all components (agent, prompts, tools)
- Updated `config.yaml.template` to add more granular log filtering options

## ⚠️ Important Note: Streaming Functionality Not Recommended
- Current streaming implementation (`streaming_agents.py` and `streaming_models.py`) has several defects
- Code structure is complex and difficult to maintain, some features may cause instability
- Exception handling mechanisms are incomplete and may lead to process interruption in certain scenarios
- **Developers and users are advised not to enable streaming mode** until the next version with optimizations
- Set `enable_streaming` parameter to `false` in `config.yaml` for both react and codact agents

## Technical Improvements
- Enhanced error handling and retry mechanisms
- Improved asynchronous processing and streaming output support
- Ensured configuration parameters propagate correctly across all modes
- Unified agent state management and tool calling interfaces
- Centralized logging configuration for better runtime diagnostics

## Next Steps
- Further optimize streaming output experience
- Add more unit tests covering new functionality
- Update documentation to reflect new APIs and features
- Refactor streaming implementation to improve code quality and maintainability

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## DeepSearchAgent Project

DeepSearchAgent is an intelligent agent system that combines the ReAct (Reasoning + Acting) framework and the CodeAct concept (executable code agents) to enable deep web search and reasoning capabilities. Built on Hugging Face's `smolagents` framework, it provides multi-step reasoning for complex queries through various interfaces.

## Development Commands

### Common Development Tasks
```bash
# Install dependencies (with development tools)
uv pip install -e ".[dev,test,cli]"

# Run tests
make test

# Run specific test file
uv run -- pytest tests/test_specific.py

# Run tests with coverage
uv run -- pytest --cov=src tests

# Start development servers
make run        # FastAPI server (default port 8000)
# Web API v2 is accessible via the main FastAPI server
make cli        # Interactive CLI mode

# CLI with specific agent modes
make cli-react  # ReAct agent (non-interactive)
make cli-codact # CodeAct agent (non-interactive)

# MCP server
python -m src.agents.servers.run_fastmcp
```

### Configuration Setup
```bash
cp config.template.toml config.toml  # Non-sensitive settings
cp .env.example .env                 # API keys
```

## High-Level Architecture

### Agent System Design
The project implements a dual-agent architecture:
- **CodeAct Agent**: Executes Python code to perform actions, suitable for computational tasks
- **ReAct Agent**: Uses structured tool calling with JSON responses, better for web search tasks
- **Runtime Manager**: Handles execution environment and tool availability for both agent types
- **Model Routing**: Supports multiple LLM providers through LiteLLM with configurable model selection
- **Web API v2**: Simplified WebSocket API with direct Gradio message pass-through (~500 lines, down from ~5000)

### Core Components Interaction
```
User Input → Agent Selection → Planning/Reasoning → Tool Execution → Response Streaming
                    ↓                    ↓                ↓
              config.toml          Prompt Templates    Toolbox Manager
                    
Web API v2 → WebSocket → Session Manager → Gradio Passthrough → stream_to_gradio → Agent
```

### Tool Ecosystem
Tools are unified through a common interface supporting both sync/async operations:
- **Search Tools**: Multi-engine support (Google via Serper, X.com via xAI)
- **Content Processing**: URL reading, text chunking, embedding, reranking
- **Computation**: WolframAlpha integration for mathematical queries
- **Final Answer**: Structured response generation with source attribution

### Configuration Hierarchy
1. Command-line arguments (highest priority)
2. Environment variables
3. config.toml settings
4. Default values (lowest priority)

### Streaming Architecture
- Streaming is now available but disabled by default for stability
- When enabled, provides real-time visibility into agent reasoning process
- Supports both FastAPI SSE and Gradio streaming interfaces
- CLI now supports streaming output with the new StreamingConsoleFormatter

#### Enabling Streaming
To enable streaming output in the CLI:

1. **In config.toml**:
```toml
[agents.common]
cli_streaming_enabled = true  # Global toggle for CLI streaming

[agents.react]
enable_streaming = true  # Enable for React agent

[agents.codact]
enable_streaming = true  # Enable for CodeAct agent
```

2. **Via command line**:
```bash
# Enable streaming for a single query
python -m src.cli --agent-type react --enable-streaming --query "your query"
```

3. **Environment variables** (highest priority):
```bash
export REACT_ENABLE_STREAMING=true
export CODACT_ENABLE_STREAMING=true
export CLI_STREAMING_ENABLED=true
```

Note: Streaming support depends on the agent and model capabilities. Not all models support streaming output.

### Web API v2 Design Principles

The v2 API follows a simplified architecture:
1. **Direct Pass-through**: Messages from smolagents' stream_to_gradio are passed with minimal transformation
2. **Field Renaming Only**: Gradio ChatMessage fields renamed to DSAgentRunMessage format
3. **No Complex Parsing**: Avoids fragile regex-based message content parsing
4. **Leverage Proven Code**: Uses smolagents' battle-tested streaming infrastructure
5. **Session-based**: WebSocket connections maintain conversation state via session IDs

## Project Structure

```tree
src/
├── main.py                # Main application entry point
├── cli.py                 # Command-line interface
├── agents/               # Agent implementations
│   ├── __init__.py        # Package initialization
│   ├── base_agent.py      # Base agent interface with model routing
│   ├── codact_agent.py    # CodeAct agent implementation
│   ├── react_agent.py     # ReAct agent implementation
│   ├── runtime.py         # Agent runtime manager
│   ├── prompt_templates/  # Modular prompt template system
│   │   ├── __init__.py
│   │   ├── codact_prompts.py
│   │   └── react_prompts.py
│   ├── servers/           # Server implementations 
│   │   ├── __init__.py
│   │   ├── run_fastmcp.py # FastMCP MCP server implementation
│   │   └── run_fastmcp.py # FastMCP MCP server implementation
├── api/                   # FastAPI service components
│   ├── v1/                # API version 1 endpoints
│   └── v2/                # API version 2 endpoints
│       ├── __init__.py
│       ├── models.py      # Simple Pydantic models
│       ├── gradio_passthrough_processor.py  # Core pass-through logic
│       ├── endpoints.py   # WebSocket and REST endpoints
│       ├── session.py     # Session management
│       ├── main.py        # Standalone API server
│       └── examples/      # Example scripts
├── core/                  # Core system components
│   ├── chunk/             # Text chunking components
│   ├── config/            # Configuration handling with Pydantic
│   ├── ranking/           # Content ranking algorithms
│   ├── scraping/          # Web content scraping (JinaAI, XCom)
│   └── search_engines/    # Search engine integrations
└── tools/                 # Tool implementations
    ├── __init__.py
    ├── chunk.py           # Text chunking tool
    ├── embed.py           # Text embedding tool
    ├── final_answer.py    # Final answer generation tool
    ├── readurl.py         # URL content reading tool
    ├── rerank.py          # Content reranking tool
    ├── search.py          # Web search tool
    ├── toolbox.py         # Tool management utilities
    └── wolfram.py         # Wolfram Alpha computational tool

tests/
└── api_v2/                # Web API v2 test suite
    ├── __init__.py
    ├── conftest.py        # Test configuration and fixtures
    ├── test_websocket_streaming.py  # WebSocket streaming tests
    ├── test_agent_steps.py          # Agent step progression tests
    ├── test_final_answer.py         # Final answer delivery tests
    └── utils.py           # Test utilities
```

## Development Guidelines

### Code Style
- Strict PEP8 compliance with 79-character line limit
- 4-space indentation, no tabs
- English for all code, comments, and docstrings
- Chinese for user-facing chat responses only
- Import order: stdlib → third-party → local

### Testing Approach
- Test framework: pytest with asyncio support
- Test files pattern: `test_*.py` in `tests/` directory
- Both sync and async test support
- Mock external API calls in tests

### Key Development Patterns
- **Async-first design**: Tools support both sync/async interfaces
- **Type hints**: Required for all function signatures
- **Error handling**: Comprehensive try-except with specific error types
- **Logging**: Use configured loggers, not print statements
- **Configuration**: All settings through config system, no hardcoded values
- **Token Counting**: Uses smolagents v1.20.0 TokenUsage API for accurate token tracking

# DeepSearchAgent

Build with 💖 for Humanity with AI

![Smolagents](https://img.shields.io/badge/Smolagents-1.13.0+-yellow.svg)
![LiteLLM](https://img.shields.io/badge/LiteLLM-1.65.4+-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.00+-009688.svg?logo=fastapi&logoColor=white)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![version](https://img.shields.io/badge/version-0.2.3-blue.svg)](https://github.com/DeepSearch-AgentTeam/DeepSearchAgent/releases/tag/v0.2.3)

> **Come From Open Source, This is the Way**

[中文版](README_Zh.md)

## 1. Introduction

DeepSearchAgent is an intelligent agent system that combines the ReAct (Reasoning + Acting) framework and the CodeAct concept (executable code agents) to enable deep web search and reasoning. It leverages a large language model (LLM) to perform reasoning and to invoke external tools, allowing it to answer complex queries through multi-step search, reading, and computation with traceable references. Built on Hugging Face's smolagents framework, this project implements a dual-mode agent capable of both tool calling and code execution, embodying the strengths of ReAct and CodeAct.

It supports a Command Line Interface (CLI) and a standard FastAPI service, making it convenient for developers to integrate and use within various systems.

## 2. ✨ Features

TODO: MCP (Model Context Protocol) Server for MCP tool server support

- 🔍 **Deep Research Capability**: Performs multi-step search, reading, and reasoning across web content to answer complex queries
- 🧩 **Dual Agent Modes**: Supports both ReAct (tool calling) and CodeAct (Python execution) paradigms, configurable via `config.yaml` or environment variables
- 🔧 **Extensible Toolchain**: Includes tools for web search, content retrieval, text processing, semantic ranking, and computation
- ⚙️ **Flexible Configuration**: Manage parameters via a `config.yaml` file and API keys via `.env`
- 📊 **Semantic Understanding**: Uses advanced embedding and reranking to identify the most relevant content
- 🧮 **Computational Integration**: Connects with WolframAlpha for solving mathematical and computational queries
- 🖥️ **Multiple Interfaces**: Offers a rich CLI experience and a standard FastAPI service
- 📝 **Traceable References**: Provides sources and references for generated answers
- 🔄 **Iterative Refinement**: Continuously improves search and analysis strategy based on initial findings

**Reference Case**
[GPT-4.1 Model Comparison Example](docs/examples/codact-gpt-4.1-example.md)

## 3. 🚀 Quick Start (CLI & FastAPI)

This section guides you through setting up the environment, installing dependencies, and running DeepSearchAgent via its command-line interface or standard FastAPI service.

### Installation & Setup

1.  **Prerequisites:**
    *   Python 3.13+.
    *   `uv` (Recommended, faster alternative to pip/venv): [Install uv](https://github.com/astral-sh/uv).
    *   Git.

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/DeepSearch-AgentTeam/DeepSearchAgent.git
    cd DeepSearchAgent
    ```

3.  **Create Virtual Environment (Recommended):**
    ```bash
    # Using uv
    uv venv
    source .venv/bin/activate  # Unix/macOS
    # .venv\Scripts\activate   # Windows

    # Or using standard venv
    # python -m venv .venv
    # source .venv/bin/activate  # Unix/macOS
    # .venv\Scripts\activate   # Windows
    ```

4.  **Install Dependencies:**

    *   **For running the FastAPI service:**
        ```bash
        uv pip install .
        ```
    *   **For running the CLI or for Development:**
        ```bash
        # Installs core + CLI dependencies + development tools in editable mode
        uv pip install -e ".[cli]"
        ```

5.  **Configure:**
    ```bash
    # Create configuration files from templates
    cp config.yaml.template config.yaml
    cp .env.template .env

    # Edit config.yaml for models, agent parameters, service settings
    # nano config.yaml

    # Edit .env for API keys (LITELLM_MASTER_KEY, SERPER_API_KEY, etc.)
    # nano .env
    ```

**Configuration Details:**
*   `config.yaml`: Contains non-sensitive configurations like model IDs, agent parameters (max steps, executor type), service settings (host, port).

```yaml
# Example config.yaml content
# Model configuration
models:
  orchestrator_id: "openrouter/openai/gpt-4.1"  # Used for main LLM orchestration
  search_id: "openrouter/openai/gpt-4.1"        # Used for search (only if different)
  reranker_type: "jina-reranker-m0"             # Default reranker type

# Agent common settings
agents:
  common:
    verbose_tool_callbacks: true        # If true, show full tool inputs/outputs
  
  # Settings specific to the ReAct agent
  react:
    max_steps: 25                       # Max number of reasoning steps

  # Settings specific to the CodeAct agent
  codact:
    executor_type: "local"              # local or lambda (for AWS Lambda execution)
    max_steps: 25                       # Max number of steps in execution
    verbosity_level: 1                  # 0=minimal, 1=normal, 2=verbose
    executor_kwargs: {}                 # Additional kwargs for executor
    additional_authorized_imports: []   # Additional Python modules to allow importing

# Service configuration
service:
  host: "0.0.0.0"
  port: 8000
  version: "0.2.3"
  deepsearch_agent_mode: "codact"       # "react" or "codact"
```

*   `.env`: Contains **only** sensitive API keys (e.g., `LITELLM_MASTER_KEY`, `SERPER_API_KEY`, `JINA_API_KEY`, `WOLFRAM_ALPHA_APP_ID`). You can also optionally set `LOG_LEVEL` here (e.g., `debug`, `info`, `warning`, `error`).

### Running the CLI

Ensure you have installed the CLI dependencies (see Step 4 in Installation & Setup).

```bash
# Run the CLI (interactive mode, uses settings from config.yaml)
make cli
# or directly:
uv run python -m src.agents.cli

# Override agent type from config.yaml via CLI argument
make cli ARGS="--agent-type react"
# or directly:
uv run python -m src.agents.cli --agent-type react

# Run with a single query (non-interactive)
uv run python -m src.agents.cli --query "Search the latest news about OpenAI's new GPT-4.1 API."
```

CLI arguments will override settings defined in `config.yaml`.

### Running the FastAPI Service

Ensure you have installed the core dependencies (see Step 4 in Installation & Setup).

```bash
# Start the main API server (uses host/port from config.yaml, e.g., http://0.0.0.0:8000)
make run
# or directly:
uv run -- uvicorn src.agents.main:app --reload
# Note: --host and --port are now taken from config.yaml via main.py
# Use LOG_LEVEL environment variable for log level (e.g., LOG_LEVEL=debug make run)
```

**API Endpoints:**

*   `POST /run_react_agent`: Runs the React agent.
*   `POST /run_deepsearch_agent`: Runs the agent configured by `service.deepsearch_agent_mode` in `config.yaml` (or `DEEPSEARCH_AGENT_MODE` env var).
*   `GET /`: API info and health check.

Example API request to the configured deep search endpoint:

```bash
curl -X POST http://localhost:8000/run_deepsearch_agent \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Search the latest news about OpenAI'''s new GPT-4.1 API."}'
```
*(Replace `localhost:8000` with the actual host and port if changed in `config.yaml`)*

## 4. 🛠️ Architecture and Modules

The core system architecture consists of:

1.  **Core Agents (`src/agents/agent.py`, `src/agents/codact_agent.py`)**: Implement the ReAct and CodeAct logic based on `smolagents`.
2.  **Tools (`src/agents/tools/`)**: Functions the agents can call (web search, read URL, etc.).
3.  **FastAPI Service (`src/agents/main.py`)**: Exposes the agent functionality via a REST API.
4.  **Configuration Loader (`src/agents/config_loader.py`)**: Manages loading settings from `config.yaml` and `.env`.

```mermaid
---
config:
  theme: dark
  themeVariables:
    primaryColor: '#1a1a2e'
    primaryTextColor: '#00fff9'
    primaryBorderColor: '#7700ff'
    lineColor: '#ff00f7'
    secondaryColor: '#16213e'
    tertiaryColor: '#0f0f1a'
    mainBkg: '#1a1a2e'
    nodeBorder: '#7700ff'
    clusterBkg: '#16213e'
    clusterBorder: '#7700ff'
    titleColor: '#00fff9'
    edgeLabelBackground: '#1a1a2e'
    textColor: '#00fff9'
  layout: elk
---
flowchart TB
    subgraph Interfaces["Interfaces"]
        direction LR
        CLI{{"CLI"}}
        FastAPI{{"FastAPI Service"}}
    end
    subgraph DeepSearchAgentSystem["DeepSearch Agents System"]
        direction TB
        CoreAgents{{"Core Agents
(Handles Mode Selection)"}}
        ConfigLoader["Config Loader (yaml, .env)"]
        subgraph Agents["Agent Logic"]
            direction LR
            ToolAgent[["ToolCallingAgent
(Normal-ReAct)"]]
            CodeAgent[["CodeAgent
(CodeAct-ReAct)"]]
        end
    end
    subgraph ToolCollection["Tool Collection"]
        direction TB
        SearchLinks[/search_links/]
        ReadURL[/read_url/]
        ChunkText[/chunk_text/]
        EmbedTexts[/embed_texts/]
        RerankTexts[/rerank_texts/]
        Wolfram[/"wolfram computational"/]
        FinalAnswer[/final_answer/]
        ExternalAPIs{{External APIs
Serper, Jina, Wolfram...}}
    end
    subgraph Execution["Execution"]
        PythonEnv[("Python Execution
Environment (for CodeAct)")]
    end

    CLI -- "User Query" --> CoreAgents
    FastAPI -- "API Request" --> CoreAgents
    CoreAgents -- "Select Mode: ReAct" --> ToolAgent
    CoreAgents -- "Select Mode: CodeAct" --> CodeAgent
    CoreAgents -- "Uses Config" --> ConfigLoader

    ToolAgent == "Calls Tools" ==> SearchLinks
    ToolAgent == "Calls Tools" ==> ReadURL
    ToolAgent == "Calls Tools" ==> ChunkText
    ToolAgent == "Calls Tools" ==> EmbedTexts
    ToolAgent == "Calls Tools" ==> RerankTexts
    ToolAgent == "Calls Tools" ==> Wolfram
    ToolAgent == "Calls Tools" ==> FinalAnswer

    CodeAgent == "Generates Code" ==> PythonEnv
    PythonEnv[("Python Execution
Environment (for CodeAct)")]
    PythonEnv -- "Calls Tools via Code" --> SearchLinks
    PythonEnv -- "Calls Tools via Code" --> ReadURL
    PythonEnv -- "Calls Tools via Code" --> ChunkText
    PythonEnv -- "Calls Tools via Code" --> EmbedTexts
    PythonEnv -- "Calls Tools via Code" --> RerankTexts
    PythonEnv -- "Calls Tools via Code" --> Wolfram
    PythonEnv -- "Calls Tools via Code" --> FinalAnswer

    SearchLinks -- "Uses External API" --> ExternalAPIs
    ReadURL -- "Uses External API" --> ExternalAPIs
    EmbedTexts -- "Uses External API" --> ExternalAPIs
    RerankTexts -- "Uses External API" --> ExternalAPIs
    Wolfram -- "Uses External API" --> ExternalAPIs
    ExternalAPIs -.-> ToolCollection

    ToolAgent -. "Final Answer" .-> CoreAgents
    CodeAgent -. "Final Answer" .-> CoreAgents
    CoreAgents -. "Response" .-> Interfaces

    classDef default fill:#1a1a2e,stroke:#7700ff,stroke-width:2px,color:#00fff9
    classDef interface fill:#16213e,stroke:#ff00f7,stroke-width:3px,color:#00fff9
    classDef agent fill:#0f0f1a,stroke:#7700ff,stroke-width:2px,color:#00fff9
    classDef manager fill:#1a1a2e,stroke:#ff00f7,stroke-width:3px,color:#00fff9
    classDef tool fill:#16213e,stroke:#00fff9,stroke-width:2px,color:#ff00f7
    classDef environment fill:#0f0f1a,stroke:#00fff9,stroke-width:2px,color:#ff00f7
    classDef external fill:#1a1a2e,stroke:#00fff9,stroke-width:2px,color:#ff00f7
    classDef config fill:#0f0f1a,stroke:#7700ff,stroke-width:1px,color:#00fff9

    CLI:::interface
    FastAPI:::interface
    CoreAgents:::manager
    ToolAgent:::agent
    CodeAgent:::agent
    SearchLinks:::tool
    ReadURL:::tool
    ChunkText:::tool
    EmbedTexts:::tool
    RerankTexts:::tool
    Wolfram:::tool
    FinalAnswer:::tool
    PythonEnv:::environment
    ExternalAPIs:::external
    ConfigLoader:::config
```

## 5. ⚙️ Agent Modes (ReAct vs CodeAct)

DeepSearchAgent supports two modes of agent operation: the ReAct tool-calling mode and the CodeAct code-execution mode. The default mode used by the `/run_deepsearch_agent` endpoint is configured in `config.yaml` (`service.deepsearch_agent_mode`) or via the `DEEPSEARCH_AGENT_MODE` environment variable.

### ReAct Mode (Tool Calling)

In ReAct mode, the agent operates in the classic reasoning+acting manner, with actions executed by invoking predefined tools. During its reasoning process, the LLM generates structured "action" outputs that specify which tool to use and with what parameters.

**Example format:**
```json
{
  "name": "search_links",
  "arguments": {
    "query": "example query"
  }
}
```

### CodeAct Mode (Code Execution)

In CodeAct mode, the agent produces executable Python code, and by running that code the agent completes its reasoning and actions. This allows for more complex operations, combining multiple steps into one code execution.

**Example format:**
```python
results = search_links("example query")
content = read_url(results[0]["link"])
final_answer("The result is...")
```

### Comparison and Use Cases

| Differences | ReAct Mode | CodeAct Mode |
|-------------|------------|--------------|
| **Action Representation** | Structured JSON instructions | Executable Python code |
| **Complex Operation Capability** | Multiple steps for complex logic | Can combine multiple steps with programming constructs |
| **Model Requirements** | General conversational ability | Requires code generation capability |
| **Debugging & Interpretability** | Human-readable thoughts and actions | Code traces with error feedback |
| **Best For** | Simple queries, fixed workflows | Complex tasks, flexible tool orchestration |

## 6. 🔧 Toolchain Mechanism

DeepSearchAgent comes with an extensible toolchain that helps the agent retrieve and process information. These tools work in concert to form a complete query-answering pipeline:

- **`search_links`**: Accepts a query string and uses an external search engine API to retrieve web results with titles, snippets, and URLs.
- **`read_url`**: Fetches HTML content from a webpage and extracts formatted text for analysis.
- **`chunk_text`**: Splits long text into manageable segments for detailed analysis.
- **`embed_texts`**: Encodes text chunks into vector representations for semantic similarity operations.
- **`rerank_texts`**: Ranks text chunks by relevance to a given query for finding the most relevant information.
- **`wolfram`**: Calls the WolframAlpha API for mathematical or computational queries.
- **`final_answer`**: Signals that the agent has reached a conclusion and terminates the reasoning loop.

In a typical sequence, the agent first uses `search_links` to find information sources, then `read_url` to obtain content. For complex content, it can use `chunk_text`, `embed_texts`, and `rerank_texts` to identify key passages. When calculations are needed, it calls `wolfram`. This cycle continues until the agent determines it has sufficient information to call `final_answer`.

## 7. 💡 Theoretical Foundations

### ReAct Paradigm Principles

ReAct (Reasoning + Acting) is a paradigm that enables a language model to produce both a chain-of-thought reasoning trace and action directives interleaved. This framework interweaves "reasoning" with "acting": the model thinks in natural language (recording its thought process) and also produces concrete actions (such as searching or reading) to interact with external tools or the environment.

Studies have shown that this tight integration of reasoning and acting outperforms reasoning-only or acting-only methods, effectively reducing hallucinations and error propagation while improving interpretability and controllability of the problem-solving process.

### CodeAct Executable Code Agents

CodeAct refers to approaches that have the agent generate and execute actions in the form of code. The core idea is that at each decision step, the model directly produces executable code, and by running this code the agent invokes tools or performs computations.

Compared to static instructions, code as an action representation offers greater expressiveness and flexibility: it can combine multiple tool calls, use programming logic to handle complex data structures, and even reuse previously defined functions, vastly expanding the agent's action space.

## 8. 📦 Installation

### Requirements

- Python 3.13+
- Create `config.yaml` from `config.yaml.template` and customize parameters.
- Create `.env` from `.env.template` and add required API keys:
  - `LITELLM_MASTER_KEY` (if using LiteLLM compatible models)
  - `SERPER_API_KEY` (for web search via `search_links`)
  - `JINA_API_KEY` (for content processing via `read_url`, `embed_texts`, `rerank_texts`)
  - `WOLFRAM_ALPHA_APP_ID` (optional, for computational queries via `wolfram`)
  - `LITELLM_BASE_URL` (optional, if using a custom LiteLLM endpoint)
  - `LOG_LEVEL` (optional, e.g., `debug`, `info`, `warning`, `error`)

## 9. 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 10. 📄 License

This project is licensed under the MIT License

## 11. 📝 Acknowledgements Open Source Projects

Special thanks to the following projects and individuals who made this project possible:

- [smolagents](https://github.com/huggingface/smolagents)
- [Litellm](https://github.com/BerriAI/litellm)
- [Jina AI](https://github.com/jina-ai)
- [FastAPI](https://github.com/tiangolo/fastapi)

## 12. Theoretical Foundations & References

> - [ReAct: Synergizing Reasoning and Acting in Language Models](https://react-lm.github.io/) `arXiv:2210.03629v3`
> - [Executable Code Actions Elicit Better LLM Agents](https://arxiv.org/html/2402.01030v4) `arXiv:2402.01030v4`
> - [DynaSaur: Large Language Agents Beyond Predefined Actions](https://arxiv.org/html/2411.01747v1) `arXiv:2411.01747v1`
> - [LLMCompiler: An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511v3) `arXiv:2312.04511v3`
> - [ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models](https://arxiv.org/abs/2305.18323) `arXiv:2305.18323v1`
> - [smolagents.agents.CodeAgent](https://github.com/huggingface/smolagents/blob/7983378593da4b393a95335aad8431f6c9d2ac23/src/smolagents/agents.py)
> - [Hugging Face smolagents library](https://huggingface.co/docs/smolagents/index)
> - [Jina AI DeepResearch repository](https://github.com/jina-ai/node-DeepResearch)
> - [A Practical Guide to Implementing DeepSearch/DeepResearch](https://jina.ai/news/a-practical-guide-to-implementing-deepsearch-deepresearch/)
> - [DeepSearch on Private Visual Documents: An Enterprise Case Study](https://jina.ai/news/deepsearch-on-private-visual-documents-an-enterprise-case-study/)
> - [Snippet Selection and URL Ranking in DeepSearch/DeepResearch](https://jina.ai/news/snippet-selection-and-url-ranking-in-deepsearch-deepresearch/)
> - [LLM-as-SERP: Search Engine Result Pages from Large Language Models](https://jina.ai/news/llm-as-serp-search-engine-result-pages-from-large-language-models/)
> - [A Practical Guide to Implementing DeepSearch/DeepResearch](https://jina.ai/news/a-practical-guide-to-implementing-deepsearch-deepresearch/)

feat: Major overhaul and features for v0.2.6.dev1

This commit marks a significant milestone, v0.2.6.dev1, introducing a comprehensive overhaul of the DeepSearchAgent framework, enhancing its architecture, toolset, interfaces, and compatibility.

**Key Changes:**

1.  **Agent Runtime & Base Agent Architecture Revamp:**
    *   Refactored core agent lifecycle management and execution logic.
    *   Introduced a more robust and extensible `BaseAgent` structure.
    *   Updated `CodeActAgent` (`src/agents/codact_agent.py`) and `ReactAgent` (`src/agents/react_agent.py`) to align with the new architecture in `src/agents/runtime.py` and `src/agents/base_agent.py`.

2.  **Agent Tools Architecture Overhaul:**
    *   Implemented a unified `Toolbox` interface in `src/tools/toolbox.py`. This new toolbox is designed for enhanced compatibility with various tool ecosystems, including Langchain Tools, Hugging Face Tools, and MCP (Model Context Protocol).
    *   Refactored the text chunking mechanism:
        *   The `ChunkTextTool` (`src/tools/chunk.py`) now utilizes the `JinaAISegmenter` from `src/core/chunk/segmenter.py` for more efficient and accurate text segmentation.

3.  **FastAPI Service Reconstruction:**
    *   The FastAPI application structure in `src/api/` has been completely rebuilt for better organization, scalability, and maintainability. This includes refined routing, request/response handling, and overall API design.

4.  **CLI Enhancements:**
    *   The Command Line Interface (CLI) for development and debugging has undergone a complete overhaul, improving user experience, interactivity, and output clarity.

5.  **New GaiaUI Web Interface:**
    *   Introduced GaiaUI, a new Gradio-based Web GUI, providing a user-friendly graphical interface for interacting with the agents.

6.  **Streaming Output & Display:**
    *   Implemented comprehensive streaming capabilities for both agent output and display.
    *   Real-time streaming is now supported in both the CLI and the new GaiaUI, offering better visibility into the agent's thought process and actions.

7.  **Updated Dependencies & Compatibility:**
    *   Ensured compatibility with `smolagents==1.16.1`, leveraging the latest features and improvements from the underlying framework.

This version represents a major step forward in the development of DeepSearchAgent, laying a more solid foundation for future features and research.

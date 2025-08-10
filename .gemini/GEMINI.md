# Gemini Workspace Context

This document provides context to Gemini for working with the DeepSearchAgents project.

## Project Overview

DeepSearchAgent is an intelligent agent system that combines the ReAct (Reasoning + Acting) framework and the CodeAct concept (executable code agents) to enable deep web search and reasoning capabilities. Built on Hugging Face's `smolagents` framework, it provides multi-step reasoning for complex queries through various interfaces.

## Version: v0.3.3-dev.250729.web-integration

This version introduces a complete web frontend, a simplified WebSocket API, and updated development workflows.

### Key Changes:

*   **Web Frontend:** A new Next.js-based web frontend provides a rich user interface for interacting with the agents.
*   **Web API v2:** A simplified WebSocket-based API (`/api/v2/ws/...`) replaces the previous, more complex event-driven system. It uses a direct message pass-through architecture from the agent to the frontend.
*   **Component-Based UI:** The frontend uses a component-based architecture, where different UI components (chat, code editor, terminal) are rendered based on metadata in the WebSocket messages.
*   **New Development Commands:**
    *   `make webui`: Starts the Next.js frontend development server.
    *   `make dev`: Starts both the backend and frontend development servers concurrently.
    *   `make kill-dev`: Stops all development services.
*   **Updated Dependencies:** The project now uses `uv` for dependency management and has updated several key libraries, including `smolagents`, `litellm`, and `fastapi`.

### Development Workflow:

1.  **Installation:**
    *   Use `uv pip install -e ".[dev,test,cli]"` to install all necessary dependencies.
2.  **Configuration:**
    *   Copy `config.template.toml` to `config.toml` for application settings.
    *   Copy `.env.example` to `.env` for API keys.
3.  **Running the Application:**
    *   `make dev` to run the full-stack application.
    *   The backend will be available at `http://localhost:8000`.
    *   The frontend will be available at `http://localhost:3000`.

### High-Level Architecture:

```
Frontend (Next.js) <--> WebSocket API (v2) <--> DSAgentMessageProcessor <--> Agent (CodeAct/ReAct)
```

The `DSAgentMessageProcessor` transforms agent events into metadata-rich messages that the frontend uses to route content to the appropriate UI components.

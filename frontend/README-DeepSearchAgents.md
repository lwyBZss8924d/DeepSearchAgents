# DeepSearchAgents Frontend

This is the web frontend for DeepSearchAgents, providing a clean interface for interacting with ReAct and CodeAct agents.

## Overview

The frontend has been adapted from a template to work with the DeepSearchAgents Web API v2, featuring:

- **Dual-panel interface**: Chat on the left, code/terminal/browser on the right
- **Real-time streaming**: Live updates as the agent processes queries
- **Step navigation**: Browse through agent execution steps
- **Code display**: Monaco Editor for viewing generated code
- **Terminal output**: xterm.js for execution logs
- **Web browser**: Track URLs visited by the agent

## Architecture

- **Framework**: Next.js 15 with React 19
- **State Management**: React Context API
- **WebSocket**: Direct integration with v2 API
- **UI Components**: shadcn/ui
- **Code Editor**: Monaco Editor (read-only)
- **Terminal**: xterm.js (display-only)

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp .env.example .env.local
```

3. Start development server:
```bash
npm run dev
```

The frontend will run on http://localhost:3000

## Key Components

- `agent-layout.tsx`: Main layout component
- `agent-chat.tsx`: Chat interface with message display
- `code-editor.tsx`: Monaco-based code viewer
- `terminal.tsx`: xterm.js-based log viewer
- `use-websocket.tsx`: WebSocket connection management
- `app-context.tsx`: Global state management

## API Integration

The frontend connects to the DeepSearchAgents backend via WebSocket:

```
ws://localhost:8000/api/v2/ws/{session_id}
```

Messages follow the DSAgentRunMessage format with automatic UI updates based on message content and metadata.
# DeepSearchAgents WebTUI Frontend

## Introduction

The DeepSearchAgents WebTUI is a modern, terminal-style web interface for the DeepSearchAgents platform, providing an intuitive way to interact with ReAct and CodeAct intelligent agents. Built with Next.js 15 and React 19, it offers a responsive chat interface with real-time streaming, metadata-driven component rendering, and seamless WebSocket integration with the DeepSearchAgents backend. The interface features a distinctive cyberpunk aesthetic with terminal-inspired UI components.

## Prerequisites

- Node.js 18+ (LTS recommended)
- npm or yarn package manager
- DeepSearchAgents backend server running (WebSocket server on port 8000)

## Installation

1. Install dependencies:

   ```bash
   npm install
   # or
   yarn install
   ```

2. Create a `.env.local` file in the frontend directory with the following variables:

   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_WS_URL=ws://localhost:8000
   NEXT_PUBLIC_VSCODE_URL=http://127.0.0.1:8080
   ```

   Note: NEXT_PUBLIC_VSCODE_URL is optional and can be omitted if you're not using VS Code integration.
   Adjust the URLs to match your backend server address.

## Development Workflow

To start the development server:

```bash
npm run dev
# or
yarn dev
```

This will start the Next.js development server with Turbopack enabled. The application will be available at [http://localhost:3000](http://localhost:3000).

The development server features:

- Hot Module Replacement (HMR)
- Fast refresh for React components
- Error reporting in the browser
- Real-time WebSocket streaming

## Building for Production

To create a production build:

```bash
npm run build
# or
yarn build
```

To start the production server:

```bash
npm run start
# or
yarn start
```

The application will be available at [http://localhost:3000](http://localhost:3000) (or the port specified in your environment).

## Project Structure

```
frontend/
├── app/                  # Next.js app directory (App Router)
│   ├── globals.css       # Global styles
│   ├── layout.tsx        # Root layout component
│   └── page.tsx          # Home page component
├── components/           # Reusable React components
│   ├── agent-chat.tsx    # Main chat interface component
│   ├── action-thought-card.tsx  # Action thinking display
│   ├── planning-card.tsx        # Planning step display
│   ├── final-answer-display.tsx # Structured final answers
│   ├── ui/               # UI components (buttons, cards, etc.)
│   └── ...
├── hooks/                # React hooks
│   └── use-websocket.tsx # WebSocket connection management
├── utils/                # Utility functions
│   └── extractors.ts     # Message type extraction utilities
├── typings/              # TypeScript type definitions
│   ├── agent.ts          # Legacy agent types
│   └── dsagent.ts        # DSAgentRunMessage types
├── .env.local            # Local environment variables (create this)
├── next.config.ts        # Next.js configuration
├── package.json          # Project dependencies and scripts
└── tsconfig.json         # TypeScript configuration
```

## Architecture Overview

### Message Flow
```
User Input → WebSocket → Backend Agent → Stream Events → DSAgentRunMessage → Frontend Components
```

### Key Architectural Decisions

1. **Metadata-Driven Rendering**: The backend sends routing metadata with each message, and the frontend components are selected based on the `component` field
2. **Streaming Support**: Messages can arrive in streaming mode with delta updates for real-time feedback
3. **Component Isolation**: Each UI component (chat, code editor, terminal) operates independently based on metadata routing
4. **Session-Based**: Each WebSocket connection maintains a unique session for conversation continuity

## Key Components

### Core Components

- **AgentChat**: Main chat interface that handles message display and routing
- **ActionThoughtCard**: Displays agent thinking process with truncated content
- **PlanningCard**: Shows planning steps with badges (Initial Plan/Updated Plan)
- **FinalAnswerDisplay**: Renders structured final answers with sources
- **CodeEditor**: Monaco-based code viewer for agent-generated code
- **Terminal**: xterm.js-based terminal for execution logs

### Message Routing

Messages are routed to components based on metadata:
```typescript
metadata.component === "chat"     → AgentChat
metadata.component === "webide"   → CodeEditor  
metadata.component === "terminal" → Terminal
```

## Technologies Used

- **Next.js 15**: React framework with App Router
- **React 19**: UI library with concurrent features
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS v4**: Utility-first CSS framework
- **WebTUI CSS Library**: Terminal-style UI components
- **Framer Motion**: Animation library
- **Lucide Icons**: Icon library
- **WebSocket API**: Real-time bidirectional communication
- **Monaco Editor**: Code editor with syntax highlighting
- **xterm.js**: Terminal emulator for HAL-9000 console

## WebTUI Design System

The frontend uses a custom Design System (DS) with terminal-inspired components:

- **DSAgentMessageCard**: Message containers with customizable borders
- **DSAgentToolBadge**: Tool execution indicators with minimal styling
- **DSAgentStreamingText**: Animated text streaming with cursor effects
- **DSAgentTerminalContainer**: Terminal window wrapper with cyberpunk aesthetic
- **DSAgentTUILogo**: ASCII art logo and branding elements
- **DSAgentCodeBlock**: Syntax-highlighted code display
- **DSAgentTimer**: Execution timer display
- **DSAgentStateBadge**: Agent state indicators

## Recent Updates (v0.3.3)

### Goal 1 Completed ✅
- Fixed action thought display (120 character truncation with ellipsis)
- Resolved markdown rendering issues in terminal style
- Removed excessive animations and glamour effects
- Consolidated component library (40% CSS reduction)
- Improved performance significantly (80% animation CPU reduction)
- Cleaned up 20+ obsolete v1 components

### Goal 2 In Progress 🚧
- HAL-9000™ CONSOLE implementation planned
- Three-terminal layout design (chat, code viewer, logger)
- Go-based CLI clients using Bubble Tea framework
- WebSocket terminal server architecture
- Real TTY support via xterm.js integration

## WebSocket Integration

The frontend connects to the DeepSearchAgents backend via WebSocket for real-time communication:

### Connection URL
```
ws://localhost:8000/api/v2/ws/{session_id}
```

### Protocol

1. **Client → Server Messages**:
```typescript
// Query message
{
  type: "query",
  query: "Your question here"
}

// Ping (keepalive)
{
  type: "ping"
}
```

2. **Server → Client Messages** (DSAgentRunMessage):
```typescript
{
  message_id: string,
  role: "user" | "assistant",
  content: string,
  metadata: {
    component?: "chat" | "webide" | "terminal",
    message_type?: string,
    step_type?: string,
    streaming?: boolean,
    is_delta?: boolean,
    // ... other metadata
  },
  session_id: string,
  step_number?: number,
  timestamp: string
}
```

### Streaming Behavior

1. **Initial Message**: Sent with `streaming: true` and empty content
2. **Delta Updates**: Sent with `is_delta: true` containing incremental content
3. **Final Message**: Sent with `streaming: false` and complete content

## Metadata-Driven UI

The frontend uses message metadata to determine rendering behavior:

### Key Metadata Fields

- `component`: Routes message to appropriate UI component
- `message_type`: Determines specific rendering logic
  - `"planning_header"`: Shows planning badge
  - `"action_thought"`: Shows thinking card
  - `"final_answer"`: Shows structured answer
- `streaming`: Indicates if message is still being generated
- `is_delta`: Marks incremental updates
- `has_structured_data`: Indicates structured final answer format

### UI Features

1. **Planning Badges**: Visual indicators for planning steps
   - Blue badge: "Initial Plan"
   - Purple badge: "Updated Plan"

2. **Action Thoughts**: Truncated thinking display
   - Format: "Thinking🤔...{60 chars}...and Action Running[Terminal]..."

3. **Final Answers**: Structured display with:
   - Title
   - Markdown content
   - Source citations

## Development Tips

1. **Component Hierarchy**: The app uses `AgentChat`, not `ChatMessage`
2. **Metadata First**: Always check metadata fields before content parsing
3. **Streaming Handling**: Use `is_delta` to identify incremental updates
4. **Debug Logging**: Enable `DEBUG_PLANNING` in use-websocket.tsx for detailed logs
5. **Type Safety**: Use TypeScript interfaces from `typings/dsagent.ts`

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Ensure backend is running on the correct port
   - Check NEXT_PUBLIC_WS_URL in .env.local

2. **Messages Not Displaying**
   - Verify metadata.component field is "chat"
   - Check browser console for WebSocket errors

3. **Streaming Not Working**
   - Ensure backend has streaming enabled
   - Check for is_delta messages in console

### Debug Mode

Enable debug logging by setting:
```typescript
const DEBUG_PLANNING = true; // in use-websocket.tsx
```

## Contributing

When contributing to the frontend:

1. Follow the existing component patterns
2. Maintain TypeScript type safety
3. Test with both ReAct and CodeAct agents
4. Ensure metadata-driven rendering is preserved
5. Add appropriate debug logging for new features
# II Agent Frontend

## Introduction

The II Agent Frontend is a modern web interface for the II Agent platform, providing an intuitive way to interact with Anthropic Claude models. It offers a responsive chat interface, file upload capabilities, browser integration, and session management through a WebSocket connection to the II Agent backend.

## Prerequisites

- Node.js 18+ (LTS recommended)
- npm or yarn package manager
- II Agent backend server running (WebSocket server)

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
   NEXT_PUBLIC_VSCODE_URL=http://127.0.0.1:8080
   ```

   Note: NEXT_PUBLIC_VSCODE_URL is optional and can be omitted if you're not using VS Code integration.
   Adjust the URL to match your backend server address.

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
│   ├── chat/             # Chat-related components
│   ├── ui/               # UI components (buttons, inputs, etc.)
│   ├── workspace/        # Workspace-related components
│   └── ...
├── lib/                  # Utility functions and helpers
├── providers/            # React context providers
├── public/               # Static assets
├── typings/              # TypeScript type definitions
│   └── agent.ts          # Agent-related type definitions
├── .env.local            # Local environment variables (create this)
├── next.config.ts        # Next.js configuration
├── package.json          # Project dependencies and scripts
└── tsconfig.json         # TypeScript configuration
```

## Key Components

- **Home**: Main page component that orchestrates the application
- **ChatView**: Handles the chat interface and message display
- **Browser**: In-app browser component for web browsing
- **CodeEditor**: Code editing component
- **Terminal**: Terminal emulation component
- **SidebarButton**: Navigation sidebar component

## Technologies Used

- **Next.js 14+**: React framework with App Router
- **React 18+**: UI library
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **Lucide Icons**: Icon library
- **WebSocket API**: Real-time communication with backend
- **ShadcnUI**: Component library based on Radix UI

## WebSocket Integration

The frontend connects to the II Agent backend via WebSocket for real-time communication. The WebSocket connection is managed in the `Home` component, handling the following:

1. Establishing the WebSocket connection
2. Sending user queries and file uploads
3. Receiving and processing agent responses
4. Managing the connection lifecycle

The WebSocket connection uses the device ID (stored in cookies) to maintain session continuity.

### Message Types

The WebSocket communication uses a structured message format:

```typescript
{
  type: string; // Message type (e.g., "query", "init_agent")
  content: {
    // Message content
    // Content varies by message type
  }
}
```

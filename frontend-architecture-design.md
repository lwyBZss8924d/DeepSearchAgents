# DeepSearchAgents Web Frontend Architecture Design

## Overview

This document outlines the comprehensive architecture design for the DeepSearchAgents Web frontend, based on the open-canvas project structure and tailored for intelligent search agent interactions.

## Technology Stack

### Core Framework
- **Next.js 14**: React framework with App Router for server-side rendering and optimal performance
- **TypeScript**: Full type safety and enhanced developer experience
- **React 18**: Latest React features including concurrent rendering and Suspense

### UI & Styling
- **Tailwind CSS**: Utility-first CSS framework with custom design system
- **Radix UI**: Accessible, unstyled UI primitives for complex components
- **shadcn/ui**: Pre-built component library based on Radix UI
- **Framer Motion**: Animation library for smooth transitions and interactions
- **Lucide React**: Modern icon library

### State Management & Data Flow
- **Zustand**: Lightweight state management for global application state
- **React Hook Form**: Form state management with Zod validation
- **TanStack Query (React Query)**: Server state management and caching

### Real-time Communication
- **Server-Sent Events (SSE)**: For streaming agent execution steps
- **WebSocket**: For real-time bidirectional communication (future enhancement)

### Development Tools
- **ESLint**: Code linting and quality assurance
- **Prettier**: Code formatting
- **Husky**: Git hooks for pre-commit validation

## Project Structure

```
deepsearch-frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── globals.css              # Global styles and CSS variables
│   │   ├── layout.tsx               # Root layout component
│   │   ├── page.tsx                 # Home page component
│   │   ├── search/                  # Search-related pages
│   │   │   ├── page.tsx            # Main search interface
│   │   │   └── [sessionId]/        # Session-specific pages
│   │   │       └── page.tsx        # Session detail view
│   │   └── api/                     # API routes (proxy to backend)
│   │       ├── agents/             # Agent execution endpoints
│   │       └── health/             # Health check endpoints
│   ├── components/                   # React components
│   │   ├── ui/                      # Base UI components (shadcn/ui)
│   │   ├── search/                  # Search-specific components
│   │   ├── agent/                   # Agent execution components
│   │   ├── layout/                  # Layout components
│   │   └── common/                  # Shared components
│   ├── hooks/                       # Custom React hooks
│   ├── lib/                         # Utility functions and configurations
│   ├── stores/                      # Zustand stores
│   ├── types/                       # TypeScript type definitions
│   └── utils/                       # Helper utilities
├── public/                          # Static assets
├── docs/                           # Documentation
└── config files                    # Various configuration files
```

## Page Layout Design

### 1. Main Search Interface Layout

The primary interface follows a dual-pane layout inspired by open-canvas:

```
┌─────────────────────────────────────────────────────────────┐
│                    Header Navigation                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │                     │  │                                 │ │
│  │   Search Interface  │  │     Agent Execution Canvas     │ │
│  │                     │  │                                 │ │
│  │  ┌───────────────┐  │  │  ┌─────────────────────────────┐ │ │
│  │  │ Search Input  │  │  │  │                             │ │ │
│  │  └───────────────┘  │  │  │    Agent Steps Display     │ │ │
│  │                     │  │  │                             │ │ │
│  │  ┌───────────────┐  │  │  └─────────────────────────────┘ │ │
│  │  │ Agent Config  │  │  │                                 │ │
│  │  └───────────────┘  │  │  ┌─────────────────────────────┐ │ │
│  │                     │  │  │                             │ │ │
│  │  ┌───────────────┐  │  │  │    Search Results           │ │ │
│  │  │ Search History│  │  │  │                             │ │ │
│  │  └───────────────┘  │  │  └─────────────────────────────┘ │ │
│  │                     │  │                                 │ │
│  └─────────────────────┘  └─────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Responsive Design Breakpoints

- **Desktop (≥1024px)**: Dual-pane layout with 40/60 split
- **Tablet (768px-1023px)**: Stacked layout with collapsible panels
- **Mobile (≤767px)**: Single column with tab-based navigation

## Component Structure Design

### 1. Component Hierarchy

```
App
├── Layout
│   ├── Header
│   │   ├── Navigation
│   │   ├── ThemeToggle
│   │   └── UserMenu
│   └── Footer
├── SearchInterface
│   ├── SearchInput
│   │   ├── QueryInput
│   │   ├── AgentSelector
│   │   └── AdvancedOptions
│   ├── AgentConfiguration
│   │   ├── ModelSelector
│   │   ├── ParameterControls
│   │   └── ToolsConfiguration
│   └── SearchHistory
│       ├── HistoryList
│       ├── HistoryItem
│       └── HistoryActions
└── AgentCanvas
    ├── ExecutionDisplay
    │   ├── StepVisualization
    │   ├── ProgressIndicator
    │   └── StatusDisplay
    ├── ResultsDisplay
    │   ├── SearchResults
    │   ├── SourcesList
    │   └── FinalAnswer
    └── InteractionControls
        ├── StopExecution
        ├── SaveResults
        └── ShareSession
```

### 2. Core Components Specification

#### SearchInterface Components

**SearchInput**
```typescript
interface SearchInputProps {
  onSubmit: (query: string, config: AgentConfig) => void;
  isLoading: boolean;
  placeholder?: string;
}
```

**AgentSelector**
```typescript
interface AgentSelectorProps {
  selectedAgent: 'react' | 'codact';
  onAgentChange: (agent: 'react' | 'codact') => void;
  disabled?: boolean;
}
```

**AgentConfiguration**
```typescript
interface AgentConfigurationProps {
  config: AgentConfig;
  onConfigChange: (config: Partial<AgentConfig>) => void;
  agentType: 'react' | 'codact';
}
```

#### AgentCanvas Components

**ExecutionDisplay**
```typescript
interface ExecutionDisplayProps {
  steps: AgentStep[];
  currentStep?: number;
  isExecuting: boolean;
  onStepSelect?: (stepIndex: number) => void;
}
```

**StepVisualization**
```typescript
interface StepVisualizationProps {
  step: AgentStep;
  isActive: boolean;
  isCompleted: boolean;
  onExpand?: () => void;
}
```

**ResultsDisplay**
```typescript
interface ResultsDisplayProps {
  results: SearchResult[];
  finalAnswer?: string;
  sources: Source[];
  onSourceClick?: (source: Source) => void;
}
```

### 3. UI Component Library (shadcn/ui based)

**Base Components:**
- Button, Input, Textarea
- Card, Badge, Avatar
- Dialog, Popover, Tooltip
- Tabs, Accordion, Collapsible
- Progress, Spinner, Skeleton
- Toast, Alert, AlertDialog

**Custom Components:**
- SearchInput with autocomplete
- AgentStepCard with syntax highlighting
- SourceCard with preview
- ConfigurationPanel with form validation
- StreamingText with typewriter effect

## State Management Architecture

### 1. Zustand Store Structure

#### Global Application Store
```typescript
interface AppStore {
  // UI State
  theme: 'light' | 'dark' | 'system';
  sidebarCollapsed: boolean;
  
  // User Preferences
  defaultAgentType: 'react' | 'codact';
  defaultModelConfig: ModelConfig;
  
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
}
```

#### Search Store
```typescript
interface SearchStore {
  // Current Search State
  currentQuery: string;
  currentSession: SearchSession | null;
  isExecuting: boolean;
  
  // Agent Configuration
  agentConfig: AgentConfig;
  
  // Execution State
  executionSteps: AgentStep[];
  currentStepIndex: number;
  
  // Results
  searchResults: SearchResult[];
  finalAnswer: string | null;
  sources: Source[];
  
  // Actions
  startSearch: (query: string, config: AgentConfig) => Promise<void>;
  stopExecution: () => void;
  updateStep: (step: AgentStep) => void;
  setResults: (results: SearchResult[], answer: string, sources: Source[]) => void;
  clearSession: () => void;
}
```

#### History Store
```typescript
interface HistoryStore {
  // Search History
  searchHistory: SearchHistoryItem[];
  
  // Saved Sessions
  savedSessions: SavedSession[];
  
  // Actions
  addToHistory: (item: SearchHistoryItem) => void;
  removeFromHistory: (id: string) => void;
  saveSession: (session: SearchSession) => void;
  loadSession: (id: string) => Promise<SearchSession>;
  clearHistory: () => void;
}
```

### 2. Server State Management (TanStack Query)

#### API Query Keys
```typescript
export const queryKeys = {
  agents: {
    all: ['agents'] as const,
    execute: (query: string, config: AgentConfig) => 
      ['agents', 'execute', query, config] as const,
    session: (sessionId: string) => 
      ['agents', 'session', sessionId] as const,
  },
  history: {
    all: ['history'] as const,
    search: (query: string) => 
      ['history', 'search', query] as const,
  },
} as const;
```

#### Custom Hooks for API Integration
```typescript
// Agent execution hook with streaming
export function useAgentExecution() {
  const searchStore = useSearchStore();
  
  return useMutation({
    mutationFn: async ({ query, config }: ExecuteAgentParams) => {
      return executeAgentWithStreaming(query, config, {
        onStep: (step) => searchStore.updateStep(step),
        onResult: (results, answer, sources) => 
          searchStore.setResults(results, answer, sources),
      });
    },
    onSuccess: (data) => {
      // Handle successful completion
    },
    onError: (error) => {
      // Handle execution errors
    },
  });
}

// Search history hook
export function useSearchHistory() {
  return useQuery({
    queryKey: queryKeys.history.all,
    queryFn: fetchSearchHistory,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

## Data Flow Architecture

### 1. Agent Execution Flow

```
User Input → SearchInput Component
     ↓
Search Store (startSearch)
     ↓
API Call (executeAgent)
     ↓
Streaming Response Handler
     ↓
Store Updates (updateStep, setResults)
     ↓
Component Re-renders
     ↓
UI Updates (ExecutionDisplay, ResultsDisplay)
```

### 2. Real-time Updates via Server-Sent Events

```typescript
// SSE connection for streaming agent steps
export function useAgentStreaming(sessionId: string) {
  const searchStore = useSearchStore();
  
  useEffect(() => {
    if (!sessionId) return;
    
    const eventSource = new EventSource(`/api/agents/stream/${sessionId}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'step':
          searchStore.updateStep(data.step);
          break;
        case 'result':
          searchStore.setResults(data.results, data.answer, data.sources);
          break;
        case 'error':
          // Handle errors
          break;
        case 'complete':
          // Handle completion
          break;
      }
    };
    
    return () => eventSource.close();
  }, [sessionId, searchStore]);
}
```

## API Integration Layer

### 1. Backend API Endpoints Integration

```typescript
// API client configuration
export const apiClient = {
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  
  // Agent execution endpoints
  agents: {
    executeReact: (query: string) => 
      post('/api/v1/agent/run_react_agent', { user_input: query }),
    
    executeDeepSearch: (query: string) => 
      post('/api/v1/agent/run_deepsearch_agent', { user_input: query }),
    
    executeAgent: (query: string, agentType: string, modelArgs?: any) =>
      post('/api/v1/agent/run_agent', { 
        user_input: query, 
        agent_type: agentType,
        model_args: modelArgs 
      }),
  },
  
  // Health check
  health: () => get('/api/v1/health'),
};
```

### 2. Type Definitions

```typescript
// Core types for agent interaction
export interface AgentConfig {
  type: 'react' | 'codact';
  model: string;
  temperature: number;
  maxSteps: number;
  tools: string[];
}

export interface AgentStep {
  id: string;
  type: 'thought' | 'action' | 'observation' | 'final_answer';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface SearchResult {
  id: string;
  title: string;
  url: string;
  snippet: string;
  relevanceScore: number;
  source: string;
}

export interface SearchSession {
  id: string;
  query: string;
  agentConfig: AgentConfig;
  steps: AgentStep[];
  results: SearchResult[];
  finalAnswer: string | null;
  status: 'running' | 'completed' | 'error' | 'stopped';
  createdAt: Date;
  completedAt?: Date;
}
```

## Performance Optimization

### 1. Code Splitting & Lazy Loading
- Route-based code splitting with Next.js dynamic imports
- Component-level lazy loading for heavy components
- Progressive loading of search results

### 2. Caching Strategy
- TanStack Query for server state caching
- Browser storage for user preferences and search history
- Service worker for offline functionality (future enhancement)

### 3. Streaming & Real-time Updates
- Server-Sent Events for agent step streaming
- Optimistic updates for immediate UI feedback
- Debounced search input to reduce API calls

## Error Handling & User Experience

### 1. Error Boundaries
- Global error boundary for unhandled errors
- Component-specific error boundaries for graceful degradation
- Retry mechanisms for failed API calls

### 2. Loading States
- Skeleton loaders for initial page load
- Progress indicators for agent execution
- Streaming text effects for real-time updates

### 3. User Feedback
- Toast notifications for actions and errors
- Status indicators for agent execution states
- Contextual help and tooltips

## Security Considerations

### 1. API Security
- Environment-based API endpoint configuration
- Request/response validation with Zod schemas
- Rate limiting on client-side API calls

### 2. Data Privacy
- Local storage for sensitive user preferences
- Optional search history with user control
- Clear data deletion mechanisms

## Deployment & Development

### 1. Development Environment
- Hot reload with Next.js dev server
- TypeScript strict mode for type safety
- ESLint and Prettier for code quality

### 2. Build & Deployment
- Static site generation where possible
- Docker containerization for consistent deployment
- Environment-specific configuration management

This architecture provides a solid foundation for building a modern, responsive, and feature-rich Web frontend for the DeepSearchAgents project, leveraging the best practices from the open-canvas project while being specifically tailored for intelligent search agent interactions.


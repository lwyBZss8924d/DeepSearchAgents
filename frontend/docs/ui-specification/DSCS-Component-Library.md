# DSCS Component Library Reference

> **Version**: 0.3.3.dev  
> **Last Updated**: 2025-01-31  
> **Status**: Implementation Complete

## Table of Contents

1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Layout Components](#layout-components)
4. [Animation Components](#animation-components)
5. [Utility Components](#utility-components)
6. [Hooks & Context](#hooks--context)
7. [Type Definitions](#type-definitions)
8. [Usage Examples](#usage-examples)

---

## Overview

This document provides a comprehensive API reference for all DeepSearchAgents UI components. Each component is documented with its props, usage examples, and integration patterns.

### Component Naming Convention

- **DS** prefix for all design system components
- **Agent** for agent-specific functionality
- **Terminal** for terminal-style UI elements

---

## Core Components

### DSAgentStateBadge

Displays the current agent state with optional animations.

```typescript
interface DSAgentStateBadgeProps {
  state: AgentState;
  text?: string;
  showIcon?: boolean;
  showSpinner?: boolean;
  isAnimated?: boolean;
  className?: string;
}

type AgentState = 
  | 'planning' 
  | 'thinking' 
  | 'coding' 
  | 'running' 
  | 'final' 
  | 'working' 
  | 'error';
```

**Usage:**
```tsx
<DSAgentStateBadge
  state="thinking"
  text="Processing query..."
  showSpinner={true}
  isAnimated={true}
/>
```

**State Configurations:**
| State | Icon | Color | Animation |
|-------|------|-------|-----------|
| planning | ◆ | Purple (#8B5CF6) | Pulse |
| thinking | ◊ | Yellow (#FFEB3B) | Rotate |
| coding | ▶ | Green (#00FF41) | Blink |
| running | ■ | Cyan (#00FFFF) | Progress |
| final | ✓ | Emerald (#10B981) | Glow |
| error | ✗ | Red (#FF5252) | None |

---

### DSAgentMessageCard

Container for agent messages with metadata and styling.

```typescript
interface DSAgentMessageCardProps {
  type: 'user' | 'assistant';
  metadata?: {
    step_type?: 'planning' | 'action' | 'final_answer';
    message_type?: string;
    tool_name?: string;
    streaming?: boolean;
  };
  timestamp?: Date;
  children: React.ReactNode;
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentMessageCard
  type="assistant"
  metadata={{
    step_type: 'action',
    tool_name: 'search_web',
    streaming: true
  }}
>
  <p>Searching for information about CodeAct...</p>
  <DSAgentCodeBlock language="python">
    {`results = search_web(query="CodeAct paradigm")`}
  </DSAgentCodeBlock>
</DSAgentMessageCard>
```

---

### DSAgentToolBadge

Interactive badge for tool execution display.

```typescript
interface DSAgentToolBadgeProps {
  toolName: string;
  icon?: string | React.ReactNode;
  status?: 'pending' | 'active' | 'completed' | 'error';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentToolBadge
  toolName="search_web"
  icon="🔍"
  status="active"
  onClick={() => console.log('Tool clicked')}
/>
```

**Tool Icon Mapping:**
```typescript
const toolIcons = {
  search_web: '🔍',
  read_url: '📄',
  wolfram_alpha: '🧮',
  python_interpreter: '🐍',
  final_answer: '✅',
  embed: '🔤',
  chunk: '📋',
  rerank: '📈'
};
```

---

### DSAgentCodeBlock

Syntax-highlighted code display with copy functionality.

```typescript
interface DSAgentCodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  highlightLines?: number[];
  showCopyButton?: boolean;
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentCodeBlock
  code={pythonCode}
  language="python"
  showLineNumbers={true}
  highlightLines={[3, 4, 5]}
  showCopyButton={true}
/>
```

---

### DSAgentTimer

Real-time execution timer component.

```typescript
interface DSAgentTimerProps {
  startTime?: number | null;
  format?: 'short' | 'long';
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentTimer 
  startTime={agentStartTime}
  format="short" // "15s" or "1m 23s"
/>
```

---

### DSAgentRandomMatrix

15-character ASCII animation with cyberpunk gradient.

```typescript
interface DSAgentRandomMatrixProps {
  isActive: boolean;
  updateInterval?: number; // Default: 200ms
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentRandomMatrix 
  isActive={isAgentRunning}
  updateInterval={150}
/>
```

---

### DSAgentASCIISpinner

Animated ASCII spinner for loading states.

```typescript
interface DSAgentASCIISpinnerProps {
  state: AgentState;
  size?: 'sm' | 'md' | 'lg';
  speed?: number; // ms per frame
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentASCIISpinner
  state="thinking"
  size="sm"
  speed={200}
/>
```

**Animation Patterns:**
```typescript
const spinnerPatterns = {
  dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
  line: ['|', '/', '-', '\\'],
  circle: ['◐', '◓', '◑', '◒'],
  square: ['◰', '◳', '◲', '◱']
};
```

---

## Layout Components

### DSAgentTerminalContainer

Main terminal-style container with header.

```typescript
interface DSAgentTerminalContainerProps {
  title?: string;
  icon?: React.ReactNode;
  headerContent?: React.ReactNode;
  headerRightContent?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}
```

**Usage:**
```tsx
<DSAgentTerminalContainer
  title="HAL-9000™ Terminal"
  icon={<TerminalIcon />}
  headerContent={<AgentRunningStatus />}
  headerRightContent={<SessionStateIndicator />}
>
  {children}
</DSAgentTerminalContainer>
```

---

### DSAgentChatLayout

Split-panel layout for chat and code/terminal.

```typescript
interface DSAgentChatLayoutProps {
  chatContent: React.ReactNode;
  codeContent: React.ReactNode;
  terminalContent: React.ReactNode;
  stepNavigator?: React.ReactNode;
  inputArea: React.ReactNode;
}
```

**Usage:**
```tsx
<DSAgentChatLayout
  chatContent={<AgentChat />}
  codeContent={<CodeEditor />}
  terminalContent={<Terminal />}
  stepNavigator={<StepNavigator />}
  inputArea={<AgentQuestionInput />}
/>
```

---

### DSTabs

Terminal-style tabbed interface.

```typescript
interface DSTabsProps {
  defaultValue: string;
  children: React.ReactNode;
  className?: string;
}

interface DSTabsTriggerProps {
  value: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}
```

**Usage:**
```tsx
<DSTabs defaultValue="code">
  <DSTabsList>
    <DSTabsTrigger value="code" icon={<CodeIcon />}>
      Code
    </DSTabsTrigger>
    <DSTabsTrigger value="browser" icon={<MonitorIcon />}>
      Browser
    </DSTabsTrigger>
  </DSTabsList>
  
  <DSTabsContent value="code">
    <CodeEditor />
  </DSTabsContent>
  
  <DSTabsContent value="browser">
    <Browser />
  </DSTabsContent>
</DSTabs>
```

---

## Animation Components

### DSStreamingText

Character-by-character text reveal animation.

```typescript
interface DSStreamingTextProps {
  text: string;
  speed?: number; // ms per character
  onComplete?: () => void;
  showCursor?: boolean;
  className?: string;
}
```

**Usage:**
```tsx
<DSStreamingText
  text="Analyzing your query..."
  speed={30}
  showCursor={true}
  onComplete={() => setStreamingComplete(true)}
/>
```

---

### DSAnimatedList

Staggered animation for list items.

```typescript
interface DSAnimatedListProps {
  items: React.ReactNode[];
  staggerDelay?: number; // ms between items
  animation?: 'fadeIn' | 'slideIn' | 'scaleIn';
  className?: string;
}
```

**Usage:**
```tsx
<DSAnimatedList
  items={messages}
  staggerDelay={50}
  animation="fadeIn"
/>
```

---

## Utility Components

### DSThemeSwitcher

Theme selection component.

```typescript
interface DSThemeSwitcherProps {
  themes?: Theme[];
  currentTheme?: string;
  onChange?: (theme: string) => void;
  className?: string;
}
```

**Usage:**
```tsx
<DSThemeSwitcher
  themes={['classic', 'solarized', 'tokyo-night']}
  currentTheme={currentTheme}
  onChange={setTheme}
/>
```

---

### DSCopyButton

Copy to clipboard button with feedback.

```typescript
interface DSCopyButtonProps {
  text: string;
  onCopy?: () => void;
  successMessage?: string;
  className?: string;
}
```

**Usage:**
```tsx
<DSCopyButton
  text={codeContent}
  successMessage="Copied!"
  onCopy={() => analytics.track('code_copied')}
/>
```

---

## Hooks & Context

### useWebSocket

WebSocket connection management.

```typescript
interface UseWebSocketReturn {
  sendQuery: (query: string) => Promise<void>;
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  messages: DSAgentRunMessage[];
}

const useWebSocket = (sessionId: string | null): UseWebSocketReturn
```

**Usage:**
```tsx
const { sendQuery, isConnected, messages } = useWebSocket(sessionId);
```

---

### useAgentState

Global agent state management.

```typescript
interface UseAgentStateReturn {
  currentStatus: DetailedAgentStatus;
  isGenerating: boolean;
  currentStep: number;
  maxStep: number;
  startTime: number | null;
}

const useAgentState = (): UseAgentStateReturn
```

---

### useStreamingAccumulator

Message streaming accumulation.

```typescript
interface UseStreamingAccumulatorReturn {
  accumulate: (streamId: string, delta: string) => string;
  complete: (streamId: string) => string;
  getContent: (streamId: string) => string;
}

const useStreamingAccumulator = (): UseStreamingAccumulatorReturn
```

---

## Type Definitions

### Core Types

```typescript
// Agent status types
type DetailedAgentStatus = 
  | 'standby'
  | 'initial_planning' 
  | 'update_planning'
  | 'thinking'
  | 'coding'
  | 'actions_running'
  | 'writing'
  | 'working'
  | 'loading'
  | 'error';

// Message types
interface DSAgentRunMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata: {
    component?: 'chat' | 'webide' | 'terminal';
    message_type?: string;
    step_type?: string;
    streaming?: boolean;
    is_delta?: boolean;
    stream_id?: string;
    tool_name?: string;
    is_final_answer?: boolean;
  };
  created_at?: string;
}

// Theme types
interface TerminalTheme {
  name: string;
  type: 'dark' | 'light';
  colors: Record<string, string>;
  fonts: {
    mono: string[];
    ui: string[];
  };
}
```

---

## Usage Examples

### Complete Agent Message Flow

```tsx
const AgentConversation = () => {
  const { state } = useAppContext();
  const { sendQuery, messages } = useWebSocket(state.sessionId);
  
  return (
    <DSAgentTerminalContainer>
      <div className="flex-1 overflow-y-auto">
        {messages.map((message, index) => (
          <DSAgentMessageCard
            key={message.message_id}
            type={message.role}
            metadata={message.metadata}
          >
            {message.metadata.step_type === 'planning' && (
              <DSAgentStateBadge 
                state="planning"
                isAnimated={message.metadata.streaming}
              />
            )}
            
            {message.metadata.tool_name && (
              <DSAgentToolBadge
                toolName={message.metadata.tool_name}
                status={message.metadata.streaming ? 'active' : 'completed'}
              />
            )}
            
            <div className="prose">
              {message.metadata.streaming ? (
                <DSStreamingText text={message.content} />
              ) : (
                <Markdown>{message.content}</Markdown>
              )}
            </div>
            
            {message.metadata.code && (
              <DSAgentCodeBlock
                code={message.metadata.code}
                language="python"
              />
            )}
          </DSAgentMessageCard>
        ))}
      </div>
      
      <AgentQuestionInput onSubmit={sendQuery} />
    </DSAgentTerminalContainer>
  );
};
```

### Custom Theme Implementation

```tsx
const customTheme: TerminalTheme = {
  name: 'Cyberpunk',
  type: 'dark',
  colors: {
    'terminal-bg': '#0a0014',
    'terminal-fg': '#ff0080',
    'terminal-bright': '#ff00ff',
    'agent-thinking': '#ffff00',
    'agent-coding': '#00ff00',
    'agent-running': '#00ffff'
  },
  fonts: {
    mono: ['Fira Code', 'monospace'],
    ui: ['Inter', 'sans-serif']
  }
};

<ThemeProvider theme={customTheme}>
  <App />
</ThemeProvider>
```

---

## Best Practices

1. **Component Composition**: Build complex UIs by composing smaller DS components
2. **Type Safety**: Always use TypeScript interfaces for props
3. **Accessibility**: Include proper ARIA labels and keyboard support
4. **Performance**: Use React.memo for expensive components
5. **Theming**: Leverage CSS variables for easy customization

---

## Contributing

When adding new components:

1. Follow the DS naming convention
2. Include TypeScript definitions
3. Add usage examples
4. Document all props
5. Include accessibility features
6. Add to component index export
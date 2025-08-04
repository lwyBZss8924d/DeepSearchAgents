# DeepSearchAgents UI Design System Specification

## Sub-Task(1.2): UI "Design System" Technical Specification

> Building on the Design Language philosophy, this document provides concrete specifications for implementing the DeepSearchAgents Web-TUI interface.

### Table of Contents
1. [System Architecture](#1-system-architecture)
2. [Core Components Library](#2-core-components-library)
3. [State Management Patterns](#3-state-management-patterns)
4. [Theme System Architecture](#4-theme-system-architecture)
5. [Animation & Interaction Specifications](#5-animation--interaction-specifications)
6. [Technical Implementation Details](#6-technical-implementation-details)
7. [Component Usage Guidelines](#7-component-usage-guidelines)

---

## 1. System Architecture

### 1.1 Component Library Organization

```
components/
├── terminal/                    # Terminal-style components
│   ├── core/                   # Core terminal components
│   │   ├── TerminalContainer
│   │   ├── TerminalPrompt
│   │   └── TerminalCursor
│   ├── agent/                  # Agent-specific components
│   │   ├── AgentMessageCard
│   │   ├── AgentStateBadge
│   │   ├── AgentToolBadge
│   │   └── AgentCodeBlock
│   ├── layout/                 # Layout components
│   │   ├── TerminalSplitView
│   │   ├── TerminalSidebar
│   │   └── TerminalTabs
│   └── ui/                     # Basic UI elements
│       ├── TerminalButton
│       ├── TerminalInput
│       └── TerminalSelect
├── streaming/                  # Streaming components
│   ├── StreamingText
│   ├── StreamingCode
│   └── StreamingIndicator
└── theme/                      # Theme components
    ├── ThemeProvider
    └── ThemeSwitcher
```

### 1.2 WebTUI Integration Strategy

```typescript
// Layer-based CSS architecture
const cssLayers = {
  base: ['webtui.base', 'ds.base'],
  utilities: ['webtui.utils', 'ds.utils'],
  components: ['webtui.components', 'ds.components'],
  overrides: ['ds.overrides']
};

// Component extension pattern
interface TerminalComponent extends WebTUIComponent {
  variant: 'terminal' | 'minimal' | 'rich';
  theme?: ThemeVariant;
  streaming?: boolean;
}
```

### 1.3 State Architecture

```typescript
// Global state structure
interface DSAgentState {
  agent: {
    status: AgentStatus;
    currentStep: number;
    planningInterval: number;
    isStreaming: boolean;
  };
  messages: DSAgentMessage[];
  theme: ThemeConfig;
  ui: {
    sidebarOpen: boolean;
    codeEditorVisible: boolean;
    terminalHeight: number;
  };
}
```

---

## 2. Core Components Library

### 2.1 Agent Message Card

**Component: `AgentMessageCard`**

```typescript
interface AgentMessageCardProps {
  type: 'planning' | 'action' | 'observation' | 'final' | 'error';
  status?: 'idle' | 'active' | 'completed';
  step?: number;
  timestamp?: Date;
  streaming?: boolean;
  children: React.ReactNode;
}
```

**Visual Specifications:**
- Border: 1px solid with left accent (3px)
- Padding: 16px (1rem)
- Border radius: 8px (0.5rem)
- Background: Elevated surface color
- Shadow: 0 2px 4px rgba(0,0,0,0.1) when active

**State Variations:**
```css
/* Planning State */
.agent-card--planning {
  border-left-color: var(--agent-planning);
  background: color-mix(in oklch, var(--agent-planning) 5%, var(--bg-elevated));
}

/* Action State */
.agent-card--action {
  border-left-color: var(--agent-coding);
  animation: pulse-border 2s ease-in-out infinite;
}

/* Active State */
.agent-card--active {
  box-shadow: 0 0 0 1px var(--border-active);
}
```

### 2.2 Agent State Badge

**Component: `AgentStateBadge`**

```typescript
interface AgentStateBadgeProps {
  state: AgentState;
  animated?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  customText?: string;
}

type AgentState = 
  | 'planning-thinking'
  | 'planning-writing'
  | 'action-thinking'
  | 'coding'
  | 'running'
  | 'observing'
  | 'final-writing'
  | 'idle';
```

**Visual Specifications:**
```
Size variants:
- sm: height 24px, font-size 12px, padding 4px 8px
- md: height 32px, font-size 14px, padding 6px 12px
- lg: height 40px, font-size 16px, padding 8px 16px

Structure:
┌─────────────────────────┐
│ [◆] Planning...         │  <- Icon + Text
└─────────────────────────┘
```

**Animation Patterns:**
```typescript
const stateAnimations = {
  'planning-thinking': 'pulse 2s ease-in-out infinite',
  'planning-writing': 'typewriter 0.15s steps(1) infinite',
  'action-thinking': 'rotate 1s linear infinite',
  'coding': 'blink 1s step-end infinite',
  'running': 'progress 1.5s ease-in-out infinite',
  'observing': 'scan 2s linear infinite',
  'final-writing': 'glow 1.5s ease-in-out infinite'
};
```

### 2.3 Tool Call Badge

**Component: `ToolCallBadge`**

```typescript
interface ToolCallBadgeProps {
  toolName: string;
  icon?: string | React.ReactNode;
  status?: 'pending' | 'active' | 'completed' | 'error';
  expandable?: boolean;
  onClick?: () => void;
  metadata?: {
    duration?: number;
    tokenCount?: number;
    resultPreview?: string;
  };
}
```

**Interaction States:**
```
Default:    [🔍 search_web]
Hover:      [🔍 search_web] (scale: 1.05, brightness: 1.2)
Active:     [⚡ search_web] (animated border)
Completed:  [✓ search_web] (green checkmark overlay)
Expanded:   ┌──────────────────────┐
           │ 🔍 search_web        │
           │ Duration: 1.2s       │
           │ Tokens: 142          │
           │ Results: 5 sources   │
           └──────────────────────┘
```

### 2.4 Code Block Component

**Component: `AgentCodeBlock`**

```typescript
interface AgentCodeBlockProps {
  code: string;
  language?: 'python' | 'javascript' | 'bash' | 'json';
  lineNumbers?: boolean;
  highlightLines?: number[];
  streaming?: boolean;
  executable?: boolean;
  onExecute?: () => void;
  executionResult?: ExecutionResult;
}
```

**Visual Structure:**
```
┌─ ```python ─────────────────[Copy][Run]─┐
│ 1 │ import search_web                   │
│ 2 │                                     │
│ 3 │ results = search_web(               │
│ 4 │     query="CodeAct paradigm",       │
│ 5 │     max_results=5                   │
│ 6 │ )                                   │
│ 7 │ print(f"Found {len(results)}")      │
└─────────────────────────────────────────┘
```

### 2.5 Terminal Container

**Component: `TerminalContainer`**

```typescript
interface TerminalContainerProps {
  variant?: 'embedded' | 'fullscreen' | 'split';
  title?: string;
  showControls?: boolean;
  height?: number | string;
  resizable?: boolean;
}
```

**Layout Specifications:**
```
┌─ DeepSearchAgents Terminal ─────[−][□][×]─┐
│ $ agent@deepsearch:~                      │
│ > Initializing CodeAct Agent...           │
│ > Loading tools: search_web, read_url...  │
│ > Ready for input.                        │
│ > _                                       │
└───────────────────────────────────────────┘
```

---

## 3. State Management Patterns

### 3.1 Message State Flow

```typescript
// Message lifecycle states
enum MessageLifecycle {
  PENDING = 'pending',        // Message created but not sent
  STREAMING = 'streaming',    // Currently receiving content
  COMPLETE = 'complete',      // Fully received
  ERROR = 'error'            // Error occurred
}

// Message update pattern
interface MessageUpdate {
  id: string;
  delta?: string;           // Incremental content
  metadata?: Partial<MessageMetadata>;
  lifecycle?: MessageLifecycle;
}
```

### 3.2 Streaming State Management

```typescript
// Streaming accumulator pattern
class StreamingAccumulator {
  private buffers: Map<string, string[]> = new Map();
  
  accumulate(streamId: string, delta: string): string {
    if (!this.buffers.has(streamId)) {
      this.buffers.set(streamId, []);
    }
    this.buffers.get(streamId)!.push(delta);
    return this.buffers.get(streamId)!.join('');
  }
  
  complete(streamId: string): string {
    const content = this.getContent(streamId);
    this.buffers.delete(streamId);
    return content;
  }
}
```

### 3.3 UI State Synchronization

```typescript
// UI state hooks
const useAgentState = () => {
  const [state, setState] = useState<AgentUIState>();
  
  // Sync with WebSocket updates
  useEffect(() => {
    const unsubscribe = wsClient.subscribe((message) => {
      setState(prev => updateAgentState(prev, message));
    });
    return unsubscribe;
  }, []);
  
  return state;
};
```

---

## 4. Theme System Architecture

### 4.1 Theme Structure

```typescript
interface TerminalTheme {
  name: string;
  type: 'dark' | 'light';
  colors: {
    // Terminal base colors
    background: string;
    foreground: string;
    cursor: string;
    selection: string;
    
    // ANSI colors (0-15)
    black: string;
    red: string;
    green: string;
    yellow: string;
    blue: string;
    magenta: string;
    cyan: string;
    white: string;
    brightBlack: string;
    brightRed: string;
    brightGreen: string;
    brightYellow: string;
    brightBlue: string;
    brightMagenta: string;
    brightCyan: string;
    brightWhite: string;
    
    // Agent-specific colors
    agentPlanning: string;
    agentThinking: string;
    agentCoding: string;
    agentRunning: string;
    agentFinal: string;
    agentError: string;
  };
  fonts: {
    mono: string[];
    ui: string[];
  };
  spacing: {
    unit: number;
    scale: number[];
  };
}
```

### 4.2 Theme Presets

```typescript
const themes = {
  classic: {
    name: 'Classic Terminal',
    type: 'dark',
    colors: {
      background: '#0a0a0a',
      foreground: '#00ff41',
      green: '#00ff41',
      brightGreen: '#33ff66',
      // ... full color palette
    }
  },
  solarized: {
    name: 'Solarized Dark',
    type: 'dark',
    colors: {
      background: '#002b36',
      foreground: '#839496',
      green: '#859900',
      // ... solarized palette
    }
  },
  tokyoNight: {
    name: 'Tokyo Night',
    type: 'dark',
    colors: {
      background: '#1a1b26',
      foreground: '#c0caf5',
      green: '#9ece6a',
      // ... tokyo night palette
    }
  }
};
```

### 4.3 CSS Custom Properties Mapping

```css
:root {
  /* Dynamic theme properties */
  --terminal-bg: var(--theme-background);
  --terminal-fg: var(--theme-foreground);
  
  /* Component-specific mappings */
  --agent-card-bg: color-mix(in oklch, var(--terminal-bg) 95%, var(--terminal-fg) 5%);
  --agent-card-border: color-mix(in oklch, var(--terminal-fg) 20%, transparent);
  
  /* State color mappings */
  --state-planning: var(--theme-agent-planning, var(--theme-blue));
  --state-thinking: var(--theme-agent-thinking, var(--theme-yellow));
  --state-coding: var(--theme-agent-coding, var(--theme-green));
}
```

---

## 5. Animation & Interaction Specifications

### 5.1 Core Animation Library

```typescript
const animations = {
  // Entrance animations
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
    duration: 200,
    easing: 'ease-out'
  },
  slideIn: {
    from: { opacity: 0, transform: 'translateY(10px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
    duration: 250,
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
  },
  
  // State animations
  pulse: {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.8 },
    duration: 2000,
    iterations: 'infinite'
  },
  
  // Terminal effects
  terminalBlink: {
    '0%, 49%': { opacity: 1 },
    '50%, 100%': { opacity: 0 },
    duration: 1000,
    iterations: 'infinite'
  },
  
  // ASCII spinner
  asciiRotate: {
    frames: ['|', '/', '-', '\\'],
    duration: 200,
    iterations: 'infinite'
  }
};
```

### 5.2 Interaction Patterns

```typescript
// Hover interactions
const hoverEffects = {
  toolBadge: {
    scale: 1.05,
    brightness: 1.2,
    transition: 'all 150ms ease'
  },
  messageCard: {
    boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
    transform: 'translateY(-1px)',
    transition: 'all 200ms ease'
  },
  codeBlock: {
    showCopyButton: true,
    highlightBackground: 'rgba(255,255,255,0.05)'
  }
};

// Click feedback
const clickFeedback = {
  button: {
    transform: 'scale(0.98)',
    transition: 'transform 100ms ease'
  },
  badge: {
    animation: 'ripple 400ms ease-out'
  }
};
```

### 5.3 Streaming Text Effects

```typescript
interface StreamingConfig {
  // Character reveal speed
  charDelay: number;
  // Word reveal speed (for faster streaming)
  wordDelay: number;
  // Cursor blink rate
  cursorBlinkRate: number;
  // Smooth scroll behavior
  scrollBehavior: 'smooth' | 'instant';
}

const streamingPresets = {
  planning: {
    charDelay: 15,
    wordDelay: 50,
    cursorBlinkRate: 500
  },
  thinking: {
    charDelay: 10,
    wordDelay: 30,
    cursorBlinkRate: 400
  },
  code: {
    charDelay: 5,
    wordDelay: 20,
    cursorBlinkRate: 300
  }
};
```

---

## 6. Technical Implementation Details

### 6.1 Component API Standards

```typescript
// Base component interface
interface TerminalComponentBase {
  className?: string;
  style?: React.CSSProperties;
  theme?: ThemeVariant;
  variant?: ComponentVariant;
  size?: 'sm' | 'md' | 'lg';
  'data-testid'?: string;
}

// Event handling pattern
interface ComponentEvents {
  onClick?: (event: MouseEvent) => void;
  onKeyDown?: (event: KeyboardEvent) => void;
  onFocus?: (event: FocusEvent) => void;
  onBlur?: (event: FocusEvent) => void;
}
```

### 6.2 Performance Optimizations

```typescript
// Virtual scrolling for message lists
const VirtualMessageList = {
  itemHeight: 120, // Estimated height
  overscan: 3,     // Items to render outside viewport
  scrollDebounce: 16 // 60fps
};

// Code syntax highlighting optimization
const SyntaxHighlighting = {
  lazy: true,              // Load highlighter on demand
  maxLength: 10000,        // Disable for large code blocks
  debounce: 100,          // Debounce highlighting updates
  languages: ['python', 'javascript', 'bash'] // Preload common
};

// Animation performance
const AnimationOptimizations = {
  useGPU: true,           // Transform3d for GPU acceleration
  willChange: 'auto',     // Browser optimization hints
  reducedMotion: true     // Respect user preferences
};
```

### 6.3 Accessibility Requirements

```typescript
// ARIA patterns
const accessibilityPatterns = {
  messageCard: {
    role: 'article',
    'aria-label': 'Agent message',
    'aria-live': 'polite',
    'aria-atomic': true
  },
  stateBadge: {
    role: 'status',
    'aria-live': 'polite',
    'aria-label': 'Agent status'
  },
  codeBlock: {
    role: 'code',
    'aria-label': 'Code snippet',
    tabIndex: 0
  }
};

// Keyboard navigation
const keyboardShortcuts = {
  'Tab': 'Navigate forward',
  'Shift+Tab': 'Navigate backward',
  'Enter': 'Activate element',
  'Space': 'Toggle selection',
  'Escape': 'Close modal/dropdown',
  'ArrowUp/Down': 'Navigate list items',
  'Ctrl+C': 'Copy code block'
};
```

---

## 7. Component Usage Guidelines

### 7.1 Composition Patterns

```tsx
// Standard agent message composition
<AgentMessageCard type="action" status="active">
  <MessageHeader>
    <AgentStateBadge state="coding" />
    <ToolCallBadge toolName="search_web" status="active" />
  </MessageHeader>
  
  <MessageContent>
    <StreamingText>
      I'll search for information about the CodeAct paradigm...
    </StreamingText>
    
    <AgentCodeBlock language="python" streaming>
      {codeContent}
    </AgentCodeBlock>
  </MessageContent>
</AgentMessageCard>
```

### 7.2 State Management Best Practices

```typescript
// Message update pattern
const updateMessage = (id: string, update: MessageUpdate) => {
  setMessages(prev => prev.map(msg => 
    msg.id === id 
      ? { ...msg, ...update, content: msg.content + (update.delta || '') }
      : msg
  ));
};

// Streaming connection pattern
const useStreaming = () => {
  const accumulator = useRef(new StreamingAccumulator());
  
  const handleStreamDelta = (delta: StreamDelta) => {
    const content = accumulator.current.accumulate(delta.id, delta.content);
    updateMessage(delta.id, { content, lifecycle: 'streaming' });
  };
  
  const handleStreamComplete = (id: string) => {
    const finalContent = accumulator.current.complete(id);
    updateMessage(id, { content: finalContent, lifecycle: 'complete' });
  };
  
  return { handleStreamDelta, handleStreamComplete };
};
```

### 7.3 Theme Integration

```tsx
// Theme-aware component example
const ThemedAgentChat = () => {
  const { theme } = useTheme();
  
  return (
    <TerminalContainer variant="embedded" className={theme}>
      <ThemeProvider theme={theme}>
        <AgentMessageList />
        <AgentInput />
      </ThemeProvider>
    </TerminalContainer>
  );
};
```

### 7.4 Testing Strategies

```typescript
// Component testing utilities
const renderWithTheme = (component: ReactElement, theme = 'classic') => {
  return render(
    <ThemeProvider theme={themes[theme]}>
      {component}
    </ThemeProvider>
  );
};

// Streaming simulation for tests
const simulateStreaming = async (text: string, callback: (delta: string) => void) => {
  const words = text.split(' ');
  for (const word of words) {
    callback(word + ' ');
    await new Promise(resolve => setTimeout(resolve, 50));
  }
};

// Accessibility testing
const a11yTest = (component: ReactElement) => {
  const { container } = render(component);
  return axe(container);
};
```

---

## Conclusion

This Design System Specification provides the technical foundation for implementing the DeepSearchAgents Web-TUI interface. By following these specifications, we ensure:

1. **Consistency**: All components follow the same patterns and behaviors
2. **Performance**: Optimized rendering and animation strategies
3. **Accessibility**: Full keyboard and screen reader support
4. **Themability**: Flexible theme system supporting multiple terminal styles
5. **Developer Experience**: Clear APIs and composition patterns

The next phase (Sub-Task 1.3) will implement these specifications using the WebTUI library and our custom extensions, creating a unique and powerful interface for observing AI agents in action.
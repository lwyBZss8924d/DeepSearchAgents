# DeepSearchAgents UI Specification (DSCS-UI)

> **Version**: 0.3.3.dev  
> **Last Updated**: 2025-01-31  
> **Status**: Implementation Complete

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Philosophy](#design-philosophy)
3. [Visual Design System](#visual-design-system)
4. [Typography & Icons](#typography--icons)
5. [Color System](#color-system)
6. [Component Architecture](#component-architecture)
7. [Animation & Interaction Design](#animation--interaction-design)
8. [State Management Patterns](#state-management-patterns)
9. [WebTUI Integration](#webtui-integration)
10. [Performance & Accessibility](#performance--accessibility)
11. [Implementation Guidelines](#implementation-guidelines)

---

## Executive Summary

The DeepSearchAgents UI Specification defines a unique **Web-TUI (Terminal User Interface)** design system that combines the authenticity of terminal interfaces with modern web capabilities. This specification documents the implemented design patterns, components, and guidelines that create a transparent, code-first interface for AI agent interactions.

### Key Achievements

- **Unified Design Language**: Cohesive terminal-inspired aesthetic across all components
- **Real-time Transparency**: Live streaming of agent thoughts, plans, and code execution
- **Performance Optimized**: Smooth animations without impacting streaming performance
- **Accessibility First**: Full keyboard navigation and screen reader support
- **Theme Flexibility**: Multiple terminal themes with cyberpunk enhancements

---

## Design Philosophy

### Core Concept: "Code is Action!"

The DeepSearchAgents Web UI embodies a design philosophy where **code execution is transparent and trustworthy**. Every design decision reinforces that agents execute real code to perform actions.

### Design Principles

1. **Transparency First**
   - Every agent thought, plan, and action is visible
   - No hidden processes or black-box operations
   - Clear state indicators throughout execution

2. **Code as Primary Interface**
   - Python code is prominently displayed, not hidden
   - Syntax highlighting and proper formatting
   - Code execution results shown in real-time

3. **Terminal Authenticity**
   - True terminal aesthetics, not skeuomorphic decoration
   - Monospace fonts and character-based layouts
   - ASCII art and text-based animations

4. **Progressive Disclosure**
   - Information revealed as the agent works
   - Streaming text with character/word reveal
   - Expandable sections for detailed views

5. **Trust Through Understanding**
   - Users see exactly what the agent does
   - Clear cause-and-effect relationships
   - No mysterious or opaque behaviors

---

## Visual Design System

### Layout Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  HAL-9000™ Terminal  [◊ Standby]    [Random ASCII] [Timer]  │
├─────────────────────────┬───────────────────────────────────┤
│                         │        Code Editor                 │
│                         │         (50% width)               │
│      Chat Interface     ├───────────────────────────────────┤
│       (50% width)       │         Terminal                  │
│                         │         (50% width)               │
│                         ├───────────────────────────────────┤
│                         │      Step Navigator               │
├─────────────────────────┴───────────────────────────────────┤
│                    Question Input                           │
└─────────────────────────────────────────────────────────────┘
```

### Spacing System

```css
/* Character-based spacing for terminal authenticity */
--ds-space-1: 0.5ch;   /* Half character width */
--ds-space-2: 1ch;     /* One character width */
--ds-space-3: 2ch;     /* Two character widths */
--ds-space-4: 3ch;     /* Three character widths */
--ds-space-5: 4ch;     /* Four character widths */
```

### Border System

```css
/* Terminal-style borders */
--ds-radius-sm: 0.25rem;   /* Subtle rounding */
--ds-radius-md: 0.375rem;  /* Standard components */
--ds-radius-lg: 0.5rem;    /* Cards and containers */
```

---

## Typography & Icons

### Font Stack

```css
/* Primary monospace font stack */
--ds-font-mono: 'Berkeley Mono', 'SF Mono', 'Monaco', 'Inconsolata', 
                'Fira Code', 'Droid Sans Mono', 'Courier New', monospace;

/* UI font for better readability */
--ds-font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                'Roboto', 'Arial', sans-serif;
```

### Type Scale

```css
--ds-text-xs: 0.75rem;    /* 12px - metadata, badges */
--ds-text-sm: 0.875rem;   /* 14px - default body text */
--ds-text-base: 1rem;     /* 16px - headings */
--ds-text-lg: 1.125rem;   /* 18px - titles */
--ds-text-xl: 1.25rem;    /* 20px - major headings */
```

### ASCII Icons

```
State Icons:
◆ Planning    ◊ Thinking    ▶ Coding
■ Running     ✓ Complete    ✗ Error

Tool Icons:
🔍 search_web      📄 read_url       🧮 wolfram_alpha
📊 analyze_data    🔤 embed          📋 chunk
📈 rerank         ✅ final_answer
```

---

## Color System

### Terminal Color Palette

```css
/* Base Terminal Colors */
--ds-terminal-bg: #0d1117;        /* Deep space black */
--ds-terminal-fg: #58a6ff;        /* Bright blue */
--ds-terminal-bright: #79c0ff;    /* Lighter blue */
--ds-terminal-dim: #388bfd;       /* Darker blue */

/* Semantic Agent State Colors */
--ds-agent-planning: #8B5CF6;     /* Purple - thoughtful */
--ds-agent-thinking: #FFEB3B;     /* Yellow - processing */
--ds-agent-coding: #00FF41;       /* Green - active */
--ds-agent-running: #00FFFF;      /* Cyan - executing */
--ds-agent-final: #10B981;        /* Emerald - success */
--ds-agent-error: #FF5252;        /* Red - failure */

/* UI Surface Colors */
--ds-border-default: #30363d;
--ds-border-active: var(--ds-terminal-fg);
--ds-bg-elevated: #161b22;
--ds-bg-code: #0d1117;
```

### Cyberpunk Gradient

```css
/* Animated gradient for special effects */
.cyberpunk-gradient {
  background: linear-gradient(
    90deg,
    #ff00ff 0%,    /* Magenta */
    #ff00aa 20%,   /* Hot pink */
    #aa00ff 40%,   /* Purple */
    #00ffff 60%,   /* Cyan */
    #00aaff 80%,   /* Blue-cyan */
    #ff00ff 100%   /* Back to magenta */
  );
  background-size: 200% 100%;
  animation: cyberpunk-gradient 3s linear infinite;
}
```

---

## Component Architecture

### Core Components

#### 1. DSAgentStateBadge

Displays current agent state with animations:

```typescript
interface DSAgentStateBadgeProps {
  state: AgentState;
  text?: string;
  showIcon?: boolean;
  showSpinner?: boolean;
  isAnimated?: boolean;
  className?: string;
}
```

**Visual States:**
- Planning: Purple with pulse animation
- Thinking: Yellow with rotation
- Coding: Green with blink
- Running: Cyan with progress
- Final: Emerald with glow

#### 2. DSAgentMessageCard

Container for agent messages with state indicators:

```typescript
interface DSAgentMessageCardProps {
  type: 'planning' | 'action' | 'observation' | 'final';
  status?: 'idle' | 'active' | 'completed';
  step?: number;
  timestamp?: Date;
  streaming?: boolean;
  children: React.ReactNode;
}
```

#### 3. DSAgentToolBadge

Interactive badges for tool execution:

```typescript
interface DSAgentToolBadgeProps {
  toolName: string;
  icon?: string;
  status?: 'pending' | 'active' | 'completed' | 'error';
  onClick?: () => void;
}
```

#### 4. DSAgentTimer

Real-time execution timer:

```typescript
interface DSAgentTimerProps {
  startTime?: number | null;
  className?: string;
}
```

#### 5. DSAgentRandomMatrix

15-character ASCII animation with cyberpunk gradient:

```typescript
interface DSAgentRandomMatrixProps {
  isActive: boolean;
  className?: string;
}
```

### Layout Components

#### DSAgentTerminalContainer

Main container with terminal styling:

```typescript
interface DSAgentTerminalContainerProps {
  headerContent?: React.ReactNode;
  headerRightContent?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}
```

---

## Animation & Interaction Design

### Core Animations

#### 1. State Transitions

```css
/* Smooth state badge transitions */
@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* ASCII spinner rotation */
@keyframes ascii-rotate {
  0% { content: "|"; }
  25% { content: "/"; }
  50% { content: "-"; }
  75% { content: "\\"; }
}
```

#### 2. Streaming Effects

```css
/* Cursor blink for active streaming */
.ds-streaming-cursor::after {
  content: "▊";
  animation: blink 1s step-end infinite;
  color: var(--ds-terminal-fg);
}
```

#### 3. Cyberpunk Effects

```css
/* Gradient animation for random matrix */
@keyframes cyberpunk-gradient {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
```

### Interaction Patterns

1. **Hover States**
   - Tool badges: Scale 1.05x with brightness
   - Message cards: Subtle border highlight
   - Buttons: Lift with shadow

2. **Click Feedback**
   - Immediate visual response
   - Ripple effect for badges
   - Scale transform for buttons

3. **Focus Indicators**
   - Clear outline for keyboard navigation
   - High contrast focus rings
   - Logical tab order

---

## State Management Patterns

### Message Streaming Architecture

```typescript
// Streaming state management
interface StreamingState {
  messages: Map<string, DSAgentRunMessage>;
  activeStreams: Set<string>;
  accumulator: StreamingAccumulator;
}

// Message routing based on metadata
const routeMessage = (message: DSAgentRunMessage) => {
  const { component, step_type } = message.metadata;
  
  switch (component) {
    case 'chat':
      return <AgentChatMessage />;
    case 'webide':
      return <CodeEditor />;
    case 'terminal':
      return <Terminal />;
  }
};
```

### Agent Status Tracking

```typescript
// Global agent state
interface AgentUIState {
  currentAgentStatus: DetailedAgentStatus;
  agentStartTime: number | null;
  isGenerating: boolean;
  isStreaming: boolean;
  currentStep: number;
  maxStep: number;
}
```

---

## WebTUI Integration

### CSS Layer Architecture

```css
/* Layer order for style precedence */
@layer webtui.base, webtui.utils, webtui.components,
       ds.base, ds.tokens, ds.components, ds.utilities, ds.overrides;
```

### Attribute-Driven Styling

```html
<!-- WebTUI badge with DS overrides -->
<span 
  is-="badge" 
  agent-badge-="state"
  agent-state-="thinking"
  class="ds-state-badge agent-thinking"
>
  ◊ Thinking...
</span>
```

### Style Overrides

```css
/* Override WebTUI badge backgrounds */
.ds-state-badge[is-~="badge"] {
  background-image: none !important;
  background-color: transparent !important;
}

/* Hide WebTUI pseudo-elements */
.ds-state-badge[is-~="badge"]::before,
.ds-state-badge[is-~="badge"]::after {
  display: none !important;
}
```

---

## Performance & Accessibility

### Performance Optimizations

1. **Animation Performance**
   - GPU-accelerated transforms
   - Will-change for animated elements
   - RequestAnimationFrame for smooth updates
   - Conditional animations based on message rate

2. **Streaming Optimization**
   - Debounced updates for rapid messages
   - Virtual scrolling for long conversations
   - Efficient DOM updates with React keys

3. **Resource Management**
   - Lazy loading for code highlighting
   - WebSocket connection pooling
   - Memory cleanup for completed streams

### Accessibility Features

1. **Keyboard Navigation**
   - Full keyboard support for all interactions
   - Logical tab order through components
   - Keyboard shortcuts for common actions

2. **Screen Reader Support**
   - Semantic HTML structure
   - ARIA labels and live regions
   - Status announcements for state changes

3. **Visual Accessibility**
   - High contrast theme option
   - Respects prefers-reduced-motion
   - WCAG AA color contrast compliance

---

## Implementation Guidelines

### Component Development

1. **Naming Convention**
   ```
   DS[Component][Type] 
   Examples: DSAgentStateBadge, DSAgentMessageCard
   ```

2. **File Structure**
   ```
   components/
   ├── ds/                    # Design system components
   │   ├── DSAgentStateBadge.tsx
   │   ├── DSAgentTimer.tsx
   │   └── index.ts
   ├── agent-chat-v2.tsx     # Main implementations
   └── agent-layout-v2.tsx
   ```

3. **Style Organization**
   ```
   styles/
   ├── terminal-theme.css    # Core terminal styles
   ├── agent-status.css      # Agent-specific styles
   ├── glamour-animations.css # Animation library
   └── compatibility-layer.css # WebTUI overrides
   ```

### Testing Strategy

1. **Component Testing**
   - Unit tests for state logic
   - Visual regression tests
   - Animation timing tests

2. **Integration Testing**
   - WebSocket message handling
   - Streaming accumulation
   - Cross-component communication

3. **Performance Testing**
   - Message throughput rates
   - Animation frame rates
   - Memory usage monitoring

### Future Enhancements

1. **Phase 1**: Enhanced theme system with user customization
2. **Phase 2**: Advanced code editor features (diff view, multi-file)
3. **Phase 3**: Collaborative features for team usage
4. **Phase 4**: Mobile-optimized responsive design
5. **Phase 5**: Extended accessibility features

---

## Conclusion

The DSCS-UI Specification represents a unique approach to AI agent interfaces, combining terminal authenticity with modern web capabilities. By prioritizing transparency, code visibility, and real-time feedback, we've created an interface that builds trust through understanding.

This living document will continue to evolve as we enhance the DeepSearchAgents platform, always maintaining our core philosophy: **"Code is Action!"**
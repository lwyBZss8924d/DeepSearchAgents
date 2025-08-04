# DeepSearchAgents UI Implementation Plan with WebTUI

## Sub-Task(1.3): "Design Language" & "Design System" Implementation Tech Stack

> This document outlines the technical implementation strategy for integrating WebTUI CSS library with our DeepSearchAgents design system, creating a harmonious blend of terminal aesthetics and agent-specific functionality.

---

## 1. WebTUI Analysis & Integration Strategy

### 1.1 WebTUI Core Concepts Alignment

**WebTUI Strengths for Our Design:**
- **Terminal-First Philosophy**: Perfect match for our Web-TUI vision
- **Modular Architecture**: Import only needed components
- **CSS Layers**: Clean style precedence management
- **Attribute-Based Styling**: Semantic HTML approach
- **Character Units**: `ch` and `lh` units for terminal grid

**Key WebTUI Features We'll Leverage:**
```css
/* WebTUI's layer system */
@layer base, utils, components;

/* Character-based sizing */
width: 80ch;  /* 80 characters wide */
height: 24lh; /* 24 lines high */

/* Attribute selectors */
[is-="badge"] { }
[box-="double"] { }
[variant-="primary"] { }
```

### 1.2 Design System Mapping

| Our Design Need | WebTUI Component | Extension Strategy |
|-----------------|------------------|-------------------|
| AgentMessageCard | box utility + custom | Add `agent-card-` attribute |
| StateBadge | badge component | Extend with animations |
| ToolBadge | badge + tooltip | Add expandable behavior |
| CodeBlock | pre component | Enhanced with highlighting |
| TerminalContainer | box utilities | Custom terminal chrome |
| StreamingText | typography + custom | Add cursor animations |

### 1.3 Layer Architecture Design

```css
/* Layer hierarchy for clean overrides */
@layer webtui.base,      /* WebTUI foundation */
       webtui.utils,     /* WebTUI utilities */
       webtui.components,/* WebTUI components */
       ds.base,          /* DeepSearch base */
       ds.tokens,        /* Design tokens */
       ds.components,    /* DS components */
       ds.utilities,     /* DS utilities */
       ds.overrides;     /* Final overrides */
```

---

## 2. Technical Architecture

### 2.1 File Structure

```
frontend/
├── styles/
│   ├── layers/
│   │   ├── 01-webtui-setup.css    # WebTUI imports & config
│   │   ├── 02-ds-tokens.css       # CSS variables & design tokens
│   │   ├── 03-ds-base.css         # Base styles & resets
│   │   ├── 04-ds-components.css   # Component definitions
│   │   ├── 05-ds-utilities.css    # Utility classes
│   │   └── 06-ds-themes.css       # Theme variations
│   ├── globals.css                 # Main entry point
│   └── fonts.css                   # Font definitions
│
├── components/
│   ├── ds-core/                    # Core system components
│   │   ├── DSThemeProvider.tsx
│   │   ├── DSLayerProvider.tsx
│   │   └── DSGlobalStyles.tsx
│   │
│   ├── ds-terminal/                # Terminal components
│   │   ├── DSTerminalContainer.tsx
│   │   ├── DSTerminalPrompt.tsx
│   │   ├── DSTerminalOutput.tsx
│   │   └── DSTerminalCursor.tsx
│   │
│   ├── ds-agent/                   # Agent-specific components
│   │   ├── DSAgentMessageCard.tsx
│   │   ├── DSAgentStateBadge.tsx
│   │   ├── DSAgentToolBadge.tsx
│   │   ├── DSAgentCodeBlock.tsx
│   │   └── DSAgentStreamingText.tsx
│   │
│   └── ds-layout/                  # Layout components
│       ├── DSSplitView.tsx
│       ├── DSSidebar.tsx
│       └── DSTabContainer.tsx
```

### 2.2 CSS Variable System

```css
@layer ds.tokens {
  :root {
    /* Berkeley Mono Font Stack */
    --ds-font-mono: 'Berkeley Mono', 'SF Mono', 'Monaco', 
                    'Inconsolata', 'Fira Code', monospace;
    
    /* Map to WebTUI's system */
    --webtui-font-family: var(--ds-font-mono);
    
    /* Terminal Colors - Classic Theme */
    --ds-terminal-bg: #0a0a0a;
    --ds-terminal-fg: #00ff41;
    --ds-terminal-bright: #33ff66;
    --ds-terminal-dim: #00cc33;
    
    /* Agent State Colors */
    --ds-agent-planning: #00bfff;
    --ds-agent-thinking: #ffeb3b;
    --ds-agent-coding: #00ff41;
    --ds-agent-running: #00ffff;
    --ds-agent-final: #33ff66;
    --ds-agent-error: #ff5252;
    
    /* Spacing Scale (character-based) */
    --ds-space-1: 0.5ch;
    --ds-space-2: 1ch;
    --ds-space-3: 2ch;
    --ds-space-4: 3ch;
    --ds-space-5: 4ch;
    
    /* Animation Timings */
    --ds-transition-fast: 150ms;
    --ds-transition-base: 250ms;
    --ds-transition-slow: 350ms;
  }
}
```

### 2.3 Component Attribute System

```css
/* Custom attribute pattern for DS components */
@layer ds.components {
  /* Agent Card States */
  [agent-card-="planning"] {
    border-left: 3px solid var(--ds-agent-planning);
    background: color-mix(in oklch, var(--ds-agent-planning) 5%, var(--ds-terminal-bg));
  }
  
  [agent-card-="action"] {
    border-left: 3px solid var(--ds-agent-coding);
  }
  
  [agent-card-="final"] {
    border-left: 3px solid var(--ds-agent-final);
  }
  
  /* Agent State Modifiers */
  [agent-state-="active"] {
    animation: ds-pulse 2s ease-in-out infinite;
  }
  
  [agent-state-="streaming"] {
    position: relative;
  }
  
  [agent-state-="streaming"]::after {
    content: "";
    display: inline-block;
    width: 0.5ch;
    height: 1lh;
    background: var(--ds-terminal-fg);
    animation: ds-blink 1s step-end infinite;
  }
}
```

---

## 3. Implementation Phases

### Phase 1: Foundation Setup (Week 1)

#### 1.1 WebTUI Installation
```bash
npm install @webtui/css
npm install @webtui/plugin-catppuccin # Theme plugin
npm install @webtui/plugin-nf        # Nerd font icons
```

#### 1.2 Base Configuration
```css
/* globals.css */
@layer webtui.base, webtui.utils, webtui.components,
       ds.base, ds.tokens, ds.components, ds.utilities, ds.overrides;

/* WebTUI imports */
@import "@webtui/css/base.css" layer(webtui.base);
@import "@webtui/css/utils/box.css" layer(webtui.utils);
@import "@webtui/css/components/badge.css" layer(webtui.components);
@import "@webtui/css/components/button.css" layer(webtui.components);
@import "@webtui/css/components/input.css" layer(webtui.components);
@import "@webtui/css/components/typography.css" layer(webtui.components);

/* DS imports */
@import "./layers/02-ds-tokens.css" layer(ds.tokens);
@import "./layers/03-ds-base.css" layer(ds.base);
@import "./layers/04-ds-components.css" layer(ds.components);
```

#### 1.3 Font Setup
```css
@font-face {
  font-family: 'Berkeley Mono';
  src: url('/fonts/BerkeleyMono-Regular.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}

@layer ds.base {
  body {
    font-family: var(--ds-font-mono);
    font-size: 14px;
    line-height: 1.6;
    letter-spacing: 0.02em;
  }
}
```

### Phase 2: Core Components (Week 2)

#### 2.1 Agent Message Card
```tsx
// DSAgentMessageCard.tsx
interface DSAgentMessageCardProps {
  type: 'planning' | 'action' | 'observation' | 'final';
  state?: 'idle' | 'active' | 'streaming';
  children: React.ReactNode;
}

export function DSAgentMessageCard({ type, state, children }: DSAgentMessageCardProps) {
  return (
    <div 
      box-="single"
      agent-card-={type}
      agent-state-={state}
      className="ds-message-card"
    >
      {children}
    </div>
  );
}
```

```css
/* Component styles */
@layer ds.components {
  .ds-message-card {
    padding: var(--ds-space-4);
    margin-bottom: var(--ds-space-3);
    transition: all var(--ds-transition-base) ease;
  }
  
  .ds-message-card:hover {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transform: translateY(-1px);
  }
}
```

#### 2.2 State Badge with Animations
```tsx
// DSAgentStateBadge.tsx
export function DSAgentStateBadge({ state, text }: Props) {
  const icons = {
    planning: '◆',
    thinking: '◊',
    coding: '▶',
    running: '■',
    final: '✓'
  };
  
  return (
    <span 
      is-="badge"
      agent-badge-={state}
      className="ds-state-badge"
    >
      <span className="ds-state-icon">{icons[state]}</span>
      <span className="ds-state-text">{text}</span>
    </span>
  );
}
```

```css
/* ASCII Spinner Animation */
@layer ds.components {
  @keyframes ds-ascii-spin {
    0% { content: "[|]"; }
    25% { content: "[/]"; }
    50% { content: "[-]"; }
    75% { content: "[\\]"; }
    100% { content: "[|]"; }
  }
  
  [agent-badge-="coding"] .ds-state-icon::before {
    content: "[|]";
    animation: ds-ascii-spin 0.8s steps(4) infinite;
  }
}
```

### Phase 3: Advanced Features (Week 3)

#### 3.1 Streaming Text Component
```tsx
// DSAgentStreamingText.tsx
export function DSAgentStreamingText({ content, isStreaming }: Props) {
  const [displayContent, setDisplayContent] = useState('');
  
  useEffect(() => {
    if (isStreaming) {
      // Character-by-character reveal
      let index = 0;
      const timer = setInterval(() => {
        if (index < content.length) {
          setDisplayContent(content.slice(0, index + 1));
          index++;
        } else {
          clearInterval(timer);
        }
      }, 15); // 15ms per character
      
      return () => clearInterval(timer);
    } else {
      setDisplayContent(content);
    }
  }, [content, isStreaming]);
  
  return (
    <span agent-state-={isStreaming ? "streaming" : undefined}>
      {displayContent}
    </span>
  );
}
```

#### 3.2 Terminal Container
```tsx
// DSTerminalContainer.tsx
export function DSTerminalContainer({ title, children }: Props) {
  return (
    <div box-="double" className="ds-terminal">
      <div className="ds-terminal-header">
        <span className="ds-terminal-title">{title}</span>
        <div className="ds-terminal-controls">
          <span>[-]</span>
          <span>[□]</span>
          <span>[×]</span>
        </div>
      </div>
      <div className="ds-terminal-body">
        {children}
      </div>
    </div>
  );
}
```

---

## 4. Theme System Implementation

### 4.1 Theme Structure
```typescript
interface DSTheme {
  name: string;
  base: 'webtui' | 'custom';
  tokens: {
    colors: Record<string, string>;
    fonts: Record<string, string>;
    spacing: Record<string, string>;
  };
}

const themes: Record<string, DSTheme> = {
  classic: {
    name: 'Classic Terminal',
    base: 'webtui',
    tokens: {
      colors: {
        '--ds-terminal-bg': '#0a0a0a',
        '--ds-terminal-fg': '#00ff41',
        // ... rest of colors
      }
    }
  },
  solarized: {
    name: 'Solarized Dark',
    base: 'webtui',
    tokens: {
      colors: {
        '--ds-terminal-bg': '#002b36',
        '--ds-terminal-fg': '#839496',
        // ... solarized palette
      }
    }
  }
};
```

### 4.2 Theme Provider
```tsx
// DSThemeProvider.tsx
export function DSThemeProvider({ theme, children }: Props) {
  useEffect(() => {
    // Apply theme tokens
    const root = document.documentElement;
    Object.entries(theme.tokens.colors).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    
    // Apply WebTUI theme if using base
    if (theme.base === 'webtui') {
      root.setAttribute('data-webtui-theme', theme.name);
    }
  }, [theme]);
  
  return <>{children}</>;
}
```

---

## 5. Integration Guidelines

### 5.1 Component Creation Pattern
```tsx
// 1. Start with WebTUI base
<div is-="badge">

// 2. Add DS-specific attributes
<div is-="badge" agent-badge-="planning">

// 3. Add behavioral classes
<div is-="badge" agent-badge-="planning" className="ds-badge-animated">

// 4. Compose with other components
<div agent-card-="action">
  <div is-="badge" agent-badge-="coding">Coding...</div>
  <pre agent-code-="python">{code}</pre>
</div>
```

### 5.2 Styling Best Practices
```css
/* Use layers for clean precedence */
@layer ds.components {
  /* Component styles here */
}

/* Leverage CSS custom properties */
.ds-component {
  color: var(--ds-terminal-fg);
  padding: var(--ds-space-3);
}

/* Use WebTUI utilities when appropriate */
[box-="double"][agent-card-="planning"] {
  /* Combines WebTUI box with DS card */
}
```

### 5.3 Performance Optimization
```typescript
// Lazy load heavy components
const DSCodeEditor = lazy(() => import('./DSCodeEditor'));

// Use CSS containment
.ds-message-list {
  contain: layout style;
}

// Optimize animations
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

---

## 6. Testing Strategy

### 6.1 Visual Regression Testing
```typescript
// Use Storybook for component development
export default {
  title: 'DS Components/Agent Message Card',
  component: DSAgentMessageCard,
};

export const Planning = {
  args: {
    type: 'planning',
    state: 'active',
    children: 'Planning content...'
  }
};
```

### 6.2 Theme Testing
```typescript
// Test all theme variations
describe('Theme System', () => {
  themes.forEach(theme => {
    it(`renders correctly with ${theme.name}`, () => {
      render(
        <DSThemeProvider theme={theme}>
          <DSAgentMessageCard type="action">Test</DSAgentMessageCard>
        </DSThemeProvider>
      );
    });
  });
});
```

---

## 7. Migration from Current UI

### 7.1 Gradual Migration Strategy
1. **Phase 1**: Set up WebTUI alongside existing shadcn components
2. **Phase 2**: Create DS components that wrap both systems
3. **Phase 3**: Gradually replace shadcn with WebTUI+DS
4. **Phase 4**: Remove shadcn dependencies

### 7.2 Compatibility Layer
```tsx
// Temporary wrapper for smooth migration
export function DSCompatButton({ variant, ...props }) {
  // Map shadcn variants to WebTUI
  const webtuiVariant = {
    'default': 'primary',
    'destructive': 'danger',
    'outline': 'secondary'
  }[variant];
  
  return <button variant-={webtuiVariant} {...props} />;
}
```

---

## 8. Benefits & Outcomes

### 8.1 Technical Benefits
- **Smaller Bundle**: WebTUI's modular approach
- **Better Performance**: CSS-based animations
- **Cleaner Code**: Attribute-based styling
- **Easy Theming**: CSS variable system

### 8.2 Design Benefits
- **Authentic Terminal Feel**: WebTUI's terminal-first design
- **Consistent Spacing**: Character-based units
- **Better Accessibility**: Semantic HTML
- **Unique Identity**: Distinctive DS components

### 8.3 Developer Experience
- **Clear Patterns**: Consistent component creation
- **Good Documentation**: WebTUI + DS docs
- **Easy Debugging**: Layer-based CSS
- **Fast Development**: Pre-built utilities

---

## Conclusion

This implementation plan provides a clear path for integrating WebTUI with our DeepSearchAgents design system. By leveraging WebTUI's terminal-focused design philosophy and extending it with our agent-specific components, we create a unique and powerful interface that truly embodies "Code is Action!"

The phased approach ensures smooth implementation while maintaining the flexibility to adapt as we discover new requirements. The result will be a distinctive, performant, and maintainable UI system that perfectly captures the essence of our CodeAgent paradigm.
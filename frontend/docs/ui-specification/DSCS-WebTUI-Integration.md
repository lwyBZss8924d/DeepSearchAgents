# DSCS WebTUI Integration Guide

> **Version**: 0.3.3.dev  
> **Last Updated**: 2025-01-31  
> **Status**: Implementation Complete

## Table of Contents

1. [Overview](#overview)
2. [WebTUI CSS Architecture](#webtui-css-architecture)
3. [Integration Strategy](#integration-strategy)
4. [Component Patterns](#component-patterns)
5. [Style Overrides](#style-overrides)
6. [Theme Integration](#theme-integration)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This document details the integration between DeepSearchAgents' custom design system (DS) and the WebTUI CSS library. WebTUI provides a foundation of terminal-style components, while our DS layer extends and customizes these for AI agent interactions.

### Key Integration Points

- **CSS Layers**: Proper layer ordering for style precedence
- **Attribute Selectors**: WebTUI's `[is-~="component"]` pattern
- **Style Overrides**: DS-specific customizations
- **Theme Variables**: Unified color and spacing tokens

---

## WebTUI CSS Architecture

### Layer System

```css
/* CSS layer declaration order */
@layer webtui.base, webtui.utils, webtui.components,
       glamour.base, glamour.animations, glamour.effects,
       ds.base, ds.tokens, ds.components, ds.utilities, ds.overrides;
```

### Import Structure

```css
/* In globals.css */
@import "tailwindcss";

/* WebTUI CSS Library */
@import "@webtui/css/base.css" layer(webtui.base);
@import "@webtui/css/utils/box.css" layer(webtui.utils);
@import "@webtui/css/components/badge.css" layer(webtui.components);
@import "@webtui/css/components/button.css" layer(webtui.components);
@import "@webtui/css/components/input.css" layer(webtui.components);
@import "@webtui/css/components/typography.css" layer(webtui.components);

/* DS Extensions */
@import "./styles/terminal-theme.css" layer(ds.tokens);
@import "./styles/agent-status.css" layer(ds.components);
@import "./styles/compatibility-layer.css" layer(ds.overrides);
```

---

## Integration Strategy

### 1. Attribute-Based Components

WebTUI uses attribute selectors for styling:

```html
<!-- WebTUI badge -->
<span is-="badge" variant-="foreground0">
  Badge Text
</span>

<!-- DS-enhanced badge -->
<span 
  is-="badge" 
  agent-badge-="state"
  agent-state-="thinking"
  class="ds-state-badge agent-thinking"
>
  ◊ Thinking...
</span>
```

### 2. CSS Variable Mapping

```css
/* Map WebTUI variables to DS tokens */
:root {
  /* WebTUI base colors */
  --background0: var(--ds-terminal-bg);
  --background1: var(--ds-bg-elevated);
  --foreground0: var(--ds-terminal-fg);
  --foreground1: var(--ds-terminal-bright);
  
  /* Font mapping */
  --font-family: var(--ds-font-mono);
  --font-size: 14px;
  --line-height: 1.6;
}
```

### 3. Component Extension Pattern

```typescript
// Extend WebTUI components with DS features
interface DSComponentProps extends WebTUIComponentProps {
  // DS-specific props
  streaming?: boolean;
  agentState?: AgentState;
  animated?: boolean;
}
```

---

## Component Patterns

### Badge Component Override

```css
/* Override WebTUI badge backgrounds */
.ds-state-badge[is-~="badge"] {
  /* Remove WebTUI gradient */
  background-image: none !important;
  background-color: transparent !important;
  
  /* Apply DS styling */
  color: var(--ds-agent-thinking);
  border: none;
}

/* Hide WebTUI badge caps */
.ds-state-badge[is-~="badge"]::before,
.ds-state-badge[is-~="badge"]::after {
  display: none !important;
}
```

### Button Integration

```tsx
// Using WebTUI button with DS styling
<button 
  is-="button" 
  variant-="primary"
  className="ds-action-button"
>
  <Send className="h-4 w-4" />
  Send Query
</button>
```

```css
/* DS button enhancements */
.ds-action-button[is-~="button"] {
  transition: all 200ms var(--ds-ease-out);
  border-radius: var(--ds-radius-md);
}

.ds-action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
```

### Input Field Styling

```tsx
// Terminal-style input
<input
  is-="input"
  type="text"
  className="ds-terminal-input"
  placeholder="Enter command..."
/>
```

```css
/* Terminal input styling */
.ds-terminal-input[is-~="input"] {
  background: var(--ds-bg-code);
  color: var(--ds-terminal-fg);
  border: 1px solid var(--ds-border-default);
  font-family: var(--ds-font-mono);
}

.ds-terminal-input:focus {
  border-color: var(--ds-terminal-bright);
  outline: none;
}
```

---

## Style Overrides

### Removing WebTUI Defaults

```css
/* Global overrides in compatibility-layer.css */
@layer ds.overrides {
  /* Remove default backgrounds */
  [is-~="badge"] {
    background-image: none !important;
  }
  
  /* Override borders */
  [is-~="separator"] {
    border-color: var(--ds-border-default);
  }
  
  /* Custom spacing */
  [is-~="container"] {
    padding: var(--ds-space-4);
  }
}
```

### Selective Overrides

```css
/* Only override specific variants */
[is-~="badge"][variant-="foreground0"] {
  --badge-color: transparent;
  --badge-text: var(--ds-terminal-fg);
}

/* Preserve WebTUI tool badges */
[agent-badge-="tool"] {
  /* Keep WebTUI styling */
}
```

---

## Theme Integration

### Dark Theme Variables

```css
[data-theme="dark"] {
  /* WebTUI variables */
  --background0: #000;
  --foreground0: #fff;
  
  /* DS overrides */
  --ds-terminal-bg: #0d1117;
  --ds-terminal-fg: #58a6ff;
  --ds-agent-planning: #A78BFA;
  --ds-agent-thinking: #FBB040;
}
```

### Theme Switching

```typescript
// Theme context integration
const { theme } = useTheme();

return (
  <div data-theme={theme} data-webtui-theme={theme}>
    {/* Components inherit theme */}
  </div>
);
```

---

## Common Patterns

### 1. Terminal Container

```tsx
<div 
  is-="container" 
  class="ds-terminal-container"
>
  <header class="ds-terminal-header">
    <span>HAL-9000™ Terminal</span>
  </header>
  <main class="ds-terminal-content">
    {children}
  </main>
</div>
```

### 2. ASCII Decorations

```css
/* WebTUI box drawing with DS colors */
[box-="single"] {
  border: 1px solid var(--ds-border-default);
}

[box-="double"] {
  border: 3px double var(--ds-border-default);
}

/* ASCII corners */
.ds-box-corners::before { content: "┌"; }
.ds-box-corners::after { content: "┐"; }
```

### 3. Responsive Utilities

```css
/* WebTUI responsive with DS breakpoints */
@media (max-width: 640px) {
  [is-~="container"] {
    padding: var(--ds-space-2);
  }
  
  .ds-terminal-header {
    font-size: var(--ds-text-sm);
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Style Conflicts

**Problem**: WebTUI styles override DS styles  
**Solution**: Use higher specificity or `!important` in DS layer

```css
/* Increase specificity */
.ds-component[is-~="badge"][agent-state-="thinking"] {
  color: var(--ds-agent-thinking);
}
```

#### 2. Missing WebTUI Features

**Problem**: WebTUI component not rendering correctly  
**Solution**: Ensure proper attribute syntax

```html
<!-- Correct -->
<div is-="separator" direction-="vertical">

<!-- Incorrect -->
<div is="separator" direction="vertical">
```

#### 3. Theme Variables Not Applied

**Problem**: Custom theme colors not showing  
**Solution**: Check CSS variable cascade

```css
/* Ensure variables are defined at correct scope */
:root {
  --ds-terminal-bg: #0d1117;
}

[data-theme="custom"] {
  --ds-terminal-bg: #1a1b26;
}
```

### Best Practices

1. **Layer Order**: Always define DS overrides in higher layers
2. **Attribute Syntax**: Use `is-~=` for WebTUI components
3. **Variable Naming**: Prefix custom variables with `--ds-`
4. **Testing**: Check both light and dark themes
5. **Performance**: Minimize use of `!important`

---

## Migration Guide

### From Pure WebTUI to DS

```css
/* Before: Pure WebTUI */
[is-~="badge"] {
  /* WebTUI defaults apply */
}

/* After: DS Integration */
.ds-state-badge[is-~="badge"] {
  background-image: none !important;
  background-color: transparent !important;
  color: var(--ds-agent-state-color);
}
```

### Adding New Components

1. Check if WebTUI has a base component
2. Extend with DS-specific attributes
3. Override styles in appropriate layer
4. Document integration pattern

---

## Resources

- [WebTUI Documentation](https://webtui.dev/docs)
- [CSS Layers Specification](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer)
- [DS Component Library](./DSCS-Component-Library.md)
- [Main UI Specification](./DSCS-UI-Specification.md)
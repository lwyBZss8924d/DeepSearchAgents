# DeepSearchAgents Frontend UI/UX Design Requirements

## Table of Contents
1. [Overview](#overview)
2. [Visual Design System](#visual-design-system)
3. [Component Architecture](#component-architecture)
4. [Agent Message Stream Components](#agent-message-stream-components)
5. [Animation & Interaction Design](#animation--interaction-design)
6. [Implementation Guidelines](#implementation-guidelines)

## Overview

This document defines the comprehensive UI/UX design requirements for DeepSearchAgents' frontend, incorporating modern visual design principles inspired by the Gemini fullstack project while maintaining compatibility with our existing shadcn/ui and Tailwind CSS stack.

### Design Philosophy
- **Dark-First Design**: Optimized for extended viewing with a sophisticated dark theme
- **Information Hierarchy**: Clear visual distinction between different types of agent messages
- **Real-Time Feedback**: Smooth streaming updates with visual indicators
- **Developer-Friendly**: Clean, professional interface for technical users

## Visual Design System

### Color Palette

```css
/* Primary Neutral Colors */
--neutral-950: #0c0c0c;  /* Terminal background */
--neutral-900: #111111;  /* Code editor background */
--neutral-800: #1a1a1a;  /* Main background */
--neutral-700: #262626;  /* Card/bubble background */
--neutral-600: #404040;  /* Borders, dividers */
--neutral-500: #737373;  /* Muted text */
--neutral-400: #a3a3a3;  /* Icons, secondary text */
--neutral-300: #d4d4d4;  /* Body text */
--neutral-200: #e5e5e5;  /* Emphasized text */
--neutral-100: #f5f5f5;  /* Primary text */

/* Semantic Colors */
--blue-500: #3b82f6;     /* Primary actions, links */
--blue-400: #60a5fa;     /* Hover states */
--green-500: #10b981;    /* Success, final answers */
--yellow-500: #f59e0b;   /* Thinking, processing */
--red-500: #ef4444;      /* Errors, stop actions */
--purple-500: #8b5cf6;   /* Special features */
--orange-500: #f97316;   /* Warnings, important */
```

### Typography

```css
/* Font Family */
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-mono: "Fira Code", "SF Mono", Monaco, monospace;

/* Font Sizes */
--text-xs: 0.75rem;      /* 12px - metadata, labels */
--text-sm: 0.875rem;     /* 14px - body text */
--text-base: 1rem;       /* 16px - default */
--text-lg: 1.125rem;     /* 18px - headings */
--text-xl: 1.25rem;      /* 20px - titles */
--text-2xl: 1.5rem;      /* 24px - major headings */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Spacing System

```css
/* Consistent spacing scale */
--space-0: 0;
--space-1: 0.25rem;     /* 4px */
--space-2: 0.5rem;      /* 8px */
--space-3: 0.75rem;     /* 12px */
--space-4: 1rem;        /* 16px */
--space-5: 1.25rem;     /* 20px */
--space-6: 1.5rem;      /* 24px */
--space-8: 2rem;        /* 32px */
--space-10: 2.5rem;     /* 40px */
--space-12: 3rem;       /* 48px */
```

### Border Radius

```css
--radius-sm: 0.375rem;   /* 6px - small elements */
--radius-md: 0.5rem;     /* 8px - buttons, inputs */
--radius-lg: 0.75rem;    /* 12px - cards, modals */
--radius-xl: 1rem;       /* 16px - large cards */
--radius-2xl: 1.5rem;    /* 24px - message bubbles */
--radius-full: 9999px;   /* Pills, avatars */
```

## Component Architecture

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                         Header Bar                          │
├─────────────────────────┬───────────────────────────────────┤
│                         │   Code Editor / Browser          │
│                         │      (50% width, 50% height)     │
│      Chat Interface     │   [Tab: Code Editor | Browser]   │
│     (50% width)         ├───────────────────────────────────┤
│                         │        Terminal                   │
│                         │   (50% width, 50% height)        │
│                         │      (Always Visible)            │
│                         ├───────────────────────────────────┤
│                         │     Step Navigator               │
├─────────────────────────┴───────────────────────────────────┤
│                    Question Input                           │
└─────────────────────────────────────────────────────────────┘
```

### Split Panel Implementation

The right panel uses a vertical split layout to maximize visibility:

#### Upper Section (Code Editor/Browser)
- **Height**: 50% of viewport height (`h-1/2`)
- **Content**: Tabbed interface for Code Editor and Browser
- **Purpose**: Display code files and web content related to agent actions
- **Note**: Browser functionality is placeholder until backend browser-use tools are implemented

#### Lower Section (Terminal)
- **Height**: 50% of viewport height (`h-1/2`)
- **Content**: Always-visible terminal for command execution output
- **Purpose**: Real-time monitoring of agent command execution
- **Benefits**: No tab switching needed to see terminal output

```css
/* Split Layout Structure */
.right-panel {
  display: flex;
  flex-direction: column;
  width: 50%;
}

.upper-section {
  height: 50%;
  border-bottom: 1px solid var(--neutral-600);
}

.lower-section {
  height: 50%;
  display: flex;
  flex-direction: column;
}
```

## Agent Message Stream Components

### 1. Chat Message Component

#### User Message
```tsx
<div className="flex items-start gap-3 justify-end">
  <div className="text-white rounded-3xl rounded-br-lg break-words 
              bg-neutral-700 max-w-[90%] px-4 pt-3">
    {/* Message content with markdown */}
  </div>
</div>
```

#### Assistant Message
```tsx
<div className="flex items-start gap-3">
  {/* Activity Timeline (if applicable) */}
  <ActivityTimeline events={stepEvents} />
  
  <div className="flex-1">
    {/* Metadata badges */}
    <div className="flex items-center gap-2 mb-1">
      <ToolBadge tool={toolName} />
      <StatusBadge status={messageStatus} />
    </div>
    
    {/* Message content */}
    <div className="bg-neutral-800 rounded-xl rounded-bl-none p-3">
      <Markdown>{content}</Markdown>
    </div>
  </div>
</div>
```

### 2. Activity Timeline Component

Visual timeline showing agent reasoning steps:

```tsx
interface TimelineEvent {
  type: 'thinking' | 'planning' | 'searching' | 'executing' | 'finalizing';
  title: string;
  description: string;
  timestamp: string;
  status: 'pending' | 'active' | 'completed';
}

<div className="relative pl-8 pb-4">
  {/* Timeline line */}
  <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600" />
  
  {/* Timeline node */}
  <div className="absolute left-0.5 top-2 h-6 w-6 rounded-full 
                  bg-neutral-600 flex items-center justify-center 
                  ring-4 ring-neutral-700">
    <Icon className="h-3 w-3 text-neutral-400" />
  </div>
  
  {/* Content */}
  <div>
    <p className="text-sm text-neutral-200 font-medium">{title}</p>
    <p className="text-xs text-neutral-300">{description}</p>
  </div>
</div>
```

### 3. Tool Badge Component

```tsx
<span className="inline-flex items-center gap-1.5 px-2 py-1 
                 bg-blue-500/10 text-blue-500 rounded-md text-xs">
  <ToolIcon className="h-3 w-3" />
  Tool: {toolName}
</span>
```

### 4. Streaming Indicator

```tsx
<span className="inline-flex items-center gap-2 px-2 py-1 
                 bg-blue-500/10 text-blue-500 rounded-md text-xs 
                 animate-pulse">
  <Loader2 className="h-3 w-3 animate-spin" />
  Streaming...
</span>
```

### 5. Final Answer Component

```tsx
<div className="w-full bg-green-500/10 border-2 border-green-500/30 
                rounded-lg p-6 mt-4">
  <div className="flex items-center gap-3 mb-4">
    <CheckCircle2 className="h-6 w-6 text-green-500" />
    <h3 className="text-lg font-semibold text-green-500">Final Answer</h3>
  </div>
  <div className="prose prose-sm dark:prose-invert max-w-none">
    <Markdown>{content}</Markdown>
  </div>
  
  {/* Sources section */}
  {sources && (
    <div className="mt-4 pt-4 border-t border-green-500/20">
      <h4 className="text-sm font-medium text-green-500 mb-2">Sources</h4>
      <div className="flex flex-wrap gap-2">
        {sources.map(source => (
          <Badge variant="secondary" className="text-xs">
            <a href={source.url} target="_blank">{source.title}</a>
          </Badge>
        ))}
      </div>
    </div>
  )}
</div>
```

### 6. Code Editor Header

```tsx
<div className="flex items-center justify-between p-3 border-b 
                bg-neutral-900 border-neutral-700">
  <div className="flex items-center gap-2">
    <span className="text-sm font-medium text-neutral-100">
      Step {currentStep}
    </span>
    <span className="text-sm text-neutral-400">
      {language}
    </span>
  </div>
  <div className="flex items-center gap-2">
    <Button variant="ghost" size="sm" className="text-neutral-400">
      <Copy className="h-4 w-4" />
      Copy
    </Button>
  </div>
</div>
```

### 7. Enhanced Input Form

```tsx
<div className="flex flex-col gap-2 p-3 pb-4">
  {/* Main input area */}
  <div className="flex flex-row items-center bg-neutral-700 
                  rounded-3xl px-4 pt-3">
    <Textarea
      className="w-full text-neutral-100 placeholder-neutral-500 
                 bg-transparent border-0 resize-none"
      placeholder="Ask anything..."
    />
    <Button variant="ghost" className="text-blue-500">
      {isLoading ? <StopCircle /> : <Send />}
    </Button>
  </div>
  
  {/* Options bar */}
  <div className="flex items-center gap-2">
    <Select value={agentType}>
      <SelectTrigger className="bg-neutral-700 border-neutral-600">
        <Brain className="h-4 w-4 mr-2" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="codact">CodeAct Agent</SelectItem>
        <SelectItem value="react">ReAct Agent</SelectItem>
      </SelectContent>
    </Select>
    
    <Select value={maxSteps}>
      <SelectTrigger className="bg-neutral-700 border-neutral-600">
        <Zap className="h-4 w-4 mr-2" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="10">Quick (10 steps)</SelectItem>
        <SelectItem value="20">Standard (20 steps)</SelectItem>
        <SelectItem value="30">Thorough (30 steps)</SelectItem>
      </SelectContent>
    </Select>
  </div>
</div>
```

## Animation & Interaction Design

### Animation Principles

1. **Smooth Transitions**: All state changes should animate smoothly
2. **Meaningful Motion**: Animations should guide user attention
3. **Performance**: Animations should not impact streaming performance
4. **Consistency**: Use consistent timing and easing across similar interactions
5. **Subtlety**: Prefer subtle animations that enhance rather than distract

### Motion System Guidelines

#### Duration Scale
- **Micro interactions**: 100-200ms (hover, active states)
- **Small transitions**: 200-300ms (fade in, slide in)
- **Medium transitions**: 300-500ms (page transitions, modals)
- **Large transitions**: 500-800ms (complex animations)

#### Easing Functions Usage
- **ease-out-expo**: Primary easing for enter animations
- **ease-out-quart**: Secondary easing for subtle movements
- **ease-in-out-quart**: Bidirectional transitions
- **ease-spring**: Playful interactions (badges, buttons)
- **linear**: Continuous animations (loading, progress)

#### Stagger Animations
For lists and multiple elements appearing:
```tsx
const staggerDelay = 50; // ms between each item
items.map((item, index) => (
  <div 
    key={item.id}
    className="animate-fadeInUp"
    style={{ animationDelay: `${index * staggerDelay}ms` }}
  >
    {item.content}
  </div>
))
```

### Component-Specific Animations

#### 1. Message Animations

**User Messages**
```css
.message-user-enter {
  animation: slideInRight 0.3s var(--ease-out-expo) forwards;
}
```

**Assistant Messages**
```css
.message-assistant-enter {
  animation: fadeInUp 0.3s var(--ease-out-expo) forwards;
}
```

**Streaming Text**
```css
.streaming-cursor::after {
  content: '▊';
  display: inline-block;
  animation: pulse 1s ease-in-out infinite;
  color: var(--blue-500);
}
```

#### 2. Activity Timeline Animations

**Timeline Node**
```css
.timeline-node {
  animation: scaleIn 0.2s var(--ease-spring) forwards;
}

.timeline-node.active {
  animation: glowPulse 2s ease-out infinite;
}
```

**Timeline Line Progress**
```css
.timeline-progress {
  animation: expandHeight 0.5s var(--ease-out-quart) forwards;
}

@keyframes expandHeight {
  from { height: 0; }
  to { height: 100%; }
}
```

#### 3. Tool Badge Animations

**Badge Entrance**
```css
.tool-badge-enter {
  animation: scaleIn 0.15s var(--ease-spring) forwards;
}

.tool-badge-icon {
  animation: spin 1s linear infinite;
  animation-play-state: paused;
}

.tool-badge.active .tool-badge-icon {
  animation-play-state: running;
}
```

#### 4. Code Editor Animations

**Code Highlight**
```css
.code-highlight {
  position: relative;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--yellow-500/20) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: highlightSweep 2s ease-out forwards;
}

@keyframes highlightSweep {
  from { background-position: -100% 0; }
  to { background-position: 100% 0; }
}
```

#### 5. Step Navigator Animations

**Step Transition**
```css
.step-indicator {
  transition: all 0.3s var(--ease-out-expo);
}

.step-indicator.active {
  transform: scale(1.2);
  background-color: var(--blue-500);
}

.step-progress-bar {
  transition: width 0.5s var(--ease-out-quart);
}
```

#### 6. Final Answer Animations

**Success Animation**
```css
@keyframes successPulse {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  70% {
    box-shadow: 0 0 0 20px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.final-answer-enter {
  animation: 
    scaleIn 0.3s var(--ease-out-expo) forwards,
    successPulse 2s ease-out 0.3s;
}
```

#### 7. Loading States

**Skeleton Loading**
```css
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--neutral-700) 25%,
    var(--neutral-600) 50%,
    var(--neutral-700) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

**Typing Indicator**
```css
.typing-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--neutral-400);
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typingBounce {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
```

### Transition Guidelines

#### Page/View Transitions
```css
.view-transition {
  transition: opacity 0.3s ease-out, transform 0.3s ease-out;
}

.view-exit {
  opacity: 0;
  transform: translateY(-10px);
}

.view-enter {
  opacity: 0;
  transform: translateY(10px);
}

.view-enter-active {
  opacity: 1;
  transform: translateY(0);
}
```

#### Modal/Dialog Transitions
```css
.modal-backdrop {
  transition: opacity 0.2s ease-out;
}

.modal-content {
  transition: all 0.3s var(--ease-out-expo);
}

.modal-enter .modal-content {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.modal-enter-active .modal-content {
  opacity: 1;
  transform: scale(1) translateY(0);
}
```

### Performance Optimizations

1. **Hardware Acceleration**
   ```css
   .animated-element {
     will-change: transform, opacity;
     transform: translateZ(0); /* Force GPU acceleration */
   }
   ```

2. **Reduce Paint Operations**
   - Use `transform` and `opacity` for animations
   - Avoid animating `width`, `height`, `top`, `left`
   - Use `transform: scale()` instead of width/height changes

3. **Animation Throttling**
   ```tsx
   // Disable animations during rapid updates
   const [animationsEnabled, setAnimationsEnabled] = useState(true);
   
   useEffect(() => {
     if (messageUpdateRate > 10) { // messages per second
       setAnimationsEnabled(false);
     }
   }, [messageUpdateRate]);
   ```

4. **Conditional Animations**
   ```css
   /* Respect user preferences */
   @media (prefers-reduced-motion: reduce) {
     * {
       animation-duration: 0.01ms !important;
       animation-iteration-count: 1 !important;
       transition-duration: 0.01ms !important;
     }
   }
   ```

### Animation Specifications

#### Core Animation Keyframes

```css
/* Fade In */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Fade In Up */
@keyframes fadeInUp {
  from { 
    opacity: 0; 
    transform: translateY(10px); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
  }
}

/* Slide In */
@keyframes slideIn {
  from { 
    opacity: 0; 
    transform: translateX(-20px); 
  }
  to { 
    opacity: 1; 
    transform: translateX(0); 
  }
}

/* Slide In Right */
@keyframes slideInRight {
  from { 
    opacity: 0; 
    transform: translateX(20px); 
  }
  to { 
    opacity: 1; 
    transform: translateX(0); 
  }
}

/* Scale In */
@keyframes scaleIn {
  from { 
    opacity: 0; 
    transform: scale(0.95); 
  }
  to { 
    opacity: 1; 
    transform: scale(1); 
  }
}

/* Pulse */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Bounce */
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-25%); }
}

/* Spin */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Expand Width */
@keyframes expandWidth {
  from { width: 0; }
  to { width: 100%; }
}

/* Glow Pulse */
@keyframes glowPulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% { 
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
  }
}
```

#### Animation Classes

```css
/* Basic Animations */
.animate-fadeIn {
  animation: fadeIn 0.3s ease-out forwards;
}

.animate-fadeInUp {
  animation: fadeInUp 0.3s ease-out forwards;
}

.animate-slideIn {
  animation: slideIn 0.3s ease-out forwards;
}

.animate-slideInRight {
  animation: slideInRight 0.3s ease-out forwards;
}

.animate-scaleIn {
  animation: scaleIn 0.2s ease-out forwards;
}

/* Continuous Animations */
.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-bounce {
  animation: bounce 1s ease-in-out infinite;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Special Effects */
.animate-glowPulse {
  animation: glowPulse 2s ease-out infinite;
}

/* Delayed Animations */
.animate-delay-100 {
  animation-delay: 100ms;
}

.animate-delay-200 {
  animation-delay: 200ms;
}

.animate-delay-300 {
  animation-delay: 300ms;
}

/* Duration Variants */
.animate-fast {
  animation-duration: 150ms;
}

.animate-slow {
  animation-duration: 500ms;
}
```

#### Timing Functions

```css
/* Custom Timing Functions */
:root {
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  --ease-in-out-quart: cubic-bezier(0.76, 0, 0.24, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### Interaction States

1. **Hover Effects**
   ```css
   /* Buttons */
   .button:hover {
     background-color: var(--neutral-600);
     transform: translateY(-1px);
     box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
     transition: all 0.2s var(--ease-out-expo);
   }
   
   /* Cards */
   .card:hover {
     border-color: var(--neutral-500);
     box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
     transform: translateY(-2px);
     transition: all 0.2s var(--ease-out-expo);
   }
   
   /* Message Bubbles */
   .message:hover {
     background-color: var(--neutral-650);
     transition: background-color 0.2s ease;
   }
   
   /* Tool Badges */
   .tool-badge:hover {
     background-color: var(--blue-500/20);
     transform: scale(1.05);
     transition: all 0.15s var(--ease-spring);
   }
   ```

2. **Active States**
   ```css
   .button:active {
     transform: scale(0.98);
     transition: transform 0.1s ease;
   }
   
   .card:active {
     transform: scale(0.99);
     transition: transform 0.1s ease;
   }
   ```

3. **Focus States**
   ```css
   .input:focus {
     border-color: var(--blue-500);
     box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
     outline: none;
     transition: all 0.2s ease;
   }
   
   .button:focus-visible {
     outline: 2px solid var(--blue-500);
     outline-offset: 2px;
   }
   ```

4. **Loading States**
   ```css
   .loading {
     position: relative;
     color: transparent;
   }
   
   .loading::after {
     content: '';
     position: absolute;
     top: 50%;
     left: 50%;
     width: 20px;
     height: 20px;
     margin: -10px 0 0 -10px;
     border: 2px solid var(--neutral-400);
     border-radius: 50%;
     border-top-color: transparent;
     animation: spin 0.8s linear infinite;
   }
   ```

## Implementation Guidelines

### Component Structure

1. **Message Flow Architecture**
   ```
   Backend (DSAgentRunMessage) 
     ↓
   WebSocket Handler (streaming detection)
     ↓
   Message Processor (component routing)
     ↓
   UI Components (Chat/Code/Terminal)
   ```

2. **State Management**
   - Use React Context for global state
   - Track streaming messages with Map by step number
   - Implement proper message deduplication
   - Handle real-time updates efficiently

3. **Performance Considerations**
   - Virtualize long message lists
   - Debounce rapid updates
   - Use React.memo for expensive components
   - Implement proper cleanup for WebSocket connections

### Responsive Design

1. **Breakpoints**
   ```css
   /* Mobile: < 640px */
   /* Tablet: 640px - 1024px */
   /* Desktop: > 1024px */
   ```

2. **Mobile Adaptations**
   - Stack layout vertically on mobile
   - Hide secondary panels by default
   - Use bottom sheet for input
   - Simplify timeline visualization

### Accessibility

1. **Color Contrast**
   - Ensure WCAG AA compliance
   - Provide high contrast mode option
   - Use semantic color meanings

2. **Keyboard Navigation**
   - All interactive elements keyboard accessible
   - Clear focus indicators
   - Logical tab order

3. **Screen Reader Support**
   - Proper ARIA labels
   - Live regions for updates
   - Semantic HTML structure

### Testing Considerations

1. **Visual Regression Testing**
   - Component screenshots
   - Animation timing
   - Theme consistency

2. **Performance Testing**
   - Message streaming rate
   - Memory usage with large conversations
   - Animation frame rates

3. **Cross-browser Compatibility**
   - Chrome, Firefox, Safari, Edge
   - Consistent animations
   - WebSocket compatibility

## Next Steps

1. **Phase 1**: Implement core visual design system
2. **Phase 2**: Enhance message components with timeline
3. **Phase 3**: Add advanced animations and transitions
4. **Phase 4**: Optimize for performance and accessibility
5. **Phase 5**: Implement responsive design adaptations

### Animation Implementation Examples

#### React Component with Animations
```tsx
import { motion, AnimatePresence } from 'framer-motion';

const MessageItem = ({ message, index }) => {
  const variants = {
    hidden: { 
      opacity: 0, 
      y: 20,
      scale: 0.95
    },
    visible: { 
      opacity: 1, 
      y: 0,
      scale: 1,
      transition: {
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1], // ease-out-expo
        delay: index * 0.05 // stagger effect
      }
    },
    exit: {
      opacity: 0,
      y: -10,
      transition: { duration: 0.2 }
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        key={message.id}
        variants={variants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="message-container"
      >
        {message.content}
      </motion.div>
    </AnimatePresence>
  );
};
```

#### CSS-Only Animation Solution
```css
/* Message container with stagger */
.message-list > .message-item {
  opacity: 0;
  animation: fadeInUp 0.3s var(--ease-out-expo) forwards;
}

.message-list > .message-item:nth-child(1) { animation-delay: 0ms; }
.message-list > .message-item:nth-child(2) { animation-delay: 50ms; }
.message-list > .message-item:nth-child(3) { animation-delay: 100ms; }
.message-list > .message-item:nth-child(4) { animation-delay: 150ms; }
/* Continue pattern or use CSS custom properties */
```

#### Activity Timeline Animation Sequence
```tsx
const TimelineNode = ({ event, isActive, delay = 0 }) => {
  return (
    <div 
      className={`
        timeline-node 
        ${isActive ? 'active' : ''}
        animate-scaleIn
      `}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="node-icon">
        {isActive && <div className="node-pulse" />}
      </div>
      <div className="node-content animate-fadeIn animate-delay-100">
        <h4>{event.title}</h4>
        <p>{event.description}</p>
      </div>
    </div>
  );
};
```

## Summary

This design system provides a solid foundation for creating a professional, modern UI for DeepSearchAgents that enhances the user experience while maintaining excellent performance for real-time agent interactions. The comprehensive animation system ensures smooth, meaningful transitions that guide user attention without impacting performance, while the visual design creates a sophisticated dark-themed interface optimized for extended use.
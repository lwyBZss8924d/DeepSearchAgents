# Agent Message Stream UI Specification

## Overview

This document provides detailed specifications for how DeepSearchAgents displays and processes agent run stream messages in the frontend UI, incorporating the visual design principles from our UI/UX requirements.

## Message Types & Display Mapping

### 1. PlanningStep Messages

**Backend Structure (smolagents)**:
```python
PlanningStep:
  - plan: str
  - timing: Timing
  - token_usage: TokenUsage
```

**Frontend Display**:
- **Component**: Chat Interface
- **Visual Style**: Yellow-tinted background with thinking icon
- **Content**: 
  - "**Planning step**" header
  - Plan content in markdown
  - Timing/token usage in footer

**UI Implementation**:
```tsx
<div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
  <div className="flex items-center gap-2 mb-2">
    <Brain className="h-4 w-4 text-yellow-500" />
    <span className="text-sm font-medium text-yellow-500">Planning</span>
  </div>
  <Markdown>{planContent}</Markdown>
</div>
```

### 2. ActionStep Messages

**Backend Structure**:
```python
ActionStep:
  - step_number: int
  - model_output: str  # "Thought"
  - code_action: str   # Python code
  - tool_calls: list[ToolCall]
  - observations: str  # Execution results
  - is_final_answer: bool
```

**Frontend Display Components**:

#### 2.1 Thought Display (Chat Interface)
```tsx
<div className="flex items-start gap-3">
  <div className="flex-1">
    <div className="text-xs text-neutral-400 mb-1">Step {stepNumber}</div>
    <div className="bg-neutral-800 rounded-lg p-3">
      <Markdown>{thought}</Markdown>
    </div>
  </div>
</div>
```

#### 2.2 Code Action Display (Code Editor)
```tsx
<CodeEditor
  code={codeAction}
  language="python"
  stepNumber={stepNumber}
  readOnly={true}
/>
```

#### 2.3 Tool Call Display (Chat Interface)
```tsx
<div className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 rounded-lg">
  <Terminal className="h-4 w-4 text-blue-500" />
  <span className="text-sm text-blue-500">
    Tool: python_interpreter
  </span>
</div>
```

#### 2.4 Execution Output (Terminal)
```tsx
<Terminal
  logs={observations}
  stepNumber={stepNumber}
  className="h-full"
/>
```

### 3. FinalAnswerStep Messages

**Backend Structure**:
```python
FinalAnswerStep:
  - output: Any  # Usually JSON with title, content, sources
```

**Frontend Display**:
```tsx
<FinalAnswer
  title={output.title}
  content={output.content}
  sources={output.sources}
  confidence={output.confidence}
/>
```

## Message Flow & Processing

### WebSocket Message Reception

```typescript
// Message structure from backend
interface DSAgentRunMessage {
  role: 'user' | 'assistant';
  content: string;
  metadata: {
    streaming?: boolean;
    component?: 'chat' | 'webide' | 'terminal';
    event_type?: string;
    tool_name?: string;
    is_final_answer?: boolean;
    [key: string]: any;
  };
  message_id: string;
  timestamp: string;
  session_id: string;
  step_number?: number;
}
```

### Message Processing Pipeline

1. **Streaming Detection**
   ```typescript
   if (message.metadata?.streaming === true) {
     // Accumulate streaming chunks
     updateStreamingMessage(stepNumber, content);
   } else {
     // Process complete message
     addCompleteMessage(message);
   }
   ```

2. **Component Routing**
   ```typescript
   switch (message.metadata?.component) {
     case 'webide':
       // Route to code editor
       updateCodeEditor(message);
       break;
     case 'terminal':
       // Route to terminal
       updateTerminal(message);
       break;
     default:
       // Display in chat
       addChatMessage(message);
   }
   ```

3. **Tab Switching Logic**
   ```typescript
   // Automatic tab switching based on content
   if (message.metadata?.component === 'webide') {
     setActiveTab('code');
   } else if (message.metadata?.component === 'terminal') {
     setActiveTab('terminal');
   }
   ```

## Visual Components

### Activity Timeline

Shows the progression of agent steps:

```tsx
interface ActivityEvent {
  type: 'planning' | 'thinking' | 'coding' | 'executing' | 'finalizing';
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed';
  timestamp: string;
}

<ActivityTimeline
  events={[
    { type: 'thinking', title: 'Analyzing task...', status: 'completed' },
    { type: 'coding', title: 'Writing solution...', status: 'active' },
    { type: 'executing', title: 'Running code...', status: 'pending' }
  ]}
  isLoading={isGenerating}
/>
```

### Step Navigator

Allows navigation between execution steps:

```tsx
<StepNavigator
  currentStep={currentStep}
  maxStep={maxStep}
  onStepChange={(step) => setCurrentStep(step)}
/>
```

### Message Metadata Display

Shows additional information about messages:

```tsx
<div className="flex items-center gap-2 text-xs text-neutral-400">
  {/* Tool usage */}
  {message.metadata?.tool_name && (
    <Badge variant="secondary">
      Tool: {message.metadata.tool_name}
    </Badge>
  )}
  
  {/* Streaming indicator */}
  {message.metadata?.streaming && (
    <Badge variant="secondary" className="animate-pulse">
      <Loader2 className="h-3 w-3 animate-spin mr-1" />
      Streaming
    </Badge>
  )}
  
  {/* Timestamp */}
  <span>{formatTimestamp(message.timestamp)}</span>
</div>
```

## State Management

### Message Accumulation

```typescript
// Track streaming messages by step
const streamingMessages = useRef<Map<number, DSAgentRunMessage>>(new Map());

// Update streaming message
function updateStreamingMessage(stepNumber: number, content: string) {
  const existing = streamingMessages.current.get(stepNumber);
  if (existing) {
    // Append content
    existing.content += content;
    dispatch({ type: 'UPDATE_MESSAGE', payload: existing });
  } else {
    // Create new streaming message
    const message = createStreamingMessage(stepNumber, content);
    streamingMessages.current.set(stepNumber, message);
    dispatch({ type: 'ADD_MESSAGE', payload: message });
  }
}
```

### Message Grouping

```typescript
// Group messages by step for display
const messagesByStep = useMemo(() => {
  return messages.reduce((acc, message) => {
    const step = message.step_number || 0;
    if (!acc[step]) acc[step] = [];
    acc[step].push(message);
    return acc;
  }, {} as Record<number, DSAgentRunMessage[]>);
}, [messages]);
```

## Styling Guidelines

### Message Container Styles

```css
/* User message */
.message-user {
  @apply bg-neutral-700 text-white rounded-3xl rounded-br-lg px-4 py-3;
  @apply max-w-[90%] ml-auto;
}

/* Assistant message */
.message-assistant {
  @apply bg-neutral-800 text-neutral-100 rounded-xl rounded-bl-none p-3;
  @apply shadow-sm;
}

/* Thinking message */
.message-thinking {
  @apply bg-yellow-500/10 border border-yellow-500/20;
  @apply text-yellow-50;
}

/* Final answer */
.message-final {
  @apply bg-green-500/10 border-2 border-green-500/30;
  @apply shadow-lg;
}
```

### Animation Classes

```css
/* Message entrance */
.message-enter {
  @apply animate-fadeInUp;
}

/* Streaming text */
.streaming-text {
  @apply animate-pulse;
}

/* Loading indicator */
.loading-dots {
  @apply inline-flex gap-1;
}

.loading-dots span {
  @apply w-2 h-2 bg-neutral-400 rounded-full animate-bounce;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.1s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.2s;
}
```

## Performance Optimizations

### 1. Message Virtualization

For long conversations, virtualize the message list:

```tsx
import { VirtualList } from '@tanstack/react-virtual';

<VirtualList
  items={messages}
  estimateSize={() => 100}
  renderItem={({ item }) => <MessageItem message={item} />}
/>
```

### 2. Streaming Debouncing

Debounce rapid streaming updates:

```typescript
const debouncedUpdate = useMemo(
  () => debounce((message: DSAgentRunMessage) => {
    dispatch({ type: 'UPDATE_MESSAGE', payload: message });
  }, 100),
  []
);
```

### 3. Component Memoization

Memoize expensive components:

```tsx
const MessageItem = React.memo(({ message }) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison logic
  return prevProps.message.message_id === nextProps.message.message_id &&
         prevProps.message.content === nextProps.message.content;
});
```

## Error Handling

### Error Message Display

```tsx
interface ErrorMessage {
  type: 'error';
  message: string;
  error_code?: string;
  details?: any;
}

<div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
  <div className="flex items-center gap-2 mb-2">
    <AlertCircle className="h-5 w-5 text-red-500" />
    <span className="font-medium text-red-500">Error</span>
  </div>
  <p className="text-sm text-red-200">{error.message}</p>
  {error.details && (
    <details className="mt-2">
      <summary className="text-xs text-red-300 cursor-pointer">
        View details
      </summary>
      <pre className="mt-2 text-xs bg-red-950/50 p-2 rounded">
        {JSON.stringify(error.details, null, 2)}
      </pre>
    </details>
  )}
</div>
```

## Accessibility Features

### 1. ARIA Labels

```tsx
<div 
  role="log" 
  aria-live="polite" 
  aria-label="Agent conversation"
>
  {messages.map(message => (
    <div
      role="article"
      aria-label={`${message.role} message at step ${message.step_number}`}
    >
      {/* Message content */}
    </div>
  ))}
</div>
```

### 2. Keyboard Navigation

```typescript
// Navigate between steps with keyboard
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && currentStep > 0) {
      setCurrentStep(currentStep - 1);
    } else if (e.key === 'ArrowRight' && currentStep < maxStep) {
      setCurrentStep(currentStep + 1);
    }
  };
  
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [currentStep, maxStep]);
```

### 3. Screen Reader Announcements

```tsx
// Announce streaming updates
<div className="sr-only" aria-live="assertive">
  {isStreaming && "Agent is typing..."}
  {isComplete && "Agent has finished responding"}
</div>
```

## Testing Strategies

### 1. Component Testing

```typescript
describe('AgentChat', () => {
  it('should display user messages correctly', () => {
    const message = {
      role: 'user',
      content: 'Test query',
      message_id: '1'
    };
    
    render(<AgentChat messages={[message]} />);
    expect(screen.getByText('Test query')).toBeInTheDocument();
  });
  
  it('should handle streaming messages', async () => {
    // Test streaming accumulation
  });
});
```

### 2. Visual Regression Testing

```typescript
// Snapshot key UI states
test('message styles match design', async () => {
  const { container } = render(<MessageItem {...props} />);
  expect(container).toMatchSnapshot();
});
```

### 3. Performance Testing

```typescript
// Measure render performance
test('handles large message lists efficiently', () => {
  const messages = generateMockMessages(1000);
  const { rerender } = render(<AgentChat messages={messages} />);
  
  performance.mark('start');
  rerender(<AgentChat messages={[...messages, newMessage]} />);
  performance.mark('end');
  
  const measure = performance.measure('update', 'start', 'end');
  expect(measure.duration).toBeLessThan(16); // 60fps
});
```

This specification provides a comprehensive guide for implementing the agent message stream UI with all the necessary visual components, interactions, and technical considerations.
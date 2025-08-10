"use client";

import { useState, useRef, KeyboardEvent, useEffect } from "react";
import { 
  DSTerminalPrompt 
} from "@/components/ds";
import { cn } from "@/lib/utils";

interface AgentQuestionInputProps {
  onSubmit: (query: string) => void;
  isRunning?: boolean;
  sessionId?: string | null;
  placeholder?: string;
}

export default function AgentQuestionInputV2({
  onSubmit,
  isRunning = false,
  sessionId
}: AgentQuestionInputProps) {
  const [query, setQuery] = useState("");
  const [isPastedOverflow, setIsPastedOverflow] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const MAX_VISIBLE_LINES = 5;
  const LINE_HEIGHT = 24; // pixels per line

  const handleSubmit = () => {
    if (query.trim() && !isRunning && sessionId) {
      onSubmit(query.trim());
      setQuery("");
      setIsPastedOverflow(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const pastedText = e.clipboardData.getData('text');
    const lineCount = pastedText.split('\n').length;
    
    if (lineCount > MAX_VISIBLE_LINES) {
      e.preventDefault();
      const firstLines = pastedText.split('\n').slice(0, MAX_VISIBLE_LINES - 1).join('\n');
      const remainingLines = lineCount - (MAX_VISIBLE_LINES - 1);
      setQuery(`${firstLines}\n[Pasted text *1 +${remainingLines} lines]`);
      setIsPastedOverflow(true);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    
    // If deleting and we have overflow indicator, clear all
    if (isPastedOverflow && newValue.length < query.length) {
      setQuery('');
      setIsPastedOverflow(false);
    } else {
      setQuery(newValue);
    }
  };

  // Auto-resize the textarea based on content
  useEffect(() => {
    if (textareaRef.current && !isPastedOverflow) {
      const textarea = textareaRef.current;
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = MAX_VISIBLE_LINES * LINE_HEIGHT;
      textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [query, isPastedOverflow]);

  // const isDisabled = !sessionId || isRunning || !query.trim();

  return (
    <div className="p-4">
      <div className="relative" ref={containerRef}>
        <span className="absolute left-3 top-2 font-mono text-sm pointer-events-none z-50" style={{ color: 'var(--ds-terminal-bright)' }}>
          &gt;
        </span>
        <textarea
          ref={textareaRef}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder=""
          disabled={!sessionId || isRunning}
          rows={1}
          className={cn(
            "ds-textarea font-mono text-sm",
            "bg-[var(--ds-terminal-bg)] text-[var(--ds-terminal-fg)]",
            "border border-[var(--ds-border-default)]",
            "px-3 py-2",
            "transition-all duration-200",
            "focus:outline-none focus:border-[var(--ds-border-active)]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "resize-none w-full",
            "overflow-hidden whitespace-pre-wrap break-words"
          )}
          style={{ 
            paddingLeft: '2rem',
            minHeight: '36px',
            maxHeight: `${MAX_VISIBLE_LINES * LINE_HEIGHT}px`
          }}
        />
      </div>
      
      {/* Terminal-style status line */}
      <div className="mt-2 text-xs font-mono text-[var(--ds-terminal-dim)]">
        {!sessionId && "⚠ No active session"}
        {sessionId && !isRunning && "Press Enter to send, Shift+Enter for new line"}
        {sessionId && isRunning && "Agent is processing your request..."}
      </div>
    </div>
  );
}

// Alternative terminal prompt style input
export function AgentTerminalInputV2({
  onSubmit,
  isRunning = false,
  sessionId
}: AgentQuestionInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (value: string) => {
    if (value.trim() && !isRunning && sessionId) {
      onSubmit(value.trim());
      setQuery("");
    }
  };

  return (
    <div className="p-4 bg-[var(--ds-terminal-bg)]">
      <DSTerminalPrompt
        prompt={isRunning ? ">" : "$"}
        value={query}
        onChange={setQuery}
        onSubmit={handleSubmit}
        placeholder={sessionId ? "Enter your query..." : "No active session"}
        className={!sessionId || isRunning ? "opacity-50" : ""}
      />
    </div>
  );
}
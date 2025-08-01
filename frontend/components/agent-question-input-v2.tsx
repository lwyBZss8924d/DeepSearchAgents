"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { SendIcon, LoaderIcon } from "@/components/terminal-icons";
import { 
  DSTextarea,
  DSButton,
  DSTerminalPrompt 
} from "@/components/ds";

interface AgentQuestionInputProps {
  onSubmit: (query: string) => void;
  isRunning?: boolean;
  sessionId?: string | null;
  placeholder?: string;
}

export default function AgentQuestionInputV2({
  onSubmit,
  isRunning = false,
  sessionId,
  placeholder = "Ask a question..."
}: AgentQuestionInputProps) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (query.trim() && !isRunning && sessionId) {
      onSubmit(query.trim());
      setQuery("");
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

  const isDisabled = !sessionId || isRunning || !query.trim();

  return (
    <div className="p-4">
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <DSTextarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={!sessionId || isRunning}
            minRows={1}
            maxRows={5}
            className="resize-none"
          />
        </div>
        <DSButton
          onClick={handleSubmit}
          disabled={isDisabled}
          variant="primary"
          size="md"
          icon={isRunning ? <LoaderIcon size={16} /> : <SendIcon size={16} />}
          aria-label={isRunning ? "Processing..." : "Send message"}
        >
          {isRunning ? "Processing" : "Send"}
        </DSButton>
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
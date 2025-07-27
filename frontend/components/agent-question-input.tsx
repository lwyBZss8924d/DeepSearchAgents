"use client";

// Simplified question input for DeepSearchAgents
import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAppContext } from "@/context/app-context";

interface AgentQuestionInputProps {
  onSubmit: (question: string) => void;
  className?: string;
}

export default function AgentQuestionInput({ onSubmit, className }: AgentQuestionInputProps) {
  const { state } = useAppContext();
  const { isGenerating, isConnected } = state;
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!question.trim() || isGenerating || !isConnected) return;
    
    onSubmit(question);
    setQuestion("");
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    
    // Auto-resize
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  return (
    <div className={`border-t bg-background p-4 ${className}`}>
      <div className="flex gap-2">
        <Textarea
          ref={textareaRef}
          value={question}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={
            !isConnected 
              ? "Connecting to agent..." 
              : isGenerating 
              ? "Agent is processing..." 
              : "Ask a question..."
          }
          disabled={!isConnected || isGenerating}
          className="min-h-[60px] max-h-[200px] resize-none"
          rows={2}
        />
        <Button
          onClick={handleSubmit}
          disabled={!question.trim() || isGenerating || !isConnected}
          size="icon"
          className="h-[60px] w-[60px]"
        >
          {isGenerating ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
      
      {/* Connection status */}
      {!isConnected && (
        <div className="mt-2 text-xs text-muted-foreground">
          Waiting for connection...
        </div>
      )}
    </div>
  );
}
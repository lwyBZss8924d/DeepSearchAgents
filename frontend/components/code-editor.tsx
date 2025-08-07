"use client";

// Terminal-style CodeEditor using DS components
import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/app-context';
import { 
  DSAgentMessageCard,
  DSAgentStateBadge
} from '@/components/ds';
import { extractPythonCode, isCodeEditorMessage } from '@/utils/extractors';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/terminal-icons';
import MonacoCodeEditor from '@/components/monaco-code-editor';

interface CodeEditorProps {
  className?: string;
}

export default function CodeEditor({ className }: CodeEditorProps) {
  const { state, dispatch } = useAppContext();
  const { messages, currentStep, maxStep } = state;
  const [code, setCode] = useState<string>('');
  const [language, setLanguage] = useState<string>('python');
  const [executionResult, setExecutionResult] = useState<{
    output?: string;
    error?: string;
    exitCode?: number;
  } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };
  
  useEffect(() => {
    // Find all messages that should appear in code editor
    const codeMessages = messages.filter(m => {
      return m.metadata?.component === 'webide' || isCodeEditorMessage(m.metadata);
    });
    
    // Find the latest code message for current step or the most recent one
    const currentStepMessages = codeMessages.filter(m => m.step_number === currentStep);
    const codeMessage = currentStepMessages.length > 0 
      ? currentStepMessages[currentStepMessages.length - 1]
      : codeMessages.length > 0 
        ? codeMessages[codeMessages.length - 1]
        : null;
    
    if (codeMessage) {
      // Set streaming state from metadata
      setIsStreaming(codeMessage.metadata?.streaming === true);
      
      // First try to get code from metadata if available
      if (codeMessage.metadata?.code) {
        setCode(codeMessage.metadata.code);
        setLanguage(codeMessage.metadata.language || 'python');
      } else {
        // Fallback to extracting from content
        const extracted = extractPythonCode(codeMessage.content);
        if (extracted) {
          setCode(extracted.code);
          setLanguage(extracted.language || 'python');
        }
      }
      
      // Check for execution results
      if (codeMessage.metadata?.execution_result) {
        setExecutionResult(codeMessage.metadata.execution_result);
      }
    }
  }, [messages, currentStep]);

  if (!code && !isStreaming) {
    return (
      <DSAgentMessageCard type="system" state="idle" className={className}>
        <div className="ds-code-editor-empty neovim-style">
          <pre className="font-mono text-sm leading-relaxed">{`~
~
~
~     No code to display
~
~
~`}</pre>
          <div className="mt-4 text-xs text-[var(--ds-terminal-dim)] font-mono">
            -- NORMAL --
          </div>
        </div>
      </DSAgentMessageCard>
    );
  }

  return (
    <DSAgentMessageCard 
      type="action" 
      state={isStreaming ? "streaming" : "idle"}
      className={`${className} flex flex-col h-full`}
    >
      {/* Compact single-line header with step navigation and copy button */}
      <div className="ds-code-editor-header flex items-center justify-between px-2 py-1 border-b border-[var(--ds-border-default)] h-8">
        {/* Step navigation */}
        {maxStep > 0 ? (
          <div className="flex items-center gap-1">
            <button
              onClick={() => dispatch({ type: 'SET_CURRENT_STEP', payload: Math.max(0, currentStep - 1) })}
              disabled={currentStep === 0}
              className="p-0.5 hover:bg-[var(--ds-bg-elevated)] rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeftIcon className="h-3 w-3" />
            </button>
            
            <select
              value={currentStep}
              onChange={(e) => dispatch({ type: 'SET_CURRENT_STEP', payload: Number(e.target.value) })}
              className="text-xs border border-[var(--ds-border-default)] rounded px-1 py-0 bg-[var(--ds-bg-default)] text-[var(--ds-terminal-fg)]"
            >
              {Array.from({ length: maxStep + 1 }, (_, i) => (
                <option key={i} value={i}>
                  Step {i}
                </option>
              ))}
            </select>
            
            <button
              onClick={() => dispatch({ type: 'SET_CURRENT_STEP', payload: Math.min(maxStep, currentStep + 1) })}
              disabled={currentStep === maxStep}
              className="p-0.5 hover:bg-[var(--ds-bg-elevated)] rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRightIcon className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <div></div>
        )}
        
        {/* Copy button */}
        <button
          onClick={handleCopy}
          className="p-0.5 text-xs hover:bg-[var(--ds-bg-elevated)] rounded transition-colors"
          aria-label="Copy code"
        >
          <span className="font-mono">
            {isCopied ? '[✓]' : '[⧉]'}
          </span>
        </button>
      </div>
      
      {/* Code display */}
      <div className="ds-code-editor-content flex-1 overflow-hidden">
        <MonacoCodeEditor
          code={code}
          language={language}
          readOnly={true}
          height="100%"
          className="h-full"
        />
      </div>
      
      {/* Execution status */}
      {executionResult && (
        <div className="ds-code-editor-status">
          <DSAgentStateBadge
            state={executionResult.error ? "error" : "final"}
            text={executionResult.error ? "Execution failed" : "Execution completed"}
            isAnimated={false}
          />
        </div>
      )}
    </DSAgentMessageCard>
  );
}
"use client";

// Terminal-style CodeEditor using DS components
import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/app-context';
import { 
  DSAgentCodeBlock, 
  DSAgentToolBadge,
  DSAgentMessageCard,
  DSAgentStateBadge
} from '@/components/ds';
import { extractPythonCode, isCodeEditorMessage } from '@/utils/extractors';

interface CodeEditorProps {
  className?: string;
}

export default function CodeEditor({ className }: CodeEditorProps) {
  const { state } = useAppContext();
  const { messages, currentStep } = state;
  const [code, setCode] = useState<string>('');
  const [language, setLanguage] = useState<string>('python');
  const [toolName, setToolName] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<{
    output?: string;
    error?: string;
    exitCode?: number;
  } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  
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
      // Set tool name from metadata
      setToolName(codeMessage.metadata?.tool_name || null);
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
      className={className}
    >
      {/* Header with tool badge */}
      <div className="ds-code-editor-header">
        {toolName && (
          <DSAgentToolBadge 
            toolName={toolName}
            status={isStreaming ? "active" : "completed"}
          />
        )}
        <DSAgentStateBadge 
          state="coding"
          text={isStreaming ? "Writing code..." : "Code"}
          showSpinner={false}
          isAnimated={false}
        />
      </div>
      
      {/* Code display */}
      <div className="ds-code-editor-content">
        <DSAgentCodeBlock
          code={code}
          language={language}
          lineNumbers={true}
          streaming={isStreaming}
          executable={language === 'python' && !isStreaming}
          executionResult={executionResult || undefined}
          className="ds-code-editor-block"
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
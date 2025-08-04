"use client";

// Simplified CodeEditor for agent code display
import { Editor } from '@monaco-editor/react';
import { useEffect, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { DSButton } from '@/components/ds';
import { useAppContext } from '@/context/app-context';
import { extractPythonCode, isCodeEditorMessage } from '@/utils/extractors';

interface CodeEditorProps {
  className?: string;
}

export default function CodeEditor({ className }: CodeEditorProps) {
  const { state } = useAppContext();
  const { messages, currentStep } = state;
  const [code, setCode] = useState<string>('');
  const [language, setLanguage] = useState<string>('python');
  const [copied, setCopied] = useState(false);
  const [toolName, setToolName] = useState<string | null>(null);
  
  useEffect(() => {
    // Find all messages that should appear in code editor
    const codeMessages = messages.filter(m => {
      // Check if this message is meant for webide component
      return m.metadata?.component === 'webide' || isCodeEditorMessage(m.metadata);
    });
    
    // Find the latest code message for current step or the most recent one
    const currentStepMessages = codeMessages.filter(m => m.step_number === currentStep);
    const codeMessage = currentStepMessages.length > 0 
      ? currentStepMessages[currentStepMessages.length - 1]  // Latest message for current step
      : codeMessages.length > 0 
        ? codeMessages[codeMessages.length - 1]  // Latest code message overall
        : null;
    
    if (codeMessage) {
      // Set tool name from metadata
      setToolName(codeMessage.metadata?.tool_name || null);
      
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
        } else {
          // If no code block found, use the content as-is
          setCode(codeMessage.content);
          setLanguage('python');
        }
      }
    } else {
      // If no code messages found, show placeholder
      setCode('# No code to display');
      setLanguage('python');
      setToolName(null);
    }
  }, [messages, currentStep]);
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };
  
  return (
    <div className={`flex flex-col h-full w-full ${className}`}>
      {/* Header with step indicator and copy button */}
      <div className="flex items-center justify-between p-3 border-b bg-background">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            Step {currentStep}
          </span>
          {toolName && (
            <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 rounded">
              Tool: {toolName}
            </span>
          )}
          <span className="text-sm text-muted-foreground">
            {language}
          </span>
        </div>
        <DSButton
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="flex items-center gap-2"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              Copy
            </>
          )}
        </DSButton>
      </div>
      
      {/* Monaco Editor - Read Only */}
      <div className="flex-1">
        <Editor
          theme="vs-dark"
          language={language}
          value={code}
          options={{
            readOnly: true,              // Make read-only
            minimap: { enabled: false }, // Remove minimap
            lineNumbers: 'on',
            automaticLayout: true,
            fontSize: 14,
            fontFamily: 'var(--ds-font-mono)',
            fontLigatures: true,
            // Remove editing features
            quickSuggestions: false,
            parameterHints: { enabled: false },
            suggestOnTriggerCharacters: false,
            acceptSuggestionOnEnter: 'off',
            tabCompletion: 'off',
            wordBasedSuggestions: 'off',
            // Visual improvements
            renderLineHighlight: 'none',
            scrollBeyondLastLine: false,
            folding: true,
            bracketPairColorization: { enabled: true },
            padding: { top: 10, bottom: 10 },
            scrollbar: {
              verticalScrollbarSize: 10,
              horizontalScrollbarSize: 10
            }
          }}
        />
      </div>
    </div>
  );
}
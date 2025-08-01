"use client";

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

// Dynamically import CodeEditor versions with SSR disabled
const CodeEditorV1 = dynamic(() => import('./code-editor'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-background">
      <p className="text-sm text-muted-foreground">Loading editor...</p>
    </div>
  )
});

const CodeEditorV2 = dynamic(() => import('./code-editor-v2'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-background">
      <p className="text-sm text-muted-foreground">Loading terminal editor...</p>
    </div>
  )
});

interface CodeEditorProps {
  className?: string;
}

export default function CodeEditorWrapper(props: CodeEditorProps) {
  const [useTerminalUI, setUseTerminalUI] = useState(true);
  
  useEffect(() => {
    // Check for terminal UI preference
    // Default to true (terminal UI) unless explicitly disabled
    const terminalUIDisabled = localStorage.getItem('ds-terminal-ui') === 'false' ||
                              window.location.search.includes('terminal=false');
    setUseTerminalUI(!terminalUIDisabled);
  }, []);
  
  // Use v2 (terminal-style) by default
  const Component = useTerminalUI ? CodeEditorV2 : CodeEditorV1;
  return <Component {...props} />;
}
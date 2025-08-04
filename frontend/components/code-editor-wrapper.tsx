"use client";

import dynamic from 'next/dynamic';

// Dynamically import CodeEditor with SSR disabled
const CodeEditor = dynamic(() => import('./code-editor'), {
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
  // Always use the terminal-style code editor (former v2)
  return <CodeEditor {...props} />;
}
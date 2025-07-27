"use client";

import dynamic from 'next/dynamic';

// Dynamically import CodeEditor with SSR disabled
const CodeEditor = dynamic(() => import('./code-editor'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-background">
      <p className="text-sm text-muted-foreground">Loading editor...</p>
    </div>
  )
});

export default CodeEditor;
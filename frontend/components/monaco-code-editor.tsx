"use client";

import { useRef } from 'react';
import Editor from '@monaco-editor/react';

interface MonacoCodeEditorProps {
  code: string;
  language: string;
  onChange?: (value: string | undefined) => void;
  readOnly?: boolean;
  height?: string;
  className?: string;
}

export default function MonacoCodeEditor({
  code,
  language,
  onChange,
  readOnly = true,
  height = "100%",
  className
}: MonacoCodeEditorProps) {
  const editorRef = useRef<unknown>(null);

  // Map our theme to Monaco theme
  const getMonacoTheme = () => {
    // All our terminal themes are dark, so use vs-dark as base
    return 'vs-dark';
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    
    // Define custom theme based on our terminal colors
    monaco.editor.defineTheme('terminal-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '388bfd' },
        { token: 'string', foreground: '3fb950' },
        { token: 'keyword', foreground: 'f85149' },
        { token: 'number', foreground: 'd29922' },
        { token: 'type', foreground: '39c5cf' },
        { token: 'function', foreground: 'bc8cff' },
      ],
      colors: {
        'editor.background': '#0d1117',
        'editor.foreground': '#58a6ff',
        'editor.lineHighlightBackground': '#161b22',
        'editorCursor.foreground': '#58a6ff',
        'editor.selectionBackground': '#388bfd40',
        'editor.inactiveSelectionBackground': '#388bfd20',
      }
    });
    
    // Apply custom theme
    monaco.editor.setTheme('terminal-dark');
  };

  return (
    <div className={className}>
      <Editor
        height={height}
        language={language}
        value={code}
        onChange={onChange}
        onMount={handleEditorDidMount}
        theme={getMonacoTheme()}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: 'var(--font-geist-mono)',
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: 'on',
          wrappingStrategy: 'advanced',
          renderLineHighlight: 'all',
          cursorStyle: 'block',
          renderWhitespace: 'selection',
          smoothScrolling: true,
          contextmenu: true,
          quickSuggestions: !readOnly,
          suggestOnTriggerCharacters: !readOnly,
          acceptSuggestionOnEnter: 'on',
          tabCompletion: 'on',
          wordBasedSuggestions: readOnly ? 'off' : 'currentDocument',
        }}
      />
    </div>
  );
}
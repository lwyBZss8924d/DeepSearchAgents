import { useEffect, useCallback } from 'react';

interface ShortcutHandler {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  handler: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: ShortcutHandler[]) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    shortcuts.forEach(shortcut => {
      const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
      const ctrlMatches = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : true;
      const metaMatches = shortcut.meta ? event.metaKey : true;
      const shiftMatches = shortcut.shift ? event.shiftKey : true;
      const altMatches = shortcut.alt ? event.altKey : true;
      
      if (keyMatches && ctrlMatches && metaMatches && shiftMatches && altMatches) {
        event.preventDefault();
        shortcut.handler();
      }
    });
  }, [shortcuts]);
  
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

// Common shortcuts for the application
export const commonShortcuts = {
  help: { key: '?', description: 'Show help' },
  commandPalette: { key: 'k', ctrl: true, description: 'Open command palette' },
  clearChat: { key: 'l', ctrl: true, description: 'Clear chat' },
  focusInput: { key: '/', description: 'Focus input' },
  toggleTheme: { key: 't', ctrl: true, description: 'Toggle theme' },
  copyLastMessage: { key: 'c', ctrl: true, shift: true, description: 'Copy last message' },
  exportChat: { key: 'e', ctrl: true, description: 'Export chat' },
};
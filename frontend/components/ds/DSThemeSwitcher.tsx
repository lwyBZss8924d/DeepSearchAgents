"use client";

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useDSTheme } from './DSThemeProvider';
import { DSAgentASCIISpinner } from './DSAgentASCIISpinner';

interface DSThemeSwitcherProps {
  className?: string;
  showPreview?: boolean;
  position?: 'top' | 'bottom';
}

/**
 * DSThemeSwitcher - Terminal-style theme switcher dropdown
 * 
 * Features ASCII borders, keyboard navigation, and live preview
 * of themes on hover
 */
export function DSThemeSwitcher({
  className,
  showPreview = true,
  position = 'bottom'
}: DSThemeSwitcherProps) {
  const { theme, themeId, setTheme, availableThemes } = useDSTheme();
  const [isOpen, setIsOpen] = useState(false);
  // State for hover preview - kept for future enhancement
  // const [hoveredTheme, setHoveredTheme] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        buttonRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex((prev) => 
            prev > 0 ? prev - 1 : availableThemes.length - 1
          );
          break;
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex((prev) => 
            prev < availableThemes.length - 1 ? prev + 1 : 0
          );
          break;
        case 'Enter':
          event.preventDefault();
          setTheme(availableThemes[selectedIndex].id);
          setIsOpen(false);
          break;
        case 'Escape':
          event.preventDefault();
          setIsOpen(false);
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, availableThemes, setTheme]);
  
  // Update selected index when theme changes
  useEffect(() => {
    const index = availableThemes.findIndex(t => t.id === themeId);
    if (index !== -1) {
      setSelectedIndex(index);
    }
  }, [themeId, availableThemes]);
  
  return (
    <div className={cn('ds-theme-switcher relative', className)}>
      {/* Theme button */}
      <button
        ref={buttonRef}
        className={cn(
          'ds-theme-button',
          'flex items-center gap-2',
          'px-3 py-2',
          'bg-[var(--ds-bg-elevated)]',
          'border border-[var(--ds-border-default)]',
          'text-[var(--ds-terminal-fg)]',
          'font-mono text-sm',
          'rounded',
          'transition-all duration-200',
          'hover:border-[var(--ds-border-active)]',
          'focus:outline-none focus:border-[var(--ds-border-active)]',
          isOpen && 'border-[var(--ds-border-active)]'
        )}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Theme switcher"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="ds-theme-icon">[T]</span>
        <span className="ds-theme-name">{theme.name}</span>
        <span className="ds-theme-arrow">{isOpen ? '▲' : '▼'}</span>
      </button>
      
      {/* Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className={cn(
            'ds-theme-dropdown',
            'absolute z-50',
            'mt-2 w-64',
            'bg-[var(--ds-terminal-bg)]',
            'border border-[var(--ds-border-active)]',
            'rounded',
            'shadow-lg',
            'overflow-hidden',
            position === 'top' ? 'bottom-full mb-2' : 'top-full'
          )}
          role="listbox"
          aria-label="Available themes"
        >
          {/* ASCII Header */}
          <div className="ds-dropdown-header px-3 py-2 border-b border-[var(--ds-border-default)]">
            <pre className="text-xs text-[var(--ds-terminal-dim)] font-mono">
              ╔═══════════════════╗
              ║  Terminal Themes  ║
              ╚═══════════════════╝
            </pre>
          </div>
          
          {/* Theme list */}
          <div className="ds-theme-list">
            {availableThemes.map((t, index) => (
              <div
                key={t.id}
                className={cn(
                  'ds-theme-item',
                  'px-3 py-2',
                  'cursor-pointer',
                  'transition-all duration-150',
                  'hover:bg-[var(--ds-bg-elevated)]',
                  selectedIndex === index && 'bg-[var(--ds-bg-elevated)]',
                  t.id === themeId && 'border-l-2 border-[var(--ds-terminal-fg)]'
                )}
                onClick={() => {
                  setTheme(t.id);
                  setIsOpen(false);
                }}
                onMouseEnter={() => {
                  // Preview on hover - future enhancement
                  // setHoveredTheme(t.id)
                }}
                onMouseLeave={() => {
                  // Clear preview - future enhancement  
                  // setHoveredTheme(null)
                }}
                role="option"
                aria-selected={t.id === themeId}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm text-[var(--ds-terminal-fg)]">
                      {t.id === themeId && '[✓] '}
                      {t.name}
                    </div>
                    {t.description && (
                      <div className="text-xs text-[var(--ds-terminal-dim)] mt-1">
                        {t.description}
                      </div>
                    )}
                  </div>
                  
                  {/* Preview dots */}
                  {showPreview && (
                    <div className="flex gap-1">
                      <span
                        className="w-3 h-3 rounded-full border border-[var(--ds-border-default)]"
                        style={{ backgroundColor: t.colors.terminalBg }}
                      />
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: t.colors.terminalFg }}
                      />
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: t.colors.agentCoding }}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {/* ASCII Footer */}
          <div className="ds-dropdown-footer px-3 py-2 border-t border-[var(--ds-border-default)]">
            <div className="text-xs text-[var(--ds-terminal-dim)] font-mono">
              ↑↓ Navigate • Enter Select • Esc Close
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Compact theme switcher for toolbar/header use
export function DSThemeSwitcherCompact({ className }: { className?: string }) {
  const { theme, setTheme, availableThemes } = useDSTheme();
  const [isChanging, setIsChanging] = useState(false);
  
  const handleCycle = () => {
    setIsChanging(true);
    const currentIndex = availableThemes.findIndex(t => t.id === theme.id);
    const nextIndex = (currentIndex + 1) % availableThemes.length;
    setTheme(availableThemes[nextIndex].id);
    
    setTimeout(() => setIsChanging(false), 500);
  };
  
  return (
    <button
      className={cn(
        'ds-theme-compact',
        'flex items-center gap-1',
        'px-2 py-1',
        'text-[var(--ds-terminal-dim)]',
        'font-mono text-xs',
        'rounded',
        'transition-all duration-200',
        'hover:text-[var(--ds-terminal-fg)]',
        'hover:bg-[var(--ds-bg-elevated)]',
        className
      )}
      onClick={handleCycle}
      aria-label={`Current theme: ${theme.name}. Click to cycle themes.`}
    >
      {isChanging ? (
        <DSAgentASCIISpinner type="dots" size="sm" />
      ) : (
        <span>◐</span>
      )}
      <span>{theme.id}</span>
    </button>
  );
}
"use client";

import React, { forwardRef, useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface DSInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  showCursor?: boolean;
}

interface DSTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  autoResize?: boolean;
  minRows?: number;
  maxRows?: number;
}

/**
 * DSInput - Terminal-style input component with cursor
 * 
 * Replaces shadcn Input with WebTUI-inspired terminal aesthetics
 */
export const DSInput = forwardRef<HTMLInputElement, DSInputProps>(
  (
    {
      className,
      label,
      error,
      hint,
      icon,
      iconPosition = 'left',
      showCursor = true,
      disabled,
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = useState(false);
    
    return (
      <div className="ds-input-wrapper">
        {label && (
          <label className="ds-input-label block text-sm font-mono text-[var(--ds-terminal-bright)] mb-1">
            {label}
          </label>
        )}
        
        <div className="ds-input-container relative">
          {icon && iconPosition === 'left' && (
            <span className="ds-input-icon absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ds-terminal-dim)]">
              {icon}
            </span>
          )}
          
          <input
            ref={ref}
            className={cn(
              'ds-input',
              'w-full',
              'font-mono text-sm',
              'bg-[var(--ds-terminal-bg)]',
              'text-[var(--ds-terminal-fg)]',
              'border border-[var(--ds-border-default)]',
              'px-3 py-2',
              'transition-all duration-200',
              'focus:outline-none',
              'focus:border-[var(--ds-border-active)]',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              error && 'border-[var(--ds-agent-error)]',
              icon && iconPosition === 'left' && 'pl-10',
              icon && iconPosition === 'right' && 'pr-10',
              showCursor && isFocused && 'ds-input-focused',
              className
            )}
            disabled={disabled}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            {...props}
          />
          
          {icon && iconPosition === 'right' && (
            <span className="ds-input-icon absolute right-3 top-1/2 -translate-y-1/2 text-[var(--ds-terminal-dim)]">
              {icon}
            </span>
          )}
          
          {showCursor && isFocused && (
            <span className="ds-input-cursor absolute right-3 top-1/2 -translate-y-1/2 text-[var(--ds-terminal-fg)] animate-pulse pointer-events-none">
              _
            </span>
          )}
        </div>
        
        {hint && !error && (
          <p className="ds-input-hint text-xs font-mono text-[var(--ds-terminal-dim)] mt-1">
            {hint}
          </p>
        )}
        
        {error && (
          <p className="ds-input-error text-xs font-mono text-[var(--ds-agent-error)] mt-1">
            {error}
          </p>
        )}
      </div>
    );
  }
);

DSInput.displayName = 'DSInput';

/**
 * DSTextarea - Terminal-style textarea with auto-resize
 */
export const DSTextarea = forwardRef<HTMLTextAreaElement, DSTextareaProps>(
  (
    {
      className,
      label,
      error,
      hint,
      autoResize = true,
      minRows = 3,
      maxRows = 10,
      disabled,
      onChange,
      ...props
    },
    ref
  ) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [isFocused, setIsFocused] = useState(false);
    
    useEffect(() => {
      const textarea = ref || textareaRef.current;
      if (autoResize && textarea && 'current' in textarea && textarea.current) {
        const element = textarea.current;
        element.style.height = 'auto';
        const scrollHeight = element.scrollHeight;
        const minHeight = minRows * 24; // Approximate line height
        const maxHeight = maxRows * 24;
        element.style.height = `${Math.max(minHeight, Math.min(scrollHeight, maxHeight))}px`;
      }
    }, [props.value, autoResize, minRows, maxRows, ref]);
    
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange?.(e);
      
      if (autoResize) {
        const element = e.target;
        element.style.height = 'auto';
        const scrollHeight = element.scrollHeight;
        const minHeight = minRows * 24;
        const maxHeight = maxRows * 24;
        element.style.height = `${Math.max(minHeight, Math.min(scrollHeight, maxHeight))}px`;
      }
    };
    
    return (
      <div className="ds-textarea-wrapper">
        {label && (
          <label className="ds-textarea-label block text-sm font-mono text-[var(--ds-terminal-bright)] mb-1">
            {label}
          </label>
        )}
        
        <div className="ds-textarea-container relative">
          <textarea
            ref={ref || textareaRef}
            className={cn(
              'ds-textarea',
              'w-full',
              'font-mono text-sm',
              'bg-[var(--ds-terminal-bg)]',
              'text-[var(--ds-terminal-fg)]',
              'border border-[var(--ds-border-default)]',
              'px-3 py-2',
              'resize-none',
              'transition-all duration-200',
              'focus:outline-none',
              'focus:border-[var(--ds-border-active)]',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              error && 'border-[var(--ds-agent-error)]',
              className
            )}
            disabled={disabled}
            onChange={handleChange}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            rows={minRows}
            {...props}
          />
          
          {isFocused && (
            <span className="ds-textarea-cursor absolute bottom-2 right-3 text-[var(--ds-terminal-fg)] animate-pulse pointer-events-none">
              _
            </span>
          )}
        </div>
        
        {hint && !error && (
          <p className="ds-textarea-hint text-xs font-mono text-[var(--ds-terminal-dim)] mt-1">
            {hint}
          </p>
        )}
        
        {error && (
          <p className="ds-textarea-error text-xs font-mono text-[var(--ds-agent-error)] mt-1">
            {error}
          </p>
        )}
      </div>
    );
  }
);

DSTextarea.displayName = 'DSTextarea';

/**
 * DSTerminalPrompt - Terminal-style input with prompt symbol
 */
export function DSTerminalPrompt({
  prompt = '$',
  value,
  onChange,
  onSubmit,
  placeholder = 'Enter command...',
  className
}: {
  prompt?: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.(value);
    }
  };
  
  return (
    <div className={cn('ds-terminal-prompt flex items-center gap-2', className)}>
      <span className="ds-prompt-symbol text-[var(--ds-terminal-bright)] font-mono">
        {prompt}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={cn(
          'flex-1',
          'bg-transparent',
          'border-none',
          'outline-none',
          'font-mono text-sm',
          'text-[var(--ds-terminal-fg)]',
          'placeholder-[var(--ds-terminal-dim)]'
        )}
      />
    </div>
  );
}
"use client";

import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface DSButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  asChild?: boolean;
}

/**
 * DSButton - Terminal-style button component with ASCII aesthetics
 * 
 * Replaces shadcn Button with WebTUI-inspired terminal styling
 */
export const DSButton = forwardRef<HTMLButtonElement, DSButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      icon,
      iconPosition = 'left',
      loading = false,
      disabled,
      children,
      asChild = false,
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: 'px-2 py-1 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base'
    };
    
    const variantClasses = {
      primary: cn(
        'bg-[var(--ds-terminal-fg)] text-[var(--ds-terminal-bg)]',
        'hover:bg-[var(--ds-terminal-bright)]',
        'border border-[var(--ds-terminal-fg)]'
      ),
      secondary: cn(
        'bg-transparent text-[var(--ds-terminal-fg)]',
        'hover:bg-[var(--ds-bg-elevated)]',
        'border border-[var(--ds-border-default)]',
        'hover:border-[var(--ds-border-active)]'
      ),
      ghost: cn(
        'bg-transparent text-[var(--ds-terminal-fg)]',
        'hover:bg-[var(--ds-bg-elevated)]',
        'hover:text-[var(--ds-terminal-bright)]'
      ),
      danger: cn(
        'bg-[var(--ds-agent-error)] text-[var(--ds-terminal-bg)]',
        'hover:opacity-90',
        'border border-[var(--ds-agent-error)]'
      ),
      success: cn(
        'bg-[var(--ds-agent-final)] text-[var(--ds-terminal-bg)]',
        'hover:opacity-90',
        'border border-[var(--ds-agent-final)]'
      )
    };
    
    const isDisabled = disabled || loading;
    
    const buttonContent = (
      <>
        {loading && (
          <span className="ds-button-loader mr-2">
            <span className="animate-spin inline-block">⟳</span>
          </span>
        )}
        {icon && iconPosition === 'left' && !loading && (
          <span className="ds-button-icon mr-2">{icon}</span>
        )}
        {children}
        {icon && iconPosition === 'right' && !loading && (
          <span className="ds-button-icon ml-2">{icon}</span>
        )}
      </>
    );
    
    if (asChild) {
      return (
        <span
          className={cn(
            'ds-button',
            'inline-flex items-center justify-center',
            'font-mono font-medium',
            'transition-all duration-200',
            'cursor-pointer',
            'focus:outline-none',
            'focus:ring-2 focus:ring-[var(--ds-terminal-fg)] focus:ring-offset-2',
            'focus:ring-offset-[var(--ds-terminal-bg)]',
            sizeClasses[size],
            variantClasses[variant],
            fullWidth && 'w-full',
            isDisabled && 'opacity-50 cursor-not-allowed',
            className
          )}
          {...props}
        >
          {buttonContent}
        </span>
      );
    }
    
    return (
      <button
        ref={ref}
        className={cn(
          'ds-button',
          'inline-flex items-center justify-center',
          'font-mono font-medium',
          'transition-all duration-200',
          'cursor-pointer',
          'focus:outline-none',
          'focus:border-[var(--ds-border-active)]',
          sizeClasses[size],
          variantClasses[variant],
          fullWidth && 'w-full',
          isDisabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {buttonContent}
      </button>
    );
  }
);

DSButton.displayName = 'DSButton';

// Terminal-style button with ASCII brackets
export function DSTerminalButton({
  children,
  onClick,
  className,
  ...props
}: DSButtonProps) {
  return (
    <DSButton
      onClick={onClick}
      className={cn('ds-terminal-button', className)}
      {...props}
    >
      <span className="text-[var(--ds-terminal-dim)]">[</span>
      {children}
      <span className="text-[var(--ds-terminal-dim)]">]</span>
    </DSButton>
  );
}

// Icon-only button variant
export function DSIconButton({
  icon,
  'aria-label': ariaLabel,
  className,
  size = 'sm',
  ...props
}: Omit<DSButtonProps, 'children'> & { 'aria-label': string }) {
  return (
    <DSButton
      size={size}
      className={cn(
        'ds-icon-button',
        'aspect-square',
        'p-0',
        size === 'sm' && 'w-8 h-8',
        size === 'md' && 'w-10 h-10',
        size === 'lg' && 'w-12 h-12',
        className
      )}
      aria-label={ariaLabel}
      {...props}
    >
      {icon}
    </DSButton>
  );
}

// Button group component
export function DSButtonGroup({
  children,
  className
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'ds-button-group',
        'inline-flex',
        '[&>*:not(:first-child)]:ml-[-1px]',
        '[&>*:first-child]:rounded-r-none',
        '[&>*:last-child]:rounded-l-none',
        '[&>*:not(:first-child):not(:last-child)]:rounded-none',
        className
      )}
    >
      {children}
    </div>
  );
}
"use client";

import React from 'react';
import { cn } from '@/lib/utils';

interface DSCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'ghost';
  border?: 'single' | 'double' | 'rounded' | 'none';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

interface DSCardHeaderProps {
  children: React.ReactNode;
  className?: string;
  showDivider?: boolean;
}

interface DSCardTitleProps {
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

interface DSCardContentProps {
  children: React.ReactNode;
  className?: string;
}

interface DSCardFooterProps {
  children: React.ReactNode;
  className?: string;
  showDivider?: boolean;
}

/**
 * DSCard - Terminal-style card component with ASCII borders
 * 
 * Replaces shadcn Card with WebTUI-inspired terminal aesthetics
 */
export function DSCard({
  children,
  className,
  variant = 'default',
  border = 'single',
  padding = 'md'
}: DSCardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-2',
    md: 'p-4',
    lg: 'p-6'
  };
  
  const variantClasses = {
    default: 'bg-[var(--ds-terminal-bg)] border-[var(--ds-border-default)]',
    elevated: 'bg-[var(--ds-bg-elevated)] border-[var(--ds-border-active)]',
    ghost: 'bg-transparent border-transparent'
  };
  
  const borderClasses = {
    single: 'border',
    double: 'border-2',
    rounded: 'border rounded-lg',
    none: ''
  };
  
  return (
    <div
      className={cn(
        'ds-card',
        'font-mono',
        'text-[var(--ds-terminal-fg)]',
        'transition-all duration-200',
        paddingClasses[padding],
        variantClasses[variant],
        borderClasses[border],
        className
      )}
      data-variant={variant}
    >
      {children}
    </div>
  );
}

/**
 * DSCardHeader - Card header section with optional divider
 */
export function DSCardHeader({
  children,
  className,
  showDivider = true
}: DSCardHeaderProps) {
  return (
    <div
      className={cn(
        'ds-card-header',
        showDivider && 'border-b border-[var(--ds-border-default)] pb-3 mb-3',
        className
      )}
    >
      {children}
    </div>
  );
}

/**
 * DSCardTitle - Card title with optional icon
 */
export function DSCardTitle({
  children,
  className,
  icon
}: DSCardTitleProps) {
  return (
    <h3
      className={cn(
        'ds-card-title',
        'text-[var(--ds-terminal-bright)]',
        'font-mono font-bold',
        'text-base',
        'flex items-center gap-2',
        className
      )}
    >
      {icon && <span className="ds-card-icon">{icon}</span>}
      {children}
    </h3>
  );
}

/**
 * DSCardContent - Main content area of the card
 */
export function DSCardContent({
  children,
  className
}: DSCardContentProps) {
  return (
    <div
      className={cn(
        'ds-card-content',
        'text-[var(--ds-terminal-fg)]',
        className
      )}
    >
      {children}
    </div>
  );
}

/**
 * DSCardFooter - Card footer with optional divider
 */
export function DSCardFooter({
  children,
  className,
  showDivider = true
}: DSCardFooterProps) {
  return (
    <div
      className={cn(
        'ds-card-footer',
        showDivider && 'border-t border-[var(--ds-border-default)] pt-3 mt-3',
        'flex items-center justify-between',
        className
      )}
    >
      {children}
    </div>
  );
}

// Composite card with ASCII border decoration
export function DSTerminalCard({
  title,
  children,
  className,
  showControls = true
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
  showControls?: boolean;
}) {
  return (
    <div className={cn('ds-terminal-card', className)}>
      {/* ASCII Border Top */}
      <div className="ds-terminal-border-top text-[var(--ds-terminal-dim)] text-xs font-mono">
        ╔══════════════════════════════════════════════════════════════╗
      </div>
      
      {/* Terminal Header */}
      {(title || showControls) && (
        <div className="ds-terminal-header flex items-center justify-between px-4 py-2 bg-[var(--ds-bg-elevated)]">
          {title && (
            <span className="text-[var(--ds-terminal-bright)] font-mono font-bold">
              {title}
            </span>
          )}
          {showControls && (
            <div className="ds-terminal-controls flex gap-2 text-[var(--ds-terminal-dim)]">
              <span className="hover:text-[var(--ds-terminal-fg)] cursor-pointer">[-]</span>
              <span className="hover:text-[var(--ds-terminal-fg)] cursor-pointer">[□]</span>
              <span className="hover:text-[var(--ds-agent-error)] cursor-pointer">[×]</span>
            </div>
          )}
        </div>
      )}
      
      {/* Content */}
      <div className="ds-terminal-card-content p-4 bg-[var(--ds-terminal-bg)]">
        {children}
      </div>
      
      {/* ASCII Border Bottom */}
      <div className="ds-terminal-border-bottom text-[var(--ds-terminal-dim)] text-xs font-mono">
        ╚══════════════════════════════════════════════════════════════╝
      </div>
    </div>
  );
}
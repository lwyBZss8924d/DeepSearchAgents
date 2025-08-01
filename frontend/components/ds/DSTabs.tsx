"use client";

import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface DSTabsProps {
  children: React.ReactNode;
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

interface DSTabsListProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'underline' | 'boxed';
}

interface DSTabsTriggerProps {
  children: React.ReactNode;
  value: string;
  className?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}

interface DSTabsContentProps {
  children: React.ReactNode;
  value: string;
  className?: string;
  forceMount?: boolean;
}

/**
 * DSTabs - Terminal-style tabs component with ASCII styling
 * 
 * Replaces shadcn Tabs with WebTUI-inspired terminal aesthetics
 */
export function DSTabs({
  children,
  defaultValue,
  value: controlledValue,
  onValueChange,
  className,
  orientation = 'horizontal'
}: DSTabsProps) {
  const [uncontrolledValue, setUncontrolledValue] = useState(defaultValue);
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : uncontrolledValue;
  
  const handleValueChange = (newValue: string) => {
    if (!isControlled) {
      setUncontrolledValue(newValue);
    }
    onValueChange?.(newValue);
  };
  
  return (
    <TabsContext.Provider value={{ value, onValueChange: handleValueChange }}>
      <div
        className={cn(
          'ds-tabs',
          orientation === 'vertical' && 'flex gap-4',
          className
        )}
        data-orientation={orientation}
      >
        {children}
      </div>
    </TabsContext.Provider>
  );
}

/**
 * DSTabsList - Container for tab triggers
 */
export function DSTabsList({
  children,
  className,
  variant = 'default'
}: DSTabsListProps) {
  const variantClasses = {
    default: 'border-b border-[var(--ds-border-default)]',
    underline: 'border-b-2 border-[var(--ds-border-default)]',
    boxed: 'bg-[var(--ds-bg-elevated)] border border-[var(--ds-border-default)] rounded p-1'
  };
  
  return (
    <div
      className={cn(
        'ds-tabs-list',
        'flex items-center gap-2',
        'font-mono',
        variantClasses[variant],
        className
      )}
      role="tablist"
    >
      {children}
    </div>
  );
}

/**
 * DSTabsTrigger - Individual tab trigger button
 */
export function DSTabsTrigger({
  children,
  value,
  className,
  disabled = false,
  icon
}: DSTabsTriggerProps) {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('DSTabsTrigger must be used within DSTabs');
  }
  
  const { value: selectedValue, onValueChange } = context;
  const isSelected = selectedValue === value;
  const triggerRef = useRef<HTMLButtonElement>(null);
  
  // Add underline animation
  useEffect(() => {
    if (isSelected && triggerRef.current) {
      triggerRef.current.scrollIntoView({ block: 'nearest', inline: 'center' });
    }
  }, [isSelected]);
  
  return (
    <button
      ref={triggerRef}
      role="tab"
      aria-selected={isSelected}
      aria-controls={`tab-content-${value}`}
      tabIndex={isSelected ? 0 : -1}
      disabled={disabled}
      onClick={() => !disabled && onValueChange(value)}
      className={cn(
        'ds-tab-trigger',
        'px-3 py-2',
        'text-sm',
        'font-mono',
        'transition-all duration-200',
        'relative',
        'focus:outline-none',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        isSelected ? [
          'text-[var(--ds-terminal-bright)]',
          'after:content-[""]',
          'after:absolute',
          'after:bottom-0',
          'after:left-0',
          'after:right-0',
          'after:h-[2px]',
          'after:bg-[var(--ds-terminal-fg)]',
          'after:animate-[ds-tab-underline_200ms_ease-out]'
        ] : [
          'text-[var(--ds-terminal-dim)]',
          'hover:text-[var(--ds-terminal-fg)]'
        ],
        className
      )}
    >
      {icon && <span className="mr-1">{icon}</span>}
      {children}
      {isSelected && (
        <span className="ml-2 text-[var(--ds-terminal-fg)] animate-pulse">_</span>
      )}
    </button>
  );
}

/**
 * DSTabsContent - Content panel for each tab
 */
export function DSTabsContent({
  children,
  value,
  className,
  forceMount = false
}: DSTabsContentProps) {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('DSTabsContent must be used within DSTabs');
  }
  
  const { value: selectedValue } = context;
  const isSelected = selectedValue === value;
  
  if (!forceMount && !isSelected) {
    return null;
  }
  
  return (
    <div
      role="tabpanel"
      aria-labelledby={`tab-trigger-${value}`}
      id={`tab-content-${value}`}
      tabIndex={0}
      hidden={!isSelected}
      className={cn(
        'ds-tab-content',
        'mt-4',
        'font-mono',
        'text-[var(--ds-terminal-fg)]',
        'focus:outline-none',
        'animate-[ds-tab-content-fade-in_200ms_ease-out]',
        className
      )}
    >
      {children}
    </div>
  );
}

// Terminal-style tab component with ASCII decorations
export function DSTerminalTabs({
  tabs,
  defaultValue,
  className
}: {
  tabs: Array<{
    value: string;
    label: string;
    icon?: React.ReactNode;
    content: React.ReactNode;
    disabled?: boolean;
  }>;
  defaultValue: string;
  className?: string;
}) {
  const [activeTab, setActiveTab] = useState(defaultValue);
  
  return (
    <div className={cn('ds-terminal-tabs', className)}>
      {/* ASCII Header */}
      <div className="ds-terminal-tabs-header text-[var(--ds-terminal-dim)] text-xs font-mono mb-2">
        ┌─────────────────────────────────────────┐
      </div>
      
      <DSTabs defaultValue={defaultValue} value={activeTab} onValueChange={setActiveTab}>
        <DSTabsList variant="underline">
          {tabs.map((tab) => (
            <DSTabsTrigger
              key={tab.value}
              value={tab.value}
              icon={tab.icon}
              disabled={tab.disabled}
            >
              {tab.label}
            </DSTabsTrigger>
          ))}
        </DSTabsList>
        
        {tabs.map((tab) => (
          <DSTabsContent key={tab.value} value={tab.value}>
            {tab.content}
          </DSTabsContent>
        ))}
      </DSTabs>
      
      {/* ASCII Footer */}
      <div className="ds-terminal-tabs-footer text-[var(--ds-terminal-dim)] text-xs font-mono mt-4">
        └─────────────────────────────────────────┘
      </div>
    </div>
  );
}
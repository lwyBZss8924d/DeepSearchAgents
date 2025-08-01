"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { DSThemeSwitcherCompact } from './DSThemeSwitcher'

interface DSAgentTerminalContainerProps {
  children: React.ReactNode
  title?: string
  showHeader?: boolean
  className?: string
}

/**
 * DSAgentTerminalContainer - WebTUI-based terminal container
 * 
 * Main container component that provides terminal-style background
 * and layout using character-based grid system
 */
export function DSAgentTerminalContainer({ 
  children,
  title = 'DeepSearchAgents Terminal',
  showHeader = true,
  className 
}: DSAgentTerminalContainerProps) {
  return (
    <div
      terminal-container-="main"
      className={cn(
        'ds-terminal-container',
        className
      )}
    >
      {showHeader && (
        <div 
          className="ds-terminal-header"
          box-="double-horizontal"
        >
          <div className="ds-terminal-title">
            <span className="ds-terminal-title-icon">▣</span>
            <span className="ds-terminal-title-text">{title}</span>
          </div>
          <div className="ds-terminal-controls">
            <DSThemeSwitcherCompact className="mr-2" />
          </div>
        </div>
      )}
      
      <div className="ds-terminal-body">
        {children}
      </div>
    </div>
  )
}
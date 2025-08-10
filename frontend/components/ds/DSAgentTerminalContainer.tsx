"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { DSThemeSwitcherCompact } from './DSThemeSwitcher'
import { DSAgentTUILogoInline } from './DSAgentTUILogo'
import { TerminalSystemIcon } from '../terminal-icons'

interface DSAgentTerminalContainerProps {
  children: React.ReactNode
  title?: string
  showHeader?: boolean
  className?: string
  headerContent?: React.ReactNode
  headerRightContent?: React.ReactNode
}

/**
 * DSAgentTerminalContainer - WebTUI-based terminal container
 * 
 * Main container component that provides terminal-style background
 * and layout using character-based grid system
 */
export function DSAgentTerminalContainer({ 
  children,
  title = 'HAL-9000™ CONSOLE',
  showHeader = true,
  className,
  headerContent,
  headerRightContent
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
          <div className="ds-terminal-header-left flex items-center gap-2">
            <span className="ds-terminal-title-text text-sm opacity-60">{title}</span>
            <TerminalSystemIcon size={16} className="text-[var(--ds-terminal-dim)] opacity-60" />
            {headerContent && (
              <>
                <span className="text-[var(--ds-terminal-dim)] opacity-60 mx-2">|</span>
                {headerContent}
              </>
            )}
          </div>
          <div className="ds-terminal-header-right flex items-center gap-2">
            <DSAgentTUILogoInline />
            {headerRightContent && (
              <>
                <span className="text-[var(--ds-terminal-dim)] opacity-60 mx-2">|</span>
                {headerRightContent}
              </>
            )}
            <div className="ds-terminal-controls">
              <DSThemeSwitcherCompact className="mr-2" />
            </div>
          </div>
        </div>
      )}
      
      <div className="ds-terminal-body">
        {children}
      </div>
    </div>
  )
}
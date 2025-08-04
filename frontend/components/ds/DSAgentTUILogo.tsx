"use client";

import React from 'react';
import { cn } from '@/lib/utils';

interface DSAgentTUILogoProps {
  className?: string;
  variant?: 'default' | 'compact' | 'banner';
  animate?: boolean;
}

/**
 * DSAgentTUILogo - Authentic TUI-style ASCII art logo
 * 
 * Uses Unicode block characters inspired by Charm's Crush design
 * Pure terminal aesthetic with no web-style effects
 */
export function DSAgentTUILogo({ 
  className, 
  variant = 'default',
  animate = true 
}: DSAgentTUILogoProps) {
  
  // Full ASCII art logo using Unicode block characters like Crush
  const fullLogo = `╱╱╱╱╱╱                                                        ╱╱╱╱╱╱
      █▀▀▄  ▄▀▀▀  ▄▀▀▀  ▄▀▀▄                                      
      █  █  ▀▀▀▄  █     █▀▀█   DeepResearch CodeAct Agent  v0.3.3 
      ▀▀▀   ▀▀▀▀  ▀▀▀▀  ▀  ▀                                      
                                                                    
╱╱╱╱╱╱  Code is Action!  ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱
                                                                    
  ◐ Large Task     ○ Small Task                                    
                                                                    
  ▶ Type your query below to start searching                       
  ▶ Agent will process your request step by step                   
  ▶ Real-time streaming shows agent's thinking                     
                                                                    
╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱`;

  // Compact ASCII logo for headers (single line like Crush)
  const compactLogo = `Charm™ DSCA ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱`;

  // Banner style with diagonal lines
  const bannerLogo = `╱╱╱╱╱ DSCAgent™ v0.3.3 ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱`;

  const logos = {
    default: fullLogo,
    compact: compactLogo,
    banner: bannerLogo
  };

  return (
    <div className={cn('ds-tui-logo font-mono whitespace-pre', className)}>
      <div className={cn(
        'ds-logo-ascii',
        animate && variant === 'default' && 'animate-pulse'
      )}>
        {variant === 'default' ? (
          <pre className="text-[var(--ds-terminal-bright)]">
            {logos[variant]}
          </pre>
        ) : variant === 'compact' ? (
          <div className="inline-block">
            <pre className="text-sm text-[var(--ds-terminal-fg)]">
              {logos[variant]}
            </pre>
          </div>
        ) : (
          <div className="text-[var(--ds-terminal-dim)]">
            {logos[variant]}
          </div>
        )}
      </div>
    </div>
  );
}

// Inline compact version for tight spaces (like Crush's sidebar)
export function DSAgentTUILogoInline({ className }: { className?: string }) {
  return (
    <span className={cn('font-mono', className)}>
      <span className="text-[var(--ds-terminal-bright)] font-bold">dsca</span>
      {' '}
      <span className="text-[var(--ds-terminal-fg)]">code-act</span>
    </span>
  );
}

// Animated loading version
export function DSAgentTUILogoLoading({ className }: { className?: string }) {
  const [frame, setFrame] = React.useState(0);
  const frames = ['◐', '◓', '◑', '◒'];
  
  React.useEffect(() => {
    const interval = setInterval(() => {
      setFrame((f) => (f + 1) % frames.length);
    }, 200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={cn('font-mono flex items-center gap-2', className)}>
      <span className="text-[var(--ds-terminal-bright)]">{frames[frame]}</span>
      <span className="text-[var(--ds-terminal-fg)]">DSCAgent™</span>
      <span className="text-[var(--ds-terminal-dim)]">Loading...</span>
    </div>
  );
}

// Export all variants
export { 
  DSAgentTUILogo as default
};
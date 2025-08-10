"use client";

import { cn } from '@/lib/utils';
import { DSAgentASCIISpinner } from './DSAgentASCIISpinner';
import { DSAgentTypewriter } from './DSAgentStateTransition';
import { progressBars } from './DSAgentASCIIAnimations';

interface DSAgentLoadingIndicatorProps {
  text?: string;
  progress?: number;
  showProgress?: boolean;
  spinnerType?: Parameters<typeof DSAgentASCIISpinner>[0]['type'];
  className?: string;
}

/**
 * DSAgentLoadingIndicator - Terminal-style loading indicator
 * 
 * Combines spinner, typewriter text, and optional progress bar
 * for various loading states in the application
 */
export function DSAgentLoadingIndicator({
  text = 'Loading...',
  progress,
  showProgress = false,
  spinnerType = 'dots',
  className
}: DSAgentLoadingIndicatorProps) {
  return (
    <div 
      className={cn(
        'ds-loading-indicator',
        'flex flex-col items-center justify-center',
        'gap-4 p-8',
        'text-[var(--ds-terminal-fg)]',
        className
      )}
    >
      {/* Main spinner */}
      <DSAgentASCIISpinner 
        type={spinnerType}
        size="lg"
        aria-label={text}
      />
      
      {/* Loading text with typewriter effect */}
      <DSAgentTypewriter 
        text={text}
        speed={50}
        cursor={true}
        className="text-sm"
      />
      
      {/* Progress bar if enabled */}
      {showProgress && progress !== undefined && (
        <div className="ds-progress-container w-full max-w-xs">
          <div className="text-center mb-2 text-xs text-[var(--ds-terminal-dim)]">
            {progressBars.percentage(progress)}
          </div>
          <div className="ds-progress-bar h-1 bg-[var(--ds-bg-elevated)] rounded overflow-hidden">
            <div 
              className="h-full bg-[var(--ds-terminal-fg)] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
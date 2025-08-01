"use client";

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { 
  bootSequence, 
  asciiLogo, 
  animationTimings,
  progressBars 
} from './DSAgentASCIIAnimations';

interface DSAgentBootSequenceProps {
  onComplete?: () => void;
  skipDelay?: number;
  className?: string;
}

/**
 * DSAgentBootSequence - Terminal-style boot animation
 * 
 * Displays a boot sequence animation when the app loads
 * Includes ASCII logo reveal and system check animations
 */
export function DSAgentBootSequence({
  onComplete,
  skipDelay = 3000,
  className
}: DSAgentBootSequenceProps) {
  const [currentLine, setCurrentLine] = useState(0);
  const [logoRevealed, setLogoRevealed] = useState(false);
  const [progress, setProgress] = useState(0);
  const [skipped, setSkipped] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  
  useEffect(() => {
    if (skipped) {
      setLines(bootSequence);
      setCurrentLine(bootSequence.length);
      setLogoRevealed(true);
      setProgress(100);
      if (onComplete) {
        setTimeout(onComplete, 500);
      }
      return;
    }
    
    // Animate boot sequence
    const timer = setInterval(() => {
      setCurrentLine((prev) => {
        const next = prev + 1;
        
        // Update displayed lines
        if (next <= bootSequence.length) {
          setLines(bootSequence.slice(0, next));
        }
        
        // Reveal logo after title
        if (next === 2) {
          setLogoRevealed(true);
        }
        
        // Update progress
        const progressValue = Math.floor((next / bootSequence.length) * 100);
        setProgress(progressValue);
        
        // Complete sequence
        if (next >= bootSequence.length) {
          clearInterval(timer);
          if (onComplete) {
            setTimeout(onComplete, animationTimings.boot.complete);
          }
        }
        
        return next;
      });
    }, animationTimings.boot.lineDelay);
    
    // Allow skip after delay
    const skipTimer = setTimeout(() => {
      // User can press any key to skip
    }, skipDelay);
    
    return () => {
      clearInterval(timer);
      clearTimeout(skipTimer);
    };
  }, [skipped, onComplete, skipDelay]);
  
  // Handle skip on click or keypress
  const handleSkip = () => {
    if (currentLine < bootSequence.length) {
      setSkipped(true);
    }
  };
  
  return (
    <div 
      className={cn(
        'ds-boot-sequence',
        'fixed inset-0 z-50',
        'bg-[var(--ds-terminal-bg)]',
        'text-[var(--ds-terminal-fg)]',
        'font-mono text-sm',
        'flex flex-col items-center justify-center',
        'cursor-pointer select-none',
        className
      )}
      onClick={handleSkip}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          handleSkip();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="Boot sequence. Click or press any key to skip."
    >
      {/* ASCII Logo with reveal animation */}
      <div 
        className={cn(
          'ds-boot-logo mb-8 whitespace-pre',
          'transition-opacity duration-1000',
          logoRevealed ? 'opacity-100' : 'opacity-0'
        )}
      >
        <pre className="text-[var(--ds-terminal-bright)]">
          {asciiLogo}
        </pre>
      </div>
      
      {/* Boot sequence lines */}
      <div className="ds-boot-lines w-full max-w-2xl px-8">
        {lines.map((line, index) => (
          <div
            key={index}
            className={cn(
              'ds-boot-line',
              'mb-1 opacity-0 animate-fadeIn',
              {
                'text-[var(--ds-terminal-bright)]': line.startsWith('[OK]'),
                'text-[var(--ds-agent-error)]': line.startsWith('[FAIL]'),
                'text-[var(--ds-terminal-dim)]': index === 0
              }
            )}
            style={{
              animationDelay: `${index * 50}ms`
            }}
          >
            {line}
          </div>
        ))}
        
        {/* Blinking cursor */}
        {currentLine < bootSequence.length && (
          <span className="ds-boot-cursor animate-pulse">_</span>
        )}
      </div>
      
      {/* Progress bar */}
      <div className="ds-boot-progress mt-8 w-full max-w-md px-8">
        <div className="text-center mb-2 text-[var(--ds-terminal-dim)]">
          {progressBars.percentage(progress)}
        </div>
        <div className="ds-progress-bar h-2 bg-[var(--ds-bg-elevated)] rounded overflow-hidden">
          <div 
            className="h-full bg-[var(--ds-terminal-fg)] transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      
      {/* Skip hint */}
      {currentLine < bootSequence.length && currentLine > 2 && (
        <div className="ds-boot-skip absolute bottom-4 text-xs text-[var(--ds-terminal-dim)]">
          Press any key to skip...
        </div>
      )}
    </div>
  );
}
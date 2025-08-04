"use client";

import React from 'react';
import { cn } from '@/lib/utils';

interface DSAgentGlamorousLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  animate?: boolean;
}

/**
 * DSAgentGlamorousLogo - Crush-inspired animated gradient logo
 * 
 * Features animated gradient text with diagonal line effects
 * Responsive sizing and glamorous color transitions
 */
export function DSAgentGlamorousLogo({ 
  className, 
  size = 'md',
  animate = true 
}: DSAgentGlamorousLogoProps) {
  const sizeClasses = {
    sm: 'text-2xl',
    md: 'text-4xl',
    lg: 'text-6xl'
  };

  return (
    <div className={cn('ds-glamorous-logo relative', className)}>
      {/* Diagonal line effects */}
      <div className="absolute inset-0 overflow-hidden opacity-30">
        <div className={cn(
          "ds-diagonal-lines",
          animate && "animate-slide"
        )}>
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="diagonal-line"
              style={{
                position: 'absolute',
                width: '200%',
                height: '1px',
                background: 'linear-gradient(90deg, transparent, var(--ds-agent-planning), var(--ds-agent-coding), transparent)',
                transform: `translateY(${i * 20}px) rotate(-45deg)`,
                left: '-50%',
                top: `${i * 15}%`,
                animation: animate ? `diagonal-slide ${3 + i * 0.5}s linear infinite` : undefined
              }}
            />
          ))}
        </div>
      </div>

      {/* Main logo text with gradient */}
      <h1 className={cn(
        'ds-logo-text relative font-mono font-bold tracking-tight',
        sizeClasses[size],
        animate && 'animate-gradient'
      )}>
        <span className="inline-block">Deep</span>
        <span className="inline-block ml-1">Research</span>
        <span className="inline-block ml-1">CodeAct</span>
        <span className="inline-block ml-1 text-[var(--ds-agent-coding)]">Agent</span>
      </h1>

      {/* Subtitle with typewriter effect */}
      <p className={cn(
        'ds-logo-subtitle font-mono text-sm mt-2 opacity-80',
        size === 'lg' && 'text-base',
        animate && 'animate-typewriter'
      )}>
        <span className="text-[var(--ds-terminal-dim)]">{">"}</span>
        <span className="ml-1">Code is Action!</span>
        <span className={cn(
          'inline-block w-2 h-4 ml-1 bg-current',
          animate && 'animate-blink'
        )} />
      </p>

      <style jsx>{`
        .ds-glamorous-logo {
          --gradient-start: var(--ds-agent-planning, #00bfff);
          --gradient-end: var(--ds-agent-coding, #00ff41);
          --gradient-accent: var(--ds-agent-running, #00ffff);
        }

        .ds-logo-text {
          background: linear-gradient(
            135deg,
            var(--gradient-start) 0%,
            var(--gradient-accent) 50%,
            var(--gradient-end) 100%
          );
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-shadow: 0 0 30px rgba(0, 255, 65, 0.3);
        }

        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient-shift 3s ease infinite;
        }

        @keyframes gradient-shift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }

        @keyframes diagonal-slide {
          0% { transform: translateX(-100%) translateY(var(--slide-y, 0)) rotate(-45deg); }
          100% { transform: translateX(100%) translateY(var(--slide-y, 0)) rotate(-45deg); }
        }

        @keyframes typewriter {
          from { width: 0; }
          to { width: 100%; }
        }

        @keyframes blink {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }

        .animate-typewriter {
          overflow: hidden;
          white-space: nowrap;
          animation: typewriter 2s steps(20) 1s forwards;
        }

        .animate-blink {
          animation: blink 1s step-end infinite;
        }
      `}</style>
    </div>
  );
}

// Compact version for header/toolbar use
export function DSAgentGlamorousLogoCompact({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 font-mono', className)}>
      <span className="text-xl font-bold bg-gradient-to-r from-[var(--ds-agent-planning)] to-[var(--ds-agent-coding)] bg-clip-text text-transparent">
        DSCA
      </span>
      <span className="text-xs text-[var(--ds-terminal-dim)]">v0.3.3</span>
    </div>
  );
}
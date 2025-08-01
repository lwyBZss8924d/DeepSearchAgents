"use client";

import { useEffect, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  asciiSpinners, 
  getSpinnerFrames, 
  animationTimings
} from './DSAgentASCIIAnimations';
import type { AgentState } from './DSAgentStateBadge';

interface DSAgentASCIISpinnerProps {
  type?: keyof typeof asciiSpinners;
  state?: AgentState;
  speed?: number;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  'aria-label'?: string;
}

// Map agent states to spinner types
const stateSpinnerMap: Record<string, keyof typeof asciiSpinners> = {
  planning: 'dots',
  thinking: 'pulse',
  coding: 'terminal',
  running: 'arrows',
  loading: 'classic',
  default: 'classic'
};

/**
 * DSAgentASCIISpinner - Animated ASCII spinner component
 * 
 * Displays various ASCII spinner animations based on type or agent state
 * Uses requestAnimationFrame for smooth 60fps animations
 */
export function DSAgentASCIISpinner({
  type,
  state,
  speed,
  color,
  size = 'md',
  className,
  'aria-label': ariaLabel = 'Loading'
}: DSAgentASCIISpinnerProps) {
  // Determine spinner type based on state or explicit type
  const spinnerType = type || (state ? stateSpinnerMap[state] || 'classic' : 'classic');
  const frames = getSpinnerFrames(spinnerType);
  const defaultSpeed = animationTimings.spinner[spinnerType as keyof typeof animationTimings.spinner] || 200;
  const animSpeed = speed || defaultSpeed;
  
  const [currentFrame, setCurrentFrame] = useState(0);
  const animationRef = useRef<number>();
  const lastUpdateRef = useRef<number>(0);
  
  useEffect(() => {
    let mounted = true;
    
    const animate = (timestamp: number) => {
      if (!mounted) return;
      
      // Control frame rate based on speed
      if (timestamp - lastUpdateRef.current >= animSpeed) {
        setCurrentFrame((prev) => (prev + 1) % frames.length);
        lastUpdateRef.current = timestamp;
      }
      
      animationRef.current = requestAnimationFrame(animate);
    };
    
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      mounted = false;
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [frames.length, animSpeed]);
  
  // Size classes
  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base'
  };
  
  // Color based on state
  const stateColors = {
    planning: 'var(--ds-agent-planning)',
    thinking: 'var(--ds-agent-thinking)',
    coding: 'var(--ds-agent-coding)',
    running: 'var(--ds-agent-running)',
    error: 'var(--ds-agent-error)'
  };
  
  const spinnerColor = color || (state && state in stateColors ? stateColors[state as keyof typeof stateColors] : undefined);
  
  return (
    <span
      className={cn(
        'ds-ascii-spinner-container inline-block',
        sizeClasses[size],
        className
      )}
      role="status"
      aria-label={ariaLabel}
      style={{
        color: spinnerColor,
        fontFamily: 'var(--ds-font-mono)'
      }}
    >
      <span className="ds-ascii-spinner-frame">
        {frames[currentFrame]}
      </span>
      <span className="sr-only">{ariaLabel}</span>
    </span>
  );
}
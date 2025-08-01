"use client";

import { useEffect, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import { stateTransitions, animationTimings } from './DSAgentASCIIAnimations';
import type { AgentState } from './DSAgentStateBadge';

interface DSAgentStateTransitionProps {
  fromState?: AgentState;
  toState: AgentState;
  duration?: number;
  onComplete?: () => void;
  showParticles?: boolean;
  className?: string;
}

/**
 * DSAgentStateTransition - Animated state transition effects
 * 
 * Provides smooth transitions between agent states with
 * optional particle effects and typewriter animations
 */
export function DSAgentStateTransition({
  fromState,
  toState,
  duration,
  onComplete,
  showParticles = false,
  className
}: DSAgentStateTransitionProps) {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [particles, setParticles] = useState<Array<{ x: number; y: number; char: string }>>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const transitionDuration = duration || animationTimings.transition.state;
  
  useEffect(() => {
    if (!fromState || fromState === toState) {
      return;
    }
    
    setIsTransitioning(true);
    
    // Generate particle effects if enabled
    if (showParticles && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const newParticles = [];
      
      // Generate 5-10 particles
      const particleCount = Math.floor(Math.random() * 5) + 5;
      for (let i = 0; i < particleCount; i++) {
        const chars = ['*', '·', '+', '×', '°'];
        newParticles.push({
          x: Math.random() * rect.width,
          y: Math.random() * rect.height,
          char: chars[Math.floor(Math.random() * chars.length)]
        });
      }
      
      setParticles(newParticles);
    }
    
    // Complete transition
    const timer = setTimeout(() => {
      setIsTransitioning(false);
      setParticles([]);
      if (onComplete) {
        onComplete();
      }
    }, transitionDuration);
    
    return () => clearTimeout(timer);
  }, [fromState, toState, showParticles, transitionDuration, onComplete]);
  
  // Get transition icons
  const getTransitionIcon = (state: AgentState) => {
    const icons = stateTransitions[state as keyof typeof stateTransitions];
    return icons ? icons[0] : '●';
  };
  
  return (
    <div
      ref={containerRef}
      className={cn(
        'ds-state-transition relative inline-block',
        className
      )}
    >
      {/* State transition effect */}
      <div
        className={cn(
          'ds-transition-content',
          'transition-all duration-500',
          isTransitioning && 'opacity-50 scale-95'
        )}
      >
        <span className="ds-transition-icon">
          {getTransitionIcon(toState)}
        </span>
      </div>
      
      {/* Particle effects */}
      {showParticles && particles.map((particle, index) => (
        <span
          key={index}
          className="ds-particle absolute pointer-events-none"
          style={{
            left: `${particle.x}px`,
            top: `${particle.y}px`,
            animation: `ds-particle-float ${transitionDuration}ms ease-out forwards`
          }}
        >
          {particle.char}
        </span>
      ))}
    </div>
  );
}

// Typewriter effect for state changes
interface DSAgentTypewriterProps {
  text: string;
  speed?: number;
  cursor?: boolean;
  onComplete?: () => void;
  className?: string;
}

export function DSAgentTypewriter({
  text,
  speed = 50,
  cursor = true,
  onComplete,
  className
}: DSAgentTypewriterProps) {
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  
  useEffect(() => {
    setDisplayText('');
    setIsTyping(true);
    
    let index = 0;
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(timer);
        if (onComplete) {
          onComplete();
        }
      }
    }, speed);
    
    return () => clearInterval(timer);
  }, [text, speed, onComplete]);
  
  return (
    <span className={cn('ds-typewriter', className)}>
      {displayText}
      {cursor && isTyping && (
        <span className="ds-typewriter-cursor animate-pulse">_</span>
      )}
    </span>
  );
}
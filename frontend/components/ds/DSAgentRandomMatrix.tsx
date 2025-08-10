"use client";

import { useEffect, useState, useRef } from 'react';
import { generateRandomASCII } from './DSAgentASCIIAnimations';

interface DSAgentRandomMatrixProps {
  isActive: boolean;
  className?: string;
}

/**
 * DSAgentRandomMatrix - 15-character random ASCII animation
 * 
 * Shows blinking random characters when agent is active
 * Disappears when agent returns to standby
 */
export function DSAgentRandomMatrix({ isActive, className }: DSAgentRandomMatrixProps) {
  const [currentFrame, setCurrentFrame] = useState('...............');
  const animationRef = useRef<number>(0);
  const lastUpdateRef = useRef<number>(0);
  
  useEffect(() => {
    if (!isActive) {
      setCurrentFrame('...............');
      return;
    }
    
    let mounted = true;
    
    const animate = (timestamp: number) => {
      if (!mounted) return;
      
      // Update every 200ms
      if (timestamp - lastUpdateRef.current >= 200) {
        setCurrentFrame(generateRandomASCII());
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
  }, [isActive]);
  
  // Always render the element, but hide it when inactive
  return (
    <span 
      className={`ds-random-matrix ${className || ''}`}
      style={{ 
        fontFamily: 'var(--ds-font-mono)',
        letterSpacing: '0.05em',
        visibility: isActive ? 'visible' : 'hidden',
        opacity: isActive ? 1 : 0
      }}
    >
      {currentFrame}
    </span>
  );
}
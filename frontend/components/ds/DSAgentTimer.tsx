"use client";

import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/app-context';

interface DSAgentTimerProps {
  className?: string;
}

/**
 * DSAgentTimer - Real-time timer showing elapsed time since agent started
 * 
 * Displays time in format (XXs) or (XXm XXs) for longer durations
 * Only renders when agent is actively running (not standby)
 */
export function DSAgentTimer({ className }: DSAgentTimerProps) {
  const { state } = useAppContext();
  const { agentStartTime } = state;
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  
  useEffect(() => {
    // Only run timer when we have a start time
    if (!agentStartTime) {
      setElapsedSeconds(0);
      return;
    }
    
    // Calculate initial elapsed time
    const updateElapsed = () => {
      const now = Date.now();
      const elapsed = Math.floor((now - agentStartTime) / 1000);
      setElapsedSeconds(elapsed);
    };
    
    // Update immediately
    updateElapsed();
    
    // Update every second
    const interval = setInterval(updateElapsed, 1000);
    
    return () => clearInterval(interval);
  }, [agentStartTime]);
  
  // Format time display
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    }
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };
  
  // Always render the element, but hide it when inactive
  return (
    <span 
      className={`ds-agent-timer ${className || ''}`}
      style={{ 
        visibility: agentStartTime ? 'visible' : 'hidden',
        opacity: agentStartTime ? 1 : 0
      }}
    >
      {agentStartTime ? formatTime(elapsedSeconds) : '0s'}
    </span>
  );
}
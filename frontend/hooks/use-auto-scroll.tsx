"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

interface UseAutoScrollOptions {
  enabled?: boolean;
  smooth?: boolean;
  threshold?: number;
  pauseOnHover?: boolean;
}

/**
 * Custom hook for auto-scrolling functionality
 * Automatically scrolls to bottom when new content is added
 * Includes pause-on-hover and manual scroll detection
 */
export function useAutoScroll({
  enabled = true,
  smooth = true,
  threshold = 100,
  pauseOnHover = true
}: UseAutoScrollOptions = {}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  
  // Check if scrolled to bottom
  const checkIsAtBottom = useCallback(() => {
    if (!scrollRef.current) return true;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    
    return distanceFromBottom <= threshold;
  }, [threshold]);
  
  // Scroll to bottom
  const scrollToBottom = useCallback((force = false) => {
    if (!scrollRef.current || !enabled) return;
    if (!force && (isPaused || (pauseOnHover && isHovered))) return;
    if (!force && !isAtBottom) return;
    
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: smooth ? 'smooth' : 'instant'
    });
  }, [enabled, isPaused, isHovered, isAtBottom, smooth, pauseOnHover]);
  
  // Handle scroll events
  const handleScroll = useCallback(() => {
    const atBottom = checkIsAtBottom();
    setIsAtBottom(atBottom);
    
    // Auto-resume if scrolled to bottom manually
    if (atBottom && isPaused) {
      setIsPaused(false);
    }
  }, [checkIsAtBottom, isPaused]);
  
  // Handle mouse enter/leave
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);
  
  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
    // Auto-scroll when mouse leaves if at bottom
    if (isAtBottom) {
      scrollToBottom();
    }
  }, [isAtBottom, scrollToBottom]);
  
  // Set up event listeners
  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    
    element.addEventListener('scroll', handleScroll, { passive: true });
    
    if (pauseOnHover) {
      element.addEventListener('mouseenter', handleMouseEnter);
      element.addEventListener('mouseleave', handleMouseLeave);
    }
    
    return () => {
      element.removeEventListener('scroll', handleScroll);
      if (pauseOnHover) {
        element.removeEventListener('mouseenter', handleMouseEnter);
        element.removeEventListener('mouseleave', handleMouseLeave);
      }
    };
  }, [handleScroll, handleMouseEnter, handleMouseLeave, pauseOnHover]);
  
  // Auto-scroll on content changes
  useEffect(() => {
    scrollToBottom();
  });
  
  return {
    scrollRef,
    isAtBottom,
    isPaused,
    isHovered,
    scrollToBottom: () => scrollToBottom(true),
    pauseAutoScroll: () => setIsPaused(true),
    resumeAutoScroll: () => setIsPaused(false),
    togglePause: () => setIsPaused(p => !p)
  };
}

// Scroll-to-bottom button component
interface ScrollToBottomButtonProps {
  isVisible: boolean;
  onClick: () => void;
  className?: string;
}

export function ScrollToBottomButton({ 
  isVisible, 
  onClick, 
  className = "" 
}: ScrollToBottomButtonProps) {
  if (!isVisible) return null;
  
  return (
    <button
      className={`ds-scroll-to-bottom ${className}`}
      onClick={onClick}
      aria-label="Scroll to bottom"
    >
      <span className="ds-scroll-icon">[↓]</span>
      <span className="ds-scroll-text">Bottom</span>
    </button>
  );
}
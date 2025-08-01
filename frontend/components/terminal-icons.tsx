"use client";

import React from 'react';
import { cn } from '@/lib/utils';

export type IconName = 
  | 'send' 
  | 'loader' 
  | 'monitor' 
  | 'code' 
  | 'terminal'
  | 'wifi'
  | 'wifi-off'
  | 'chevron-down'
  | 'chevron-up'
  | 'chevron-left'
  | 'chevron-right'
  | 'eye'
  | 'eye-off'
  | 'bug'
  | 'check'
  | 'x'
  | 'plus'
  | 'minus'
  | 'copy'
  | 'clear'
  | 'play'
  | 'stop';

interface TerminalIconProps {
  name: IconName;
  size?: number;
  className?: string;
  animate?: boolean;
}

// Terminal-style ASCII/Unicode icon mappings
const iconMap: Record<IconName, string> = {
  send: '→',
  loader: '◌',
  monitor: '◾',
  code: '</>',
  terminal: '>_',
  wifi: '◉',
  'wifi-off': '◎',
  'chevron-down': '▼',
  'chevron-up': '▲',
  'chevron-left': '◀',
  'chevron-right': '▶',
  eye: '◉',
  'eye-off': '⊗',
  bug: '[BUG]',
  check: '✓',
  x: '✗',
  plus: '+',
  minus: '-',
  copy: '⧉',
  clear: '⌫',
  play: '▶',
  stop: '■',
};

// ASCII spinner frames for loader animation
const spinnerFrames = ['[|]', '[/]', '[-]', '[\\]'];

export function TerminalIcon({ 
  name, 
  size = 16, 
  className, 
  animate = false 
}: TerminalIconProps) {
  const [frame, setFrame] = React.useState(0);
  
  // Handle spinner animation
  React.useEffect(() => {
    if (name === 'loader' && animate) {
      const interval = setInterval(() => {
        setFrame((prev) => (prev + 1) % spinnerFrames.length);
      }, 200);
      return () => clearInterval(interval);
    }
  }, [name, animate]);
  
  // Get the icon character
  const getIcon = () => {
    if (name === 'loader' && animate) {
      return spinnerFrames[frame];
    }
    return iconMap[name] || '?';
  };
  
  const fontSize = size <= 16 ? '1em' : `${size / 16}em`;
  
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center',
        'font-mono select-none',
        className
      )}
      style={{ 
        fontSize,
        width: 'auto',
        height: 'auto',
        lineHeight: 1
      }}
      role="img"
      aria-label={name}
    >
      {getIcon()}
    </span>
  );
}

// Convenience components for common icons
export const SendIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="send" {...props} />;

export const LoaderIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="loader" animate {...props} />;

export const MonitorIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="monitor" {...props} />;

export const CodeIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="code" {...props} />;

export const TerminalIconComponent = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="terminal" {...props} />;

export const WifiIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="wifi" {...props} />;

export const WifiOffIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="wifi-off" {...props} />;

export const ChevronDownIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="chevron-down" {...props} />;

export const ChevronUpIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="chevron-up" {...props} />;

export const ChevronLeftIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="chevron-left" {...props} />;

export const ChevronRightIcon = (props: Omit<TerminalIconProps, 'name'>) => 
  <TerminalIcon name="chevron-right" {...props} />;
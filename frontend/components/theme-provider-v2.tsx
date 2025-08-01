"use client";

import * as React from "react";
import { DSThemeProvider } from "@/components/ds/DSThemeProvider";

/**
 * ThemeProvider v2 - Wrapper that uses DSThemeProvider
 * 
 * This replaces the existing next-themes provider with our
 * terminal-themed DS provider while maintaining compatibility
 */
interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: string;
  forcedTheme?: string;
  [key: string]: unknown;
}

export function ThemeProvider({
  children,
  ...props
}: ThemeProviderProps) {
  // Extract any relevant props that might be passed
  const defaultTheme = props.forcedTheme || props.defaultTheme || 'classic';
  
  return (
    <DSThemeProvider defaultTheme={defaultTheme}>
      {children}
    </DSThemeProvider>
  );
}
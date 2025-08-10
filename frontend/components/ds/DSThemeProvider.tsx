"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { themes, getTheme, getThemeCSSVariables, type DSTheme } from './DSThemeDefinitions';

interface DSThemeContextType {
  theme: DSTheme;
  themeId: string;
  setTheme: (themeId: string) => void;
  availableThemes: DSTheme[];
}

const DSThemeContext = createContext<DSThemeContextType | undefined>(undefined);

interface DSThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: string;
  storageKey?: string;
}

/**
 * DSThemeProvider - Terminal theme management for DeepSearchAgents
 * 
 * Provides theme context and handles theme switching with
 * localStorage persistence and CSS variable updates
 */
export function DSThemeProvider({
  children,
  defaultTheme = 'classic',
  storageKey = 'ds-theme'
}: DSThemeProviderProps) {
  const [themeId, setThemeId] = useState<string>(defaultTheme);
  const [theme, setThemeState] = useState<DSTheme>(getTheme(defaultTheme));
  
  // Load theme from localStorage on mount
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem(storageKey);
      if (savedTheme && themes[savedTheme]) {
        setThemeId(savedTheme);
        setThemeState(getTheme(savedTheme));
      }
    } catch (error) {
      console.warn('Failed to load theme from localStorage:', error);
    }
  }, [storageKey]);
  
  // Apply theme CSS variables
  useEffect(() => {
    const root = document.documentElement;
    const cssVars = getThemeCSSVariables(theme);
    
    // Apply all CSS variables
    Object.entries(cssVars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    
    // Set theme attribute for CSS targeting
    root.setAttribute('data-ds-theme', theme.id);
    
    // Update body classes for compatibility
    document.body.classList.remove(...Object.keys(themes).map(id => `theme-${id}`));
    document.body.classList.add(`theme-${theme.id}`);
    
    return () => {
      // Cleanup on unmount
      root.removeAttribute('data-ds-theme');
    };
  }, [theme]);
  
  // Theme setter with persistence
  const setTheme = useCallback((newThemeId: string) => {
    if (!themes[newThemeId]) {
      console.warn(`Theme "${newThemeId}" not found, falling back to classic`);
      newThemeId = 'classic';
    }
    
    setThemeId(newThemeId);
    setThemeState(getTheme(newThemeId));
    
    // Save to localStorage
    try {
      localStorage.setItem(storageKey, newThemeId);
    } catch (error) {
      console.warn('Failed to save theme to localStorage:', error);
    }
  }, [storageKey]);
  
  // Get all available themes
  const availableThemes = Object.values(themes);
  
  return (
    <DSThemeContext.Provider
      value={{
        theme,
        themeId,
        setTheme,
        availableThemes
      }}
    >
      {children}
    </DSThemeContext.Provider>
  );
}

// Hook to use theme context
export function useDSTheme() {
  const context = useContext(DSThemeContext);
  if (context === undefined) {
    throw new Error('useDSTheme must be used within a DSThemeProvider');
  }
  return context;
}

// Hook to get current theme
export function useTheme() {
  const { theme } = useDSTheme();
  return theme;
}

// Hook to get theme setter
export function useThemeSetter() {
  const { setTheme } = useDSTheme();
  return setTheme;
}
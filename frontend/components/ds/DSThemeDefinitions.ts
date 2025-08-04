/**
 * DSThemeDefinitions - Terminal theme collection for DeepSearchAgents
 * 
 * Defines various terminal-inspired color themes with consistent
 * structure for easy switching and customization
 */

// Theme definitions for DeepSearchAgents terminal UI

export interface DSTheme {
  id: string;
  name: string;
  description?: string;
  colors: {
    // Terminal base colors
    terminalBg: string;
    terminalFg: string;
    terminalBright: string;
    terminalDim: string;
    
    // UI colors
    borderDefault: string;
    borderActive: string;
    bgElevated: string;
    bgCode: string;
    
    // Agent state colors
    agentPlanning: string;
    agentThinking: string;
    agentCoding: string;
    agentRunning: string;
    agentFinal: string;
    agentError: string;
  };
  fonts?: {
    mono: string[];
  };
}

// Classic Terminal Theme (Default)
export const classicTheme: DSTheme = {
  id: 'classic',
  name: 'Classic Terminal',
  description: 'Modern terminal with improved contrast',
  colors: {
    terminalBg: '#0d1117',
    terminalFg: '#58a6ff',
    terminalBright: '#79c0ff',
    terminalDim: '#388bfd',
    borderDefault: '#30363d',
    borderActive: '#58a6ff',
    bgElevated: '#161b22',
    bgCode: '#0d1117',
    agentPlanning: '#58a6ff',
    agentThinking: '#d29922',
    agentCoding: '#3fb950',
    agentRunning: '#39c5cf',
    agentFinal: '#3fb950',
    agentError: '#f85149'
  }
};

// Solarized Dark Theme
export const solarizedDarkTheme: DSTheme = {
  id: 'solarized-dark',
  name: 'Solarized Dark',
  description: 'Popular theme with carefully chosen contrast ratios',
  colors: {
    terminalBg: '#002b36',
    terminalFg: '#839496',
    terminalBright: '#93a1a1',
    terminalDim: '#657b83',
    borderDefault: '#073642',
    borderActive: '#268bd2',
    bgElevated: '#073642',
    bgCode: '#002b36',
    agentPlanning: '#268bd2',
    agentThinking: '#b58900',
    agentCoding: '#859900',
    agentRunning: '#2aa198',
    agentFinal: '#859900',
    agentError: '#dc322f'
  }
};

// Catppuccin Mocha Theme
export const catppuccinMochaTheme: DSTheme = {
  id: 'catppuccin-mocha',
  name: 'Catppuccin Mocha',
  description: 'Soft pastel colors with a warm feel',
  colors: {
    terminalBg: '#1e1e2e',
    terminalFg: '#cdd6f4',
    terminalBright: '#f5e0dc',
    terminalDim: '#a6adc8',
    borderDefault: '#313244',
    borderActive: '#89b4fa',
    bgElevated: '#232334',
    bgCode: '#181825',
    agentPlanning: '#89b4fa',
    agentThinking: '#f9e2af',
    agentCoding: '#a6e3a1',
    agentRunning: '#94e2d5',
    agentFinal: '#a6e3a1',
    agentError: '#f38ba8'
  }
};

// Nord Theme
export const nordTheme: DSTheme = {
  id: 'nord',
  name: 'Nord',
  description: 'Cool, muted palette inspired by the Arctic',
  colors: {
    terminalBg: '#2e3440',
    terminalFg: '#eceff4',
    terminalBright: '#e5e9f0',
    terminalDim: '#d8dee9',
    borderDefault: '#434c5e',
    borderActive: '#88c0d0',
    bgElevated: '#323845',
    bgCode: '#242933',
    agentPlanning: '#81a1c1',
    agentThinking: '#ebcb8b',
    agentCoding: '#a3be8c',
    agentRunning: '#88c0d0',
    agentFinal: '#a3be8c',
    agentError: '#bf616a'
  }
};


// High Contrast Theme
export const highContrastTheme: DSTheme = {
  id: 'high-contrast',
  name: 'High Contrast',
  description: 'Maximum contrast for accessibility',
  colors: {
    terminalBg: '#000000',
    terminalFg: '#ffffff',
    terminalBright: '#ffffff',
    terminalDim: '#c0c0c0',
    borderDefault: '#808080',
    borderActive: '#ffffff',
    bgElevated: '#1a1a1a',
    bgCode: '#0a0a0a',
    agentPlanning: '#00bfff',
    agentThinking: '#ffff00',
    agentCoding: '#00ff00',
    agentRunning: '#00ffff',
    agentFinal: '#00ff00',
    agentError: '#ff0000'
  }
};

// Matrix Theme
export const matrixTheme: DSTheme = {
  id: 'matrix',
  name: 'Matrix',
  description: 'Green phosphor terminal from the movies',
  colors: {
    terminalBg: '#000000',
    terminalFg: '#00ff00',
    terminalBright: '#50ff50',
    terminalDim: '#008000',
    borderDefault: '#004000',
    borderActive: '#00ff00',
    bgElevated: '#001000',
    bgCode: '#000500',
    agentPlanning: '#00ff00',
    agentThinking: '#00ff00',
    agentCoding: '#00ff00',
    agentRunning: '#00ff00',
    agentFinal: '#50ff50',
    agentError: '#ff0000'
  }
};

// Synthwave Theme
export const synthwaveTheme: DSTheme = {
  id: 'synthwave',
  name: 'Synthwave',
  description: 'Retro 80s neon aesthetic with vibrant gradients',
  colors: {
    terminalBg: '#0f0e17',
    terminalFg: '#ff006e',
    terminalBright: '#ff4098',
    terminalDim: '#cc0055',
    borderDefault: '#ff006e',
    borderActive: '#00ffff',
    bgElevated: '#1a1625',
    bgCode: '#160f22',
    agentPlanning: '#3a86ff',
    agentThinking: '#ffaa00',
    agentCoding: '#00ff88',
    agentRunning: '#00ffff',
    agentFinal: '#ff00ff',
    agentError: '#ff006e'
  }
};

// Cyberpunk Theme
export const cyberpunkTheme: DSTheme = {
  id: 'cyberpunk',
  name: 'Cyberpunk',
  description: 'Futuristic theme with glitch effects and bold contrasts',
  colors: {
    terminalBg: '#000814',
    terminalFg: '#ffd60a',
    terminalBright: '#ffee32',
    terminalDim: '#fcbf49',
    borderDefault: '#ffd60a',
    borderActive: '#06ffa5',
    bgElevated: '#001d3d',
    bgCode: '#000814',
    agentPlanning: '#00b4d8',
    agentThinking: '#ffd60a',
    agentCoding: '#06ffa5',
    agentRunning: '#00b4d8',
    agentFinal: '#06ffa5',
    agentError: '#ff1053'
  }
};

// Miami Theme
export const miamiTheme: DSTheme = {
  id: 'miami',
  name: 'Miami Vice',
  description: 'Sunset-inspired colors with tropical vibes',
  colors: {
    terminalBg: '#1a0033',
    terminalFg: '#f72585',
    terminalBright: '#ff006e',
    terminalDim: '#c9184a',
    borderDefault: '#f72585',
    borderActive: '#06ffa5',
    bgElevated: '#240046',
    bgCode: '#10002b',
    agentPlanning: '#7209b7',
    agentThinking: '#ffb700',
    agentCoding: '#06ffa5',
    agentRunning: '#4cc9f0',
    agentFinal: '#06ffa5',
    agentError: '#f72585'
  }
};

// Theme collection
export const themes: Record<string, DSTheme> = {
  classic: classicTheme,
  'catppuccin-mocha': catppuccinMochaTheme,
  nord: nordTheme,
  'solarized-dark': solarizedDarkTheme,
  'high-contrast': highContrastTheme,
  matrix: matrixTheme,
  synthwave: synthwaveTheme,
  cyberpunk: cyberpunkTheme,
  miami: miamiTheme
};

// Get theme by ID with fallback to classic
export function getTheme(themeId: string): DSTheme {
  return themes[themeId] || classicTheme;
}

// Theme CSS variable mapping
export function getThemeCSSVariables(theme: DSTheme): Record<string, string> {
  return {
    '--ds-terminal-bg': theme.colors.terminalBg,
    '--ds-terminal-fg': theme.colors.terminalFg,
    '--ds-terminal-bright': theme.colors.terminalBright,
    '--ds-terminal-dim': theme.colors.terminalDim,
    '--ds-border-default': theme.colors.borderDefault,
    '--ds-border-active': theme.colors.borderActive,
    '--ds-bg-elevated': theme.colors.bgElevated,
    '--ds-bg-code': theme.colors.bgCode,
    '--ds-agent-planning': theme.colors.agentPlanning,
    '--ds-agent-thinking': theme.colors.agentThinking,
    '--ds-agent-coding': theme.colors.agentCoding,
    '--ds-agent-running': theme.colors.agentRunning,
    '--ds-agent-final': theme.colors.agentFinal,
    '--ds-agent-error': theme.colors.agentError,
    
    // Map to existing design tokens for compatibility
    '--background': theme.colors.terminalBg,
    '--foreground': theme.colors.terminalFg,
    '--primary': theme.colors.terminalFg,
    '--primary-foreground': theme.colors.terminalBg,
    '--border': theme.colors.borderDefault,
    '--muted': theme.colors.terminalDim,
    '--muted-foreground': theme.colors.terminalDim
  };
}
"use client";

/**
 * DSAgentASCIIAnimations - Collection of ASCII animations for agent states
 * 
 * Provides various spinner types, progress bars, and animated effects
 * to enhance the terminal aesthetic of the DeepSearchAgents UI
 */

// ASCII spinner collections
export const asciiSpinners = {
  classic: ['|', '/', '-', '\\'],
  wheel: ['◊', '◈', '◉', '◎', '◍', '◌', '○', '◯', '⭕', '〇', '◦', '∘', '·', '∙', '•', '●', '◉', '◈', '◊'],
  dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
  blueprint: ['◆', '◇', '◈', '⬡', '⬢', '⬣', '⬤', '◉', '◎', '◍', '◌', '○', '◌', '◍', '◎', '◉', '⬤', '⬣', '⬢', '⬡', '◈', '◇', '◆'],
  blocks: ['▖', '▘', '▝', '▗'],
  arrows: ['↑', '→', '↓', '←'],
  gears: ['■', '▪', '▫', '□', '▢', '▣', '▤', '▥', '▦', '▧', '▨', '▩', '▨', '▧', '▦', '▥', '▤', '▣', '▢', '□', '▫', '▪', '■'],
  pulse: ['◐', '◓', '◑', '◒'],
  thought: ['◊', '◈', '◉', '◎', '◍', '◌', '○', '◯', '∘', '·', '∙', '•', '●', '○', '◌', '◍', '◎', '◉', '◈', '◊'],
  box: ['⎺', '⎻', '⎼', '⎽', '⎯'],
  brackets: ['[|]', '[/]', '[-]', '[\\]'],
  typewriter: ['✓', '√', '∨', '⌄', '˅', 'ˬ', '،', ',', '.', '·', '∙', '•', '●', '○', '◎', '◉', '◈', '◇', '◆', '◈', '◉', '◎', '○', '●', '•', '∙', '·', '.', ',', '،', 'ˬ', '˅', '⌄', '∨', '√', '✓'],
  bars: ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄', '▃', '▂'],
  binary: ['00', '01', '10', '11'],
  matrix: ['⠀', '⠁', '⠉', '⠛', '⠟', '⠿', '⡿', '⣿'],
  terminal: ['>  ', '>> ', '>>>', ' >>', '  >'],
  compilation: ['▶', '▷', '▸', '▹', '►', '⟩', '⟫', '》', '〉', '›', '>', '˃', 'ˬ', '¸', '˛', '¸', 'ˬ', '˃', '>', '›', '〉', '》', '⟫', '⟩', '►', '▹', '▸', '▷', '▶'],
  divining: ['✻', '✺', '✹', '✸', '✷', '✶', '+', '×', '∙', '·', '∙', '×', '+', '✶', '✷', '✸', '✹', '✺', '✻'],
  randomMatrix: [] // Will be generated dynamically
};

// Progress bar animations
export const progressBars = {
  classic: [
    '[    ]',
    '[=   ]',
    '[==  ]',
    '[=== ]',
    '[====]'
  ],
  dots: [
    '[·   ]',
    '[··  ]',
    '[··· ]',
    '[····]'
  ],
  blocks: [
    '[□□□□]',
    '[■□□□]',
    '[■■□□]',
    '[■■■□]',
    '[■■■■]'
  ],
  arrows: [
    '[>   ]',
    '[=> ]',
    '[==>]',
    '[===>]'
  ],
  percentage: (percent: number) => {
    const filled = Math.floor((percent / 100) * 20);
    const bar = '='.repeat(filled) + ' '.repeat(20 - filled);
    return `[${bar}] ${percent}%`;
  }
};

// Agent state transitions
export const stateTransitions = {
  planning: ['🤔', '💭', '📋', '✍️'],
  thinking: ['🤔', '💭', '💡'],
  coding: ['⚡', '💻', '⌨️', '🔧'],
  running: ['⚙️', '🔄', '⚡', '🚀'],
  success: ['✓', '✅', '🎉', '✨'],
  error: ['✗', '❌', '⚠️', '🔥']
};

// ASCII art patterns for backgrounds
export const asciiPatterns = {
  matrix: [
    '010110101',
    '110101001',
    '001011010',
    '101100101'
  ],
  dots: [
    '·.·.·.·.',
    '.·.·.·.·',
    '·.·.·.·.',
    '.·.·.·.·'
  ],
  lines: [
    '─┼─┼─┼─┼',
    '┼─┼─┼─┼─',
    '─┼─┼─┼─┼',
    '┼─┼─┼─┼─'
  ]
};

// Boot sequence frames
export const bootSequence = [
  'DeepSearchAgents v0.3.3',
  'Initializing terminal...',
  'Loading agent modules...',
  '[OK] Core system',
  '[OK] WebSocket connection',
  '[OK] Agent runtime',
  '[OK] Tool registry',
  'System ready.',
  'Code is Action! 🚀'
];

// ASCII logo (compact version)
export const asciiLogo = `
╔══════════════════════╗
║  DeepSearchAgents    ║
║  Code is Action! ⚡  ║
╚══════════════════════╝
`;

// Get spinner frames for a specific type
export function getSpinnerFrames(type: keyof typeof asciiSpinners): string[] {
  return asciiSpinners[type] || asciiSpinners.classic;
}

// Get progress bar for a specific type and progress
export function getProgressBar(type: keyof typeof progressBars, progress: number): string {
  if (type === 'percentage') {
    return progressBars.percentage(Math.min(100, Math.max(0, progress)));
  }
  
  const frames = progressBars[type as keyof Omit<typeof progressBars, 'percentage'>];
  if (!frames) return progressBars.classic[0];
  
  const index = Math.floor((progress / 100) * (frames.length - 1));
  return frames[Math.min(index, frames.length - 1)];
}

// Helper to cycle through animation frames
export function cycleFrames(frames: string[]): {
  currentFrame: string;
  nextFrame: () => string;
} {
  let index = 0;
  // Frame time could be used for advanced timing, keeping for future use
  // const frameTime = duration / frames.length;
  
  return {
    currentFrame: frames[0],
    nextFrame: () => {
      index = (index + 1) % frames.length;
      return frames[index];
    }
  };
}

// Generate random 15-character ASCII string
export function generateRandomASCII(): string {
  const chars = [
    // Dots and spaces (40% chance)
    '.', '.', '.', '.', ' ', ' ', ' ', ' ',
    // Alphanumeric (30% chance)
    'a', 'b', 'c', 'd', 'e', 'f', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    // Special characters (30% chance)
    '#', '%', '^', '*', '+', '~', '!', '@', '&', '(', ')', '[', ']', '{', '}',
    '?', '/', '\\', '|', '-', '_', '=', '<', '>', ':', ';', ',', '€', '£', '$'
  ];
  
  let result = '';
  for (let i = 0; i < 15; i++) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

// Generate frames for random matrix animation
export function generateRandomMatrixFrames(frameCount: number = 20): string[] {
  const frames: string[] = [];
  
  // Start with dots
  frames.push('...............');
  
  // Generate random frames
  for (let i = 0; i < frameCount - 2; i++) {
    frames.push(generateRandomASCII());
  }
  
  // End with dots
  frames.push('...............');
  
  return frames;
}

// Animation timing configurations
export const animationTimings = {
  spinner: {
    classic: 200,
    dots: 80,
    blocks: 150,
    arrows: 180,
    pulse: 250,
    terminal: 100,
    box: 200,
    brackets: 200,
    bars: 150,
    binary: 100,
    matrix: 120,
    divining: 150,  // Faster for smoother animation with more frames
    blueprint: 120,
    thought: 140,
    compilation: 100,
    gears: 110,
    typewriter: 90,
    wheel: 130,
    randomMatrix: 200
  },
  transition: {
    state: 500,
    fade: 300,
    slide: 400
  },
  boot: {
    lineDelay: 150,
    logoReveal: 1000,
    complete: 2000
  }
};
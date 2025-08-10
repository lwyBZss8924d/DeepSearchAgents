/**
 * DeepSearchAgents Design System (DS) Components
 * 
 * WebTUI-based components that implement the terminal-inspired
 * design language for transparent agent task execution visualization
 */

export { DSAgentMessageCard } from './DSAgentMessageCard'
export type { AgentCardType, AgentCardState } from './DSAgentMessageCard'

export { DSAgentStateBadge } from './DSAgentStateBadge'
export type { AgentState } from './DSAgentStateBadge'

export { DSAgentToolBadge } from './DSAgentToolBadge'

export { DSAgentCodeBlock } from './DSAgentCodeBlock'

export { DSAgentStreamingText, streamingProfiles } from './DSAgentStreamingText'
export type { StreamingMode } from './DSAgentStreamingText'

export { DSAgentTerminalContainer } from './DSAgentTerminalContainer'

export { DSAgentASCIISpinner } from './DSAgentASCIISpinner'

export { DSAgentBootSequence } from './DSAgentBootSequence'

export { DSAgentGlamorousLogo, DSAgentGlamorousLogoCompact } from './DSAgentGlamorousLogo'

export { 
  default as DSAgentTUILogo,
  DSAgentTUILogoInline,
  DSAgentTUILogoLoading
} from './DSAgentTUILogo'

export { DSAgentStateTransition, DSAgentTypewriter } from './DSAgentStateTransition'

export { 
  asciiSpinners, 
  progressBars, 
  stateTransitions,
  bootSequence,
  asciiLogo,
  animationTimings 
} from './DSAgentASCIIAnimations'

export { DSThemeProvider, useDSTheme, useTheme, useThemeSetter } from './DSThemeProvider'

export { DSThemeSwitcher, DSThemeSwitcherCompact } from './DSThemeSwitcher'

export { themes, getTheme, getThemeCSSVariables } from './DSThemeDefinitions'
export type { DSTheme } from './DSThemeDefinitions'

export { DSCard, DSCardHeader, DSCardTitle, DSCardContent, DSCardFooter, DSTerminalCard } from './DSCard'

export { DSTabs, DSTabsList, DSTabsTrigger, DSTabsContent, DSTerminalTabs } from './DSTabs'

export { DSButton, DSTerminalButton, DSIconButton, DSButtonGroup } from './DSButton'

export { DSInput, DSTextarea, DSTerminalPrompt } from './DSInput'
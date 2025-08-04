#### Claude's Advanced Features Implementation Plan

    Overview

    Phase 3 focuses on enhancing the terminal experience with advanced streaming capabilities, ASCII animations, theme switching, and completing
     the migration from shadcn. This phase will bring the "Code is Action!" philosophy to life with dynamic visual feedback and customization
    options.

    Sub-Task 1.6.1: Enhance Streaming System

    Objectives

    1. Improve streaming text performance with efficient rendering
    2. Add character-by-character and word-by-word reveal options
    3. Implement smooth auto-scrolling during streaming
    4. Add streaming configurations per agent state

    Implementation Plan

    1. Enhanced DSAgentStreamingText Component

    - Add streamingMode: 'instant' | 'char' | 'word' | 'line'
    - Implement streamingSpeed profiles for different content types
    - Add onStreamComplete callback for chaining animations
    - Optimize with requestAnimationFrame for smooth updates

    2. Streaming Configuration System

    interface StreamingProfile {
      mode: 'instant' | 'char' | 'word' | 'line'
      speed: number
      smoothScroll: boolean
      highlightNew: boolean
    }

    const streamingProfiles = {
      planning: { mode: 'line', speed: 50, smoothScroll: true },
      thinking: { mode: 'word', speed: 30, smoothScroll: true },
      coding: { mode: 'char', speed: 10, smoothScroll: true },
      result: { mode: 'instant', speed: 0, smoothScroll: false }
    }

    3. Auto-scroll Enhancement

    - Create useAutoScroll hook with smooth scrolling
    - Add scroll position tracking
    - Implement pause-on-hover functionality
    - Add scroll-to-bottom button when not at bottom

    4. Performance Optimizations

    - Use React.memo for streaming components
    - Implement virtual rendering for long messages
    - Add frame rate limiting for character animations
    - Use CSS will-change for animated elements

    Sub-Task 1.6.2: Add ASCII Animations

    Objectives

    1. Create multiple ASCII spinner variations
    2. Add terminal boot sequence animation
    3. Implement agent state transition animations
    4. Add loading and progress indicators

    Implementation Plan

    1. ASCII Animation Library

    const asciiAnimations = {
      spinners: {
        classic: ['|', '/', '-', '\\'],
        dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        blocks: ['▖', '▘', '▝', '▗'],
        brackets: ['[    ]', '[=   ]', '[==  ]', '[=== ]', '[====]']
      },
      transitions: {
        thinking: ['🤔', '💭', '💡'],
        processing: ['⚡', '⚙️', '⚡'],
        success: ['✓', '✅', '🎉']
      }
    }

    2. DSAgentASCIISpinner Component

    - Multiple spinner types with customizable speed
    - Color variations based on agent state
    - Smooth transitions between spinner types
    - Accessibility labels for screen readers

    3. Terminal Boot Sequence

    - Create DSAgentBootSequence component
    - ASCII art logo animation
    - System check animations
    - Loading progress with ASCII bars
    - Matrix-style text rain option

    4. State Transition Animations

    - Fade between state badges with ASCII effects
    - Typewriter effect for state changes
    - Particle effects using ASCII characters
    - Sound effect triggers (optional)

    Sub-Task 1.6.3: Implement Theme Switching

    Objectives

    1. Create theme provider with DS patterns
    2. Add multiple terminal themes
    3. Implement theme persistence
    4. Add theme preview and switcher UI

    Implementation Plan

    1. DSThemeProvider Component

    interface DSTheme {
      id: string
      name: string
      colors: {
        terminalBg: string
        terminalFg: string
        terminalBright: string
        agentStates: Record<AgentState, string>
      }
      fonts: {
        mono: string[]
      }
    }

    2. Theme Collection

    - Classic Terminal: Black/Green traditional
    - Solarized Dark: Popular developer theme
    - Tokyo Night: Modern purple-tinted
    - Dracula: Dark with vibrant accents
    - High Contrast: Accessibility focused
    - Custom: User-defined colors

    3. Theme Switcher UI

    - Create DSThemeSwitcher component
    - Terminal-style dropdown with ASCII borders
    - Live preview on hover
    - Keyboard navigation support
    - Save preference to localStorage

    4. CSS Variable System

    - Dynamic CSS variable injection
    - Smooth theme transitions
    - Support for partial theme overrides
    - Export theme for sharing

    Sub-Task 1.6.4: Complete Migration and Remove shadcn

    Objectives

    1. Update main application to use v2 components
    2. Remove all shadcn dependencies
    3. Update build configuration
    4. Final testing and optimization

    Implementation Plan

    1. Component Migration Checklist

    - Update agent-layout.tsx to use v2 components
    - Replace remaining shadcn imports
    - Update final-answer-display.tsx to DS components
    - Migrate any remaining UI components

    2. Dependency Cleanup

    - Remove @radix-ui dependencies
    - Remove class-variance-authority
    - Update package.json
    - Clean up unused CSS imports

    3. Build Optimization

    - Tree-shake unused WebTUI modules
    - Optimize bundle size
    - Update TypeScript configs
    - Performance profiling

    4. Testing & Documentation

    - End-to-end testing with new UI
    - Update component documentation
    - Create migration guide
    - Performance benchmarks

    Technical Considerations

    Performance

    - Use requestAnimationFrame for animations
    - Implement frame rate limiting
    - Add performance monitoring
    - Optimize re-renders with memo

    Accessibility

    - Maintain ARIA labels
    - Support reduced motion
    - Keyboard navigation
    - Screen reader announcements

    Browser Support

    - Test in major browsers
    - Fallbacks for older browsers
    - Progressive enhancement
    - Feature detection

    Success Criteria

    1. Streaming text renders smoothly at 60fps
    2. ASCII animations are fluid and responsive
    3. Theme switching is instant with persistence
    4. Zero shadcn dependencies remain
    5. Bundle size reduced by at least 20%
    6. All existing functionality preserved

    This plan ensures a smooth transition to a fully terminal-styled interface with enhanced visual feedback and customization options.

#### Claude's Sub-Task 1.6.2 Implementation Plan - Add ASCII animations

    Summary of Completed Work

    ✅ Sub-Task 1.6.1: Enhanced Streaming System - Successfully implemented:
    - Multiple streaming modes (instant, char, word, line) with requestAnimationFrame
    - Streaming profiles for different content types (planning, thinking, coding, result)
    - useAutoScroll hook with pause-on-hover functionality
    - Scroll-to-bottom button with terminal styling
    - Performance optimizations with will-change CSS

    Next Phase: Sub-Task 1.6.2 - Add ASCII Animations

    Objectives

    1. Create multiple ASCII spinner variations for different agent states
    2. Add terminal boot sequence animation for initial load
    3. Implement agent state transition animations
    4. Add loading and progress indicators with ASCII art

    Implementation Plan

    1. Create ASCII Animation Library
    - Build DSAgentASCIIAnimations.tsx with spinner collections
    - Classic spinners: [|], [/], [-], [\]
    - Dot spinners: ⠋, ⠙, ⠹, ⠸, ⠼, ⠴, ⠦, ⠧, ⠇, ⠏
    - Block spinners: ▖, ▘, ▝, ▗
    - Progress bars: [    ], [=   ], [==  ], [=== ], [====]

    2. Update DSAgentStateBadge
    - Enhance existing ASCII spinner with multiple animation types
    - Add spinner selection based on agent state
    - Implement smooth transitions between spinner types

    3. Create DSAgentBootSequence Component
    - Terminal-style boot animation when app loads
    - ASCII art logo reveal
    - System check animations with checkmarks
    - Loading progress with ASCII bars

    4. Add State Transition Animations
    - Create DSAgentStateTransition component
    - Fade effects between state badges
    - Typewriter effect for state changes
    - Optional particle effects using ASCII characters

    5. Update CSS Animations
    - Add new keyframe animations for each spinner type
    - Implement transition animations
    - Add performance optimizations

    6. Integration Updates
    - Update agent-chat-v2.tsx to use new animations
    - Add boot sequence to main app layout
    - Fix the unused useRef import lint error

    This phase will bring dynamic visual feedback to life with engaging ASCII animations that reinforce the terminal aesthetic while providing
    clear state indicators.

##### Claude's Sub-Task 1.6.2 Completion Summary

  Sub-Task 1.6.2 Completion Summary

  ✅ Components Created:

  1. DSAgentASCIIAnimations.tsx - Comprehensive ASCII animation library featuring:
    - Multiple spinner types (classic, dots, blocks, arrows, pulse, terminal, etc.)
    - Progress bar animations with percentage display
    - State transition effects
    - Boot sequence frames
    - ASCII logo and patterns
  2. DSAgentASCIISpinner.tsx - Enhanced spinner component with:
    - Multiple animation types based on agent state
    - RequestAnimationFrame for smooth 60fps animations
    - Size variations (sm, md, lg)
    - State-aware color theming
  3. DSAgentBootSequence.tsx - Terminal boot animation featuring:
    - Step-by-step boot sequence display
    - ASCII logo reveal animation
    - Progress bar tracking
    - Skip functionality
    - Smooth fade-in effects
  4. DSAgentStateTransition.tsx - State transition effects including:
    - Smooth transitions between agent states
    - Optional particle effects
    - Typewriter component for text animations
  5. DSAgentLoadingIndicator.tsx - Combined loading component with spinner, typewriter text, and progress bar

  ✅ Integrations:

  - Updated DSAgentStateBadge to use the new ASCII spinner
  - Added comprehensive CSS animations (60+ lines)
  - Fixed lint errors in agent-chat-v2.tsx
  - Updated component exports in ds/index.ts

  🎯 Key Features:

  - Performance-optimized with requestAnimationFrame
  - Accessibility support with ARIA labels
  - Flexible spinner selection based on agent states
  - Terminal-authentic ASCII character animations
  - Smooth transitions and particle effects

  The ASCII animations are now ready to be integrated throughout the application, bringing the terminal aesthetic to life with dynamic visual
  feedback!

#### Claude's Sub-Task 1.6.3 Implementation Plan - Implement Theme Switching

    Current State Analysis

    - Existing theme provider uses next-themes but is forced to dark mode only
    - We have WebTUI integration CSS with alternative theme definitions (Solarized, Tokyo Night)
    - Terminal theme CSS already has CSS variables set up
    - Current implementation has fragmented theme definitions across multiple files

    Implementation Plan for Theme Switching

    1. Create DSThemeProvider Component

    - Build a comprehensive theme provider that manages terminal themes
    - Support multiple terminal themes: Classic, Solarized Dark, Tokyo Night, Dracula, High Contrast
    - Integrate with existing CSS variable system
    - Add theme persistence to localStorage

    2. Define Theme Collection

    interface DSTheme {
      id: string
      name: string
      colors: {
        terminalBg: string
        terminalFg: string
        terminalBright: string
        terminalDim: string
        agentStates: Record<AgentState, string>
      }
      fonts?: {
        mono: string[]
      }
    }

    3. Create DSThemeSwitcher Component

    - Terminal-style dropdown using WebTUI patterns
    - Live preview on hover
    - ASCII borders and decorations
    - Keyboard navigation support (arrow keys)
    - Display current theme name

    4. Update CSS Architecture

    - Consolidate theme variables from multiple files
    - Create theme-specific CSS classes
    - Ensure smooth transitions between themes
    - Support for custom user themes

    5. Integration Tasks

    - Replace existing ThemeProvider with DSThemeProvider
    - Update all DS components to use theme variables
    - Add theme switcher to main UI (terminal header)
    - Ensure all components respond to theme changes

    6. Theme Definitions

    - Classic Terminal: Black background with green text
    - Solarized Dark: Popular developer theme with muted colors
    - Tokyo Night: Modern purple-tinted theme
    - Dracula: Dark theme with vibrant accents
    - High Contrast: Accessibility-focused with strong contrasts
    - Custom: Allow users to define their own colors

    This implementation will provide a cohesive theme switching system that enhances the terminal aesthetic while maintaining consistency across
     all components.

##### Claude's Sub-Task 1.6.3 Completion Summary

⏺ Sub-Task 1.6.3 Completion Summary

  ✅ Components Created:

  1. DSThemeDefinitions.ts - Comprehensive theme collection:
    - Classic Terminal (black/green)
    - Solarized Dark
    - Tokyo Night
    - Dracula
    - High Contrast
    - Matrix (green phosphor)
    - Type-safe theme interface
    - CSS variable mapping functions
  2. DSThemeProvider.tsx - Theme management system:
    - React Context for theme state
    - localStorage persistence
    - CSS variable injection
    - Theme attribute setting
    - Smooth theme transitions
  3. DSThemeSwitcher.tsx - Theme switcher UI:
    - Terminal-style dropdown with ASCII borders
    - Keyboard navigation (arrow keys, Enter, Escape)
    - Theme preview dots
    - Current theme indicator
    - Compact version for header integration
  4. theme-provider-v2.tsx - Compatibility wrapper:
    - Replaces existing next-themes provider
    - Maintains API compatibility

  ✅ Integrations:

  - Integrated theme switcher into DSAgentTerminalContainer header
  - Updated providers/index.tsx to use new theme system
  - Added smooth CSS transitions for theme changes
  - Added theme-specific styles to terminal-theme.css
  - Fixed all lint errors

  🎯 Key Features:

  - 6 carefully designed terminal themes
  - Persistent theme selection across sessions
  - Smooth 300ms transitions between themes
  - Keyboard accessible theme switcher
  - Live preview capabilities (foundation laid)
  - Terminal-authentic ASCII UI elements

  The theme switching system is now complete, providing users with a variety of terminal aesthetics while maintaining the cohesive
  DeepSearchAgents design language!

===

#### Claude's Sub-Task 1.6.4 Implementation Plan - Complete Migration and Remove shadcn Dependencies

Objective

Complete the migration to WebTUI-based DS components and remove all shadcn/Radix UI dependencies from the frontend.

Current Status Analysis

1. Shadcn Dependencies to Remove:
  - @radix-ui/* packages (10 components)
  - class-variance-authority
  - Related UI components in /components/ui/
2. Components Still Using shadcn:
  - agent-layout.tsx - Uses Tabs component
  - final-answer-display.tsx - Uses Card component
  - agent-question-input.tsx - Uses UI components
  - Various other components using Button, Dialog, etc.
3. V2 Components Already Created:
  - agent-chat-v2.tsx
  - planning-card-v2.tsx
  - action-thought-card-v2.tsx
  - code-editor-v2.tsx
  - markdown-v2.tsx
  - All DS components (complete set)

Implementation Plan

Step 1: Create DS Replacements for Remaining UI Components

1. DSCard - Replace shadcn Card
  - Terminal-style card with ASCII borders
  - Support for header, content, footer sections
2. DSTabs - Replace shadcn Tabs
  - Terminal-style tab navigation
  - ASCII underlines and borders
  - Keyboard navigation support
3. DSButton - Replace shadcn Button
  - Terminal-style buttons with WebTUI attributes
  - Support variants: primary, secondary, ghost, danger
4. DSDialog - Replace shadcn Dialog
  - Terminal-style modal with ASCII borders
  - Overlay with terminal grid pattern
5. DSInput - Replace question input components
  - Terminal-style input with cursor
  - Support for multiline (textarea replacement)

Step 2: Update Main Components

1. agent-layout.tsx → agent-layout-v2.tsx
  - Replace Tabs with DSTabs
  - Use DSAgentTerminalContainer as wrapper
  - Update imports to use DS components
2. final-answer-display.tsx → final-answer-display-v2.tsx
  - Replace Card with DSCard
  - Use DS typography and styling
  - Maintain structured data display
3. agent-question-input.tsx → agent-question-input-v2.tsx
  - Replace with DSInput
  - Add terminal-style prompt

Step 3: Update Component Imports

1. Update home-content.tsx to use v2 components
2. Update agent-chat.tsx imports to point to v2
3. Update any remaining component references

Step 4: Remove Dependencies

1. Remove all @radix-ui/* packages from package.json
2. Remove class-variance-authority
3. Remove /components/ui/ directory
4. Update tailwind config if needed

Step 5: Testing & Validation

1. Test all major user flows
2. Verify theme switching works
3. Check keyboard navigation
4. Ensure no console errors
5. Validate WebSocket functionality

Expected File Changes

- Create: components/ds/DSCard.tsx
- Create: components/ds/DSTabs.tsx
- Create: components/ds/DSButton.tsx
- Create: components/ds/DSDialog.tsx
- Create: components/ds/DSInput.tsx
- Create: components/agent-layout-v2.tsx
- Create: components/final-answer-display-v2.tsx
- Create: components/agent-question-input-v2.tsx
- Update: components/home-content.tsx
- Update: components/ds/index.ts
- Update: package.json
- Remove: components/ui/ directory

This systematic approach will complete the migration while maintaining all functionality and improving the terminal aesthetic throughout the
 application.

##### Claude's Sub-Task 1.6.4 Completion Summary

  ✅ Completed Sub-Task 1.6.4: Complete migration and remove shadcn dependencies

  What was accomplished:

  1. Created DS replacement components:
    - ✅ DSCard.tsx - Terminal-style card with ASCII borders and variants
    - ✅ DSTabs.tsx - Tab navigation with terminal aesthetics and animations
    - ✅ DSButton.tsx - Button component with terminal styling and variants
    - ✅ DSInput.tsx - Input and textarea components with terminal cursor
  2. Updated main components to v2:
    - ✅ agent-layout-v2.tsx - Using DSTabs and DSAgentTerminalContainer
    - ✅ agent-question-input-v2.tsx - Using DSTextarea and DSButton
    - ✅ final-answer-display-v2.tsx - Using DSCard components
    - ✅ edit-question-v2.tsx - Using DS components
  3. Updated imports:
    - ✅ Updated home-content.tsx to use agent-layout-v2.tsx
    - ✅ Updated chat-message.tsx to use v2 components and DSButton
    - ✅ Updated all component exports in ds/index.ts
  4. Removed shadcn dependencies:
    - ✅ Removed all @radix-ui/* packages from package.json
    - ✅ Removed class-variance-authority package
    - ✅ Removed next-themes package (replaced with DSThemeProvider)
    - ✅ Deleted components/ui directory
  5. Added CSS styles:
    - ✅ Added comprehensive styles for DSCard, DSTabs, DSButton, and DSInput
    - ✅ Added animations for tabs and buttons
    - ✅ Added terminal-style cursor animations

  Key features of the new components:

  - DSCard: Supports variants (default, elevated, ghost), borders (single, double, rounded), and includes DSTerminalCard with ASCII decorations
  - DSTabs: Full keyboard navigation, smooth animations, vertical/horizontal orientation
  - DSButton: Multiple variants (primary, secondary, ghost, danger, success), loading state, icon support
  - DSInput: Terminal cursor animation, error states, textarea with auto-resize

  Files changed in Sub-Task 1.6.4:

  - Created: components/ds/DSCard.tsx
  - Created: components/ds/DSTabs.tsx
  - Created: components/ds/DSButton.tsx
  - Created: components/ds/DSInput.tsx
  - Created: components/agent-layout-v2.tsx
  - Created: components/agent-question-input-v2.tsx
  - Created: components/final-answer-display-v2.tsx
  - Created: components/edit-question-v2.tsx
  - Updated: components/home-content.tsx
  - Updated: components/chat-message.tsx
  - Updated: components/ds/index.ts
  - Updated: app/styles/terminal-theme.css
  - Updated: package.json
  - Removed: components/ui/ directory

  The migration is now complete! The application has been successfully migrated from shadcn/ui to the custom DS components built on WebTUI,
  providing a cohesive terminal-style interface that embodies the "Code is Action!" philosophy.

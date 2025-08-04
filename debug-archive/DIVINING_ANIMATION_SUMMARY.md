# Divining Animation Implementation

## Overview
Changed the loading status from "Loading..." to "Divining..." with an animated star pattern that cycles through different sizes.

## Changes Implemented

### 1. Status Configuration Update
In `agent-status.types.ts`:
```typescript
loading: { 
  text: 'Divining...', 
  icon: '✻', 
  animated: true,
  animationType: 'divining',
  agentState: 'thinking'
}
```

### 2. Animation Type Addition
- Added `'divining'` to the `AnimationType` enum
- This enables the system to recognize the new animation type

### 3. Animation Frames Definition
In `DSAgentASCIIAnimations.tsx`:
```typescript
divining: ['✻', '✶', '·', '✶', '✻']
```
- Cycles through: large star → medium star → dot → medium star → large star
- Creates a pulsing/breathing effect

### 4. Animation Timing
```typescript
animationTimings = {
  spinner: {
    // ...
    divining: 300  // 300ms per frame for smooth transition
  }
}
```

### 5. Spinner Mapping
In `DSAgentASCIISpinner.tsx`:
```typescript
stateSpinnerMap = {
  // ...
  loading: 'divining'  // Maps loading state to divining animation
}
```

### 6. Animation Enablement
In `agent-running-status.tsx`:
- Re-enabled animation specifically for the divining/loading status
- Other statuses remain unanimated for simplicity

## Animation Behavior

When the agent is in a "loading" state (gaps between events):

1. **Initial Display**: ✻ Divining...
2. **Animation Cycle**:
   - ✻ Divining... (largest star)
   - ✶ Divining... (medium star)
   - · Divining... (small dot)
   - ✶ Divining... (medium star)
   - ✻ Divining... (back to largest)
3. **Timing**: Each frame displays for 300ms
4. **Loop**: Continues until status changes

## Visual Effect

The animation creates a mystical, pulsing effect that:
- Provides engaging visual feedback during processing gaps
- Maintains the terminal/ASCII aesthetic
- Indicates active processing without being distracting
- Uses star symbols that evoke a sense of "divining" or discovering information

## Result

Users now see an animated "Divining..." status with pulsing stars during gaps between agent events, creating a more engaging and thematically appropriate loading indicator.
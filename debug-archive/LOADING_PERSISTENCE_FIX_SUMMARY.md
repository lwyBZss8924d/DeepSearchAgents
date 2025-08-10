# Loading Status Persistence Fix

## Overview
Fixed the issue where "Loading..." status only appeared at the beginning and was replaced by "Standby" during subsequent status change intervals.

## Problem
- Every message updated `currentAgentStatus`, even structural messages (separators, footers)
- These messages have no `agent_status` field, causing fallback to "standby"
- "Loading..." was overwritten immediately by the next structural message

## Solution Implemented

### 1. Enhanced Status Mapping
In `mapBackendToFrontendStatus`:
- Now accepts `currentStatus` parameter
- Identifies structural messages (separators, footers, headers)
- Preserves current status for structural messages
- Only changes status for meaningful updates

### 2. Status Update Logic
In `updateAgentTaskStatus`:
- Passes current status to mapping function
- Only dispatches status update if status actually changes
- Logs when status is preserved vs changed

### 3. Structural Message Detection
Identifies these message types as structural:
- `separator`
- `action_footer`
- `planning_footer`
- Messages with `status: "done"` but not final answers

## Technical Implementation

```typescript
// In mapBackendToFrontendStatus
const isStructuralMessage = 
  message_type === 'separator' || 
  message_type === 'action_footer' || 
  message_type === 'planning_footer' ||
  (status === 'done' && !is_final_answer);

// Preserve current status for structural messages
if (isStructuralMessage && currentStatus && currentStatus !== 'standby') {
  return currentStatus;
}
```

```typescript
// In updateAgentTaskStatus
if (detailedStatus !== currentStatus) {
  // Only update if status is changing
  dispatch({ type: 'SET_CURRENT_AGENT_STATUS', payload: detailedStatus });
} else {
  // Preserve current status
  console.log(`Preserving current status: ${currentStatus}`);
}
```

## Expected Behavior

1. **Initial gap**: Shows "Loading..." and keeps it
2. **During execution**: Status persists between events
3. **Structural messages**: Don't change the current status
4. **Status continuity**: No flickering or resets to "Standby"
5. **Completion**: Only returns to "Standby" after final answer

## Testing

Run the test script:
```bash
python debug-archive/scripts/test_loading_persistence.py
```

This verifies:
- "Loading..." persists during gaps
- Structural messages don't reset status
- No inappropriate "Standby" during execution

## Result

The agent status now maintains continuity throughout execution:
- "Loading..." persists between events
- Structural messages (separators, footers) don't affect status
- Smooth transitions without flickering
- "Standby" only appears when agent is truly idle
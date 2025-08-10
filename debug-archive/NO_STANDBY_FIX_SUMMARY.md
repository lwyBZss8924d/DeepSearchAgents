# Fix for "Standby" Status During Agent Execution

## Overview
Fixed the issue where "Standby" status incorrectly appeared during gaps between streaming events while the agent was actively running.

## Problem
- Backend sends `status: "done"` for many intermediate messages (headers, footers, separators)
- Frontend was interpreting these as the entire agent being complete
- This caused status to flicker to "Standby" between events during active execution

## Solution Implemented

### 1. Added Loading Status
In `agent-status.types.ts`:
- Added new status: `'loading'`
- Configured to show "Loading..." with ⟳ icon
- Used for gaps between streaming events when agent is still running

### 2. Enhanced Status Mapping
In `mapBackendToFrontendStatus`:
- Now accepts `isGenerating` parameter
- Returns `'loading'` instead of `'standby'` when `isGenerating` is true
- Only returns `'standby'` when agent is truly idle

### 3. Fixed Status Update Logic
In `updateAgentTaskStatus`:
- Now accepts `state` parameter to check `isGenerating`
- Only sets "standby" when:
  - Message indicates final completion (is_final_answer)
  - AND `isGenerating` is false
- Removed check for `status === 'done'` which was causing false positives

### 4. Updated Components
- `agent-running-status.tsx`: Shows "Loading..." when generating but no specific status
- All `processAgentMessage` calls now pass `state` parameter

## Technical Flow

```
Message arrives → processAgentMessage → updateAgentTaskStatus
                                                ↓
                                    Check isGenerating state
                                                ↓
                            If generating: Never set to standby
                            If not generating: Set standby only for final answer
```

## Expected Behavior

1. **Before query**: Status shows "Standby"
2. **During execution**: 
   - Shows specific statuses (Planning, Thinking, Coding, etc.)
   - Shows "Loading..." during gaps between events
   - NEVER shows "Standby"
3. **After completion**: Returns to "Standby"

## Testing

Run the test script:
```bash
python debug-archive/scripts/test_no_standby_during_execution.py
```

This verifies:
- No "standby" status appears during active execution
- "Loading..." appears for gaps as expected
- "Standby" only appears when agent is truly idle

## Result

The agent status now accurately reflects the execution state throughout the entire process, providing better user feedback and eliminating confusing "Standby" messages during active processing.
# Streaming Message Type Fix Summary

## Problem
When streaming is enabled (`skip_model_outputs=True`), all streaming deltas after an ActionStep were being incorrectly marked as "planning_content" instead of "action_thought". This prevented the frontend from displaying action thoughts with the correct 60-character truncated format.

## Root Cause
The `stream_agent_messages` function in `src/api/v2/web_ui.py` was using the `skip_model_outputs` flag (which just indicates whether streaming is enabled) to determine message types, rather than tracking the actual phase (planning vs action).

## Solution Implemented

### 1. Added Phase Tracking
- The existing `current_phase` variable is now properly utilized to track whether we're in 'planning' or 'action' phase

### 2. Updated Phase on Events
- When processing a `PlanningStep` event, set `current_phase = "planning"`
- When processing an `ActionStep` event, set `current_phase = "action"`

### 3. Fixed Message Type Assignment
Changed the logic from:
```python
current_streaming_type = (
    "planning_content"
    if skip_model_outputs
    else "action_thought"
)
```

To:
```python
current_streaming_type = (
    "planning_content"
    if current_phase == "planning"
    else "action_thought"
)
```

### 4. Fixed Step Type Assignment
Similarly updated the step_type assignment to use `current_phase` instead of `skip_model_outputs`.

## Files Modified
- `/src/api/v2/web_ui.py` - Fixed streaming message type assignment logic in both async and sync generator sections

## Expected Results
- Messages containing "Thought:" content from ActionSteps will now be correctly marked as "action_thought"
- The frontend will display them with the proper 60-character truncated format
- Planning content will still be correctly marked as "planning_content"
- Message types will accurately reflect the agent's current phase (planning vs action)

## Testing
Created `test_message_type_fix.py` to verify that:
1. Thought messages are correctly typed as "action_thought"
2. No thought messages are incorrectly typed as "planning_content"
3. The streaming context properly tracks the current phase

## Additional Notes
- The typo "Runing" → "Running" in `action-thought-card.tsx` was already fixed
- Planning headers are being sent correctly with empty content and proper metadata
- Final answer messages have correct backend implementation
# CLI Streaming Display Issue

## Issue Description
The CLI streaming display repeatedly renders content in the terminal, causing duplicated streaming blocks and making the output unreadable. This occurs specifically in Research Multi-Agent Team mode but affects all streaming output.

## Symptoms
- "Streaming Response Streaming..." messages appear multiple times
- Content duplicates (e.g., "1. Facts survey" appearing repeatedly)
- Terminal output becomes cluttered and difficult to read
- The display continuously refreshes even when no new content arrives

## Root Cause
The issue is in `src/agents/ui_common/streaming_formatter.py`:
- Uses Rich's `Live` display component with `refresh_per_second=4`
- This causes the entire panel to be redrawn 4 times per second
- Each refresh adds to the terminal output instead of updating in place

## Solution
Remove the Rich Live display and replace with incremental printing:

### Changes Required in `streaming_formatter.py`:

1. **Remove imports**:
   - Remove `from rich.live import Live`
   - Remove `from rich.spinner import Spinner`

2. **Remove Live display initialization**:
   ```python
   # REMOVE THIS:
   self.live_display = Live(
       Panel(...),
       console=self.console,
       refresh_per_second=4
   )
   ```

3. **Update `on_stream_start()`**:
   ```python
   def on_stream_start(self):
       """Initialize streaming display"""
       self.stream_start_time = time.time()
       self.stream_content = ""
       self.is_streaming = True
       self._last_displayed_length = 0
       
       # Simple header instead of Live display
       agent_color = COLORS.get(self.agent_type, {}).get('primary', 'cyan')
       self.console.print(
           f"[{agent_color}]{THINKING_EMOJI} Streaming Response Starting..."
           f"[/{agent_color}]"
       )
   ```

4. **Update `on_stream_chunk()`**:
   ```python
   # Replace panel update with incremental print:
   # OLD: self.live_display.update(panel)
   # NEW:
   self.console.print(cleaned_chunk, end="", markup=False)
   ```

5. **Simplify `on_stream_end()`**:
   - Remove `self.live_display.stop()`
   - Just print completion message

## Benefits
- Eliminates repetitive rendering
- Maintains streaming visibility
- Reduces complexity
- Improves performance

## Testing
After implementing the fix:
1. Test with simple queries
2. Test with complex multi-agent queries
3. Verify no duplicate output
4. Ensure streaming still provides real-time feedback

## Priority
**CRITICAL** - This issue significantly impacts user experience and makes streaming output unusable.

## Related Files
- `src/agents/ui_common/streaming_formatter.py` (main fix)
- `src/cli.py` (uses StreamingConsoleFormatter)
- `src/agents/base_agent.py` (streaming integration)
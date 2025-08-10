# Comprehensive Streaming Test Guide

This guide explains how to use the test tools to debug WebSocket streaming issues in DeepSearchAgents.

## Overview

We have created several test tools to isolate and identify streaming issues:

1. **Backend Instrumentation** - Adds detailed logging to track message flow
2. **Real API Test** - Runs the actual API with instrumentation
3. **React Test App** - Minimal React implementation to isolate frontend issues
4. **Mock Backend** - Simulates streaming without using LLM tokens

## Quick Diagnosis

Run this first to check your configuration:

```bash
cd tests/streaming
python diagnose_streaming.py
```

This will show you:
- Whether streaming is enabled in config
- If agents are created with correct parameters
- Whether stream_to_gradio supports streaming
- WebSocket flow configuration

## Step-by-Step Testing Process

### Step 1: Test with Mock Backend First

This verifies that WebSocket streaming CAN work correctly:

```bash
# Terminal 1: Start mock backend
cd tests/streaming
python test_streaming_backend.py

# Terminal 2: Test with Python client
python test_ws_client.py

# Or test with browser
open test_streaming_browser.html
```

✅ **Expected**: Messages arrive progressively with consistent timing

### Step 2: Test Real API with Instrumentation

This identifies issues in the actual backend:

```bash
cd tests/streaming
python test_real_api_streaming.py
```

**Alternative: Test Backend Directly**

If the API test shows no messages, test the agent directly:

```bash
python test_backend_directly.py
```

This bypasses the WebSocket layer to see if the agent itself can stream.

**Alternative: Run Instrumented API Manually**

For more control, run the instrumented API in one terminal:

```bash
python run_instrumented_api.py
```

Then test with the WebSocket client in another terminal:

```bash
python test_ws_client.py --real --session YOUR_SESSION_ID
```

This script will:
1. Start the API with comprehensive instrumentation
2. Create a session automatically
3. Send a minimal query ("What is 2+2?")
4. Log detailed timing at each step
5. Analyze the results

✅ **Expected Output**:
```
[0.010s] Message #1 - STREAM - step: 1 - content: 5 chars
[0.052s] Message #2 - STREAM - step: 1 - content: 10 chars
[0.103s] Message #3 - STREAM - step: 1 - content: 15 chars
...
✅ Good message distribution: 2/19 bunched
✅ Good streaming ratio: 15/20
```

❌ **Problem Indicators**:
```
⚠️ MESSAGE BUNCHING DETECTED: 18/19 messages < 10ms apart
❌ NO STREAMING MESSAGES RECEIVED
```

### Step 3: Test Frontend in Isolation

Open the minimal React test app:

```bash
open test_react_streaming.html
```

1. Click "Create Session"
2. Click "Connect"
3. Click "Send Query"
4. Watch both panels:
   - Left: What the user sees
   - Right: Debug logs showing every state update

✅ **Expected**: 
- Messages appear immediately as they arrive
- "ADD streaming message" logs for new content
- "UPDATE streaming message" logs for increments
- Render count increases with each update

❌ **Problem Indicators**:
- All messages appear at once
- No UPDATE logs (only ADD at the end)
- Low render count despite many messages

### Step 4: Compare with Production Frontend

Run the same test with the actual frontend:

1. Start the backend normally:
   ```bash
   make run
   ```

2. Open the frontend and check browser console

3. Send the same query: "What is 2+2?"

4. Look for console logs we added:
   - "WebSocket message:" logs
   - "AgentChat: messages updated" logs
   - "Streaming chunk for step" logs

## Interpreting Results

### Scenario 1: Mock Works, Real API Doesn't Stream

**Diagnosis**: Backend configuration or agent initialization issue

**Check**:
- Is `enable_streaming = true` in config.toml?
- Does the agent have `stream_outputs` parameter?
- Are messages being buffered in `stream_to_gradio`?

**Solution**: The instrumentation logs will show where messages are delayed

### Scenario 2: Backend Streams, Frontend Doesn't Display

**Diagnosis**: Frontend state management or rendering issue

**Check**:
- Are WebSocket messages arriving? (Check browser console)
- Is state being updated? (Check React DevTools)
- Are messages filtered out? (Check rendering logic)

**Solution**: Compare minimal React app behavior with production

### Scenario 3: All Messages Arrive at Once

**Diagnosis**: Messages are being buffered somewhere

**Check timing logs**:
```
Message gradio_1: Generated at 0.000s → Sent at 15.234s
Message gradio_2: Generated at 0.051s → Sent at 15.235s
```

Large gap between "Generated" and "Sent" = buffering issue

### Scenario 4: React State Updates Don't Trigger Renders

**Diagnosis**: React optimization or memoization issue

**Check**:
- Render count in test app
- React DevTools Profiler
- useEffect dependencies

## Quick Debugging Checklist

1. **Backend Streaming Enabled?**
   ```toml
   [agents.codact]
   enable_streaming = true
   ```

2. **Agent Has stream_outputs?**
   Check instrumentation log:
   ```
   Agent.run called - stream_outputs: True
   ```

3. **Messages Sent Immediately?**
   Check backend log timestamps:
   ```
   [11:23:45.123] Sending message #1
   [11:23:45.175] Sending message #2  # ~50ms gap = good
   ```

4. **Frontend Receives in Real-time?**
   Check browser console:
   ```
   WebSocket message: streaming: true, step: 1
   ```

5. **State Updates Trigger Renders?**
   Check React test app render count

## Troubleshooting: No Messages Received

If `test_real_api_streaming.py` shows "NO STREAMING MESSAGES RECEIVED":

1. **Check if agent is actually running**:
   - The 30-second timeout suggests the agent might be stuck
   - Try a simpler query like "What is 2+2?"
   - Check backend logs for errors

2. **Run diagnostics**:
   ```bash
   python diagnose_streaming.py
   ```
   Look for:
   - `enable_streaming: NOT SET` or `False`
   - `stream_outputs: NOT SET` or `False`
   - Any ❌ errors

3. **Test agent directly**:
   ```bash
   python test_backend_directly.py
   ```
   This will show if the agent can stream at all.

4. **Check for LLM API issues**:
   - Ensure your API keys are set in `.env`
   - Check if the LLM is responding
   - Try with a different model

## Common Fixes

### Backend Not Streaming
```python
# In codact_agent.py, ensure:
agent = CodeAgent(
    stream_outputs=self.enable_streaming  # This must be present!
)
```

### Frontend Not Updating
```javascript
// Remove any filtering that delays display:
// ❌ .filter(step => step <= currentStep)
// ✅ Show all messages immediately
```

### WebSocket Buffering
```python
# In endpoints.py, add explicit flushing:
await websocket.send_json(message)
# Force flush if needed
```

## Summary

Use these tests in order:
1. Mock backend → Verify infrastructure works
2. Real API test → Find backend issues  
3. React test app → Isolate frontend issues
4. Production comparison → Identify specific problems

The instrumentation will show exactly where messages get delayed or lost.
# WebSocket Streaming Test Suite

This test suite helps verify that WebSocket streaming is working correctly throughout the entire stack without using any LLM tokens.

## Quick Start

### 1. Test with Mock Backend (Recommended)

First, start the mock streaming backend:
```bash
cd tests/streaming
python test_streaming_backend.py
```

This starts a mock server on port 8001 that simulates agent streaming.

### 2. Test with Python Client

In another terminal:
```bash
# Test default scenario
python test_ws_client.py

# Test fast streaming
python test_ws_client.py -u ws://localhost:8001/test/ws/fast

# Test slow streaming
python test_ws_client.py -u ws://localhost:8001/test/ws/slow

# Test error handling
python test_ws_client.py -u ws://localhost:8001/test/ws/error
```

### 3. Test with Browser

Open `test_streaming_browser.html` in your browser:
```bash
# On macOS
open test_streaming_browser.html

# Or just drag the file into your browser
```

Then:
1. Select "Test Backend (Mock)" 
2. Choose a scenario
3. Click "Connect"
4. Click "Send Query"
5. Watch the real-time streaming!

## Testing Against Real API

### 1. Create a session first:
```bash
# Using curl
curl -X POST http://localhost:8000/api/v2/sessions \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "codact"}'

# Note the session_id from the response
```

### 2. Test with Python client:
```bash
python test_ws_client.py --real --session YOUR_SESSION_ID
```

### 3. Test with Browser:
1. Select "Real API" in the dropdown
2. Enter your session ID
3. Connect and send a query

## Understanding the Output

### Python Client Output
```
[0.001s] #1   | USER         step:0 | 'Test query for streaming'
[0.052s] #2   | STREAM       step:1 +5 chars  | 'I'll '
[0.103s] #3   | STREAM       step:1 +10 chars | 'help you t'
[0.154s] #4   | ASSISTANT    step:1 | 'I'll help you test the streaming functionality...'
```

- **Timestamp**: Time since query was sent
- **Message #**: Sequential message number
- **Type**: STREAM (incremental), ASSISTANT (complete), etc.
- **Step**: Agent step number
- **Content**: Message content or incremental addition

### Browser Test Features

The browser test shows:
- **Real-time message display** with color coding
- **Statistics**: Total messages, streaming count, average interval
- **Timeline visualization**: Visual representation of message timing
- **Detailed analysis**: Automatic detection of issues like message bunching

## Test Scenarios

### Default
Simulates a typical agent run with planning, tool use, and final answer.

### Fast
Rapid-fire streaming messages to test throughput and UI performance.

### Slow
Character-by-character streaming to test patience and buffering.

### Error
Tests error handling during streaming.

### Delayed
Adds artificial delays to test timeout handling.

## What to Look For

### ✅ Good Streaming
- Messages arrive progressively (not all at once)
- Consistent intervals between messages (50-200ms typical)
- Smooth character-by-character updates
- No message bunching

### ❌ Problems to Watch For
- All messages arriving at once
- Large gaps between messages (>1s)
- Messages bunched together (many within 10ms)
- Missing streaming messages
- Connection drops

## Debugging Tips

1. **Check Backend Logs**: The mock backend logs every message sent with timing
2. **Check Browser Console**: Open DevTools to see detailed WebSocket frames
3. **Compare Mock vs Real**: Test both to isolate backend vs frontend issues
4. **Network Tab**: Use browser DevTools Network tab to inspect WebSocket frames

## Common Issues

### "Connection refused"
- Make sure the backend is running (mock on 8001, real on 8000)
- Check firewall/proxy settings

### "No messages received"
- Verify the WebSocket URL is correct
- Check for CORS issues in browser console
- Ensure session exists (for real API)

### "Messages arrive all at once"
- Backend might not be streaming properly
- Check if agent has `stream_outputs=True`
- Verify `enable_streaming=true` in config.toml

## Advanced Testing

### Custom Scenarios
Edit `test_streaming_backend.py` to add new scenarios:
```python
elif self.scenario == "custom":
    # Your custom streaming logic here
    pass
```

### Performance Testing
Use the fast scenario with multiple clients:
```bash
# Terminal 1
python test_ws_client.py -u ws://localhost:8001/test/ws/fast &

# Terminal 2
python test_ws_client.py -u ws://localhost:8001/test/ws/fast &

# Terminal 3
python test_ws_client.py -u ws://localhost:8001/test/ws/fast &
```

### Load Testing
Create multiple WebSocket connections to test server capacity.

## Next Steps

Once streaming is verified:
1. Fix any identified issues
2. Test with real agent queries
3. Optimize frontend rendering
4. Add progressive disclosure for better UX
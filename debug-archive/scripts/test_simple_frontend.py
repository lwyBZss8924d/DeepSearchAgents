#!/usr/bin/env python
"""Simple test to see what messages are actually sent"""

import asyncio
import websockets
import json

async def test():
    ws_url = "ws://localhost:8000/api/v2/ws/test-simple?agent_type=codact"
    
    async with websockets.connect(ws_url) as ws:
        # Send simple query
        await ws.send(json.dumps({
            "type": "query",
            "query": "Step-by-step solve: y' = y^2 x"
        }))
        
        # Collect first 10000 messages
        messages = []
        for i in range(10000):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=300.0)
                data = json.loads(msg)
                
                # Extract key info
                msg_type = data.get('metadata', {}).get('message_type', 'unknown')
                content_len = len(data.get('content', ''))
                content_preview = data.get('content', '')[:50]
                
                print(f"#{i+1} - type: {msg_type}, len: {content_len}, content: {content_preview}...")
                
                messages.append(data)
                
                # Stop at final answer
                if data.get('metadata', {}).get('is_final_answer'):
                    break
                    
            except asyncio.TimeoutError:
                print("Timeout")
                break
                
        # Analyze
        print("\nSUMMARY:")
        print(f"Total messages: {len(messages)}")
        
        # Count types
        types = {}
        for m in messages:
            t = m.get('metadata', {}).get('message_type', 'none')
            types[t] = types.get(t, 0) + 1
            
        print("\nMessage types:")
        for t, count in types.items():
            print(f"  {t}: {count}")
            
        # Check for specific issues
        print("\nISSUES:")
        planning_headers = [m for m in messages if m.get('metadata', {}).get('message_type') == 'planning_header']
        action_thoughts = [m for m in messages if m.get('metadata', {}).get('message_type') == 'action_thought']
        
        if not planning_headers:
            print("❌ No planning_header messages found!")
        else:
            print(f"✓ Found {len(planning_headers)} planning headers")
            
        if not action_thoughts:
            print("❌ No action_thought messages found!")
            # Check for Thought: in content
            thought_contents = [m for m in messages if m.get('content', '').startswith('Thought:')]
            if thought_contents:
                print(f"  But found {len(thought_contents)} messages with 'Thought:' in content")
        else:
            print(f"✓ Found {len(action_thoughts)} action thoughts")

asyncio.run(test())
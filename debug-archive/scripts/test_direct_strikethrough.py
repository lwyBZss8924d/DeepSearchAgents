#!/usr/bin/env python3
"""
Direct test to inject strikethrough content and see how it's rendered.
Tests the hypothesis that markdown is rendering ~~ as strikethrough.
"""

import asyncio
import websockets
import json
import time
from typing import List, Dict, Any

class DirectStrikethroughTest:
    def __init__(self):
        self.ws_url = "ws://localhost:8000/api/v2/ws/stream"
        
    async def send_test_messages(self):
        """Send messages with strikethrough marks to test rendering"""
        print("🔧 Direct Strikethrough Injection Test")
        print("=" * 50)
        
        # First create a session
        import urllib.request
        import urllib.parse
        
        session_data = json.dumps({"agent_type": "react"}).encode()
        req = urllib.request.Request(
            "http://localhost:8000/api/v2/sessions",
            data=session_data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib.request.urlopen(req)
            session_info = json.loads(response.read())
            session_id = session_info['session_id']
            print(f"✓ Created session: {session_id}")
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return
        
        # Connect to WebSocket with session ID
        ws_url = f"ws://localhost:8000/api/v2/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"✓ Connected to {ws_url}")
                
                # Send test messages with strikethrough marks
                test_messages = [
                    {
                        "message_id": "test-1",
                        "role": "assistant",
                        "content": "Testing strikethrough: ~~✓~~ ~~💻~~python_interpreter~~",
                        "metadata": {
                            "component": "chat",
                            "message_type": "tool_call",
                            "tool_name": "~~✓~~ ~~💻~~python_interpreter~~",
                            "step_type": "action"
                        },
                        "step_number": 1
                    },
                    {
                        "message_id": "test-2",
                        "role": "assistant",
                        "content": "Clean tool name: python_interpreter",
                        "metadata": {
                            "component": "chat",
                            "message_type": "tool_call",
                            "tool_name": "python_interpreter",
                            "step_type": "action"
                        },
                        "step_number": 2
                    },
                    {
                        "message_id": "test-3",
                        "role": "assistant",
                        "content": "Mixed content with ~~strikethrough~~ and normal text",
                        "metadata": {
                            "component": "chat",
                            "message_type": "message"
                        },
                        "step_number": 3
                    }
                ]
                
                print("\n📨 Sending test messages...")
                for msg in test_messages:
                    await websocket.send(json.dumps(msg))
                    print(f"  ✓ Sent: {msg['content'][:50]}...")
                    await asyncio.sleep(0.5)
                
                print("\n⏳ Waiting 5 seconds for rendering...")
                await asyncio.sleep(5)
                
                print("\n✓ Test completed")
                print("\n📋 Instructions:")
                print("1. Check the frontend browser window")
                print("2. Look for how the strikethrough marks are rendered")
                print("3. Check if '~~' appears as literal text or as strikethrough")
                print("\nExpected: Tool badges should NOT show strikethrough")
                print("Actual: Check the browser to see what was rendered")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

async def main():
    tester = DirectStrikethroughTest()
    await tester.send_test_messages()

if __name__ == "__main__":
    asyncio.run(main())
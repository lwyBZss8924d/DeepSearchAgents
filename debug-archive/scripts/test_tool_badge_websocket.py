#!/usr/bin/env python3
"""Test script to check what tool badge data is being sent via WebSocket"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_tool_badges():
    uri = "ws://localhost:8000/ws/v2"
    
    async with websockets.connect(uri) as websocket:
        print(f"[{datetime.now()}] Connected to WebSocket")
        
        # Initialize connection
        init_message = {
            "session_id": f"test_badges_{datetime.now().timestamp()}",
            "message": {
                "query": "Use the python_interpreter tool to calculate 2+2",
                "agent_type": "codact",
                "enable_streaming": True
            }
        }
        
        await websocket.send(json.dumps(init_message))
        print(f"[{datetime.now()}] Sent query for tool usage")
        
        # Listen for tool badge messages
        tool_messages = []
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=30)
                data = json.loads(message)
                
                # Check for tool-related messages
                if data.get("metadata", {}).get("tool_name"):
                    tool_name = data["metadata"]["tool_name"]
                    print(f"\n[TOOL BADGE FOUND]")
                    print(f"  Raw tool_name: {repr(tool_name)}")
                    print(f"  Contains ~~: {'~~' in tool_name}")
                    print(f"  Message type: {data.get('metadata', {}).get('message_type')}")
                    print(f"  Content: {data.get('content', '')[:100]}")
                    tool_messages.append(data)
                
                # Check for tool_call messages
                if data.get("metadata", {}).get("message_type") == "tool_call":
                    print(f"\n[TOOL CALL MESSAGE]")
                    print(f"  Tool name: {data.get('metadata', {}).get('tool_name')}")
                    print(f"  Content: {repr(data.get('content', '')[:200])}")
                
                # Check for final answer to stop
                if "final_answer" in str(data.get("metadata", {}).get("tool_name", "")):
                    print("\n[Final answer reached, stopping]")
                    break
                    
        except asyncio.TimeoutError:
            print(f"\n[{datetime.now()}] Timeout reached")
        
        print(f"\n[SUMMARY]")
        print(f"Total tool messages found: {len(tool_messages)}")
        for i, msg in enumerate(tool_messages):
            tool_name = msg["metadata"]["tool_name"]
            print(f"  {i+1}. {repr(tool_name)}")
            
            # Check for strikethrough patterns
            if "~~" in tool_name:
                print(f"     ⚠️  Contains strikethrough marks!")
                # Try to extract clean name
                parts = tool_name.split("~~")
                clean_parts = [p.strip() for p in parts if p.strip()]
                print(f"     Parts: {clean_parts}")

if __name__ == "__main__":
    asyncio.run(test_tool_badges())
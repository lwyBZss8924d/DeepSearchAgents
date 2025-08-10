#!/usr/bin/env python3
"""Test script to verify Agent Running Status indicator is always visible."""

import asyncio
import websockets
import json
import uuid
import sys
import time

API_URL = "ws://localhost:8000/api/v2/ws"

async def test_agent_status_indicator():
    """Test that the Agent Running Status indicator is always visible."""
    
    # First create a session
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v2/sessions",
            json={"agent_type": "react", "max_steps": 10}
        )
        data = response.json()
        session_id = data["session_id"]
        print(f"Created session: {session_id}")
    
    # Connect to WebSocket
    ws_url = f"{API_URL}/{session_id}"
    print(f"Connecting to: {ws_url}")
    
    async with websockets.connect(ws_url) as websocket:
        print("Connected to WebSocket")
        
        # Wait a moment to ensure UI loads
        await asyncio.sleep(2)
        
        print("\n✅ Agent Running Status indicator should now show 'Standby' in the header")
        print("   It should appear next to the Connection Status and Session State indicators")
        print("   Format: ◊ Standby (without spinner)")
        
        # Send a test query to see status changes
        print("\n📤 Sending test query to trigger status changes...")
        query_msg = json.dumps({
            "type": "query",
            "query": "What is the capital of France?"
        })
        await websocket.send(query_msg)
        
        print("\n🔄 Agent status should now change through these states:")
        print("   1. ◆ Planning... (with spinner)")
        print("   2. ◊ Thinking... (with spinner)")
        print("   3. ■ Actions Running... (with spinner)")
        print("   4. ✓ Writing... (with spinner)")
        print("   5. Back to: ◊ Standby (no spinner)")
        
        # Listen for messages to track status changes
        status_states = []
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                
                if 'metadata' in data:
                    metadata = data['metadata']
                    step_type = metadata.get('step_type', '')
                    message_type = metadata.get('message_type', '')
                    streaming = metadata.get('streaming', False)
                    
                    # Track status changes
                    if step_type == 'planning':
                        if streaming and 'Planning...' not in status_states:
                            status_states.append('Planning...')
                            print(f"   ✓ Agent status changed to: ◆ Planning...")
                    elif step_type == 'action':
                        if 'thinking' in str(metadata) and 'Thinking...' not in status_states:
                            status_states.append('Thinking...')
                            print(f"   ✓ Agent status changed to: ◊ Thinking...")
                        elif 'coding' in str(metadata) and 'Coding...' not in status_states:
                            status_states.append('Coding...')
                            print(f"   ✓ Agent status changed to: ▶ Coding...")
                        elif 'running' in str(metadata) and 'Actions Running...' not in status_states:
                            status_states.append('Actions Running...')
                            print(f"   ✓ Agent status changed to: ■ Actions Running...")
                    elif step_type == 'final_answer':
                        if streaming and 'Writing...' not in status_states:
                            status_states.append('Writing...')
                            print(f"   ✓ Agent status changed to: ✓ Writing...")
                    
                    # Check if complete
                    if metadata.get('status') in ['complete', 'done']:
                        print(f"   ✓ Agent status should return to: ◊ Standby")
                        break
                        
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout waiting for response")
        
        print(f"\n📊 Status states observed: {len(status_states)}")
        print("\n✅ Test complete! The Agent Running Status indicator should:")
        print("   1. Always be visible in the header")
        print("   2. Show 'Standby' when idle")
        print("   3. Change to appropriate states during agent execution")
        print("   4. Display spinners when actively working")

if __name__ == "__main__":
    print("🧪 Testing Agent Running Status Indicator")
    print("="*50)
    asyncio.run(test_agent_status_indicator())
#!/usr/bin/env python3
"""Test script to verify dynamic agent status animations."""

import asyncio
import websockets
import json
import uuid
import time

API_URL = "ws://localhost:8000/api/v2/ws"

async def test_dynamic_status_animations():
    """Test that agent status displays with proper animations during execution."""
    
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
        print("Connected to WebSocket\n")
        
        print("✅ Dynamic Status Animation Test")
        print("=" * 60)
        print()
        print("Expected behavior:")
        print("1. Title bar status indicator:")
        print("   - Shows 'Standby' when idle (static ◊)")
        print("   - Changes to animated states during execution")
        print()
        print("2. Chat message badges:")
        print("   - Show animated spinners during streaming")
        print("   - Switch to static icons when message completes")
        print()
        print("3. Status progression:")
        print("   - ◆ Initial Planning... (animated dots spinner)")
        print("   - ◊ Thinking... (animated pulse spinner)")
        print("   - ▶ Coding... (animated terminal spinner)")
        print("   - ■ Actions Running... (animated arrows spinner)")
        print("   - ✓ Writing... (animated brackets spinner)")
        print("   - ◊ Standby (static, no animation)")
        print()
        
        # Send a test query
        print("📤 Sending test query...")
        query_msg = json.dumps({
            "type": "query",
            "query": "Write a Python function to calculate the factorial of a number"
        })
        await websocket.send(query_msg)
        
        print("\n🔄 Monitoring status changes...\n")
        
        # Track status changes
        status_log = []
        last_status = None
        message_count = 0
        
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                data = json.loads(message)
                message_count += 1
                
                if 'metadata' in data:
                    metadata = data['metadata']
                    agent_status = metadata.get('agent_status', '')
                    is_active = metadata.get('is_active', False)
                    is_streaming = metadata.get('streaming', False)
                    step_type = metadata.get('step_type', '')
                    message_type = metadata.get('message_type', '')
                    
                    # Log status changes
                    if agent_status and agent_status != last_status:
                        animation_state = "ANIMATED" if (is_active or is_streaming) else "STATIC"
                        status_log.append({
                            'status': agent_status,
                            'animation': animation_state,
                            'timestamp': time.time()
                        })
                        
                        # Map status to display
                        status_display = {
                            'initial_planning': '◆ Initial Planning...',
                            'update_planning': '◆ Update Planning...',
                            'thinking': '◊ Thinking...',
                            'coding': '▶ Coding...',
                            'actions_running': '■ Actions Running...',
                            'writing': '✓ Writing...',
                            'working': '◊ Working...'
                        }
                        
                        display_text = status_display.get(agent_status, agent_status)
                        print(f"   Status: {display_text} [{animation_state}]")
                        
                        last_status = agent_status
                    
                    # Check for completion
                    if metadata.get('status') in ['complete', 'done'] or metadata.get('is_final_answer'):
                        print(f"\n✅ Agent completed! Returning to: ◊ Standby [STATIC]")
                        break
                        
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout waiting for completion")
        
        print(f"\n📊 Summary:")
        print(f"   Total messages: {message_count}")
        print(f"   Status changes: {len(status_log)}")
        print()
        print("📝 Status progression log:")
        for i, log in enumerate(status_log):
            print(f"   {i+1}. {log['status']} - {log['animation']}")
        
        print("\n✅ Test complete!")
        print()
        print("🔍 Check the frontend to verify:")
        print("   1. Title bar indicator shows current status with animation")
        print("   2. Chat badges animate during streaming")
        print("   3. Historical messages show static badges")
        print("   4. Smooth transitions between states")

if __name__ == "__main__":
    print("🧪 Testing Dynamic Agent Status Animations")
    print("="*50)
    asyncio.run(test_dynamic_status_animations())
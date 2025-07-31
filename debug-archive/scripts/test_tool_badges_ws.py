#!/usr/bin/env python3
"""
Direct WebSocket test for tool call messages
"""
import asyncio
import websockets
import json
import time
from typing import List, Dict, Any

class DirectWSTest:
    def __init__(self):
        self.ws_url = "ws://localhost:8000/api/v2/ws/stream"
        self.messages: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        
    async def test_tool_messages(self):
        """Test WebSocket for tool_call messages"""
        print("🔧 Direct WebSocket Tool Message Test")
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
                
                # Send test query
                test_query = {
                    "type": "query",
                    "query": "search for information about quantum computing and summarize what you find"
                }
                
                await websocket.send(json.dumps(test_query))
                print(f"✓ Sent query type: {test_query['type']}")
                print(f"✓ Query: {test_query['query']}")
                print("\n📨 Collecting messages for 30 seconds...")
                
                # Collect messages
                start_time = time.time()
                timeout = 30  # seconds
                
                while time.time() - start_time < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        self.messages.append(data)
                        
                        # Check message type
                        msg_type = data.get('metadata', {}).get('message_type', 'unknown')
                        tool_name = data.get('metadata', {}).get('tool_name')
                        
                        if msg_type == 'tool_call':
                            self.tool_calls.append(data)
                            print(f"\n🔧 TOOL CALL FOUND!")
                            print(f"   Tool: {tool_name}")
                            print(f"   Content: {data.get('content', '')[:100]}...")
                            print(f"   Full metadata: {json.dumps(data.get('metadata', {}), indent=2)}")
                        else:
                            print(f"   Message type: {msg_type}", end='\r')
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"\nError: {e}")
                        break
                
                print(f"\n\n✓ Test completed after {time.time() - start_time:.1f} seconds")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return
        
        # Results
        print("\n📊 Results")
        print("=" * 50)
        print(f"Total messages: {len(self.messages)}")
        print(f"Tool call messages: {len(self.tool_calls)}")
        
        # Message type breakdown
        msg_types = {}
        for msg in self.messages:
            msg_type = msg.get('metadata', {}).get('message_type', 'unknown')
            msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        
        print("\nMessage types received:")
        for msg_type, count in sorted(msg_types.items()):
            print(f"  - {msg_type}: {count}")
        
        # Tool calls detail
        if self.tool_calls:
            print(f"\n✅ SUCCESS: Found {len(self.tool_calls)} tool call messages!")
            print("\nTool calls:")
            tools_used = {}
            for tc in self.tool_calls:
                tool_name = tc.get('metadata', {}).get('tool_name', 'unknown')
                tools_used[tool_name] = tools_used.get(tool_name, 0) + 1
            
            for tool, count in sorted(tools_used.items()):
                print(f"  - {tool}: {count}")
        else:
            print("\n❌ FAILURE: No tool_call messages found!")
            print("\nDebugging info:")
            
            # Show some sample messages
            print("\nFirst 5 messages:")
            for i, msg in enumerate(self.messages[:5]):
                print(f"\n{i+1}. {msg.get('metadata', {}).get('message_type', 'unknown')}")
                print(f"   Content: {msg.get('content', '')[:100]}...")
                if msg.get('metadata'):
                    print(f"   Metadata keys: {list(msg['metadata'].keys())}")
        
        # Save full log
        log_file = "test_tool_badges_ws_log.json"
        with open(log_file, 'w') as f:
            json.dump({
                "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_messages": len(self.messages),
                "tool_calls": len(self.tool_calls),
                "message_types": msg_types,
                "tool_call_details": self.tool_calls,
                "all_messages": self.messages
            }, f, indent=2)
        print(f"\n📝 Full log saved to: {log_file}")

async def main():
    tester = DirectWSTest()
    await tester.test_tool_messages()

if __name__ == "__main__":
    asyncio.run(main())
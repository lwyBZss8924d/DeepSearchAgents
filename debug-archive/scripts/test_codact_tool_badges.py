#!/usr/bin/env python3
"""
Test script to debug CodeAct tool badge messages
"""
import asyncio
import websockets
import json
import time
from typing import List, Dict, Any

class CodeActToolBadgeTest:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        
    async def test_codact_tools(self):
        """Test CodeAct agent for tool_call messages"""
        print("🔧 CodeAct Tool Badge Test")
        print("=" * 50)
        
        # Create a session with CodeAct agent
        import urllib.request
        
        session_data = json.dumps({"agent_type": "codact"}).encode()
        req = urllib.request.Request(
            "http://localhost:8000/api/v2/sessions",
            data=session_data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib.request.urlopen(req)
            session_info = json.loads(response.read())
            session_id = session_info['session_id']
            print(f"✓ Created CodeAct session: {session_id}")
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return
        
        # Connect to WebSocket
        ws_url = f"ws://localhost:8000/api/v2/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"✓ Connected to {ws_url}")
                
                # Send a query that will trigger tool usage
                test_query = {
                    "type": "query",
                    "query": "search for information about quantum computing and summarize what you find"
                }
                
                await websocket.send(json.dumps(test_query))
                print(f"✓ Sent query: {test_query['query']}")
                print("\n📨 Collecting messages for 40 seconds...")
                
                # Collect messages
                start_time = time.time()
                timeout = 40  # seconds - CodeAct might take longer
                
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
                            print(f"\n🔧 TOOL CALL FOUND: {tool_name}")
                            print(f"   Args summary: {data.get('metadata', {}).get('tool_args_summary', '')}")
                            print(f"   Is Python Interpreter: {data.get('metadata', {}).get('is_python_interpreter', False)}")
                            
                        # Also log other interesting messages
                        if msg_type in ['planning_header', 'action', 'webide', 'final_answer']:
                            print(f"   [{msg_type}] ", end='')
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"\nError: {e}")
                        break
                
                print(f"\n\n✓ Test completed after {time.time() - start_time:.1f} seconds")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return
        
        # Analyze results
        print("\n📊 Analysis")
        print("=" * 50)
        print(f"Total messages: {len(self.messages)}")
        print(f"Tool call messages: {len(self.tool_calls)}")
        
        # Message types breakdown
        msg_types = {}
        for msg in self.messages:
            msg_type = msg.get('metadata', {}).get('message_type', 'unknown')
            msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        
        print("\nMessage types breakdown:")
        for msg_type, count in sorted(msg_types.items()):
            print(f"  - {msg_type}: {count}")
        
        # Tool calls analysis
        if self.tool_calls:
            print(f"\n✅ Found {len(self.tool_calls)} tool call messages!")
            print("\nTool calls breakdown:")
            
            # Separate python_interpreter and extracted tools
            python_interpreter_calls = []
            extracted_tool_calls = []
            
            for tc in self.tool_calls:
                tool_name = tc.get('metadata', {}).get('tool_name', 'unknown')
                if tool_name == 'python_interpreter':
                    python_interpreter_calls.append(tc)
                else:
                    extracted_tool_calls.append(tc)
            
            print(f"  - python_interpreter: {len(python_interpreter_calls)}")
            print(f"  - Extracted tools: {len(extracted_tool_calls)}")
            
            if extracted_tool_calls:
                print("\n  Extracted tools found:")
                tools_found = {}
                for tc in extracted_tool_calls:
                    tool_name = tc.get('metadata', {}).get('tool_name', 'unknown')
                    tools_found[tool_name] = tools_found.get(tool_name, 0) + 1
                
                for tool, count in sorted(tools_found.items()):
                    print(f"    - {tool}: {count}")
            else:
                print("\n❌ NO extracted tool badges found!")
                print("   Only python_interpreter badges are being sent")
        else:
            print("\n❌ NO tool_call messages found at all!")
        
        # Save detailed log
        log_file = "test_codact_tool_badges_log.json"
        with open(log_file, 'w') as f:
            json.dump({
                "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_type": "codact",
                "total_messages": len(self.messages),
                "tool_calls": len(self.tool_calls),
                "message_types": msg_types,
                "tool_call_messages": self.tool_calls,
                "all_messages": self.messages
            }, f, indent=2)
        print(f"\n📝 Full log saved to: {log_file}")

async def main():
    tester = CodeActToolBadgeTest()
    await tester.test_codact_tools()

if __name__ == "__main__":
    asyncio.run(main())
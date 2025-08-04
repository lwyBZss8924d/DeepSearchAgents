#!/usr/bin/env python3
"""Test complete agent status flow synchronization.

This script tests the following:
1. Title bar status updates in real-time during execution
2. Thinking messages appear immediately when streaming starts
3. Status transitions are smooth and synchronized
4. All components show consistent status
"""

import asyncio
import json
import websockets
import time
from datetime import datetime


class StatusFlowTester:
    def __init__(self, ws_url="ws://localhost:8000/api/v2/ws"):
        self.ws_url = ws_url
        self.session_id = None
        self.status_history = []
        self.thinking_message_timing = []
        
    async def connect(self):
        """Connect to WebSocket and get session ID."""
        uri = f"{self.ws_url}/test-session-{int(time.time())}"
        self.ws = await websockets.connect(uri)
        print(f"✅ Connected to WebSocket: {uri}")
        
    async def send_query(self, query):
        """Send a query to the agent."""
        message = {
            "type": "query",
            "query": query
        }
        await self.ws.send(json.dumps(message))
        print(f"📤 Sent query: {query}")
        
    async def monitor_status_flow(self):
        """Monitor status changes and timing."""
        start_time = time.time()
        message_count = 0
        first_thinking_time = None
        statuses_seen = set()
        
        print("\n🔍 Monitoring status flow...")
        print("-" * 60)
        
        try:
            while True:
                raw_message = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                message = json.loads(raw_message)
                message_count += 1
                current_time = time.time() - start_time
                
                # Skip non-agent messages
                if message.get("type") in ["pong", "state"]:
                    continue
                    
                # Extract status info
                metadata = message.get("metadata", {})
                agent_status = metadata.get("agent_status", "unknown")
                message_type = metadata.get("message_type", "unknown")
                is_streaming = metadata.get("streaming", False)
                is_delta = metadata.get("is_delta", False)
                content_length = len(message.get("content", ""))
                
                # Track status changes
                if agent_status not in statuses_seen and agent_status != "unknown":
                    statuses_seen.add(agent_status)
                    status_info = {
                        "status": agent_status,
                        "time": current_time,
                        "message_type": message_type,
                        "streaming": is_streaming
                    }
                    self.status_history.append(status_info)
                    print(f"⚡ [{current_time:.2f}s] Status: {agent_status} "
                          f"(type: {message_type}, streaming: {is_streaming})")
                
                # Track thinking message timing
                if message_type == "action_thought" and not is_delta:
                    if first_thinking_time is None:
                        first_thinking_time = current_time
                        print(f"🤔 [{current_time:.2f}s] First thinking message appeared!")
                    
                    self.thinking_message_timing.append({
                        "time": current_time,
                        "content_length": content_length,
                        "is_initial": content_length == 0,
                        "streaming": is_streaming
                    })
                
                # Log significant messages
                if message_type in ["planning_header", "planning_content", "action_thought", 
                                   "tool_call", "final_answer"]:
                    print(f"📨 [{current_time:.2f}s] {message_type}: "
                          f"step={message.get('step_number', 0)}, "
                          f"content_len={content_length}, "
                          f"streaming={is_streaming}, delta={is_delta}")
                
                # Check for completion
                if message_type == "final_answer" or agent_status == "standby":
                    print(f"\n✅ Agent completed at {current_time:.2f}s")
                    break
                    
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout waiting for messages")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            
        return message_count, first_thinking_time
        
    def analyze_results(self, message_count, first_thinking_time):
        """Analyze test results."""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        # Status flow analysis
        print("\n📈 Status Flow:")
        expected_flow = ["initial_planning", "thinking", "coding", "actions_running", "writing"]
        actual_flow = [s["status"] for s in self.status_history]
        
        print(f"Expected: {' → '.join(expected_flow)}")
        print(f"Actual:   {' → '.join(actual_flow)}")
        
        # Check if flow matches expectations
        flow_correct = all(status in actual_flow for status in expected_flow)
        print(f"Flow correct: {'✅ Yes' if flow_correct else '❌ No'}")
        
        # Timing analysis
        print("\n⏱️ Timing Analysis:")
        print(f"Total messages: {message_count}")
        print(f"Status changes: {len(self.status_history)}")
        
        if first_thinking_time:
            print(f"First thinking message: {first_thinking_time:.2f}s")
            if first_thinking_time < 2.0:
                print("✅ Thinking message appeared quickly!")
            else:
                print("⚠️ Thinking message was delayed")
        else:
            print("❌ No thinking messages detected")
            
        # Thinking message details
        if self.thinking_message_timing:
            print(f"\n🤔 Thinking Messages:")
            for i, tm in enumerate(self.thinking_message_timing[:3]):  # Show first 3
                print(f"  {i+1}. Time: {tm['time']:.2f}s, "
                      f"Initial: {tm['is_initial']}, "
                      f"Streaming: {tm['streaming']}")
                      
        # Status transition times
        print("\n🔄 Status Transitions:")
        for i in range(1, len(self.status_history)):
            prev = self.status_history[i-1]
            curr = self.status_history[i]
            transition_time = curr["time"] - prev["time"]
            print(f"  {prev['status']} → {curr['status']}: {transition_time:.2f}s")
            
        # Summary
        print("\n📋 Summary:")
        issues = []
        
        if not flow_correct:
            issues.append("Status flow doesn't match expected sequence")
        if first_thinking_time and first_thinking_time > 2.0:
            issues.append("Thinking message appeared too late")
        if not first_thinking_time:
            issues.append("No thinking messages detected")
            
        if issues:
            print("❌ Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ All status synchronization tests passed!")
            
    async def run_test(self):
        """Run the complete test."""
        print("🚀 Starting Agent Status Flow Test")
        print("=" * 60)
        
        try:
            # Connect to WebSocket
            await self.connect()
            
            # Send test query
            test_query = "What is the square root of 144? Show your calculation."
            await self.send_query(test_query)
            
            # Monitor status flow
            message_count, first_thinking_time = await self.monitor_status_flow()
            
            # Analyze results
            self.analyze_results(message_count, first_thinking_time)
            
        finally:
            if hasattr(self, 'ws'):
                await self.ws.close()
                print("\n🔌 WebSocket connection closed")


async def main():
    """Main entry point."""
    tester = StatusFlowTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
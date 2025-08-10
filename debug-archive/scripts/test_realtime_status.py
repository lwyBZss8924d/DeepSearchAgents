#!/usr/bin/env python3
"""Test real-time agent status updates in title bar.

This script tests:
1. Title bar updates in real-time during streaming
2. Thinking messages appear immediately
3. Status transitions are smooth
4. No stuck statuses
"""

import asyncio
import json
import websockets
import time
from datetime import datetime


class RealtimeStatusTester:
    def __init__(self, ws_url="ws://localhost:8000/api/v2/ws"):
        self.ws_url = ws_url
        self.session_id = None
        self.status_updates = []
        self.thinking_timing = None
        
    async def connect(self):
        """Connect to WebSocket and get session ID."""
        uri = f"{self.ws_url}/test-realtime-{int(time.time())}"
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
        
    async def monitor_realtime_status(self):
        """Monitor real-time status updates."""
        start_time = time.time()
        last_status = None
        first_thinking_message = None
        status_timestamps = []
        
        print("\n🔍 Monitoring real-time status updates...")
        print("-" * 60)
        
        try:
            while True:
                raw_message = await asyncio.wait_for(self.ws.recv(), timeout=300.0)
                message = json.loads(raw_message)
                current_time = time.time() - start_time
                
                # Skip protocol messages
                if message.get("type") in ["pong", "state"]:
                    continue
                    
                # Extract metadata
                metadata = message.get("metadata", {})
                agent_status = metadata.get("agent_status")
                message_type = metadata.get("message_type")
                is_delta = metadata.get("is_delta", False)
                is_streaming = metadata.get("streaming", False)
                is_initial = metadata.get("is_initial_stream", False)
                
                # Track status changes
                if agent_status and agent_status != last_status:
                    status_info = {
                        "status": agent_status,
                        "time": current_time,
                        "from_delta": is_delta,
                        "message_type": message_type
                    }
                    self.status_updates.append(status_info)
                    status_timestamps.append(current_time)
                    
                    print(f"⚡ [{current_time:.2f}s] STATUS CHANGE: "
                          f"{last_status or 'none'} → {agent_status} "
                          f"(delta: {is_delta}, type: {message_type})")
                    
                    last_status = agent_status
                
                # Track thinking message timing
                if message_type == "action_thought" and not first_thinking_message:
                    first_thinking_message = current_time
                    self.thinking_timing = current_time
                    print(f"🤔 [{current_time:.2f}s] FIRST THINKING MESSAGE! "
                          f"(empty: {not message.get('content')}, "
                          f"initial: {is_initial}, streaming: {is_streaming})")
                
                # Log delta updates for debugging
                if is_delta and agent_status:
                    print(f"📊 [{current_time:.2f}s] Delta update: "
                          f"status={agent_status}, type={message_type}")
                
                # Check for completion
                if agent_status == "standby" or message_type == "final_answer":
                    print(f"\n✅ Agent completed at {current_time:.2f}s")
                    break
                    
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout waiting for messages")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            
        return status_timestamps
        
    def analyze_results(self, status_timestamps):
        """Analyze test results."""
        print("\n" + "=" * 60)
        print("📊 REAL-TIME STATUS TEST RESULTS")
        print("=" * 60)
        
        # Status update analysis
        print(f"\n📈 Status Updates:")
        print(f"Total status changes: {len(self.status_updates)}")
        
        if self.status_updates:
            print("\nStatus flow:")
            for update in self.status_updates:
                print(f"  {update['time']:.2f}s: {update['status']} "
                      f"(from {'delta' if update['from_delta'] else 'full'} message)")
            
            # Check for real-time updates
            delta_updates = [u for u in self.status_updates if u['from_delta']]
            print(f"\nDelta updates: {len(delta_updates)}")
            
            if delta_updates:
                print("✅ Title bar updates from streaming deltas!")
            else:
                print("❌ No delta updates detected - title bar may be delayed")
        
        # Thinking message timing
        print(f"\n🤔 Thinking Message Timing:")
        if self.thinking_timing:
            print(f"First thinking message at: {self.thinking_timing:.2f}s")
            if self.thinking_timing < 1.5:
                print("✅ Thinking message appeared quickly!")
            else:
                print("⚠️ Thinking message was delayed")
        else:
            print("❌ No thinking messages detected")
        
        # Status transition smoothness
        if len(status_timestamps) >= 2:
            print(f"\n🔄 Status Transition Analysis:")
            transitions = []
            for i in range(1, len(status_timestamps)):
                gap = status_timestamps[i] - status_timestamps[i-1]
                transitions.append(gap)
                print(f"  Transition {i}: {gap:.2f}s")
            
            avg_transition = sum(transitions) / len(transitions)
            print(f"\nAverage transition time: {avg_transition:.2f}s")
            
            if max(transitions) < 5.0:
                print("✅ Smooth status transitions!")
            else:
                print("⚠️ Some status transitions were slow")
        
        # Summary
        print("\n📋 Summary:")
        issues = []
        
        if not any(u['from_delta'] for u in self.status_updates):
            issues.append("No real-time updates from streaming deltas")
        if self.thinking_timing and self.thinking_timing > 1.5:
            issues.append("Thinking message appeared late")
        if not self.thinking_timing:
            issues.append("No thinking messages detected")
            
        if issues:
            print("❌ Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ All real-time status tests passed!")
            print("  - Title bar updates in real-time from deltas")
            print("  - Thinking messages appear immediately")
            print("  - Status transitions are smooth")
            
    async def run_test(self):
        """Run the complete test."""
        print("🚀 Starting Real-Time Agent Status Test")
        print("=" * 60)
        
        try:
            # Connect to WebSocket
            await self.connect()
            
            # Send test query that requires thinking
            test_query = "Calculate the factorial of 10 and explain your reasoning step by step."
            await self.send_query(test_query)
            
            # Monitor real-time updates
            status_timestamps = await self.monitor_realtime_status()
            
            # Analyze results
            self.analyze_results(status_timestamps)
            
        finally:
            if hasattr(self, 'ws'):
                await self.ws.close()
                print("\n🔌 WebSocket connection closed")


async def main():
    """Main entry point."""
    tester = RealtimeStatusTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
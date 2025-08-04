#!/usr/bin/env python3
"""Test that 'Loading...' status persists during gaps between events.

This script tests:
1. Loading status appears and persists between events
2. Structural messages (separators, footers) don't reset status
3. Status continuity throughout execution
"""

import asyncio
import json
import websockets
import time


class LoadingPersistenceTester:
    def __init__(self, ws_url="ws://localhost:8000/api/v2/ws"):
        self.ws_url = ws_url
        self.session_id = None
        self.status_history = []
        self.loading_durations = []
        self.status_resets = []
        
    async def connect(self):
        """Connect to WebSocket and get session ID."""
        uri = f"{self.ws_url}/test-loading-{int(time.time())}"
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
        
    async def monitor_loading_persistence(self):
        """Monitor status changes focusing on loading persistence."""
        start_time = time.time()
        last_status = None
        last_status_time = start_time
        loading_start_time = None
        in_execution = False
        
        print("\n🔍 Monitoring 'Loading...' status persistence...")
        print("-" * 60)
        
        try:
            while True:
                raw_message = await asyncio.wait_for(
                    self.ws.recv(), timeout=60.0
                )
                message = json.loads(raw_message)
                current_time = time.time() - start_time
                
                # Skip protocol messages
                if message.get("type") in ["pong", "state"]:
                    continue
                    
                # Extract metadata
                metadata = message.get("metadata", {})
                agent_status = metadata.get("agent_status")
                message_type = metadata.get("message_type")
                is_final = metadata.get("is_final_answer", False)
                
                # Track when execution starts
                if agent_status and agent_status != "standby" and not in_execution:
                    in_execution = True
                    print(f"🚀 [{current_time:.2f}s] Execution started")
                
                # Log structural messages
                if message_type in ["separator", "action_footer", 
                                   "planning_footer", "action_header",
                                   "planning_header"]:
                    print(f"📄 [{current_time:.2f}s] Structural message: "
                          f"{message_type} (status in message: {agent_status})")
                
                # Track status changes
                if agent_status and agent_status != last_status:
                    # Calculate duration of previous status
                    if last_status:
                        duration = current_time - last_status_time
                        
                        # Track loading durations
                        if last_status == "loading":
                            self.loading_durations.append(duration)
                            print(f"⏱️  Loading lasted {duration:.2f}s")
                        
                        # Check for inappropriate status resets
                        if (last_status != "standby" and 
                            agent_status == "standby" and 
                            in_execution and not is_final):
                            self.status_resets.append({
                                "from": last_status,
                                "to": agent_status,
                                "time": current_time,
                                "message_type": message_type
                            })
                            print(f"❌ [{current_time:.2f}s] INAPPROPRIATE RESET: "
                                  f"{last_status} → standby (via {message_type})")
                    
                    # Update status
                    self.status_history.append({
                        "status": agent_status,
                        "time": current_time,
                        "message_type": message_type
                    })
                    
                    # Special handling for loading status
                    if agent_status == "loading":
                        loading_start_time = current_time
                        print(f"⟳ [{current_time:.2f}s] LOADING status started")
                    else:
                        print(f"📊 [{current_time:.2f}s] Status: "
                              f"{last_status or 'none'} → {agent_status}")
                    
                    last_status = agent_status
                    last_status_time = current_time
                
                # Check for completion
                if is_final or agent_status == "standby" and in_execution:
                    print(f"✅ [{current_time:.2f}s] Execution completed")
                    break
                    
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout waiting for messages")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            
    def analyze_results(self):
        """Analyze test results."""
        print("\n" + "=" * 60)
        print("📊 LOADING PERSISTENCE TEST RESULTS")
        print("=" * 60)
        
        # Loading status analysis
        print(f"\n⟳ Loading Status Analysis:")
        print(f"Times 'Loading' appeared: {len(self.loading_durations)}")
        
        if self.loading_durations:
            avg_duration = sum(self.loading_durations) / len(self.loading_durations)
            print(f"Average loading duration: {avg_duration:.2f}s")
            print(f"Longest loading: {max(self.loading_durations):.2f}s")
            print(f"Shortest loading: {min(self.loading_durations):.2f}s")
        
        # Status reset analysis
        print(f"\n❌ Inappropriate Status Resets:")
        if self.status_resets:
            print(f"Found {len(self.status_resets)} inappropriate resets:")
            for reset in self.status_resets:
                print(f"  - {reset['from']} → standby at {reset['time']:.2f}s "
                      f"(via {reset['message_type']})")
        else:
            print("No inappropriate resets to standby!")
        
        # Status flow
        print("\n🔄 Complete Status Flow:")
        for i, entry in enumerate(self.status_history[:15]):  # First 15
            print(f"  {entry['time']:.2f}s: {entry['status']} "
                  f"({entry['message_type']})")
        if len(self.status_history) > 15:
            print(f"  ... and {len(self.status_history) - 15} more")
        
        # Summary
        print("\n📋 Summary:")
        success = True
        
        if not self.loading_durations:
            print("⚠️ No 'Loading' status detected")
            success = False
        elif any(d < 0.5 for d in self.loading_durations):
            print("⚠️ Some 'Loading' durations were too short (< 0.5s)")
            print("   This suggests Loading is being overwritten quickly")
            success = False
        
        if self.status_resets:
            print("❌ Found inappropriate resets to standby")
            success = False
            
        if success:
            print("✅ Test PASSED!")
            print("   - Loading status persists appropriately")
            print("   - No inappropriate resets during execution")
        else:
            print("❌ Test FAILED - Loading status not persisting properly")
            
    async def run_test(self):
        """Run the complete test."""
        print("🚀 Starting Loading Persistence Test")
        print("=" * 60)
        
        try:
            # Connect to WebSocket
            await self.connect()
            
            # Send test query
            test_query = "Calculate the sum of the first 20 prime numbers"
            await self.send_query(test_query)
            
            # Monitor loading persistence
            await self.monitor_loading_persistence()
            
            # Analyze results
            self.analyze_results()
            
        finally:
            if hasattr(self, 'ws'):
                await self.ws.close()
                print("\n🔌 WebSocket connection closed")


async def main():
    """Main entry point."""
    tester = LoadingPersistenceTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
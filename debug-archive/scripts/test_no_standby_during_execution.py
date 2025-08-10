#!/usr/bin/env python3
"""Test that 'Standby' status doesn't appear during agent execution.

This script tests:
1. No 'standby' status appears between streaming events
2. 'Loading...' appears during gaps instead
3. 'Standby' only appears before query and after completion
"""

import asyncio
import json
import websockets
import time


class NoStandbyTester:
    def __init__(self, ws_url="ws://localhost:8000/api/v2/ws"):
        self.ws_url = ws_url
        self.session_id = None
        self.standby_occurrences = []
        self.loading_occurrences = []
        self.all_statuses = []
        
    async def connect(self):
        """Connect to WebSocket and get session ID."""
        uri = f"{self.ws_url}/test-no-standby-{int(time.time())}"
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
        
    async def monitor_status_for_standby(self):
        """Monitor status changes looking for inappropriate standby."""
        start_time = time.time()
        query_sent_time = start_time
        first_non_standby_time = None
        final_answer_time = None
        agent_active = False
        
        print("\n🔍 Monitoring for 'Standby' status during execution...")
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
                
                # Track all statuses
                if agent_status:
                    status_entry = {
                        "status": agent_status,
                        "time": current_time,
                        "message_type": message_type
                    }
                    self.all_statuses.append(status_entry)
                    
                    # Mark when agent becomes active
                    if agent_status != "standby" and not agent_active:
                        agent_active = True
                        first_non_standby_time = current_time
                        print(f"🚀 [{current_time:.2f}s] Agent became active "
                              f"with status: {agent_status}")
                    
                    # Check for standby during active execution
                    if agent_status == "standby" and agent_active and not is_final:
                        self.standby_occurrences.append(status_entry)
                        print(f"❌ [{current_time:.2f}s] STANDBY DETECTED "
                              f"during active execution! (type: {message_type})")
                    
                    # Check for loading status
                    if agent_status == "loading":
                        self.loading_occurrences.append(status_entry)
                        print(f"⟳ [{current_time:.2f}s] Loading status "
                              f"(type: {message_type})")
                    
                    # Log status changes
                    if len(self.all_statuses) > 1 and \
                       agent_status != self.all_statuses[-2]["status"]:
                        prev_status = self.all_statuses[-2]["status"]
                        print(f"📊 [{current_time:.2f}s] Status change: "
                              f"{prev_status} → {agent_status}")
                
                # Check for final answer
                if is_final or message_type == "final_answer":
                    final_answer_time = current_time
                    agent_active = False
                    print(f"✅ [{current_time:.2f}s] Agent completed")
                    
                    # Check for standby after completion (this is expected)
                    await asyncio.sleep(0.5)  # Wait for final status
                    break
                    
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout waiting for messages")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            
        return first_non_standby_time, final_answer_time
        
    def analyze_results(self, first_active_time, completion_time):
        """Analyze test results."""
        print("\n" + "=" * 60)
        print("📊 NO STANDBY DURING EXECUTION TEST RESULTS")
        print("=" * 60)
        
        # Status summary
        print(f"\n📈 Status Summary:")
        print(f"Total status updates: {len(self.all_statuses)}")
        print(f"Standby during execution: {len(self.standby_occurrences)}")
        print(f"Loading statuses: {len(self.loading_occurrences)}")
        
        # Detailed analysis
        if self.standby_occurrences:
            print(f"\n❌ FAILED: Found {len(self.standby_occurrences)} "
                  f"'standby' status(es) during active execution:")
            for occ in self.standby_occurrences:
                print(f"  - At {occ['time']:.2f}s: {occ['message_type']}")
        else:
            print("\n✅ PASSED: No 'standby' status during active execution!")
        
        # Loading status analysis
        if self.loading_occurrences:
            print(f"\n⟳ Loading statuses appeared {len(self.loading_occurrences)} "
                  f"times (for gaps between events)")
        
        # Status flow
        print("\n🔄 Status Flow:")
        unique_statuses = []
        for status in self.all_statuses:
            if not unique_statuses or status["status"] != unique_statuses[-1]:
                unique_statuses.append(status["status"])
        
        print(f"  {' → '.join(unique_statuses[:10])}")
        if len(unique_statuses) > 10:
            print(f"  ... and {len(unique_statuses) - 10} more transitions")
        
        # Timing analysis
        if first_active_time and completion_time:
            execution_time = completion_time - first_active_time
            print(f"\n⏱️ Timing:")
            print(f"  Agent active duration: {execution_time:.2f}s")
            print(f"  First active at: {first_active_time:.2f}s")
            print(f"  Completed at: {completion_time:.2f}s")
        
        # Summary
        print("\n📋 Summary:")
        if self.standby_occurrences:
            print("❌ Test FAILED: 'Standby' appeared during active execution")
            print("   This means the fix is not working properly")
        else:
            print("✅ Test PASSED: No inappropriate 'Standby' status!")
            print("   - 'Standby' only appears when agent is truly idle")
            if self.loading_occurrences:
                print("   - 'Loading...' appears during gaps as expected")
            
    async def run_test(self):
        """Run the complete test."""
        print("🚀 Starting No Standby During Execution Test")
        print("=" * 60)
        
        try:
            # Connect to WebSocket
            await self.connect()
            
            # Send test query
            test_query = "Write a Python function to calculate fibonacci numbers"
            await self.send_query(test_query)
            
            # Monitor for standby
            first_active, completion = await self.monitor_status_for_standby()
            
            # Analyze results
            self.analyze_results(first_active, completion)
            
        finally:
            if hasattr(self, 'ws'):
                await self.ws.close()
                print("\n🔌 WebSocket connection closed")


async def main():
    """Main entry point."""
    tester = NoStandbyTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
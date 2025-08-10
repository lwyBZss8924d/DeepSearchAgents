#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for real API streaming with comprehensive logging.

This script runs the actual DeepSearchAgents API with instrumentation
to identify streaming issues.
"""

import asyncio
import sys
import os
import json
import time
import subprocess
import requests
import websockets
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import instrumentation
from tests.streaming.instrument_backend import apply_all_instrumentation, timing_tracker


class RealAPIStreamingTest:
    """Test real API streaming behavior."""

    def __init__(self):
        self.api_process = None
        self.session_id = None
        self.api_url = "http://localhost:8000"
        self.messages_received = []

    async def start_instrumented_api(self):
        """Start the API with instrumentation."""
        print("\n🚀 Starting instrumented API server...")

        # Create a startup script that applies instrumentation
        startup_script = project_root / "tests/streaming/start_instrumented_api.py"

        with open(startup_script, 'w') as f:
            f.write("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Apply instrumentation before importing API
from tests.streaming.instrument_backend import apply_all_instrumentation
timing_tracker = apply_all_instrumentation()

# Now import and run the API
from src.api.v2.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=60,
        ws_max_size=16777216,
        ws_per_message_deflate=False
    )
""")

        # Start the API process
        self.api_process = subprocess.Popen(
            [sys.executable, str(startup_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Wait for API to start
        print("Waiting for API to start...")
        for i in range(30):
            try:
                response = requests.get(f"{self.api_url}/api/v2/health")
                if response.status_code == 200:
                    print("✅ API is ready!")
                    return True
            except:
                pass
            await asyncio.sleep(1)

        print("❌ API failed to start")
        return False

    def create_session(self):
        """Create a new session."""
        print("\n📝 Creating session...")

        response = requests.post(
            f"{self.api_url}/api/v2/sessions",
            json={"agent_type": "codact", "max_steps": 25}
        )

        if response.status_code == 200:
            data = response.json()
            self.session_id = data["session_id"]
            print(f"✅ Created session: {self.session_id}")
            return True
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            return False

    async def test_streaming(self):
        """Test WebSocket streaming with minimal query."""
        print(f"\n🔌 Connecting to WebSocket...")

        ws_url = f"ws://localhost:8000/api/v2/ws/{self.session_id}"

        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connected")

                # Send a minimal query
                query = "solve y' = y^2 x ?"
                print(f"\n📤 Sending query: {query}")

                await websocket.send(json.dumps({
                    "type": "query",
                    "query": query
                }))

                # Track timing
                start_time = time.time()
                first_message_time = None
                message_count = 0
                streaming_count = 0
                message_timeline = []

                print("\n📥 Receiving messages:")
                print("-" * 80)

                # Receive messages
                try:
                    while True:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=600.0
                        )

                        receive_time = time.time()
                        elapsed = receive_time - start_time

                        data = json.loads(message)
                        self.messages_received.append(data)

                        message_count += 1

                        if first_message_time is None:
                            first_message_time = elapsed

                        # Extract info
                        is_streaming = data.get('metadata', {}).get('streaming', False)
                        content_length = len(data.get('content', ''))
                        step = data.get('step_number', 0)

                        if is_streaming:
                            streaming_count += 1

                        # Log message
                        print(f"[{elapsed:6.3f}s] Message #{message_count} - "
                              f"{'STREAM' if is_streaming else 'COMPLETE'} - "
                              f"step: {step} - "
                              f"content: {content_length} chars")

                        # Track in timeline
                        message_timeline.append({
                            "time": elapsed,
                            "streaming": is_streaming,
                            "content_length": content_length,
                            "step": step
                        })

                        # Check for completion
                        if data.get('metadata', {}).get('is_final_answer'):
                            print("\n✅ Final answer received")
                            break

                except asyncio.TimeoutError:
                    print("\n⏱️  Timeout waiting for messages")

                # Analyze results
                print("\n" + "="*80)
                print("STREAMING ANALYSIS")
                print("="*80)

                total_time = time.time() - start_time

                print(f"\n📊 Statistics:")
                print(f"  • Total messages: {message_count}")
                print(f"  • Streaming messages: {streaming_count}")
                print(f"  • Total time: {total_time:.3f}s")
                print(f"  • Time to first message: {first_message_time:.3f}s" if first_message_time else "  • No messages received")

                if message_count > 1:
                    # Check message intervals
                    intervals = []
                    for i in range(1, len(message_timeline)):
                        interval = message_timeline[i]["time"] - message_timeline[i-1]["time"]
                        intervals.append(interval)

                    avg_interval = sum(intervals) / len(intervals)

                    print(f"  • Average interval: {avg_interval:.3f}s")
                    print(f"  • Min interval: {min(intervals):.3f}s")
                    print(f"  • Max interval: {max(intervals):.3f}s")

                    # Check for bunching
                    bunched = sum(1 for i in intervals if i < 0.01)
                    if bunched > len(intervals) * 0.5:
                        print(f"\n⚠️  MESSAGE BUNCHING DETECTED: {bunched}/{len(intervals)} messages < 10ms apart")
                    else:
                        print(f"\n✅ Good message distribution: {bunched}/{len(intervals)} bunched")

                # Check streaming effectiveness
                if streaming_count == 0:
                    print("\n❌ NO STREAMING MESSAGES RECEIVED")
                elif streaming_count < message_count * 0.3:
                    print(f"\n⚠️  Low streaming ratio: {streaming_count}/{message_count}")
                else:
                    print(f"\n✅ Good streaming ratio: {streaming_count}/{message_count}")

        except Exception as e:
            print(f"\n❌ WebSocket error: {e}")

    def analyze_backend_logs(self):
        """Analyze backend logs for timing."""
        print("\n" + "="*80)
        print("BACKEND LOG ANALYSIS")
        print("="*80)

        if self.api_process and self.api_process.stdout:
            print("\n📋 Recent backend logs:")

            # Read some recent output
            try:
                # Set stdout to non-blocking
                import fcntl
                flags = fcntl.fcntl(self.api_process.stdout.fileno(), fcntl.F_GETFL)
                fcntl.fcntl(self.api_process.stdout.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)

                lines = []
                while True:
                    line = self.api_process.stdout.readline()
                    if not line:
                        break
                    lines.append(line.strip())

                # Show last 20 lines
                for line in lines[-20:]:
                    if any(keyword in line for keyword in ["STREAM", "WEBSOCKET", "TIMING", "Sending message"]):
                        print(f"  {line}")

            except Exception as e:
                print(f"  Could not read logs: {e}")

    async def run_test(self):
        """Run the complete test."""
        print("🧪 DeepSearchAgents Real API Streaming Test")
        print("=" * 80)

        try:
            # Start instrumented API
            if not await self.start_instrumented_api():
                return

            # Create session
            if not self.create_session():
                return

            # Test streaming
            await self.test_streaming()

            # Analyze backend logs
            self.analyze_backend_logs()

            # Print timing summary
            print("\n" + "="*80)
            print("TIMING TRACKER SUMMARY")
            print("="*80)
            timing_tracker.print_summary()

        finally:
            # Cleanup
            if self.api_process:
                print("\n🛑 Stopping API server...")
                self.api_process.terminate()
                self.api_process.wait()

            # Clean up startup script
            startup_script = project_root / "tests/streaming/start_instrumented_api.py"
            if startup_script.exists():
                startup_script.unlink()


async def main():
    """Run the test."""
    test = RealAPIStreamingTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())

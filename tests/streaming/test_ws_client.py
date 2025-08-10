#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket client test script to verify streaming functionality.

This connects to either the test backend or the real API and logs
all messages with timing information.
"""

import asyncio
import json
import time
import argparse
import websockets
from datetime import datetime
from typing import Dict, List
from collections import defaultdict


class StreamingTester:
    """Tests WebSocket streaming and provides detailed analysis."""
    
    def __init__(self, url: str):
        self.url = url
        self.messages: List[Dict] = []
        self.message_times: List[float] = []
        self.start_time: float = 0
        self.streaming_messages: Dict[int, List[Dict]] = defaultdict(list)
        
    async def test_streaming(self, query: str = "Test streaming"):
        """Connect and test streaming functionality."""
        print(f"\n🔌 Connecting to: {self.url}")
        
        try:
            async with websockets.connect(self.url) as websocket:
                print("✅ Connected successfully")
                
                # Send initial query
                await self._send_query(websocket, query)
                
                # Receive and analyze messages
                await self._receive_messages(websocket)
                
                # Print analysis
                self._print_analysis()
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            
    async def _send_query(self, websocket, query: str):
        """Send a query message."""
        message = {
            "type": "query",
            "query": query
        }
        print(f"\n📤 Sending query: {query}")
        self.start_time = time.time()
        await websocket.send(json.dumps(message))
        
    async def _receive_messages(self, websocket):
        """Receive messages until completion or timeout."""
        print("\n📥 Receiving messages:")
        print("-" * 80)
        
        message_count = 0
        last_content = {}
        
        try:
            while True:
                # Set a timeout for receiving messages
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=30.0
                )
                
                data = json.loads(message)
                receive_time = time.time()
                elapsed = receive_time - self.start_time
                
                message_count += 1
                self.messages.append(data)
                self.message_times.append(elapsed)
                
                # Extract key info
                role = data.get('role', 'unknown')
                content = data.get('content', '')
                metadata = data.get('metadata', {})
                is_streaming = metadata.get('streaming', False)
                step = data.get('step_number', 0)
                
                # Track streaming messages
                if is_streaming:
                    self.streaming_messages[step].append({
                        'time': elapsed,
                        'content_length': len(content)
                    })
                
                # Print message info
                if is_streaming:
                    # For streaming, show incremental content
                    prev_len = len(last_content.get(step, ''))
                    new_content = content[prev_len:] if len(content) > prev_len else content
                    last_content[step] = content
                    
                    print(f"[{elapsed:6.3f}s] #{message_count:3d} | "
                          f"STREAM step:{step} +{len(new_content)} chars | "
                          f"'{new_content[:50]}{'...' if len(new_content) > 50 else ''}'")
                else:
                    # For complete messages
                    msg_type = self._get_message_type(data)
                    print(f"[{elapsed:6.3f}s] #{message_count:3d} | "
                          f"{msg_type:12s} step:{step} | "
                          f"'{content[:80]}{'...' if len(content) > 80 else ''}'")
                
                # Check for completion
                if metadata.get('is_final_answer') or metadata.get('status') == 'complete':
                    print("\n✅ Streaming completed")
                    break
                    
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout waiting for messages")
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Connection closed by server")
        except Exception as e:
            print(f"\n❌ Error receiving messages: {e}")
            
    def _get_message_type(self, data: Dict) -> str:
        """Determine message type for display."""
        if data.get('type') == 'error':
            return "ERROR"
        
        metadata = data.get('metadata', {})
        if metadata.get('streaming'):
            return "STREAMING"
        elif metadata.get('is_final_answer'):
            return "FINAL_ANSWER"
        elif metadata.get('tool_name'):
            return f"TOOL:{metadata['tool_name'][:8]}"
        elif data.get('role') == 'user':
            return "USER"
        else:
            return "ASSISTANT"
            
    def _print_analysis(self):
        """Print detailed analysis of the streaming session."""
        print("\n" + "=" * 80)
        print("📊 STREAMING ANALYSIS")
        print("=" * 80)
        
        # Overall stats
        total_messages = len(self.messages)
        total_time = self.message_times[-1] if self.message_times else 0
        streaming_count = sum(1 for m in self.messages if m.get('metadata', {}).get('streaming'))
        
        print(f"\n📈 Overall Statistics:")
        print(f"  • Total messages: {total_messages}")
        print(f"  • Total time: {total_time:.3f}s")
        print(f"  • Streaming messages: {streaming_count}")
        print(f"  • Average message interval: {total_time/total_messages:.3f}s" if total_messages > 0 else "N/A")
        
        # Streaming analysis by step
        if self.streaming_messages:
            print(f"\n🌊 Streaming Analysis by Step:")
            for step, messages in sorted(self.streaming_messages.items()):
                if len(messages) > 1:
                    times = [m['time'] for m in messages]
                    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
                    
                    print(f"\n  Step {step}:")
                    print(f"    • Messages: {len(messages)}")
                    print(f"    • Duration: {times[-1] - times[0]:.3f}s")
                    print(f"    • Avg interval: {sum(intervals)/len(intervals):.3f}s")
                    print(f"    • Min interval: {min(intervals):.3f}s")
                    print(f"    • Max interval: {max(intervals):.3f}s")
                    
                    # Check for buffering
                    if max(intervals) > 0.5:
                        print(f"    ⚠️  Large gap detected: {max(intervals):.3f}s")
        
        # Message timeline
        print(f"\n📅 Message Timeline:")
        step_times = defaultdict(list)
        for i, (msg, t) in enumerate(zip(self.messages, self.message_times)):
            step = msg.get('step_number', 0)
            step_times[step].append((i, t))
            
        for step, times in sorted(step_times.items()):
            start = times[0][1]
            end = times[-1][1]
            print(f"  • Step {step}: {start:6.3f}s - {end:6.3f}s ({len(times)} messages)")
            
        # Potential issues
        print(f"\n⚠️  Potential Issues:")
        issues_found = False
        
        # Check for message bunching
        if len(self.message_times) > 1:
            intervals = [self.message_times[i+1] - self.message_times[i] for i in range(len(self.message_times)-1)]
            bunched = sum(1 for i in intervals if i < 0.01)
            if bunched > len(intervals) * 0.5:
                print(f"  • Message bunching detected: {bunched}/{len(intervals)} messages arrived within 10ms")
                issues_found = True
                
        # Check for long delays
        if any(i > 1.0 for i in intervals):
            print(f"  • Long delays detected: {sum(1 for i in intervals if i > 1.0)} gaps > 1s")
            issues_found = True
            
        if not issues_found:
            print("  • No issues detected ✅")


async def main():
    parser = argparse.ArgumentParser(description='Test WebSocket streaming')
    parser.add_argument('--url', '-u', 
                       default='ws://localhost:8001/test/ws/default',
                       help='WebSocket URL to test')
    parser.add_argument('--query', '-q',
                       default='Test streaming functionality',
                       help='Query to send')
    parser.add_argument('--real', '-r',
                       action='store_true',
                       help='Test against real API instead of mock')
    parser.add_argument('--session', '-s',
                       help='Session ID for real API')
    
    args = parser.parse_args()
    
    # Adjust URL for real API
    if args.real:
        if not args.session:
            print("❌ Session ID required for real API testing (use -s SESSION_ID)")
            return
        args.url = f'ws://localhost:8000/api/v2/ws/{args.session}'
    
    tester = StreamingTester(args.url)
    await tester.test_streaming(args.query)


if __name__ == "__main__":
    print("🚀 WebSocket Streaming Tester")
    print("=" * 80)
    asyncio.run(main())
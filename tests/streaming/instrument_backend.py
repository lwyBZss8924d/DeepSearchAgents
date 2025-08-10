#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backend instrumentation for detailed streaming analysis.

This script adds comprehensive logging to track message flow through the system.
"""

import time
import functools
import logging
from typing import Any, Callable, AsyncGenerator, Generator
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s.%(msecs)03d] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Create loggers for different components
timing_logger = logging.getLogger("TIMING")
stream_logger = logging.getLogger("STREAM")
ws_logger = logging.getLogger("WEBSOCKET")
agent_logger = logging.getLogger("AGENT")


class TimingTracker:
    """Tracks timing of messages through the system."""
    
    def __init__(self):
        self.events = []
        self.message_map = {}
        
    def record_event(self, message_id: str, event_type: str, details: dict = None):
        """Record a timing event."""
        timestamp = time.time()
        event = {
            "message_id": message_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "details": details or {}
        }
        self.events.append(event)
        
        # Track message lifecycle
        if message_id not in self.message_map:
            self.message_map[message_id] = {}
        self.message_map[message_id][event_type] = timestamp
        
        # Log the event
        timing_logger.info(
            f"Message {message_id} - {event_type} - "
            f"Details: {details}"
        )
        
    def get_message_timeline(self, message_id: str) -> dict:
        """Get timeline for a specific message."""
        if message_id not in self.message_map:
            return {}
            
        timeline = self.message_map[message_id]
        result = {"message_id": message_id, "events": timeline}
        
        # Calculate intervals
        if "generated" in timeline and "sent" in timeline:
            result["generation_to_send"] = timeline["sent"] - timeline["generated"]
        if "sent" in timeline and "received" in timeline:
            result["send_to_receive"] = timeline["received"] - timeline["sent"]
            
        return result
        
    def print_summary(self):
        """Print timing summary."""
        print("\n" + "="*80)
        print("TIMING SUMMARY")
        print("="*80)
        
        for msg_id, timeline in self.message_map.items():
            print(f"\nMessage {msg_id}:")
            
            # Sort events by timestamp
            sorted_events = sorted(timeline.items(), key=lambda x: x[1])
            
            if sorted_events:
                start_time = sorted_events[0][1]
                
                for event, timestamp in sorted_events:
                    elapsed = timestamp - start_time
                    print(f"  {elapsed:6.3f}s - {event}")
                    
                # Total time
                total_time = sorted_events[-1][1] - start_time
                print(f"  Total: {total_time:6.3f}s")


# Global timing tracker
timing_tracker = TimingTracker()


def instrument_stream_to_gradio():
    """Instrument the stream_to_gradio function."""
    try:
        from smolagents.gradio_ui import stream_to_gradio
        original_stream_to_gradio = stream_to_gradio
        
        def instrumented_stream_to_gradio(*args, **kwargs):
            """Wrapped stream_to_gradio with timing."""
            stream_logger.info(f"stream_to_gradio called with args: {len(args)}, kwargs: {list(kwargs.keys())}")
            
            # Get the generator
            generator = original_stream_to_gradio(*args, **kwargs)
            
            message_count = 0
            start_time = time.time()
            
            # Process each item
            for item in generator:
                message_count += 1
                elapsed = time.time() - start_time
                
                # Generate message ID
                msg_id = f"gradio_{message_count}_{int(start_time*1000)}"
                
                # Log what's being yielded
                if isinstance(item, str):
                    stream_logger.info(
                        f"[{elapsed:.3f}s] Yielding string: {len(item)} chars - "
                        f"Preview: '{item[:50]}...'"
                    )
                    timing_tracker.record_event(msg_id, "generated", {
                        "type": "string",
                        "length": len(item)
                    })
                else:
                    stream_logger.info(
                        f"[{elapsed:.3f}s] Yielding object: {type(item).__name__}"
                    )
                    timing_tracker.record_event(msg_id, "generated", {
                        "type": type(item).__name__
                    })
                
                yield item
                
            stream_logger.info(
                f"stream_to_gradio completed - {message_count} items in {time.time() - start_time:.3f}s"
            )
        
        # Replace the function
        import smolagents.gradio_ui
        smolagents.gradio_ui.stream_to_gradio = instrumented_stream_to_gradio
        
        print("✅ Instrumented stream_to_gradio")
        
    except ImportError:
        print("⚠️  Could not import stream_to_gradio")


def instrument_websocket_send():
    """Instrument WebSocket send operations."""
    try:
        from fastapi import WebSocket
        original_send_json = WebSocket.send_json
        
        async def instrumented_send_json(self, data, mode='text'):
            """Wrapped WebSocket.send_json with timing."""
            # Extract message info
            msg_content = data.get('content', '')
            msg_streaming = data.get('metadata', {}).get('streaming', False)
            step_number = data.get('step_number', 0)
            
            # Generate or extract message ID
            msg_id = data.get('message_id', f"ws_{int(time.time()*1000)}")
            
            ws_logger.info(
                f"Sending WebSocket message - "
                f"streaming: {msg_streaming}, "
                f"step: {step_number}, "
                f"content_length: {len(msg_content)}"
            )
            
            timing_tracker.record_event(msg_id, "sent", {
                "streaming": msg_streaming,
                "content_length": len(msg_content),
                "step": step_number
            })
            
            # Call original
            await original_send_json(data, mode)
        
        # Replace the method
        WebSocket.send_json = instrumented_send_json
        
        print("✅ Instrumented WebSocket.send_json")
        
    except ImportError:
        print("⚠️  Could not instrument WebSocket")


def instrument_agent_run():
    """Instrument agent run method."""
    try:
        from smolagents import Agent
        
        # Store original run method
        if hasattr(Agent, 'run'):
            original_run = Agent.run
            
            def instrumented_run(self, *args, stream=False, **kwargs):
                """Wrapped Agent.run with logging."""
                agent_logger.info(
                    f"Agent.run called - "
                    f"type: {type(self).__name__}, "
                    f"stream: {stream}, "
                    f"stream_outputs: {getattr(self, 'stream_outputs', 'N/A')}"
                )
                
                # Check configuration
                if hasattr(self, 'enable_streaming'):
                    agent_logger.info(f"Agent enable_streaming: {self.enable_streaming}")
                
                # Call original
                return original_run(self, *args, stream=stream, **kwargs)
            
            # Replace the method
            Agent.run = instrumented_run
            
            print("✅ Instrumented Agent.run")
    
    except ImportError:
        print("⚠️  Could not instrument Agent")


def instrument_gradio_processor():
    """Instrument the DSAgent message processor."""
    try:
        from src.api.v2.ds_agent_message_processor import DSAgentMessageProcessor
        
        # Instrument process_agent_stream
        original_process = DSAgentMessageProcessor.process_agent_stream
        
        async def instrumented_process(self, *args, **kwargs):
            """Wrapped process_agent_stream with timing."""
            stream_logger.info("DSAgentMessageProcessor.process_agent_stream called")
            
            message_count = 0
            start_time = time.time()
            
            async for message in original_process(self, *args, **kwargs):
                message_count += 1
                elapsed = time.time() - start_time
                
                # Log processing
                stream_logger.info(
                    f"[{elapsed:.3f}s] Processing message #{message_count} - "
                    f"streaming: {message.metadata.get('streaming', False)}"
                )
                
                # Track timing
                if hasattr(message, 'message_id'):
                    timing_tracker.record_event(message.message_id, "processed", {
                        "count": message_count,
                        "elapsed": elapsed
                    })
                
                yield message
            
            stream_logger.info(
                f"process_agent_stream completed - {message_count} messages in {elapsed:.3f}s"
            )
        
        # Replace the method
        DSAgentMessageProcessor.process_agent_stream = instrumented_process
        
        print("✅ Instrumented DSAgentMessageProcessor")
        
    except ImportError:
        print("⚠️  Could not instrument DSAgentMessageProcessor")


def apply_all_instrumentation():
    """Apply all instrumentation."""
    print("\n🔧 Applying backend instrumentation...")
    
    instrument_stream_to_gradio()
    instrument_websocket_send()
    instrument_agent_run()
    instrument_gradio_processor()
    
    print("\n✅ Instrumentation complete!")
    print("All streaming operations will now be logged with detailed timing.\n")
    
    return timing_tracker


if __name__ == "__main__":
    # Test the instrumentation
    apply_all_instrumentation()
    print("\nInstrumentation can be imported and applied to any backend process.")
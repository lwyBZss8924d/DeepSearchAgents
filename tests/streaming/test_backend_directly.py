#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct backend test to verify agent streaming configuration.

This script tests the agent directly without WebSocket layer.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Apply instrumentation first
from tests.streaming.instrument_backend import apply_all_instrumentation
timing_tracker = apply_all_instrumentation()

# Now import the agent runtime
from src.agents.runtime import agent_runtime


async def test_agent_streaming():
    """Test agent streaming directly."""
    print("\n🧪 Direct Agent Streaming Test")
    print("=" * 80)
    
    # Create an agent
    print("\n1️⃣ Creating CodeAct agent...")
    agent = agent_runtime.create_codact_agent(
        session_id="test-streaming",
        step_callback=None,
        debug_mode=True
    )
    
    # Check configuration
    print(f"\n📋 Agent Configuration:")
    print(f"  • Type: {type(agent).__name__}")
    print(f"  • Has enable_streaming: {hasattr(agent, 'enable_streaming')}")
    if hasattr(agent, 'enable_streaming'):
        print(f"  • enable_streaming value: {agent.enable_streaming}")
    
    # Check inner agent
    if hasattr(agent, 'agent'):
        inner = agent.agent
        print(f"\n📋 Inner Agent Configuration:")
        print(f"  • Type: {type(inner).__name__}")
        print(f"  • Has stream_outputs: {hasattr(inner, 'stream_outputs')}")
        if hasattr(inner, 'stream_outputs'):
            print(f"  • stream_outputs value: {inner.stream_outputs}")
    
    # Test with minimal query
    query = "solve y' = y^2 x"
    print(f"\n2️⃣ Running query: {query}")
    print("-" * 80)
    
    try:
        # Run with stream=True
        print("\n🌊 Testing streaming mode (stream=True)...")
        
        stream = agent.run(query, stream=True)
        
        event_count = 0
        start_time = asyncio.get_event_loop().time()
        
        for event in stream:
            event_count += 1
            elapsed = asyncio.get_event_loop().time() - start_time
            
            event_type = type(event).__name__
            print(f"[{elapsed:6.3f}s] Event #{event_count}: {event_type}")
            
            # Show content preview for certain events
            if hasattr(event, 'content'):
                content = str(event.content)[:100]
                print(f"           Content: {content}")
            elif hasattr(event, 'delta'):
                delta = str(event.delta)[:100]
                print(f"           Delta: {delta}")
                
        print(f"\n✅ Streaming completed: {event_count} events")
        
    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()
    
    # Test non-streaming for comparison
    print("\n\n3️⃣ Testing non-streaming mode (stream=False)...")
    print("-" * 80)
    
    try:
        result = agent.run(query, stream=False)
        print(f"Result type: {type(result).__name__}")
        if hasattr(result, 'answer'):
            print(f"Answer: {result.answer}")
    except Exception as e:
        print(f"❌ Error in non-streaming: {e}")
    
    # Print timing summary
    print("\n" + "="*80)
    print("TIMING SUMMARY")
    print("="*80)
    timing_tracker.print_summary()


async def test_stream_to_gradio():
    """Test stream_to_gradio function directly."""
    print("\n\n4️⃣ Testing stream_to_gradio directly...")
    print("=" * 80)
    
    from smolagents.gradio_ui import stream_to_gradio
    
    # Create a simple agent
    agent = agent_runtime.create_codact_agent(
        session_id="test-gradio",
        step_callback=None,
        debug_mode=False
    )
    
    # Test stream_to_gradio
    query = "What is 2 + 2?"
    print(f"Query: {query}")
    
    try:
        generator = stream_to_gradio(agent=agent, task=query)
        
        item_count = 0
        for item in generator:
            item_count += 1
            item_type = type(item).__name__
            
            if isinstance(item, str):
                print(f"Item #{item_count}: String - {len(item)} chars")
            else:
                print(f"Item #{item_count}: {item_type}")
                
        print(f"\n✅ stream_to_gradio yielded {item_count} items")
        
    except Exception as e:
        print(f"\n❌ Error in stream_to_gradio: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    await test_agent_streaming()
    await test_stream_to_gradio()


if __name__ == "__main__":
    asyncio.run(main())
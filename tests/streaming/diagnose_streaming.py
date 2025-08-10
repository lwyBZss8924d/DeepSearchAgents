#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnose streaming configuration issues.

This script checks all the components involved in streaming.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_config():
    """Check configuration settings."""
    print("\n1️⃣ Checking Configuration")
    print("=" * 80)
    
    try:
        from src.core.config import get_config
        config = get_config()
        
        print("\n📋 Agent Configuration:")
        
        # Check React agent
        react_config = config.agents.get('react', {})
        print(f"\nReact Agent:")
        print(f"  • enable_streaming: {react_config.get('enable_streaming', 'NOT SET')}")
        print(f"  • max_steps: {react_config.get('max_steps', 'NOT SET')}")
        
        # Check CodeAct agent
        codact_config = config.agents.get('codact', {})
        print(f"\nCodeAct Agent:")
        print(f"  • enable_streaming: {codact_config.get('enable_streaming', 'NOT SET')}")
        print(f"  • max_steps: {codact_config.get('max_steps', 'NOT SET')}")
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")


def check_agent_creation():
    """Check how agents are created."""
    print("\n\n2️⃣ Checking Agent Creation")
    print("=" * 80)
    
    try:
        from src.agents.runtime import agent_runtime
        
        # Create CodeAct agent
        print("\nCreating CodeAct agent...")
        agent = agent_runtime.create_codact_agent(
            session_id="test",
            step_callback=None,
            debug_mode=True
        )
        
        print(f"\n📋 Created Agent:")
        print(f"  • Type: {type(agent).__name__}")
        print(f"  • Agent Type: {getattr(agent, 'agent_type', 'NOT SET')}")
        print(f"  • Enable Streaming: {getattr(agent, 'enable_streaming', 'NOT SET')}")
        
        # Check inner agent
        if hasattr(agent, 'agent'):
            inner = agent.agent
            print(f"\n📋 Inner Agent (smolagents):")
            print(f"  • Type: {type(inner).__name__}")
            print(f"  • Stream Outputs: {getattr(inner, 'stream_outputs', 'NOT SET')}")
            print(f"  • Max Steps: {getattr(inner, 'max_steps', 'NOT SET')}")
            
            # Check if run method supports streaming
            import inspect
            run_sig = inspect.signature(inner.run)
            print(f"  • Run method params: {list(run_sig.parameters.keys())}")
            
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()


def check_stream_to_gradio():
    """Check stream_to_gradio function."""
    print("\n\n3️⃣ Checking stream_to_gradio")
    print("=" * 80)
    
    try:
        from smolagents.gradio_ui import stream_to_gradio
        import inspect
        
        sig = inspect.signature(stream_to_gradio)
        print(f"\n📋 stream_to_gradio signature:")
        print(f"  • Parameters: {list(sig.parameters.keys())}")
        
        # Check source to see if it calls agent.run with stream=True
        source = inspect.getsource(stream_to_gradio)
        if "stream=True" in source:
            print("  • ✅ Calls agent.run with stream=True")
        else:
            print("  • ❌ Does NOT call agent.run with stream=True")
            
        # Look for the actual agent.run call
        import re
        run_calls = re.findall(r'agent\.run\([^)]+\)', source)
        if run_calls:
            print(f"\n  • Found agent.run calls:")
            for call in run_calls[:3]:  # Show first 3
                print(f"    - {call}")
                
    except Exception as e:
        print(f"❌ Error checking stream_to_gradio: {e}")


def check_websocket_flow():
    """Check WebSocket message flow."""
    print("\n\n4️⃣ Checking WebSocket Flow")
    print("=" * 80)
    
    try:
        # Check session process_query
        from src.api.v2.session import AgentSession
        import inspect
        
        process_sig = inspect.signature(AgentSession.process_query)
        print(f"\n📋 AgentSession.process_query:")
        print(f"  • Parameters: {list(process_sig.parameters.keys())}")
        print(f"  • Is async generator: {'async' in str(process_sig.return_annotation)}")
        
        # Check processor
        from src.api.v2.ds_agent_message_processor import DSAgentMessageProcessor
        
        process_sig = inspect.signature(DSAgentMessageProcessor.process_agent_stream)
        print(f"\n📋 DSAgentMessageProcessor.process_agent_stream:")
        print(f"  • Parameters: {list(process_sig.parameters.keys())}")
        
    except Exception as e:
        print(f"❌ Error checking WebSocket flow: {e}")


def main():
    """Run all diagnostics."""
    print("🔍 DeepSearchAgents Streaming Diagnostics")
    print("=" * 80)
    
    check_config()
    check_agent_creation()
    check_stream_to_gradio()
    check_websocket_flow()
    
    print("\n\n📊 Summary")
    print("=" * 80)
    print("Check the output above for any ❌ errors or NOT SET values.")
    print("These indicate potential issues with streaming configuration.")


if __name__ == "__main__":
    main()
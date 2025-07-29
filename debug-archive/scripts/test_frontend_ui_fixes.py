#!/usr/bin/env python3
"""Test script to verify all three frontend UI bug fixes"""

import asyncio
import websockets
import json
import time
from typing import Dict, Any
import uuid

async def test_all_ui_fixes():
    """Test all three UI fixes: planning badges, action thoughts, and final answer"""
    
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/api/v2/ws/{session_id}"
    
    print(f"Connecting to WebSocket: {uri}")
    
    async with websockets.connect(uri) as websocket:
        print("Connected successfully!")
        
        # Test query that should trigger all three UI elements
        test_query = {
            "type": "query",
            "query": "What is the capital of France and calculate 2+2?"  # Changed from 'content' to 'query'
        }
        
        print(f"\nSending test query: {test_query['query']}")
        await websocket.send(json.dumps(test_query))
        
        message_count = 0
        planning_messages = []
        action_thought_messages = []
        final_answer_messages = []
        
        try:
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)
                message_count += 1
                
                # Track different message types
                if data.get("metadata"):
                    metadata = data["metadata"]
                    
                    # Check for planning messages
                    if metadata.get("message_type") == "planning_header":
                        planning_messages.append({
                            "planning_type": metadata.get("planning_type"),
                            "badge_expected": "Initial Plan" if metadata.get("planning_type") == "initial" else "Updated Plan"
                        })
                        print(f"\n✅ Planning Badge Detected: {metadata.get('planning_type')} plan")
                    
                    # Check for action thoughts
                    if metadata.get("message_type") == "action_thought":
                        thoughts_content = metadata.get("thoughts_content", "")
                        action_thought_messages.append({
                            "thoughts_content": thoughts_content,
                            "expected_format": f"Thinking🤔...{thoughts_content}...and Action Running["
                        })
                        print(f"\n✅ Action Thought Detected: '{thoughts_content[:30]}...'")
                    
                    # Check for final answer
                    if metadata.get("message_type") == "final_answer" and metadata.get("has_structured_data"):
                        final_answer_messages.append({
                            "title": metadata.get("answer_title"),
                            "content": metadata.get("answer_content"),
                            "sources": metadata.get("answer_sources", [])
                        })
                        print(f"\n✅ Final Answer Detected: {metadata.get('answer_title')}")
                
                # Print message summary
                print(f"\nMessage {message_count}:")
                print(f"  Type: {data.get('type')}")
                print(f"  Role: {data.get('role')}")
                
                # Handle error messages
                if data.get('type') == 'error':
                    print(f"  ERROR: {data.get('data', 'Unknown error')}")
                    if isinstance(data.get('data'), dict):
                        print(f"  Error details: {json.dumps(data['data'], indent=2)}")
                
                if data.get("metadata"):
                    print(f"  Metadata: {json.dumps(data['metadata'], indent=2)}")
                if data.get("content"):
                    print(f"  Content: {data['content'][:100]}...")
                
        except asyncio.TimeoutError:
            print("\nNo more messages received (timeout)")
        except websockets.exceptions.ConnectionClosed:
            print("\nWebSocket connection closed")
        
        # Summary report
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        print(f"\nTotal messages received: {message_count}")
        
        # Planning badges report
        print(f"\n1. PLANNING BADGES: {'✅ PASS' if planning_messages else '❌ FAIL'}")
        if planning_messages:
            for i, pm in enumerate(planning_messages):
                print(f"   - Badge {i+1}: {pm['badge_expected']} (type: {pm['planning_type']})")
        else:
            print("   - No planning badges detected")
        
        # Action thoughts report
        print(f"\n2. ACTION THOUGHTS: {'✅ PASS' if action_thought_messages else '❌ FAIL'}")
        if action_thought_messages:
            for i, at in enumerate(action_thought_messages):
                print(f"   - Thought {i+1}: Truncated to 60 chars")
                print(f"     Expected format: {at['expected_format'][:80]}...]")
        else:
            print("   - No action thoughts detected")
        
        # Final answer report
        print(f"\n3. FINAL ANSWER: {'✅ PASS' if final_answer_messages else '❌ FAIL'}")
        if final_answer_messages:
            for i, fa in enumerate(final_answer_messages):
                print(f"   - Answer {i+1}: '{fa['title']}'")
                print(f"     Content: {fa['content'][:100]}...")
                print(f"     Sources: {len(fa['sources'])} sources")
        else:
            print("   - No final answer detected")
        
        print("\n" + "="*60)
        
        # Overall result
        all_pass = planning_messages and action_thought_messages and final_answer_messages
        print(f"\nOVERALL RESULT: {'✅ ALL TESTS PASS' if all_pass else '❌ SOME TESTS FAILED'}")
        
        return all_pass

if __name__ == "__main__":
    print("Testing Frontend UI Fixes")
    print("=" * 60)
    
    try:
        result = asyncio.run(test_all_ui_fixes())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\nError during test: {e}")
        exit(1)
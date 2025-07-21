#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/test_api.py
# code style: PEP 8

"""
Simple test script for Web API v2.

Tests basic functionality of the new event-driven API.
"""

import asyncio
import json
import logging
from typing import List
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_api():
    """Test WebSocket API functionality."""
    session_id = "test-session-123"
    uri = f"ws://localhost:8000/api/v2/ws/agent/{session_id}"
    
    logger.info(f"Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected successfully")
            
            # Send a query
            query = {
                "type": "query",
                "query": "What is 2 + 2?"
            }
            
            await websocket.send(json.dumps(query))
            logger.info(f"Sent query: {query['query']}")
            
            # Collect events
            events: List[dict] = []
            
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=30.0
                    )
                    
                    event = json.loads(message)
                    events.append(event)
                    
                    logger.info(
                        f"Event: {event.get('event_type', 'unknown')} - "
                        f"{event.get('event_id', 'no-id')}"
                    )
                    
                    # Log specific event types
                    if event.get('event_type') == 'agent_thought':
                        logger.info(f"Thought: {event.get('content', '')[:100]}...")
                    elif event.get('event_type') == 'code_generated':
                        logger.info(f"Code: {event.get('code', '')[:100]}...")
                    elif event.get('event_type') == 'final_answer':
                        logger.info(f"Answer: {event.get('content', '')}")
                    elif event.get('event_type') == 'task_complete':
                        logger.info("Task completed!")
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for events")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Connection closed")
                    break
            
            logger.info(f"Total events received: {len(events)}")
            
            # Print summary
            event_types = {}
            for event in events:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            logger.info("Event summary:")
            for event_type, count in event_types.items():
                logger.info(f"  {event_type}: {count}")
                
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")


async def test_rest_api():
    """Test REST API functionality."""
    import aiohttp
    
    base_url = "http://localhost:8000/api/v2"
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Health check: {data}")
                else:
                    logger.error(f"Health check failed: {response.status}")
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        # Test query submission
        try:
            query_data = {
                "query": "What is the capital of France?",
                "agent_type": "codact",
                "stream": False
            }
            
            async with session.post(
                f"{base_url}/agent/query",
                json=query_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Query response: {data}")
                    
                    # Get session events
                    session_id = data.get('session_id')
                    if session_id:
                        await asyncio.sleep(5)  # Wait for processing
                        
                        async with session.get(
                            f"{base_url}/session/{session_id}/events"
                        ) as events_response:
                            if events_response.status == 200:
                                events_data = await events_response.json()
                                logger.info(
                                    f"Events: {events_data.get('total', 0)} total"
                                )
                else:
                    logger.error(f"Query submission failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"REST API test error: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting Web API v2 tests...")
    
    # Test REST API
    logger.info("\n=== Testing REST API ===")
    await test_rest_api()
    
    # Test WebSocket API
    logger.info("\n=== Testing WebSocket API ===")
    await test_websocket_api()
    
    logger.info("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python
"""Test frontend rendering of final answer with structured metadata"""

import asyncio
import json
import logging
import websockets
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def simulate_frontend():
    """Simulate frontend WebSocket connection and message handling"""
    uri = "ws://localhost:8000/v2/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket")
            
            # Send query
            query_msg = {
                "type": "start",
                "data": {
                    "query": "What is 2+2? Please provide a final answer with title 'Simple Math' and sources.",
                    "agent_type": "codact",
                    "reset_agent_memory": True,
                    "session_id": f"test-frontend-{datetime.now().isoformat()}",
                }
            }
            
            await websocket.send(json.dumps(query_msg))
            logger.info(f"Sent query: {query_msg['data']['query']}")
            
            # Process messages
            final_answer_received = False
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    
                    if data.get("metadata", {}).get("message_type") == "final_answer":
                        final_answer_received = True
                        logger.info("=" * 60)
                        logger.info("FINAL ANSWER RECEIVED - SIMULATING FRONTEND RENDERING")
                        logger.info("=" * 60)
                        
                        metadata = data.get("metadata", {})
                        content = data.get("content", "")
                        
                        # Simulate frontend logic from final-answer-display.tsx
                        if metadata.get("has_structured_data") and metadata.get("answer_format") == "json":
                            logger.info("✅ Frontend detected structured data in metadata")
                            logger.info(f"Title: {metadata.get('answer_title', 'Final Answer')}")
                            logger.info(f"Content: {metadata.get('answer_content', '')[:200]}...")
                            logger.info(f"Sources: {metadata.get('answer_sources', [])}")
                            logger.info("\nFRONTEND WOULD RENDER:")
                            logger.info("- Card with title from metadata")
                            logger.info("- Markdown content from metadata")
                            logger.info("- Sources list from metadata")
                            logger.info("- NO RAW JSON VISIBLE")
                        else:
                            logger.warning("❌ Frontend did not detect structured data")
                            logger.warning(f"Raw content would be displayed: {content[:200]}...")
                            logger.warning("This is the bug - raw JSON shown to user")
                        
                        break
                        
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for messages")
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    if final_answer_received:
                        break
                    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_frontend())
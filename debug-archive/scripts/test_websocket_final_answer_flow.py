#!/usr/bin/env python
"""
Comprehensive test script to trace Final Answer message flow from backend to frontend.
This script will:
1. Send a query that triggers a final_answer response
2. Log the exact DSAgentRunMessage structure sent by the backend
3. Capture and analyze WebSocket messages
4. Identify where structured metadata might be getting lost
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import websockets
from httpx import AsyncClient

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.v2.models import DSAgentQuery, DSAgentRunMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("final_answer_flow_debug.log", mode="w"),
    ],
)
logger = logging.getLogger(__name__)

# Test configuration
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/v2/ws"
TEST_QUERY = "What is 2+2? Please provide a final answer with title 'Simple Math' and sources."


class WebSocketMessageLogger:
    """Log and analyze WebSocket messages"""

    def __init__(self):
        self.messages = []
        self.final_answer_messages = []
        self.message_count = 0

    def log_message(self, raw_message: str):
        """Log a raw WebSocket message"""
        self.message_count += 1
        try:
            # Parse the message
            data = json.loads(raw_message)
            
            # Create a detailed log entry
            log_entry = {
                "index": self.message_count,
                "timestamp": datetime.now().isoformat(),
                "raw_length": len(raw_message),
                "parsed": data,
            }
            
            # Check if it's a DSAgentRunMessage
            if "role" in data and "metadata" in data:
                metadata = data.get("metadata", {})
                message_type = metadata.get("message_type", "unknown")
                
                log_entry["message_type"] = message_type
                log_entry["has_content"] = bool(data.get("content"))
                log_entry["content_preview"] = data.get("content", "")[:100]
                
                # Special handling for final_answer messages
                if message_type == "final_answer":
                    log_entry["is_final_answer"] = True
                    log_entry["has_structured_data"] = metadata.get("has_structured_data", False)
                    log_entry["answer_format"] = metadata.get("answer_format")
                    log_entry["answer_title"] = metadata.get("answer_title")
                    log_entry["answer_content_preview"] = (metadata.get("answer_content", "")[:100] 
                                                          if metadata.get("answer_content") else None)
                    log_entry["answer_sources"] = metadata.get("answer_sources")
                    self.final_answer_messages.append(log_entry)
                    
                    # Log critical info
                    logger.info(f"🎯 FINAL ANSWER MESSAGE #{self.message_count}:")
                    logger.info(f"  - Content: '{data.get('content', '')}'")
                    logger.info(f"  - Has structured data: {metadata.get('has_structured_data')}")
                    logger.info(f"  - Title in metadata: {metadata.get('answer_title')}")
                    logger.info(f"  - Content in metadata: {bool(metadata.get('answer_content'))}")
                    logger.info(f"  - Sources in metadata: {metadata.get('answer_sources')}")
            
            self.messages.append(log_entry)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message #{self.message_count}: {e}")
            self.messages.append({
                "index": self.message_count,
                "error": str(e),
                "raw": raw_message[:200],
            })

    def analyze_final_answers(self):
        """Analyze all final answer messages"""
        if not self.final_answer_messages:
            logger.warning("No final answer messages found!")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"FINAL ANSWER ANALYSIS - Found {len(self.final_answer_messages)} final answer message(s)")
        logger.info(f"{'='*60}")
        
        for msg in self.final_answer_messages:
            logger.info(f"\nFinal Answer Message #{msg['index']}:")
            logger.info(f"  Timestamp: {msg['timestamp']}")
            
            # Check content field
            content = msg['parsed'].get('content', '')
            logger.info(f"  Content field: {repr(content)}")
            logger.info(f"  Content is empty: {content == ''}")
            
            # Check metadata
            metadata = msg['parsed'].get('metadata', {})
            logger.info(f"  Metadata keys: {list(metadata.keys())}")
            
            # Check structured data flags
            if metadata.get('has_structured_data'):
                logger.info("  ✅ Has structured data flag is True")
                logger.info(f"  ✅ Answer format: {metadata.get('answer_format')}")
                logger.info(f"  ✅ Answer title: {metadata.get('answer_title')}")
                logger.info(f"  ✅ Answer content exists: {bool(metadata.get('answer_content'))}")
                logger.info(f"  ✅ Answer sources: {metadata.get('answer_sources')}")
            else:
                logger.info("  ❌ No structured data flag or it's False")
            
            # Check if content has raw JSON
            if content.strip().startswith('{') and content.strip().endswith('}'):
                logger.warning("  ⚠️  Content field contains raw JSON - this will be displayed as-is!")
                try:
                    json_data = json.loads(content)
                    logger.info(f"  JSON keys: {list(json_data.keys())}")
                except:
                    pass

    def save_detailed_log(self, filename="websocket_messages_detailed.json"):
        """Save all messages to a detailed log file"""
        with open(filename, "w") as f:
            json.dump({
                "total_messages": self.message_count,
                "final_answer_count": len(self.final_answer_messages),
                "messages": self.messages,
                "final_answers": self.final_answer_messages,
            }, f, indent=2)
        logger.info(f"Saved detailed log to {filename}")


async def test_final_answer_flow():
    """Test the complete final answer flow"""
    msg_logger = WebSocketMessageLogger()
    
    try:
        # Start WebSocket connection
        logger.info("Connecting to WebSocket...")
        async with websockets.connect(WS_URL) as websocket:
            logger.info("WebSocket connected")
            
            # Send the query
            query = DSAgentQuery(
                query=TEST_QUERY,
                agent_type="codact",
                reset_agent_memory=True,
            )
            
            logger.info(f"Sending query: {TEST_QUERY}")
            await websocket.send(query.model_dump_json())
            
            # Receive messages
            logger.info("Waiting for messages...")
            start_time = time.time()
            timeout = 30  # 30 second timeout
            
            while True:
                try:
                    # Set a timeout for each message
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=5.0
                    )
                    
                    logger.debug(f"Received message (length: {len(message)})")
                    msg_logger.log_message(message)
                    
                    # Check if we have final answer
                    if msg_logger.final_answer_messages:
                        logger.info("Received final answer, waiting for any remaining messages...")
                        # Wait a bit more for any trailing messages
                        try:
                            extra_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            msg_logger.log_message(extra_msg)
                        except asyncio.TimeoutError:
                            break
                    
                    # Overall timeout check
                    if time.time() - start_time > timeout:
                        logger.warning("Overall timeout reached")
                        break
                        
                except asyncio.TimeoutError:
                    if msg_logger.final_answer_messages:
                        logger.info("No more messages after final answer")
                        break
                    else:
                        logger.warning("Timeout waiting for messages (no final answer yet)")
                        break
                except websockets.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    break
            
            logger.info(f"Total messages received: {msg_logger.message_count}")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        return
    
    # Analyze results
    msg_logger.analyze_final_answers()
    msg_logger.save_detailed_log()
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total messages: {msg_logger.message_count}")
    logger.info(f"Final answer messages: {len(msg_logger.final_answer_messages)}")
    
    if msg_logger.final_answer_messages:
        final_msg = msg_logger.final_answer_messages[0]
        metadata = final_msg['parsed'].get('metadata', {})
        content = final_msg['parsed'].get('content', '')
        
        logger.info("\nFinal Answer Message Status:")
        logger.info(f"  - Content is empty: {content == ''}")
        logger.info(f"  - Has structured data: {metadata.get('has_structured_data', False)}")
        logger.info(f"  - Answer format: {metadata.get('answer_format', 'not set')}")
        
        if content and content.strip().startswith('{'):
            logger.error("  ❌ ISSUE: Content field contains raw JSON!")
            logger.error("     This will be displayed as-is in the UI")
            logger.error("     Backend should send empty content when structured data is in metadata")
        elif not content and metadata.get('has_structured_data'):
            logger.info("  ✅ CORRECT: Empty content with structured data in metadata")
            logger.info("     Frontend should use metadata fields for rendering")
        else:
            logger.warning("  ⚠️  Unexpected state - needs investigation")
    
    # Also test via HTTP API to compare
    logger.info(f"\n{'='*60}")
    logger.info("Testing via HTTP API for comparison...")
    logger.info(f"{'='*60}")
    
    async with AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/v2/query",
            json={
                "query": TEST_QUERY,
                "agent_type": "codact",
                "reset_agent_memory": True,
            },
            timeout=30.0,
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"HTTP API response received")
            logger.info(f"  Final answer: {result.get('final_answer', 'not found')[:200]}...")
            
            # Check if final answer is JSON
            final_answer = result.get('final_answer', '')
            if final_answer.strip().startswith('{'):
                try:
                    fa_json = json.loads(final_answer)
                    logger.info(f"  Final answer is JSON with keys: {list(fa_json.keys())}")
                except:
                    pass
        else:
            logger.error(f"HTTP API error: {response.status_code}")


if __name__ == "__main__":
    logger.info("Starting Final Answer Flow Debug Test")
    logger.info(f"Test query: {TEST_QUERY}")
    asyncio.run(test_final_answer_flow())
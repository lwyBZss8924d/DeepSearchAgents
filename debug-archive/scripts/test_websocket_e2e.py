#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-end WebSocket test for action_thought message handling

This script:
1. Connects to the running Web API v2 WebSocket
2. Sends a query that triggers ActionStep with Thought
3. Captures and logs all messages
4. Helps identify where the frontend issue occurs
"""

import asyncio
import websockets
import json
import logging
import sys
from datetime import datetime
import uuid

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('websocket_e2e_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
BACKEND_URL = "ws://localhost:8000/api/v2/ws"
FRONTEND_URL = "http://localhost:3000"

class WebSocketTester:
    def __init__(self):
        self.messages_received = []
        self.action_thought_messages = []
        self.final_answer_messages = []
        self.planning_messages = []
        
    async def test_agent_flow(self):
        """Test the complete agent flow"""
        # Generate a unique session ID
        session_id = f"test-{uuid.uuid4().hex[:8]}"
        ws_url = f"{BACKEND_URL}/{session_id}?agent_type=codact"
        
        logger.info(f"Connecting to WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected successfully!")
                
                # Send a query that will trigger agent thinking
                query = {
                    "type": "query",
                    "query": "Solve the differential equation: y' = y^x"
                }
                
                logger.info(f"Sending query: {json.dumps(query, indent=2)}")
                await websocket.send(json.dumps(query))
                
                # Listen for messages
                logger.info("Listening for messages...")
                message_count = 0
                
                while True:
                    try:
                        # Set a timeout to avoid hanging forever
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=30.0
                        )
                        
                        data = json.loads(message)
                        message_count += 1
                        
                        # Store all messages
                        self.messages_received.append(data)
                        
                        # Log basic info
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Message #{message_count}")
                        logger.info(f"{'='*60}")
                        
                        # The WebSocket sends DSAgentRunMessage directly
                        # Check if it's an error message
                        if data.get('error'):
                            logger.error(f"Error message: {data}")
                        # Check if it's a completion message
                        elif data.get('metadata', {}).get('is_final_answer'):
                            self.analyze_agent_message(data, message_count)
                            logger.info("Final answer received, agent likely completed")
                            # Don't break - let's see all messages
                        else:
                            # Regular agent message
                            self.analyze_agent_message(data, message_count)
                            
                    except asyncio.TimeoutError:
                        logger.info("No more messages (timeout)")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("WebSocket connection closed")
                        break
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            
        # Generate report
        self.generate_report()
        
    def analyze_agent_message(self, data, count):
        """Analyze DSAgentRunMessage structure"""
        # The message IS the DSAgentRunMessage, not wrapped
        msg = data
        
        # Extract key fields
        message_id = msg.get('message_id', 'N/A')
        content = msg.get('content', '')
        metadata = msg.get('metadata', {})
        step_number = msg.get('step_number', 0)
        
        # Log structure
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Step Number: {step_number}")
        logger.info(f"Content Length: {len(content)}")
        logger.info(f"Content Preview: {content[:100]}..." if content else "Content: EMPTY")
        
        # Log metadata
        if metadata:
            logger.info("Metadata:")
            for key, value in metadata.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.info("Metadata: NONE")
            
        # Categorize message
        message_type = metadata.get('message_type', '')
        
        if message_type == 'action_thought':
            self.action_thought_messages.append({
                'count': count,
                'message_id': message_id,
                'content': content,
                'metadata': metadata,
                'step_number': step_number
            })
            logger.info(">>> ACTION THOUGHT MESSAGE DETECTED! <<<")
            logger.info(f"Expected display: Thinking🤔...{content[:60]}...and Action Running[<Terminal />]...")
            
        elif message_type == 'final_answer':
            self.final_answer_messages.append({
                'count': count,
                'message_id': message_id,
                'content': content,
                'metadata': metadata
            })
            logger.info(">>> FINAL ANSWER MESSAGE DETECTED! <<<")
            
        elif message_type in ['planning_header', 'planning_content']:
            self.planning_messages.append({
                'count': count,
                'message_id': message_id,
                'message_type': message_type,
                'planning_type': metadata.get('planning_type', ''),
                'content': content,
                'metadata': metadata
            })
            logger.info(f">>> PLANNING MESSAGE DETECTED: {message_type} <<<")
            
    def generate_report(self):
        """Generate a summary report"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY REPORT")
        logger.info("="*80)
        
        logger.info(f"Total messages received: {len(self.messages_received)}")
        logger.info(f"Action thought messages: {len(self.action_thought_messages)}")
        logger.info(f"Final answer messages: {len(self.final_answer_messages)}")
        logger.info(f"Planning messages: {len(self.planning_messages)}")
        
        # Detail action thoughts
        if self.action_thought_messages:
            logger.info("\n" + "-"*60)
            logger.info("ACTION THOUGHT MESSAGES:")
            logger.info("-"*60)
            for msg in self.action_thought_messages:
                logger.info(f"Message #{msg['count']}:")
                logger.info(f"  ID: {msg['message_id']}")
                logger.info(f"  Step: {msg['step_number']}")
                logger.info(f"  Content: {msg['content'][:100]}...")
                logger.info(f"  Metadata: {json.dumps(msg['metadata'], indent=4)}")
                logger.info("")
                
        # Detail planning messages
        if self.planning_messages:
            logger.info("\n" + "-"*60)
            logger.info("PLANNING MESSAGES:")
            logger.info("-"*60)
            for msg in self.planning_messages:
                logger.info(f"Message #{msg['count']}:")
                logger.info(f"  Type: {msg['message_type']}")
                logger.info(f"  Planning Type: {msg['planning_type']}")
                logger.info(f"  Content Empty: {not bool(msg['content'])}")
                logger.info("")
                
        # Frontend debugging instructions
        logger.info("\n" + "="*80)
        logger.info("FRONTEND DEBUGGING INSTRUCTIONS:")
        logger.info("="*80)
        logger.info("1. Open browser console at http://localhost:3000")
        logger.info("2. Look for these console logs:")
        logger.info("   - [WebSocket] ACTION_THOUGHT message received")
        logger.info("   - [Action Thought FILTER]")
        logger.info("   - [renderAssistantMessage] Full message")
        logger.info("   - [ACTION_THOUGHT DETECTED]")
        logger.info("   - [RENDER CONDITION CHECK]")
        logger.info("3. Check if ActionThoughtCard component is rendered")
        logger.info("4. Verify planning badges are visible")
        logger.info("5. Check final answer is formatted, not JSON")

async def main():
    tester = WebSocketTester()
    await tester.test_agent_flow()

if __name__ == "__main__":
    logger.info("Starting WebSocket E2E Test")
    logger.info(f"Backend: {BACKEND_URL}")
    logger.info(f"Frontend: {FRONTEND_URL}")
    logger.info("-"*60)
    
    asyncio.run(main())
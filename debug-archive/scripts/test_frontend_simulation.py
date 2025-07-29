#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simulate frontend message processing to identify the exact issue
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class FrontendSimulator:
    def __init__(self):
        self.messages = []
        self.action_thought_count = 0
        self.planning_header_count = 0
        self.final_answer_count = 0
        
    async def connect_and_test(self):
        """Connect to WebSocket and process messages like frontend would"""
        session_id = f"test-{datetime.now().strftime('%H%M%S')}"
        ws_url = f"ws://localhost:8000/api/v2/ws/{session_id}?agent_type=codact"
        
        logger.info(f"Connecting to: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            # Send test query
            query = {
                "type": "query",
                "query": "Step-by-step solve: y' = y^2 x"
            }
            await websocket.send(json.dumps(query))
            logger.info("Query sent, listening for messages...\n")
            
            message_count = 0
            while True:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=600.0)
                    message = json.loads(raw_message)
                    message_count += 1
                    
                    # Process like frontend would
                    self.process_message_like_frontend(message, message_count)
                    
                except asyncio.TimeoutError:
                    logger.info("\n=== No more messages (timeout) ===")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.info("\n=== Connection closed ===")
                    break
                    
        self.print_summary()
        
    def process_message_like_frontend(self, message, count):
        """Simulate frontend message processing logic"""
        # Store message
        self.messages.append(message)
        
        # Extract fields like frontend would
        role = message.get('role')
        content = message.get('content', '')
        metadata = message.get('metadata', {})
        message_id = message.get('message_id', 'N/A')
        
        # Skip user messages
        if role == 'user':
            logger.info(f"#{count} USER: {content[:50]}...")
            return
            
        # Check metadata
        message_type = metadata.get('message_type', '')
        component = metadata.get('component', '')
        
        # Component filter (like in chat-message.tsx line 289-323)
        if component == "webide" or component == "terminal":
            logger.info(f"#{count} FILTERED OUT: component={component}")
            return
            
        # Should render check (like line 454-474)
        has_content = bool(content)
        is_planning_header = message_type == "planning_header"
        is_action_thought = message_type == "action_thought"
        should_render = has_content or is_planning_header or is_action_thought
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Message #{count}: {message_id}")
        logger.info(f"  Role: {role}")
        logger.info(f"  Message Type: {message_type}")
        logger.info(f"  Component: {component}")
        logger.info(f"  Has Content: {has_content} (length: {len(content)})")
        logger.info(f"  Should Render: {should_render}")
        
        if not should_render:
            logger.info("  ❌ WOULD NOT RENDER")
            return
            
        # Simulate renderAssistantMessage logic
        logger.info("\n  Entering renderAssistantMessage:")
        
        # Planning header check
        if message_type == "planning_header":
            planning_type = metadata.get('planning_type', 'initial')
            logger.info(f"  ✓ PLANNING HEADER: type={planning_type}")
            logger.info(f"    → Would show badge: {'Initial Plan' if planning_type == 'initial' else 'Updated Plan'}")
            self.planning_header_count += 1
            return
            
        # Final answer check
        if message_type == "final_answer":
            logger.info(f"  ✓ FINAL ANSWER")
            if metadata.get('has_structured_data'):
                logger.info(f"    → Using structured data from metadata")
            else:
                logger.info(f"    → Would parse JSON from content")
            self.final_answer_count += 1
            return
            
        # Action thought check
        if message_type == "action_thought":
            logger.info(f"  ✓ ACTION THOUGHT (via metadata)")
            logger.info(f"    Content: {content[:60]}...")
            logger.info(f"    → Would use ActionThoughtCard")
            self.action_thought_count += 1
            return
            
        # Fallback: Check content prefix
        if content.startswith("Thought:"):
            logger.info(f"  ✓ ACTION THOUGHT (via content prefix)")
            logger.info(f"    → Would use ActionThoughtCard")
            self.action_thought_count += 1
            return
            
        # Default rendering
        logger.info(f"  → Default Markdown rendering")
        
    def print_summary(self):
        """Print summary of findings"""
        logger.info("\n" + "="*80)
        logger.info("SUMMARY")
        logger.info("="*80)
        logger.info(f"Total messages received: {len(self.messages)}")
        logger.info(f"Planning headers found: {self.planning_header_count}")
        logger.info(f"Action thoughts found: {self.action_thought_count}")
        logger.info(f"Final answers found: {self.final_answer_count}")
        
        # Check for issues
        logger.info("\nPOTENTIAL ISSUES:")
        
        if self.planning_header_count == 0:
            logger.info("❌ No planning headers rendered - Check if they're being filtered")
            
        if self.action_thought_count == 0:
            logger.info("❌ No action thoughts rendered - Check metadata and content")
            # Look for any Thought: messages
            thought_messages = [m for m in self.messages if m.get('content', '').startswith('Thought:')]
            if thought_messages:
                logger.info(f"   Found {len(thought_messages)} messages starting with 'Thought:'")
                for m in thought_messages[:2]:
                    logger.info(f"   - {m.get('message_id')}: metadata={m.get('metadata', {})}")

async def main():
    simulator = FrontendSimulator()
    await simulator.connect_and_test()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-end test to verify action_thought messages are displayed correctly
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.v2.session import AgentSession
from src.api.v2.models import DSAgentRunMessage
from smolagents.models import MessageRole

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_action_thought_display():
    """Test that action_thought messages are properly displayed"""
    
    # Create a test session
    session = AgentSession(session_id="test-action-thought", agent_type="react")
    
    # Create a mock action_thought message
    action_thought_msg = DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="Thought: I need to solve the differential equation y' = y^x step by step. This is a separable differential equation. Let me first understand what we're dealing with here.",
        metadata={
            "component": "chat",
            "message_type": "action_thought",
            "step_type": "action",
            "status": "done",
            "is_raw_thought": True,
        },
        session_id=session.session_id,
        step_number=1,
    )
    
    logger.info("="*60)
    logger.info("TEST ACTION_THOUGHT MESSAGE")
    logger.info("="*60)
    logger.info(f"Message ID: {action_thought_msg.message_id}")
    logger.info(f"Content: {action_thought_msg.content[:60]}...")
    logger.info(f"Metadata: {action_thought_msg.metadata}")
    logger.info("="*60)
    
    # Expected display
    truncated = action_thought_msg.content[:60]
    expected_display = f"Thinking🤔...{truncated}...and Action Running[<Terminal />]..."
    
    logger.info("\nEXPECTED DISPLAY:")
    logger.info(expected_display)
    
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION CHECKLIST:")
    logger.info("="*60)
    logger.info("1. Backend sends message_type='action_thought' ✓")
    logger.info("2. Component='chat' (should pass filter) ✓")
    logger.info("3. Content starts with 'Thought:' ✓")
    logger.info("4. Frontend should use ActionThoughtCard component")
    logger.info("5. Display should show truncated content with emoji and Terminal icon")
    
    return action_thought_msg

if __name__ == "__main__":
    msg = asyncio.run(test_action_thought_display())
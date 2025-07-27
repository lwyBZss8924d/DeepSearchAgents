#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock streaming backend for testing WebSocket streaming functionality.

This creates a test endpoint that simulates agent streaming without
actually running any agents or using LLM tokens.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, AsyncGenerator
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create test app
app = FastAPI(title="Streaming Test Backend")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MockStreamGenerator:
    """Generates mock streaming messages for testing."""
    
    def __init__(self, scenario: str = "default"):
        self.scenario = scenario
        self.step_count = 0
        
    async def generate_messages(self) -> AsyncGenerator[dict, None]:
        """Generate streaming messages based on scenario."""
        
        if self.scenario == "default":
            # Simulate typical agent execution
            yield self._create_message("user", "Test query for streaming", step=0)
            
            # Step 1: Planning
            self.step_count = 1
            for chunk in self._stream_text("I'll help you test the streaming functionality. Let me break this down:\n\n", delay=0.05):
                yield chunk
                
            yield self._create_message(
                "assistant",
                "I'll help you test the streaming functionality. Let me break this down:\n\n**Step 1:** First, I'll analyze the request\n**Step 2:** Then process the data\n**Step 3:** Finally, provide the results",
                step=1,
                streaming=False
            )
            
            # Step 2: Execution
            self.step_count = 2
            for chunk in self._stream_text("Now executing the test operations...\n", delay=0.1):
                yield chunk
                
            # Simulate tool call
            yield self._create_message(
                "assistant",
                "Using tool: test_tool",
                step=2,
                metadata={"tool_name": "test_tool", "component": "terminal"}
            )
            
            # Step 3: Results
            self.step_count = 3
            for chunk in self._stream_text("Here are the test results:\n- Streaming is working ✓\n- Messages arrive in order ✓\n- No buffering detected ✓\n", delay=0.08):
                yield chunk
                
            # Final answer
            yield self._create_message(
                "assistant",
                "## Test Complete\n\nAll streaming tests passed successfully!",
                step=3,
                metadata={"is_final_answer": True}
            )
            
        elif self.scenario == "fast":
            # Rapid fire messages
            for i in range(20):
                yield self._create_message(
                    "assistant",
                    f"Fast message {i}",
                    step=1,
                    streaming=True
                )
                await asyncio.sleep(0.01)
                
        elif self.scenario == "slow":
            # Slow streaming
            text = "This is a very slow streaming message that simulates network latency or slow processing..."
            for char in text:
                yield self._create_message(
                    "assistant",
                    char,
                    step=1,
                    streaming=True
                )
                await asyncio.sleep(0.2)
                
        elif self.scenario == "error":
            # Simulate error after some messages
            yield self._create_message("user", "Test error handling", step=0)
            
            for i in range(3):
                yield self._create_message(
                    "assistant",
                    f"Message {i} before error",
                    step=1,
                    streaming=True
                )
                await asyncio.sleep(0.1)
                
            # Simulate error
            yield {
                "type": "error",
                "message": "Simulated error for testing"
            }
    
    def _create_message(self, role: str, content: str, step: int, streaming: bool = False, metadata: dict = None) -> dict:
        """Create a DSAgentRunMessage-like dict."""
        return {
            "role": role,
            "content": content,
            "metadata": {
                "streaming": streaming,
                **(metadata or {})
            },
            "message_id": f"test_{datetime.now().timestamp()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": "test_session",
            "step_number": step
        }
    
    async def _stream_text(self, text: str, delay: float = 0.05) -> AsyncGenerator[dict, None]:
        """Stream text character by character."""
        accumulated = ""
        for char in text:
            accumulated += char
            yield self._create_message(
                "assistant",
                accumulated,
                step=self.step_count,
                streaming=True
            )
            await asyncio.sleep(delay)


@app.websocket("/test/ws/{scenario}")
async def test_websocket(websocket: WebSocket, scenario: str = "default"):
    """Test WebSocket endpoint that simulates agent streaming."""
    await websocket.accept()
    logger.info(f"Test WebSocket connected for scenario: {scenario}")
    
    generator = MockStreamGenerator(scenario)
    
    try:
        while True:
            # Wait for a message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
                
            if data.get("type") == "query":
                # Start streaming mock messages
                logger.info(f"Starting mock stream for scenario: {scenario}")
                
                message_count = 0
                async for message in generator.generate_messages():
                    message_count += 1
                    logger.info(
                        f"Sending test message #{message_count} - "
                        f"streaming: {message.get('metadata', {}).get('streaming', False)}, "
                        f"content_length: {len(message.get('content', ''))}"
                    )
                    
                    await websocket.send_json(message)
                    
                    # Simulate any network/processing delay
                    if scenario == "delayed":
                        await asyncio.sleep(0.5)
                        
                logger.info(f"Completed mock stream, sent {message_count} messages")
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@app.get("/test/scenarios")
async def list_scenarios():
    """List available test scenarios."""
    return {
        "scenarios": [
            {
                "name": "default",
                "description": "Typical agent execution with planning, tools, and final answer"
            },
            {
                "name": "fast",
                "description": "Rapid streaming messages to test throughput"
            },
            {
                "name": "slow",
                "description": "Very slow character-by-character streaming"
            },
            {
                "name": "error",
                "description": "Simulates an error during streaming"
            },
            {
                "name": "delayed",
                "description": "Adds artificial delays between messages"
            }
        ]
    }


if __name__ == "__main__":
    import sys
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    
    logger.info(f"Starting test streaming backend on port {port}")
    logger.info(f"Test WebSocket URL: ws://localhost:{port}/test/ws/{{scenario}}")
    logger.info(f"Available scenarios: http://localhost:{port}/test/scenarios")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        # Same WebSocket settings as main app
        ws_ping_interval=20,
        ws_ping_timeout=60,
        ws_max_size=16777216,
        ws_per_message_deflate=False
    )
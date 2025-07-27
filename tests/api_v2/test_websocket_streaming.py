#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/api_v2/test_websocket_streaming.py
# code style: PEP 8

"""
Main WebSocket streaming tests for DeepSearchAgents Web API v2.
"""

import pytest
import asyncio
import json
from typing import Dict, Any

from tests.api_v2.utils import (
    websocket_session, assert_message_format,
    MessageCollector, WebSocketManager
)


class TestWebSocketStreaming:
    """Test WebSocket streaming functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_client, websocket_url):
        """Test basic WebSocket connection."""
        async with test_client.websocket_connect(websocket_url) as websocket:
            # Send ping
            await websocket.send_json({"type": "ping"})

            # Receive pong
            response = await websocket.receive_json()
            assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_query_submission(self, test_client, websocket_url):
        """Test submitting a query and receiving response."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Send simple query
            await manager.send_query("Solve the quadratic equation x^2 - 5x + 6 = 0")

            # Wait for at least 2 messages (user + assistant)
            messages = await manager.wait_for_messages(2, timeout=1000)

            # Validate first message is user message
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Solve the quadratic equation x^2 - 5x + 6 = 0"
            assert_message_format(messages[0])

            # Validate we get assistant response
            assert any(msg["role"] == "assistant" for msg in messages)

    @pytest.mark.asyncio
    async def test_streaming_updates(self, api_client):
        """Test that messages are streamed progressively."""
        # Create session first
        response = await api_client.post(
            "/api/v2/sessions",
            json={"agent_type": "codact", "max_steps": 25}
        )
        assert response.status_code == 200
        data = response.json()
        websocket_url = data["websocket_url"]
        
        # Use the actual running server URL
        import websockets
        ws_url = f"ws://0.0.0.0:8000{websocket_url}"
        
        async with websockets.connect(ws_url) as websocket:
            # Create a message collector
            collector = MessageCollector()
            
            # Start collecting messages in background
            async def collect_messages():
                try:
                    async for message in websocket:
                        import json
                        msg = json.loads(message)
                        collector.add_message(msg)
                except Exception as e:
                    print(f"Collection error: {e}")
            
            collect_task = asyncio.create_task(collect_messages())
            
            # Send query that requires multiple steps
            await websocket.send(json.dumps({
                "type": "query",
                "query": "Solve the equation x^2 + 5x + 6 = 0"
            }))
            
            # Collect messages for a few seconds
            await asyncio.sleep(5)
            
            # Cancel collection
            collect_task.cancel()
            try:
                await collect_task
            except asyncio.CancelledError:
                pass
            
            # Should have multiple messages
            assert len(collector.messages) > 2
            
            # Should have progressive updates
            assistant_messages = collector.assistant_messages
            assert len(assistant_messages) > 0
            
            # Validate all messages
            for msg in collector.messages:
                assert_message_format(msg)

    @pytest.mark.asyncio
    async def test_error_handling(self, test_client, websocket_url):
        """Test error handling in WebSocket."""
        async with test_client.websocket_connect(websocket_url) as websocket:
            # Send invalid message type
            await websocket.send_json({
                "type": "invalid_type",
                "data": "test"
            })

            response = await websocket.receive_json()
            assert response["type"] == "error"
            assert "Unknown message type" in response["message"]

            # Send query without content
            await websocket.send_json({"type": "query"})

            response = await websocket.receive_json()
            assert response["type"] == "error"
            assert "Query is required" in response["message"]

    @pytest.mark.asyncio
    async def test_session_busy_handling(self, test_client, websocket_url):
        """Test handling when session is busy."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Send first query
            await manager.send_query("solve 22 = 10 mod n")

            # Wait a bit for processing to start
            await asyncio.sleep(1)

            # Try to send another query while busy
            await manager.websocket.send_json({
                "type": "query",
                "query": "solve x^3 - 4x^2 + 6x - 24 = 0 over the reals"
            })

            # Should get error about session being busy
            # Look for error in next few messages
            for _ in range(10):
                msg = await manager.websocket.receive_json()
                if msg.get("type") == "error":
                    assert "already processing" in msg["message"]
                    break
            else:
                # If no error found, check if we're getting messages from first query
                assert any(
                    "count" in msg.get("content", "").lower()
                    for msg in manager.collector.messages
                )

    @pytest.mark.asyncio
    async def test_message_metadata(self, test_client, websocket_url):
        """Test message metadata fields."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query("Hello, assistant!")

            # Wait for response
            await manager.wait_for_messages(2, timeout=1000)

            # Check metadata in messages
            for msg in manager.collector.messages:
                assert_message_format(msg)

                # Should have timestamp
                assert "timestamp" in msg

                # Should have message_id
                assert "message_id" in msg

                # Should have session_id
                if "session_id" in msg:
                    assert isinstance(msg["session_id"], str)

    @pytest.mark.asyncio
    async def test_get_session_state(self, test_client, websocket_url):
        """Test getting session state via WebSocket."""
        async with test_client.websocket_connect(websocket_url) as websocket:
            # Request session state
            await websocket.send_json({"type": "get_state"})

            response = await websocket.receive_json()
            assert response["type"] == "state"
            assert "state" in response

            state = response["state"]
            assert "session_id" in state
            assert "agent_type" in state
            assert "state" in state
            assert state["state"] == "idle"  # Should be idle initially

    @pytest.mark.asyncio
    async def test_get_message_history(self, test_client, websocket_url):
        """Test retrieving message history."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Send a query first
            await manager.send_query("complete the square x^2+10x+28")

            # Wait for response
            await manager.wait_for_messages(2, timeout=1000)

            # Clear collector
            initial_count = len(manager.collector.messages)
            manager.collector.clear()

            # Request message history
            await manager.websocket.send_json({
                "type": "get_messages",
                "limit": 10
            })

            # Should receive the previous messages
            await asyncio.sleep(1)
            assert len(manager.collector.messages) >= 2

            # Messages should include the original query
            assert any(
                msg.get("content") == "complete the square x^2+10x+28"
                for msg in manager.collector.messages
            )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_connections(
        self,
        test_client,
        api_client
    ):
        """Test multiple concurrent WebSocket connections."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            response = await api_client.post(
                "/api/v2/sessions",
                json={"agent_type": "codact"}
            )
            sessions.append(response.json())

        # Connect to all sessions concurrently
        managers = []
        for session in sessions:
            ws_url = session["websocket_url"]

            # Create WebSocket connection
            websocket = await test_client.websocket_connect(ws_url).__aenter__()
            manager = WebSocketManager(websocket)
            await manager.start_receiving()
            managers.append(manager)

        try:
            # Send queries to all sessions
            queries = [
                "Solve the quadratic equation x^2 - 5x + 6 = 0"
            ]

            for manager, query in zip(managers, queries):
                await manager.send_query(query)

            # Wait for all to complete
            results = await asyncio.gather(*[
                manager.wait_for_final_answer(timeout=1000)
                for manager in managers
            ])

            # Verify all got responses
            assert len(results) == 3
            for result in results:
                assert result is not None
                assert_message_format(result)

        finally:
            # Cleanup
            for manager in managers:
                await manager.close()

    @pytest.mark.asyncio
    async def test_long_running_query(self, test_client, websocket_url):
        """Test handling of long-running queries."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Send a complex query
            await manager.send_query(
                "List the first 10 Fibonacci numbers and explain "
                "the pattern"
            )

            # Should get progressive updates
            await asyncio.sleep(2)
            initial_count = len(manager.collector.messages)

            await asyncio.sleep(3)
            later_count = len(manager.collector.messages)

            # Should have received more messages
            assert later_count > initial_count

            # Wait for completion
            final_answer = await manager.wait_for_final_answer(timeout=1000)
            assert final_answer is not None

            # Should have reasonable number of steps
            step_messages = manager.collector.get_step_messages()
            assert len(step_messages) > 0

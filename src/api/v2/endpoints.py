#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/endpoints.py
# code style: PEP 8

"""
Simplified FastAPI endpoints for DeepSearchAgents Web API v2.

Uses direct Gradio message pass-through for maximum reliability.
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect,
    HTTPException, Query, BackgroundTasks
)
from pydantic import BaseModel, Field

from .session import session_manager, SessionState
from .models import (
    DSAgentRunMessage, QueryRequest as QueryRequestModel,
    ErrorMessage, PingMessage, PongMessage
)

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v2", tags=["v2"])


# Additional request/response models
class CreateSessionRequest(BaseModel):
    """Create session request"""
    agent_type: str = Field(
        default="codact",
        description="Agent type (react/codact)"
    )
    max_steps: Optional[int] = Field(
        default=None,
        description="Maximum steps for agent"
    )


class CreateSessionResponse(BaseModel):
    """Create session response"""
    session_id: str = Field(description="Created session ID")
    agent_type: str = Field(description="Agent type")
    websocket_url: str = Field(description="WebSocket URL for this session")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_sessions: int = Field(description="Number of active sessions")
    version: str = Field(default="2.0.0")


# REST endpoint for session creation
@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new agent session.

    Use the returned WebSocket URL to connect and send queries.
    """
    session = session_manager.create_session(
        agent_type=request.agent_type,
        max_steps=request.max_steps
    )

    return CreateSessionResponse(
        session_id=session.session_id,
        agent_type=session.agent_type,
        websocket_url=f"/api/v2/ws/{session.session_id}"
    )


# WebSocket endpoint for real-time streaming
@router.websocket("/ws/{session_id}")
async def agent_websocket(
    websocket: WebSocket, 
    session_id: str,
    agent_type: str = Query("codact", description="Agent type (react/codact)")
):
    """
    WebSocket endpoint for real-time agent interaction.

    Protocol:
    - Client sends: {"type": "query", "query": "..."}
    - Server streams: DSAgentRunMessage objects
    - Client sends: {"type": "ping"} (keepalive)
    - Server sends: {"type": "pong"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session {session_id}")
    
    # Note: TCP_NODELAY configuration removed due to compatibility issues
    # The asyncio.sleep(0) after each message send is sufficient for streaming

    # Get or create session with specified agent type
    session = session_manager.get_or_create(session_id, agent_type=agent_type)

    try:
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json(
                    ErrorMessage(
                        message="Invalid JSON"
                    ).model_dump()
                )
                continue

            msg_type = data.get("type")

            if msg_type == "query":
                # Process query
                query = data.get("query")
                if not query:
                    await websocket.send_json(
                        ErrorMessage(
                            message="Query is required"
                        ).model_dump()
                    )
                    continue

                # Check if session is busy
                if session.state == SessionState.PROCESSING:
                    await websocket.send_json(
                        ErrorMessage(
                            message="Session is already processing a query"
                        ).model_dump()
                    )
                    continue

                # Process query and stream messages
                try:
                    message_count = 0
                    async for message in session.process_query(query):
                        message_count += 1
                        # Log streaming messages with more detail
                        logger.info(
                            f"Sending message #{message_count} - "
                            f"message_id: {message.message_id}, "
                            f"streaming: {message.metadata.get('streaming', False)}, "
                            f"is_delta: {message.metadata.get('is_delta', False)}, "
                            f"is_initial_stream: {message.metadata.get('is_initial_stream', False)}, "
                            f"stream_id: {message.metadata.get('stream_id')}, "
                            f"step: {message.step_number}, "
                            f"content_length: {len(message.content) if message.content else 0}"
                        )
                        # Send message as JSON
                        await websocket.send_json(
                            message.model_dump(mode='json')
                        )
                        
                        # Force immediate delivery - critical for streaming
                        # Yield control to allow message to be sent
                        await asyncio.sleep(0)

                except Exception as e:
                    logger.error(
                        f"Error processing query: {e}",
                        exc_info=True
                    )
                    await websocket.send_json(
                        ErrorMessage(
                            message=f"Processing error: {str(e)}"
                        ).model_dump()
                    )

            elif msg_type == "ping":
                # Keepalive
                await websocket.send_json(PongMessage().model_dump())

            elif msg_type == "get_messages":
                # Get historical messages
                limit = data.get("limit", 100)
                messages = session.get_messages(limit=limit)

                # Send all messages
                for message in messages:
                    await websocket.send_json(
                        message.model_dump(mode='json')
                    )

            elif msg_type == "get_state":
                # Get session state
                state = session.get_state()
                await websocket.send_json({
                    "type": "state",
                    "state": state.model_dump(mode='json')
                })

            else:
                await websocket.send_json(
                    ErrorMessage(
                        message=f"Unknown message type: {msg_type}"
                    ).model_dump()
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(
            f"WebSocket error for session {session_id}: {e}",
            exc_info=True
        )
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# REST endpoints for session management
@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions():
    """Get list of active sessions."""
    sessions = session_manager.get_active_sessions()
    return [s.model_dump(mode='json') for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.get_state().model_dump(mode='json')


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.remove_session(session_id)
    return {"message": "Session deleted"}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = Query(100, description="Maximum messages to return")
):
    """Get messages from a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get_messages(limit=limit)
    return {
        "session_id": session_id,
        "messages": [m.model_dump(mode='json') for m in messages],
        "total": len(messages)
    }


# Health check endpoint
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    active_sessions = len(session_manager._sessions)

    return HealthResponse(
        active_sessions=active_sessions
    )


# Startup event
@router.on_event("startup")
async def startup_event():
    """Start background tasks."""
    await session_manager.start()
    logger.info("API v2 started")


# Shutdown event
@router.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    await session_manager.shutdown()
    logger.info("API v2 shutdown")

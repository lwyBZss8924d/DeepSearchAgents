#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/endpoints.py
# code style: PEP 8

"""
FastAPI endpoints for DeepSearchAgents Web API v2.

Provides WebSocket and REST endpoints for real-time agent interaction,
supporting both streaming and batch processing modes.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect,
    HTTPException, Query, Depends, BackgroundTasks
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .session import session_manager, SessionState
from .events import EventType, BaseEvent

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v2", tags=["v2"])


# Request/Response models
class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(description="User query to process")
    agent_type: str = Field(
        default="codact",
        description="Agent type (react/codact)"
    )
    max_steps: Optional[int] = Field(
        default=None,
        description="Maximum steps for agent"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream responses"
    )


class QueryResponse(BaseModel):
    """Query response model"""
    session_id: str = Field(description="Session ID for this query")
    status: str = Field(description="Query status")
    message: str = Field(description="Status message")


class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    state: str
    agent_type: str
    current_task: Optional[str]
    created_at: str
    last_activity: str
    total_events: int
    total_steps: int
    total_tokens: Dict[str, int]


class EventsResponse(BaseModel):
    """Events response model"""
    events: List[Dict[str, Any]] = Field(
        description="List of events"
    )
    total: int = Field(description="Total number of events")
    session_id: str = Field(description="Session ID")


# WebSocket endpoint for real-time streaming
@router.websocket("/ws/agent/{session_id}")
async def agent_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time agent interaction.
    
    Supports bidirectional communication with streaming events.
    
    Protocol:
    - Client sends: {"type": "query", "query": "..."}
    - Server sends: Event objects as JSON
    - Client sends: {"type": "ping"} (keepalive)
    - Server sends: {"type": "pong"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session {session_id}")
    
    # Get or create session
    session = session_manager.get_or_create(session_id)
    
    try:
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue
            
            msg_type = data.get("type")
            
            if msg_type == "query":
                # Process query
                query = data.get("query")
                if not query:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Query is required"
                    })
                    continue
                
                # Check if session is busy
                if session.state == SessionState.PROCESSING:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session is already processing a query"
                    })
                    continue
                
                # Process query and stream events
                try:
                    async for event in session.process_query(
                        query, 
                        stream=True
                    ):
                        # Send event as JSON
                        await websocket.send_json(event.dict())
                        
                except Exception as e:
                    logger.error(
                        f"Error processing query: {e}",
                        exc_info=True
                    )
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Processing error: {str(e)}"
                    })
            
            elif msg_type == "ping":
                # Keepalive
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "get_events":
                # Get historical events
                event_type = data.get("event_type")
                limit = data.get("limit", 100)
                
                events = session.get_events(
                    event_type=event_type,
                    limit=limit
                )
                
                await websocket.send_json({
                    "type": "events",
                    "events": [e.dict() for e in events],
                    "total": len(events)
                })
            
            elif msg_type == "get_state":
                # Get session state
                state = session.get_state()
                await websocket.send_json({
                    "type": "state",
                    "state": state
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(
            f"WebSocket error for session {session_id}: {e}",
            exc_info=True
        )
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


# REST endpoint for non-streaming queries
@router.post("/agent/query", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a query for processing.
    
    For streaming responses, use the WebSocket endpoint instead.
    """
    # Create new session
    session = session_manager.create_session(
        agent_type=request.agent_type,
        max_steps=request.max_steps
    )
    
    if request.stream:
        # For streaming, return session ID and use WebSocket
        return QueryResponse(
            session_id=session.session_id,
            status="created",
            message="Use WebSocket endpoint for streaming"
        )
    else:
        # Process in background
        background_tasks.add_task(
            process_query_background,
            session,
            request.query
        )
        
        return QueryResponse(
            session_id=session.session_id,
            status="processing",
            message="Query is being processed"
        )


async def process_query_background(session, query: str):
    """Process query in background (for non-streaming)."""
    try:
        # Process query without streaming
        events = []
        async for event in session.process_query(query, stream=False):
            events.append(event)
        
        logger.info(
            f"Processed query for session {session.session_id}, "
            f"generated {len(events)} events"
        )
        
    except Exception as e:
        logger.error(
            f"Error processing background query: {e}",
            exc_info=True
        )


# Server-Sent Events endpoint for one-way streaming
@router.post("/agent/query/stream")
async def stream_query(request: QueryRequest):
    """
    Stream query results using Server-Sent Events (SSE).
    
    This is an alternative to WebSocket for one-way streaming.
    """
    # Create new session
    session = session_manager.create_session(
        agent_type=request.agent_type,
        max_steps=request.max_steps
    )
    
    async def event_generator():
        """Generate SSE events."""
        try:
            # Send session info
            yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
            
            # Process query and stream events
            async for event in session.process_query(
                request.query,
                stream=True
            ):
                # Format as SSE
                event_data = {
                    "type": "event",
                    "event": event.dict()
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            # Send error
            error_data = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )


# Get session information
@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a session."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = session.get_state()
    
    return SessionInfo(**state)


# Get session events
@router.get("/session/{session_id}/events", response_model=EventsResponse)
async def get_session_events(
    session_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    step_number: Optional[int] = Query(None, description="Filter by step number"),
    limit: int = Query(100, description="Maximum events to return")
):
    """Get events from a session."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    events = session.get_events(
        event_type=event_type,
        step_number=step_number,
        limit=limit
    )
    
    return EventsResponse(
        events=[e.dict() for e in events],
        total=len(events),
        session_id=session_id
    )


# List active sessions
@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """List all active sessions."""
    sessions = session_manager.get_active_sessions()
    
    return [SessionInfo(**s) for s in sessions]


# Delete session
@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and clean up resources."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session_manager.remove_session(session_id)
    
    return {"message": "Session deleted successfully"}


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    active_sessions = len(session_manager.get_active_sessions())
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": active_sessions,
        "version": "2.0.0"
    }


# WebSocket connection manager (optional, for broadcasting)
class ConnectionManager:
    """Manage WebSocket connections for broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Add connection."""
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def broadcast_to_session(
        self,
        session_id: str,
        message: dict
    ):
        """Broadcast message to all connections for a session."""
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


# Global connection manager
connection_manager = ConnectionManager()
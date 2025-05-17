#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/v1/endpoints/agent_streaming.py
# code style: PEP 8
# code-related content: MUST be in English
"""
DeepSearchAgents - Streaming API (CURRENTLY NOT WORKING)

This module contains the Streamable HTTP & SSE functionality that has been
separated from the main application. This code is currently not functional
and requires further development.

NOTE: Agent Callbacks & Stream Real-Time Data (Streamable HTTP & SSE)
      FastAPI are not working. This file is for reference only.
"""

import redis.asyncio as redis
from fastapi import (
    APIRouter, HTTPException, BackgroundTasks, Request, Response, Header,
    status, Query, Path
)
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
import logging
import json
import asyncio
import uuid
import os
import time

from src.agents.runtime import agent_runtime
from src.api_streaming.agent_response import (
    agent_observer, EventType, AgentSessionStatus
)
from src.api_streaming.v1.faststream import SessionCreate
from src.api_streaming.v1.responses import StreamableHTTPResponse

logger = logging.getLogger(__name__)

# Get Redis connection information
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_password = os.getenv("REDIS_PASSWORD", "yourpassword")
redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"

router = APIRouter()


class UserInput(BaseModel):
    """User input request model"""
    user_input: str = Field(..., description="User query content")


class DeepSearchRequest(BaseModel):
    """Deep search request model"""
    user_input: str = Field(..., description="User query content")
    agent_type: Optional[str] = Field(
        "codact", description="Agent type used (codact or react)"
    )
    model_args: Optional[Dict[str, Any]] = Field(
        None, description="Model additional parameters"
    )


class SessionResponse(BaseModel):
    """Session response model"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status "
                        "(ready/running/completed/error)")


class AgentSession(BaseModel):
    """Agent session information model"""
    id: str = Field(..., description="Session ID")
    agent_type: str = Field(..., description="Agent type (codact or react)")
    query: str = Field(..., description="User query")
    status: str = Field(..., description="Session status")
    start_time: float = Field(..., description="Start timestamp")
    end_time: Optional[float] = Field(None, description="End timestamp")
    steps: List[Dict[str, Any]] = Field([], description="Execution steps")
    final_answer: Optional[Any] = Field(None, description="Final answer")
    error: Optional[str] = Field(None, description="Error message (if any)")


class AgentQuery(BaseModel):
    """Agent query model"""
    query: str = Field(..., description="User query")
    agent_type: str = Field(
        default="codact",
        description="Agent type (react or codact)"
    )


class AgentSessionResponse(BaseModel):
    """Agent session response model"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")


class AgentSessionDetail(BaseModel):
    """Agent session detail model"""
    id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    query: str = Field(..., description="User query")
    agent_type: str = Field(..., description="Agent type")
    created_at: float = Field(..., description="Creation timestamp")
    updated_at: float = Field(..., description="Last update timestamp")
    final_answer: Optional[Dict[str, Any]] = Field(
        None, description="Final answer"
    )


class AgentStreamData(BaseModel):
    """Agent stream data model"""
    type: str = Field(..., description="Event type")
    data: Optional[Dict[str, Any]] = Field(None, description="Event data")
    timestamp: Optional[float] = Field(
        None, description="Event timestamp"
    )


# Two-phase execution - 1st phase: Prepare session
@router.post(
    "/prepare_session",
    response_model=SessionResponse,
    operation_id="prepare_session",
    tags=["agents"],
    summary="Prepare agent session but do not start execution",
    description="Create a new agent session but do not start execution, "
                "allowing the client to establish an SSE connection first"
)
async def prepare_session(input_data: DeepSearchRequest) -> SessionResponse:
    """Prepare a new agent session but do not start execution"""
    agent_type = input_data.agent_type or "codact"

    logger.info(
        f"Preparing {agent_type} agent session, query: "
        f"{input_data.user_input[:50]}..."
    )

    # Use FastStream to create a session
    from ..faststream import create_session
    response = await create_session(
        SessionCreate(query=input_data.user_input, agent_type=agent_type)
    )
    session = response["session"]

    logger.info(f"Session is ready, ID: {session['id']}, status: created")

    return SessionResponse(
        session_id=session["id"],
        status=session["status"]
    )


# Two-phase execution - 2nd phase: Execute session
@router.post(
    "/execute_session/{session_id}",
    response_model=SessionResponse,
    operation_id="execute_session",
    tags=["agents"],
    summary="Execute a previously prepared agent session",
    description="Start executing a session previously prepared using the "
                "prepare_session endpoint"
)
async def execute_session(session_id: str, background_tasks: BackgroundTasks):
    logger.info(f"🚀 Received session execution request: {session_id}")

    # Verify session
    session_data = await agent_observer._get_session_data(session_id)
    if not session_data:
        error_msg = f"Session {session_id} does not exist"
        logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    # Check current status
    current_status = session_data.get("status")
    logger.info(f"Session {session_id} current status: {current_status}")

    if current_status != AgentSessionStatus.CREATED:
        error_msg = (f"Session must be in 'created' status to execute, "
                     f"current status: {current_status}")
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # Create custom execution function
        async def run_with_full_logging(sid):
            logger.info(
                f"⚡ Starting to execute session in the background: {sid}"
            )
            try:
                # Get session query
                session_data = await agent_observer._get_session_data(sid)
                user_query = session_data.get("query", "")
                agent_type = session_data.get("agent_type", "codact")

                # Execute agent, passing session_id parameter
                logger.info(
                    f"📝 Calling agent_runtime.run({user_query[:50]}..., "
                    f"session_id={sid})"
                )
                result = await agent_runtime.run(
                    user_query,
                    agent_type=agent_type,
                    session_id=sid
                )

                # Record final answer via FastStream
                from ..faststream import publish_final_answer
                await publish_final_answer(result, sid)

                logger.info(f"✓ Session {sid} execution completed")
                return result
            except Exception as e:
                logger.error(f"❌ Error executing session: {e}", exc_info=True)

                # Publish error event via FastStream
                from ..faststream import publish_event
                await publish_event(
                    agent_observer.format_event_data(
                        session_id=sid,
                        event_type=EventType.ERROR,
                        data={"message": str(e)}
                    ),
                    sid
                )

                return f"Error: {str(e)}"

        # Add background task
        logger.info(f"Adding session {session_id} to background tasks")
        background_tasks.add_task(run_with_full_logging, session_id)

        # Return response
        return SessionResponse(
            session_id=session_id,
            status=AgentSessionStatus.RUNNING
        )

    except Exception as e:
        logger.error(f"Error processing execution request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions/{session_id}/events",
    tags=["agent_sessions"],
    summary="Get session events via SSE stream"
)
async def stream_session_events(
    request: Request,
    session_id: str
) -> StreamingResponse:
    """Stream session events via SSE

    This endpoint uses the Redis broker to stream events.

    Args:
        request: FastAPI request
        session_id: Session ID

    Returns:
        StreamingResponse: SSE stream of events
    """
    # Check if session exists
    session_data = await agent_observer._get_session_data(session_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send initial connection event
        conn_data = json.dumps({
            'type': 'connected',
            'session_id': session_id
        })
        yield f"data: {conn_data}\n\n"

        # Connect to Redis stream using FastStream's broker
        broker = redis.Redis.from_url(redis_url, decode_responses=True)
        async with broker.pubsub() as pubsub:
            await pubsub.subscribe(f"agent_events:{session_id}")
            try:
                # Stream messages with filtering
                async for message in pubsub.listen():
                    try:
                        # Convert message to JSON
                        event_data = message['data']
                        if isinstance(event_data, bytes):
                            event_data = json.loads(
                                event_data.decode("utf-8")
                            )

                        # Generate unique event ID
                        event_type = event_data.get('event_type', '')
                        timestamp = time.time()
                        uuid_part = uuid.uuid4().hex[:8]
                        event_id = (
                            f"{event_type}-{timestamp}-{uuid_part}"
                        )

                        # Send event
                        yield f"id: {event_id}\n"
                        yield f"data: {json.dumps(event_data)}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
                        error_data = json.dumps({'error': str(e)})
                        yield f"data: {error_data}\n\n"

            except asyncio.CancelledError:
                # Client disconnected
                logger.info("Client disconnected from events stream")

            except Exception as e:
                logger.error(f"Error in events stream: {e}")
                error_data = json.dumps({'error': str(e)})
                yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get(
    "/sessions/{session_id}/steps",
    tags=["agent_sessions"],
    summary="Get session steps via SSE stream"
)
async def stream_session_steps(
    request: Request,
    session_id: str
) -> StreamingResponse:
    """Stream session steps via SSE

    This endpoint uses the Redis broker to stream steps.

    Args:
        request: FastAPI request
        session_id: Session ID

    Returns:
        StreamingResponse: SSE stream of steps
    """
    # Check if session exists
    session_data = await agent_observer._get_session_data(session_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    async def steps_generator() -> AsyncGenerator[str, None]:
        # Send initial connection event
        conn_data = json.dumps({
            'type': 'connected',
            'session_id': session_id
        })
        yield f"data: {conn_data}\n\n"

        # Connect to Redis stream using FastStream's broker
        broker = redis.Redis.from_url(redis_url, decode_responses=True)
        async with broker.pubsub() as pubsub:
            await pubsub.subscribe(f"agent_steps:{session_id}")
            try:
                # Stream messages with filtering
                async for message in pubsub.listen():
                    try:
                        # Convert message to JSON
                        step_data = message['data']
                        if isinstance(step_data, bytes):
                            step_data = json.loads(
                                step_data.decode("utf-8")
                            )

                        # Send as SSE
                        yield f"data: {json.dumps(step_data)}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing step: {e}")
                        error_data = json.dumps({'error': str(e)})
                        yield f"data: {error_data}\n\n"

            except asyncio.CancelledError:
                # Client disconnected
                logger.info("Client disconnected from steps stream")

            except Exception as e:
                logger.error(f"Error in steps stream: {e}")
                error_data = json.dumps({'error': str(e)})
                yield f"data: {error_data}\n\n"

    return StreamingResponse(
        steps_generator(),
        media_type="text/event-stream"
    )


# Backward compatibility endpoints

@router.post(
    "/run_react_agent",
    response_class=PlainTextResponse,
    operation_id="run_react",
    tags=["agents"],
    summary="Execute React agent search",
    description="Execute network search and analysis using ReAct "
                "chain of thought agent, return detailed results"
)
async def run_agent_endpoint(input_data: UserInput) -> PlainTextResponse:
    """Execute React agent

    Args:
        input_data: Request containing user query

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing React agent with query: {input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(input_data.user_input, "react")

    if result.startswith("Error:") or result.startswith(
        "Error processing request:"
    ):
        logger.error(f"Error executing React agent: {result[:100]}...")
        return PlainTextResponse(content=result, status_code=500)
    else:
        return PlainTextResponse(content=result)


@router.post(
    "/run_deepsearch_agent",
    response_class=PlainTextResponse,
    operation_id="deep_search",
    tags=["agents"],
    summary="Execute deep network search and analysis",
    description="Execute comprehensive network search and analysis "
                "for the given query, using ReAct-CodeAct agent, "
                "return detailed results"
)
async def run_deepsearch_agent(input_data: UserInput) -> PlainTextResponse:
    """Execute DeepSearch agent

    Args:
        input_data: Request containing user query

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing DeepSearch agent with query: "
        f"{input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(input_data.user_input)

    # Handle different result types
    if isinstance(result, dict):
        # If result is dict, convert to JSON string
        result_text = json.dumps(result)
    elif isinstance(result, str):
        result_text = result
    else:
        result_text = json.dumps({"content": str(result)})

    # Check for error
    if (isinstance(result_text, str) and
            (result_text.startswith("Error:") or
             result_text.startswith("Error processing request:"))):
        logger.error(f"Error executing DeepSearch agent: "
                     f"{result_text[:100]}...")
        return PlainTextResponse(content=result_text, status_code=500)
    else:
        return PlainTextResponse(content=result_text)


@router.post(
    "/run_agent",
    response_class=PlainTextResponse,
    operation_id="run_agent",
    tags=["agents"],
    summary="Execute any type of agent",
    description="Select CodeAct-ReAct or normal ReAct agent type "
                "based on agent_type (codact or react) parameter "
                "in request"
)
async def run_selected_agent(
    input_data: DeepSearchRequest
) -> PlainTextResponse:
    """Execute any type of agent

    Args:
        input_data: Request containing user query and agent type

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing {input_data.agent_type} agent with query: "
        f"{input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(
        input_data.user_input,
        input_data.agent_type
    )

    if result.startswith("Error:") or result.startswith(
        "Error processing request:"
    ):
        logger.error(
            f"Error executing {input_data.agent_type} agent: "
            f"{result[:100]}..."
        )
        return PlainTextResponse(content=result, status_code=500)
    else:
        return PlainTextResponse(content=result)


@router.post(
    "/mcp",
    tags=["agent_streams"],
    summary="Streamable HTTP MCP endpoint",
    response_model=None
)
async def mcp_endpoint(
    request: Request,
    mcp_session_id: Optional[str] = Header(None),
    last_event_id: Optional[str] = Header(None)
) -> Union[Response, StreamableHTTPResponse]:
    """Streamable HTTP compliant single endpoint

    Supports JSON-RPC message exchange and SSE streams

    Args:
        request: FastAPI request object
        mcp_session_id: Optional session ID header
        last_event_id: Last received event ID

    Returns:
        JSON response or SSE stream based on request content
    """
    # Check Accept header
    accept_header = request.headers.get("Accept", "")
    supports_sse = "text/event-stream" in accept_header
    supports_json = "application/json" in accept_header

    if not (supports_sse and supports_json):
        return Response(
            content="Accept header must include both "
                    "application/json and text/event-stream",
            status_code=400
        )

    # Extract request body (JSON-RPC message)
    try:
        body = await request.json()
    except Exception:
        return Response(
            content=json.dumps({"error": "Invalid JSON request"}),
            status_code=400,
            media_type="application/json"
        )

    # Analyze request type
    is_notification = body.get("method") and "id" not in body
    is_request = body.get("method") and "id" in body

    # Handle session initialization request
    if is_request and body.get("method") == "initialize":
        # Create new session or resume existing session
        params = body.get("params", {})
        query = params.get("query", "")
        agent_type = params.get("agent_type", "codact")

        # Use FastStream to create session
        from ..faststream import create_session
        response = await create_session(
            SessionCreate(query=query, agent_type=agent_type)
        )
        session = response["session"]
        session_id = session["id"]

        # Return initialization response with session ID
        json_response = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "session_id": session_id,
                "status": session["status"]
            }
        }

        return Response(
            content=json.dumps(json_response),
            status_code=200,
            headers={"Mcp-Session-Id": session_id},
            media_type="application/json"
        )

    # Handle session execution request - return SSE stream
    if is_request and body.get("method") == "execute":
        # Get session ID
        session_id = mcp_session_id
        if not session_id and "params" in body:
            session_id = body["params"].get("session_id")

        if not session_id:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {
                        "code": -32602,
                        "message": "Missing session_id"
                    }
                }),
                status_code=400,
                media_type="application/json"
            )

        # Validate session
        session_data = await agent_observer._get_session_data(session_id)
        if not session_data:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {
                        "code": -32602,
                        "message": f"Session {session_id} not found"
                    }
                }),
                status_code=404,
                media_type="application/json"
            )

        # Start background task to execute Agent
        background_tasks = BackgroundTasks()

        async def run_agent(sid, request_id):
            """Execute agent in background"""
            try:
                # Get session information
                session_data = await agent_observer._get_session_data(sid)
                user_query = session_data.get("query", "")
                agent_type = session_data.get("agent_type", "codact")

                # Execute Agent
                logger.info(f"Running agent for session {sid}")
                result = await agent_runtime.run(
                    user_query,
                    agent_type=agent_type,
                    session_id=sid
                )

                # Record final answer
                from ..faststream import publish_final_answer
                await publish_final_answer(result, sid)

            except Exception as e:
                logger.error(f"❌ Agent execution error: {e}", exc_info=True)

                # Publish error event
                from ..faststream import publish_event
                await publish_event(
                    agent_observer.format_event_data(
                        session_id=sid,
                        event_type=EventType.ERROR,
                        data={"message": str(e)}
                    ),
                    sid
                )

        background_tasks.add_task(
            run_agent, session_id, body["id"]
        )

        # Return SSE stream
        async def event_stream() -> AsyncGenerator[str, None]:
            """Enhanced event stream generator, ensuring real-time
            transmission"""
            client_id = f"stream-{uuid.uuid4().hex[:8]}"
            logger.info(f"Starting event stream: session={session_id}, "
                        f"client={client_id}")

            # send initial connection event
            yield StreamableHTTPResponse.format_sse_event(
                "connected",
                {"session_id": session_id,
                 "mode": "enhanced_streaming",
                 "client_id": client_id},
                f"conn-{time.time()}"
            )

            # force buffer flush
            await asyncio.sleep(0)

            # create Redis connection
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()

            # subscribe to all possible channels
            channels = [
                f"agent_step_notifications:{session_id}",
                f"agent_direct_notifications:{session_id}",
                f"agent_runtime_events:{session_id}",
                f"agent_event_notifications:{session_id}",
                f"agent_notifications:{session_id}"  # add extra channels
            ]

            for channel in channels:
                await pubsub.subscribe(channel)

            logger.info(f"Subscribed to {len(channels)} Redis channels")

            # publish client connection event
            await r.publish(
                "agent_client_connections",
                json.dumps({
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "action": "stream_connected",
                    "client_id": client_id
                })
            )

            # check if there is existing step cache, load and send
            try:
                # get existing step keys
                step_keys = await r.keys(f"step:{session_id}:*")
                if step_keys:
                    logger.info(f"Found {len(step_keys)} existing steps, "
                                "sending history data")
                    for key in sorted(step_keys):
                        step_data = await r.hgetall(key)
                        if step_data:
                            # extract step type
                            event_type = step_data.get("step_type", "step")
                            # generate event ID
                            timestamp = time.time()
                            uuid_part = uuid.uuid4().hex[:8]
                            event_id = (
                                f"{event_type}-{timestamp}-{uuid_part}"
                            )
                            # send history steps
                            yield StreamableHTTPResponse.format_sse_event(
                                event_type,
                                step_data,
                                event_id
                            )
                            # force buffer flush
                            await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error sending history steps: {e}")

            # main event loop - reduce timeout to increase responsiveness
            try:
                last_heartbeat = time.time()
                while True:
                    # check session status
                    status = await agent_observer._get_session_status(
                        session_id
                    )
                    if status in [AgentSessionStatus.COMPLETED,
                                  AgentSessionStatus.ERROR]:
                        # session completed, send completion event
                        yield StreamableHTTPResponse.format_sse_event(
                            "complete",
                            {
                                "message": f"Session {status}",
                                "session_id": session_id,
                                "timestamp": time.time()
                            },
                            f"complete-{time.time()}"
                        )
                        break

                    # get message, use smaller timeout to
                    # increase responsiveness
                    message = await pubsub.get_message(timeout=0.01)

                    if message and message["type"] == "message":
                        try:
                            # parse message content
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode("utf-8")

                            parsed_data = json.loads(data)

                            # determine event type
                            event_type = (
                                parsed_data.get("step_type") or
                                parsed_data.get("event_type") or
                                parsed_data.get("type") or
                                "step"
                            )

                            # generate event ID
                            timestamp = time.time()
                            uuid_part = uuid.uuid4().hex[:8]
                            event_id = (
                                f"{event_type}-{timestamp}-{uuid_part}"
                            )

                            # send SSE event
                            yield StreamableHTTPResponse.format_sse_event(
                                event_type,
                                parsed_data,
                                event_id
                            )

                            # force buffer flush
                            await asyncio.sleep(0)

                            logger.info(f"Sending {event_type} "
                                        f"event: {event_id}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

                    # send heartbeat, more frequently to maintain connection
                    current_time = time.time()
                    if current_time - last_heartbeat >= 2.0:
                        heartbeat_data = json.dumps({
                            "timestamp": current_time,
                            "type": "heartbeat"
                        })
                        yield f"event: heartbeat\ndata: {heartbeat_data}\n\n"
                        # force buffer flush
                        await asyncio.sleep(0)
                        last_heartbeat = current_time

                    # loop faster, reduce delay
                    await asyncio.sleep(0.01)

            finally:
                # clean up resources
                await pubsub.unsubscribe()
                await pubsub.close()
                await r.close()

        return StreamableHTTPResponse(
            content=event_stream(),
            headers={"Mcp-Session-Id": session_id},
            background=background_tasks,
            last_event_id=last_event_id
        )

    # Handle notification (no response needed)
    if is_notification:
        # Handle cancellation request
        if body.get("method") == "cancelled":
            session_id = mcp_session_id
            if not session_id and "params" in body:
                session_id = body["params"].get("session_id")

            if session_id:
                # Publish cancellation event
                from ..faststream import publish_event
                await publish_event(
                    agent_observer.format_event_data(
                        session_id=session_id,
                        event_type=EventType.ERROR,
                        data={"message": "Request cancelled by client"}
                    ),
                    session_id
                )

            return Response(status_code=202)  # Accepted

    # Default error response
    return Response(
        content=json.dumps({"error": "Invalid request"}),
        status_code=400,
        media_type="application/json"
    )


@router.get(
    "/mcp",
    tags=["agent_streams"],
    summary="Get events via Streamable HTTP",
    response_model=None
)
async def mcp_listen(
    request: Request,
    mcp_session_id: Optional[str] = Header(None),
    last_event_id: Optional[str] = Header(None)
) -> StreamableHTTPResponse:
    """Open SSE stream to receive server messages

    Compliant with Streamable HTTP standard

    Args:
        request: FastAPI request object
        mcp_session_id: Session ID
        last_event_id: Last received event ID

    Returns:
        SSE event stream
    """
    # Check Accept header
    accept_header = request.headers.get("Accept", "")
    if "text/event-stream" not in accept_header:
        return Response(
            content="Accept header must include text/event-stream",
            status_code=400
        )

    # Check session ID
    if not mcp_session_id:
        return Response(
            content="Missing Mcp-Session-Id header",
            status_code=400
        )

    # Validate session
    session_data = await agent_observer._get_session_data(mcp_session_id)
    if not session_data:
        return Response(
            content=f"Session {mcp_session_id} not found",
            status_code=404
        )

    # Create event stream generator
    async def event_stream() -> AsyncGenerator[str, None]:
        # Send initial connection message
        yield "id: init\n"
        yield f"data: {json.dumps(
            {'type': 'connected', 'session_id': mcp_session_id}
        )}\n\n"

        # Use Redis broker to get events
        broker = redis.Redis.from_url(redis_url, decode_responses=True)
        async with broker.pubsub() as pubsub:
            await pubsub.subscribe(f"agent_events:{mcp_session_id}")
            try:
                # Stream events
                async for message in pubsub.listen():
                    try:
                        event_data = message['data']
                        if isinstance(event_data, bytes):
                            event_data = json.loads(event_data.decode("utf-8"))

                        # Generate unique event ID
                        event_type = event_data.get('event_type', '')
                        timestamp = time.time()
                        uuid_part = uuid.uuid4().hex[:8]
                        event_id = (
                            f"{event_type}-{timestamp}-{uuid_part}"
                        )

                        # Send event
                        yield f"id: {event_id}\n"
                        yield f"data: {json.dumps(event_data)}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"

            except asyncio.CancelledError:
                logger.info("Client disconnected from events stream")

            except Exception as e:
                logger.error(f"Error in events stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamableHTTPResponse(
        content=event_stream(),
        headers={"Mcp-Session-Id": mcp_session_id},
        last_event_id=last_event_id
    )


@router.delete(
    "/mcp",
    tags=["agent_streams"],
    summary="Terminate session"
)
async def mcp_terminate(
    request: Request,
    mcp_session_id: str = Header(...)
) -> Response:
    """Terminate session

    Args:
        request: FastAPI request object
        mcp_session_id: Session ID

    Returns:
        Success or failure response
    """
    # Validate session
    session_data = await agent_observer._get_session_data(mcp_session_id)
    if not session_data:
        return Response(
            content=f"Session {mcp_session_id} not found",
            status_code=404
        )

    # Publish termination event
    from ..faststream import publish_event
    await publish_event(
        agent_observer.format_event_data(
            session_id=mcp_session_id,
            event_type=EventType.COMPLETE,
            data={"message": "Session terminated by client"}
        ),
        mcp_session_id
    )

    # Remove session from memory
    if (hasattr(agent_observer, "sessions") and
            mcp_session_id in agent_observer.sessions):
        del agent_observer.sessions[mcp_session_id]

    return Response(status_code=200)


@router.post(
    "/agents/query",
    response_model=AgentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent session",
    description="Creates a new agent session for the given query"
)
async def create_agent_session(
    agent_query: AgentQuery,
) -> AgentSessionResponse:
    """Create a new agent session

    Args:
        agent_query: Agent query model with required parameters

    Returns:
        AgentSessionResponse: Session response with ID and status
    """
    try:
        # Validate agent type
        agent_type = agent_query.agent_type.lower()
        if agent_type not in ["react", "codact"]:
            agent_type = "codact"  # Default to codact

        # Create session
        session_id = await agent_observer.create_session(
            agent_query.query,
            agent_type
        )

        # Return session info
        return {
            "session_id": session_id,
            "status": AgentSessionStatus.CREATED
        }
    except Exception as e:
        logger.error(f"Error creating agent session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating agent session: {str(e)}"
        )


@router.post(
    "/agents/sessions/{session_id}/execute",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute an agent session",
    description="Executes an existing agent session"
)
async def execute_agent_session(
    session_id: str = Path(..., description="Session ID"),
    background_tasks: BackgroundTasks = None,
) -> dict:
    """Execute an agent session

    Args:
        session_id: Session ID to execute
        background_tasks: Background tasks to execute

    Returns:
        dict: Session execution confirmation
    """
    try:
        # Get session data
        session = await agent_observer._get_session_data(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Check session status
        status_str = session.get("status")
        if status_str not in [
            AgentSessionStatus.CREATED,
            AgentSessionStatus.RUNNING
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute session with status '{status_str}'"
            )

        # immediately update session status to "running", so the client can
        # immediately see the status change
        # no need to wait for agent_runtime callback
        await agent_observer.update_session_status(
            session_id,
            AgentSessionStatus.RUNNING
        )

        # send execution start event
        await agent_observer.publish_event(
            session_id,
            EventType.STEP_UPDATE,
            {
                "message": f"Session {session_id} execution started",
                "timestamp": time.time(),
                "step_counter": 0,
                "step_type": "initialization"
            }
        )

        # Add execution task to background
        if background_tasks:
            background_tasks.add_task(
                agent_runtime.run_on_session,
                session_id
            )

        # Return execution confirmation
        return {
            "message": f"Session {session_id} execution started",
            "session_id": session_id,
            "status": AgentSessionStatus.RUNNING
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error executing session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing session: {str(e)}"
        )


@router.get(
    "/agents/sessions/{session_id}",
    response_model=AgentSessionDetail,
    summary="Get agent session details",
    description="Returns details about an agent session"
)
async def get_agent_session(
    session_id: str = Path(..., description="Session ID"),
) -> AgentSessionDetail:
    """Get agent session details

    Args:
        session_id: Session ID to retrieve

    Returns:
        AgentSessionDetail: Session details
    """
    try:
        # Get session data
        session = await agent_observer._get_session_data(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Parse final answer if present
        final_answer = None
        if "final_answer" in session and session["final_answer"]:
            try:
                if isinstance(session["final_answer"], str):
                    final_answer = json.loads(session["final_answer"])
                else:
                    final_answer = session["final_answer"]
            except Exception as e:
                logger.error(f"Error parsing final answer: {e}")
                final_answer = {"content": str(session["final_answer"])}

        # Return session details
        return {
            "id": session["id"],
            "status": session["status"],
            "query": session["query"],
            "agent_type": session["agent_type"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "final_answer": final_answer
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session: {str(e)}"
        )


@router.get(
    "/agents/sessions/{session_id}/stream",
    summary="Stream agent session events",
    description="Streams events from an agent session using Streamable HTTP",
    response_model=None
)
async def stream_agent_session(
    session_id: str = Path(..., description="Session ID"),
    last_event_id: Optional[str] = Query(
        None, description="Last event ID for resuming"
    ),
) -> StreamableHTTPResponse:
    """Improved stream session events endpoint

    Args:
        session_id: Session ID
        last_event_id: Last event ID for resuming

    Returns:
        StreamableHTTPResponse: Streamable HTTP response
    """
    try:
        # validate session
        session = await agent_observer._get_session_data(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        async def event_stream():
            """Enhanced event stream generator,
            ensuring real-time transmission"""
            client_id = f"stream-{uuid.uuid4().hex[:8]}"
            logger.info(f"Starting event stream: session={session_id}, "
                        f"client={client_id}")

            # send initial connection event
            yield StreamableHTTPResponse.format_sse_event(
                "connected",
                {"session_id": session_id,
                 "mode": "enhanced_streaming",
                 "client_id": client_id},
                f"conn-{time.time()}"
            )

            # force buffer flush
            await asyncio.sleep(0)

            # create Redis connection
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()

            # subscribe to all possible channels
            channels = [
                f"agent_step_notifications:{session_id}",
                f"agent_direct_notifications:{session_id}",
                f"agent_runtime_events:{session_id}",
                f"agent_event_notifications:{session_id}",
                f"agent_notifications:{session_id}"  # add extra channels
            ]

            for channel in channels:
                await pubsub.subscribe(channel)

            logger.info(f"Subscribed to {len(channels)} Redis channels")

            # publish client connection event
            await r.publish(
                "agent_client_connections",
                json.dumps({
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "action": "stream_connected",
                    "client_id": client_id
                })
            )

            # check if there is existing step cache, load and send
            try:
                # get existing step keys
                step_keys = await r.keys(f"step:{session_id}:*")
                if step_keys:
                    logger.info(f"Found {len(step_keys)} existing steps, "
                                "sending history data")
                    for key in sorted(step_keys):
                        step_data = await r.hgetall(key)
                        if step_data:
                            # extract step type
                            event_type = step_data.get("step_type", "step")
                            # generate event ID
                            timestamp = time.time()
                            uuid_part = uuid.uuid4().hex[:8]
                            event_id = (
                                f"{event_type}-{timestamp}-{uuid_part}"
                            )
                            # send history steps
                            yield StreamableHTTPResponse.format_sse_event(
                                event_type,
                                step_data,
                                event_id
                            )
                            # force buffer flush
                            await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error sending history steps: {e}")

            # main event loop - reduce timeout to increase responsiveness
            try:
                last_heartbeat = time.time()
                while True:
                    # check session status
                    status = await agent_observer._get_session_status(
                        session_id
                    )
                    if status in [
                        AgentSessionStatus.COMPLETED,
                        AgentSessionStatus.ERROR
                    ]:
                        # session completed, send completion event
                        yield StreamableHTTPResponse.format_sse_event(
                            "complete",
                            {
                                "message": f"Session {status}",
                                "session_id": session_id,
                                "timestamp": time.time()
                            },
                            f"complete-{time.time()}"
                        )
                        break

                    # get message, use smaller timeout to
                    # increase responsiveness
                    message = await pubsub.get_message(timeout=0.01)

                    if message and message["type"] == "message":
                        try:
                            # parse message content
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode("utf-8")

                            parsed_data = json.loads(data)

                            # determine event type
                            event_type = (
                                parsed_data.get("step_type") or
                                parsed_data.get("event_type") or
                                parsed_data.get("type") or
                                "step"
                            )

                            # generate event ID
                            timestamp = time.time()
                            uuid_part = uuid.uuid4().hex[:8]
                            event_id = (
                                f"{event_type}-{timestamp}-{uuid_part}"
                            )

                            # send SSE event
                            yield StreamableHTTPResponse.format_sse_event(
                                event_type,
                                parsed_data,
                                event_id
                            )

                            # force buffer flush
                            await asyncio.sleep(0)

                            logger.info(f"Sending {event_type} "
                                        f"event: {event_id}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

                    # send heartbeat, more frequently to maintain connection
                    current_time = time.time()
                    if current_time - last_heartbeat >= 2.0:
                        heartbeat_data = json.dumps({
                            "timestamp": current_time,
                            "type": "heartbeat"
                        })
                        yield f"event: heartbeat\ndata: {heartbeat_data}\n\n"
                        # force buffer flush
                        await asyncio.sleep(0)
                        last_heartbeat = current_time

                    # loop faster, reduce delay
                    await asyncio.sleep(0.01)

            finally:
                # clean up resources
                await pubsub.unsubscribe()
                await pubsub.close()
                await r.close()

        return StreamableHTTPResponse(
            content=event_stream(),
            session_id=session_id,
            last_event_id=last_event_id
        )
    except Exception as e:
        logger.error(f"Error creating event stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating event stream: {str(e)}"
        )


@router.post(
    "/agents/run",
    response_model=dict,
    summary="Run agent query directly",
    description="Runs agent query without creating a separate session"
)
async def run_agent_query(
    agent_query: AgentQuery,
    background_tasks: BackgroundTasks = None,
) -> dict:
    """Run agent query directly

    Args:
        agent_query: Agent query model with required parameters
        background_tasks: Background tasks to execute

    Returns:
        dict: Query response or session information
    """
    try:
        # Create session
        session_id = await agent_observer.create_session(
            agent_query.query,
            agent_query.agent_type
        )

        # Start execution in background
        if background_tasks:
            background_tasks.add_task(
                agent_runtime.run_on_session,
                session_id
            )
            return {
                "message": "Agent query execution started",
                "session_id": session_id,
                "status": "running"
            }
        else:
            # Run synchronously if no background tasks
            result = await agent_runtime.run_on_session(session_id)
            return {
                "result": result,
                "session_id": session_id,
                "status": "completed"
            }
    except Exception as e:
        logger.error(f"Error running agent query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running agent query: {str(e)}"
        )


def message_identifier(msg_data):
    """Generate unique message identifier for tracking"""
    return f"msg-{time.time()}-{uuid.uuid4().hex[:6]}"

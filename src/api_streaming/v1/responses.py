#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/v1/responses.py
# code style: PEP 8
# code-related content: MUST be in English
"""
NOTE: Agent Callbacks &  Stream Real-Time Data(Streamable HTTP & SSE)
      FastAPI are not working.
"""

from typing import Any, List
from starlette.background import BackgroundTask
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)


class StreamableHTTPResponse(StreamingResponse):
    """
    Custom response class implementing Streamable HTTP standards
    Supports reconnection and session management, optimizing real-time
    transmission functionality
    """

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
        session_id: str = None,
        last_event_id: str = None,
    ):
        if headers is None:
            headers = {}

        # set standard SSE headers and cache control, optimize real-time
        # transmission
        headers.update({
            "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx close buffering
            "Content-Type": "text/event-stream"
        })

        # add session ID
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/event-stream",
            background=background
        )

        self.session_id = session_id
        self.last_event_id = last_event_id
        logger.info(f"Created StreamableHTTPResponse: session_id={session_id}")

    async def stream_response(self, send: Send) -> None:
        """Optimized streaming response method, ensuring real-time
        transmission

        Args:
            send: ASGI send function
        """
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self.raw_headers,
        })

        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)

            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True
            })
            # key: ensure each event is sent immediately, not waiting for
            # buffer to fill
            await asyncio.sleep(0)

        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False
        })

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:
        """Handle ASGI request/response

        Add error handling and logging, ensure connection is closed properly

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if self.background is not None:
            await self.background()

        try:
            await self.stream_response(send)
        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                logger.info(
                    f"Client disconnected: session_id={self.session_id}"
                )
            else:
                logger.error(
                    f"Streaming response error: {e}, "
                    f"session_id={self.session_id}",
                    exc_info=True
                )
            # ensure connection is closed properly
            try:
                await send({
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False
                })
            except Exception:
                pass
            raise

    @staticmethod
    def format_sse_event(
        event_type: str,
        data: Any,
        event_id: str = None
    ) -> str:
        """Format SSE event

        Args:
            event_type: event type
            data: event data
            event_id: optional event ID

        Returns:
            str: formatted SSE event
        """
        lines: List[str] = []

        # add event ID
        if event_id:
            lines.append(f"id: {event_id}")

        # add event type
        if event_type:
            lines.append(f"event: {event_type}")

        # serialize data
        if isinstance(data, str):
            data_str = data
        else:
            try:
                data_str = json.dumps(data)
            except Exception:
                data_str = str(data)

        # data may contain multiple lines, each line needs prefix "data: "
        for data_line in data_str.split("\n"):
            lines.append(f"data: {data_line}")

        # SSE event ends with an empty line
        return "\n".join(lines) + "\n\n"

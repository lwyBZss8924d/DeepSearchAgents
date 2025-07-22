#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/gradio_passthrough_processor.py
# code style: PEP 8

"""
Gradio pass-through processor for DeepSearchAgents v2 Web API.

Minimal wrapper around smolagents' stream_to_gradio that passes
messages through with field renaming only.
"""

import re
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timezone

from smolagents.gradio_ui import stream_to_gradio
try:
    import gradio as gr
except ImportError:
    # Fallback - create a simple ChatMessage class
    class ChatMessage:
        def __init__(self, role, content, metadata=None):
            self.role = role
            self.content = content
            self.metadata = metadata or {}
    gr = type('gr', (), {'ChatMessage': ChatMessage})()

from .models import DSAgentRunMessage

logger = logging.getLogger(__name__)


class GradioPassthroughProcessor:
    """
    Minimal processor that passes through Gradio messages.

    This processor:
    1. Uses stream_to_gradio to get properly formatted messages
    2. Converts Gradio ChatMessage to DSAgentRunMessage
    3. Adds minimal DS-specific metadata
    4. No content parsing or event type detection
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the processor.

        Args:
            session_id: Session ID for message correlation
        """
        self.session_id = session_id
        self.message_count = 0
        self.current_step = 0

    async def process_agent_stream(
        self,
        agent,
        task: str,
        task_images: Optional[List] = None,
        reset_agent_memory: bool = False,
        additional_args: Optional[Dict] = None
    ) -> AsyncGenerator[DSAgentRunMessage, None]:
        """
        Stream Gradio messages with field renaming.

        Args:
            agent: The agent instance to run
            task: The task/query to execute
            task_images: Optional images for the task
            reset_agent_memory: Whether to reset agent memory
            additional_args: Additional arguments for agent

        Yields:
            DSAgentRunMessage objects
        """
        try:
            # Raw agent - call stream_to_gradio directly
            # Check the signature of stream_to_gradio
            import inspect
            sig = inspect.signature(stream_to_gradio)
            params = sig.parameters
            
            # Build kwargs based on available parameters
            kwargs = {"agent": agent, "task": task}
            
            # Only add parameters that stream_to_gradio accepts
            if "task_images" in params:
                kwargs["task_images"] = task_images
            elif "images" in params:
                kwargs["images"] = task_images
                
            if "reset_agent_memory" in params:
                kwargs["reset_agent_memory"] = reset_agent_memory
            elif "reset" in params:
                kwargs["reset"] = reset_agent_memory
                
            if "additional_args" in params:
                kwargs["additional_args"] = additional_args
            
            stream_generator = stream_to_gradio(**kwargs)

            # Process stream - handle both sync generators and async generators
            try:
                # Check if it's an async generator
                if hasattr(stream_generator, '__aiter__'):
                    async for item in stream_generator:
                        self.message_count += 1
                        yield self._process_stream_item(item)
                else:
                    # Sync generator - convert to async
                    for item in stream_generator:
                        self.message_count += 1
                        yield self._process_stream_item(item)
            except Exception as e:
                logger.error(f"Error processing stream: {e}", exc_info=True)
                raise

        except Exception as e:
            logger.error(
                f"Error in agent stream processing: {e}",
                exc_info=True
            )
            # Yield error message
            yield DSAgentRunMessage(
                role="assistant",
                content=f"Error: {str(e)}",
                metadata={
                    "error": True,
                    "error_type": type(e).__name__
                },
                session_id=self.session_id,
                step_number=self.current_step
            )

    def _extract_step_number(self, message: gr.ChatMessage) -> Optional[int]:
        """
        Extract step number from message content if present.

        Args:
            message: Gradio ChatMessage

        Returns:
            Step number if found, None otherwise
        """
        if not message.content:
            return None

        # Look for "**Step N**" pattern
        match = re.search(r'\*\*Step (\d+)\*\*', message.content)
        if match:
            return int(match.group(1))

        return None

    def _process_stream_item(self, item) -> DSAgentRunMessage:
        """
        Process a single stream item and convert to DSAgentRunMessage.

        Args:
            item: Stream item from stream_to_gradio

        Returns:
            DSAgentRunMessage
        """
        if isinstance(item, str):
            # Streaming text update
            return DSAgentRunMessage(
                role="assistant",
                content=item,
                metadata={"streaming": True},
                session_id=self.session_id,
                step_number=self.current_step
            )
        elif isinstance(item, gr.ChatMessage):
            # Complete Gradio ChatMessage
            # Extract step number if present
            step_num = self._extract_step_number(item)
            if step_num is not None:
                self.current_step = step_num

            return DSAgentRunMessage(
                role=item.role,
                content=item.content,
                metadata=item.metadata or {},
                session_id=self.session_id,
                step_number=self.current_step
            )
        else:
            # Handle other types gracefully
            logger.warning(
                f"Unexpected item type from stream_to_gradio: "
                f"{type(item)}"
            )
            return DSAgentRunMessage(
                role="assistant",
                content=str(item),
                metadata={"type": type(item).__name__},
                session_id=self.session_id,
                step_number=self.current_step
            )

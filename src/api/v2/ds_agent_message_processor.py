#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/ds_agent_message_processor.py
# code style: PEP 8

"""
DSAgent message processor for DeepSearchAgents v2 Web API.

Handles agent message streaming and processing using the web_ui module.
"""

import logging
from typing import Optional, List, Dict, AsyncGenerator

from .web_ui import stream_agent_messages
from .models import DSAgentRunMessage

logger = logging.getLogger(__name__)


class DSAgentMessageProcessor:
    """
    Processor for DSAgent messages with proper formatting and routing.

    This processor:
    1. Uses web_ui.stream_agent_messages to process agent events
    2. Generates DSAgentRunMessage objects with component routing metadata
    3. Handles session management and error handling
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the processor.

        Args:
            session_id: Session ID for message correlation
        """
        self.session_id = session_id
        self.message_count = 0

    async def process_agent_stream(
        self,
        agent,
        task: str,
        task_images: Optional[List] = None,
        reset_agent_memory: bool = False,
        additional_args: Optional[Dict] = None
    ) -> AsyncGenerator[DSAgentRunMessage, None]:
        """
        Stream agent messages with proper formatting and metadata.

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
            # Use web_ui to process the agent stream
            async for message in stream_agent_messages(
                agent=agent,
                task=task,
                task_images=task_images,
                reset_agent_memory=reset_agent_memory,
                additional_args=additional_args,
                session_id=self.session_id
            ):
                self.message_count += 1
                # Log message details for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"Message {self.message_count}: "
                        f"component={message.metadata.get('component')}, "
                        f"type={message.metadata.get('message_type')}, "
                        f"is_delta={message.metadata.get('is_delta', False)}, "
                        f"step={message.step_number}"
                    )
                yield message

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
                    "component": "chat",
                    "message_type": "error",
                    "error": True,
                    "error_type": type(e).__name__,
                    "status": "done"
                },
                session_id=self.session_id,
                step_number=0
            )

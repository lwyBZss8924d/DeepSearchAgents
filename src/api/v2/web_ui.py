#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/web_ui.py
# code style: PEP 8

"""
Web UI message processing for DeepSearchAgents v2 Web API.

This module processes agent events and generates DSAgentRunMessage objects
with proper component routing metadata for the frontend.
"""

import re
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator, Generator, Union

# Import agent event types
try:
    from smolagents.agents import PlanningStep
    from smolagents.memory import ActionStep, FinalAnswerStep
    from smolagents.models import (
        ChatMessageStreamDelta, MessageRole, agglomerate_stream_deltas
    )
    from smolagents.agent_types import AgentAudio, AgentImage, AgentText
except ImportError as e:
    logging.error(f"Failed to import smolagents types: {e}")
    raise

from .models import DSAgentRunMessage

logger = logging.getLogger(__name__)


def get_step_footnote_content(
    step_log: Union[ActionStep, PlanningStep],
    step_name: str
) -> str:
    """Get a footnote string for step log with duration and token info."""
    step_footnote = f"**{step_name}**"
    if hasattr(step_log, 'token_usage') and step_log.token_usage is not None:
        step_footnote += (
            f" | Input tokens: {step_log.token_usage.input_tokens:,} | "
            f"Output tokens: {step_log.token_usage.output_tokens:,}"
        )
    if (hasattr(step_log, 'timing') and step_log.timing and
            step_log.timing.duration):
        duration = round(float(step_log.timing.duration), 2)
        step_footnote += f" | Duration: {duration}s"
    step_footnote_content = (
        f'<span style="color: #bbbbc2; font-size: 12px;">'
        f'{step_footnote}</span>'
    )
    return step_footnote_content


def _clean_model_output(model_output: str) -> str:
    """
    Clean up model output by removing trailing tags and extra backticks.

    Args:
        model_output: Raw model output.

    Returns:
        Cleaned model output.
    """
    if not model_output:
        return ""
    model_output = model_output.strip()
    # Remove any trailing <end_code> and extra backticks
    model_output = re.sub(r"```\s*<end_code>", "```", model_output)
    model_output = re.sub(r"<end_code>\s*```", "```", model_output)
    model_output = re.sub(r"```\s*\n\s*<end_code>", "```", model_output)
    return model_output.strip()


def _format_code_content(content: str) -> str:
    """
    Format code content as Python code block if not already formatted.

    Args:
        content: Code content to format.

    Returns:
        Code content formatted as a Python code block.
    """
    content = content.strip()
    # Remove existing code blocks and end_code tags
    content = re.sub(r"```.*?\n", "", content)
    content = re.sub(r"\s*<end_code>\s*", "", content)
    content = content.strip()
    # Add Python code block formatting if not already present
    if not content.startswith("```python"):
        content = f"```python\n{content}\n```"
    return content


def _extract_code_from_content(content: str) -> Optional[str]:
    """Extract code from markdown code blocks."""
    match = re.search(r"```(?:python)?\n([\s\S]*?)```", content)
    if match:
        return match.group(1).strip()
    return None


def process_planning_step(
    step_log: PlanningStep,
    step_number: int,
    session_id: Optional[str] = None,
    skip_model_outputs: bool = False,
    is_streaming: bool = False
) -> Generator[DSAgentRunMessage, None, None]:
    """
    Process a PlanningStep and yield DSAgentRunMessage objects.

    Args:
        step_log: PlanningStep to process.
        step_number: The step number this planning is for.
        session_id: Session ID for the messages.
        skip_model_outputs: Whether to skip model outputs.
        is_streaming: Whether we're in streaming mode.

    Yields:
        DSAgentRunMessage objects.
    """
    # Planning header
    if not skip_model_outputs:
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content="**Planning step**",
            metadata={
                "component": "chat",
                "message_type": "planning_header",
                "step_type": "planning",
                "status": "done"
            },
            session_id=session_id,
            step_number=step_number
        )

    # Planning content - always send initial message when streaming
    if not skip_model_outputs and step_log.plan:
        # Non-streaming mode - send complete content
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=step_log.plan,
            metadata={
                "component": "chat",
                "message_type": "planning_content",
                "step_type": "planning",
                "status": "done",
                "streaming": False
            },
            session_id=session_id,
            step_number=step_number
        )
    elif skip_model_outputs and is_streaming:
        # In streaming mode but also check if we have plan content
        # If we have plan content, send it even in streaming mode
        if step_log.plan:
            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=step_log.plan,
                metadata={
                    "component": "chat",
                    "message_type": "planning_content",
                    "step_type": "planning",
                    "status": "done",
                    "streaming": False
                },
                session_id=session_id,
                step_number=step_number
            )
        else:
            # Streaming mode - send initial empty message with stream_id
            stream_id = f"msg-{step_number}-planning_content-stream"
            logger.info(f"BACKEND: Creating initial streaming message with ID: {stream_id}, step: {step_number}")
            msg = DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content="",  # Start with empty content
                metadata={
                    "component": "chat",
                    "message_type": "planning_content", 
                    "step_type": "planning",
                    "status": "streaming",
                    "streaming": True,
                    "stream_id": stream_id,
                    "is_initial_stream": True
                },
                message_id=stream_id,
                session_id=session_id,
                step_number=step_number
            )
            logger.info(f"BACKEND: Initial streaming message details: {msg.model_dump()}")
            yield msg

    # Planning footer with timing info
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, "Planning step"),
        metadata={
            "component": "chat",
            "message_type": "planning_footer",
            "step_type": "planning",
            "status": "done"
        },
        session_id=session_id,
        step_number=step_number
    )

    # Separator
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="-----",
        metadata={
            "component": "chat",
            "message_type": "separator",
            "step_type": "planning",
            "status": "done"
        },
        session_id=session_id,
        step_number=step_number
    )


def process_action_step(
    step_log: ActionStep,
    session_id: Optional[str] = None,
    skip_model_outputs: bool = False
) -> Generator[DSAgentRunMessage, None, None]:
    """
    Process an ActionStep and yield DSAgentRunMessage objects.

    Args:
        step_log: ActionStep to process.
        session_id: Session ID for the messages.
        skip_model_outputs: Whether to skip model outputs.

    Yields:
        DSAgentRunMessage objects.
    """
    step_number = step_log.step_number

    # Step header
    if not skip_model_outputs:
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=f"**Step {step_number}**",
            metadata={
                "component": "chat",
                "message_type": "action_header",
                "step_type": "action",
                "status": "done"
            },
            session_id=session_id,
            step_number=step_number
        )

        # Thought/reasoning from the LLM
        if getattr(step_log, "model_output", ""):
            model_output = _clean_model_output(step_log.model_output)
            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=model_output,
                metadata={
                    "component": "chat",
                    "message_type": "action_thought",
                    "step_type": "action",
                    "status": "done",
                    "title": "Thought"
                },
                session_id=session_id,
                step_number=step_number
            )

    # Tool calls
    if getattr(step_log, "tool_calls", []):
        first_tool_call = step_log.tool_calls[0]
        tool_name = first_tool_call.name

        # Process arguments
        args = first_tool_call.arguments
        if isinstance(args, dict):
            content = str(args.get("answer", str(args)))
        else:
            content = str(args).strip()

        # Determine component based on tool
        if tool_name == "python_interpreter":
            # Format as code block
            content = _format_code_content(content)
            # Extract just the code for the code editor
            code_only = _extract_code_from_content(content)

            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=content,  # Full markdown for display
                metadata={
                    "component": "webide",
                    "message_type": "tool_invocation",
                    "tool_name": tool_name,
                    "step_type": "action",
                    "title": f"🛠️ Used tool {tool_name}",
                    "status": "done",
                    "code": code_only,  # Just the code for the editor
                    "language": "python"
                },
                session_id=session_id,
                step_number=step_number
            )
        else:
            # Other tools go to chat
            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                metadata={
                    "component": "chat",
                    "message_type": "tool_invocation",
                    "tool_name": tool_name,
                    "step_type": "action",
                    "title": f"🛠️ Used tool {tool_name}",
                    "status": "done"
                },
                session_id=session_id,
                step_number=step_number
            )

    # Execution logs / observations
    if getattr(step_log, "observations", "") and step_log.observations.strip():
        log_content = step_log.observations.strip()
        # Remove "Execution logs:" prefix if present
        log_content = re.sub(r"^Execution logs:\s*", "", log_content)

        # Check which tool generated these logs
        tool_name = None
        if hasattr(step_log, "tool_calls") and step_log.tool_calls:
            tool_name = step_log.tool_calls[0].name

        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=f"```bash\n{log_content}\n```",
            metadata={
                "component": "terminal",
                "message_type": "execution_logs",
                "tool_name": tool_name,
                "step_type": "action",
                "title": "📝 Execution Logs",
                "status": "done"
            },
            session_id=session_id,
            step_number=step_number
        )

    # Images in observations
    if getattr(step_log, "observations_images", []):
        for image in step_log.observations_images:
            path_image = AgentImage(image).to_string()
            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=f"![Image]({path_image})",
                metadata={
                    "component": "chat",
                    "message_type": "observation_image",
                    "step_type": "action",
                    "title": "🖼️ Output Image",
                    "status": "done",
                    "image_path": path_image,
                    "mime_type": f"image/{path_image.split('.')[-1]}"
                },
                session_id=session_id,
                step_number=step_number
            )

    # Errors
    if getattr(step_log, "error", None):
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=str(step_log.error),
            metadata={
                "component": "chat",
                "message_type": "error",
                "step_type": "action",
                "title": "💥 Error",
                "status": "done"
            },
            session_id=session_id,
            step_number=step_number
        )

    # Step footer
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, f"Step {step_number}"),
        metadata={
            "component": "chat",
            "message_type": "action_footer",
            "step_type": "action",
            "status": "done"
        },
        session_id=session_id,
        step_number=step_number
    )

    # Separator
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="-----",
        metadata={
            "component": "chat",
            "message_type": "separator",
            "step_type": "action",
            "status": "done"
        },
        session_id=session_id,
        step_number=step_number
    )


def process_final_answer_step(
    step_log: FinalAnswerStep,
    session_id: Optional[str] = None,
    step_number: Optional[int] = None
) -> Generator[DSAgentRunMessage, None, None]:
    """
    Process a FinalAnswerStep and yield DSAgentRunMessage objects.

    Args:
        step_log: FinalAnswerStep to process.
        session_id: Session ID for the messages.
        step_number: Step number for the message.

    Yields:
        DSAgentRunMessage objects.
    """
    final_answer = step_log.output

    if isinstance(final_answer, AgentText):
        content = f"**Final answer:**\n{final_answer.to_string()}\n"
    elif isinstance(final_answer, AgentImage):
        path = final_answer.to_string()
        content = f"**Final answer:**\n![Image]({path})"
    elif isinstance(final_answer, AgentAudio):
        path = final_answer.to_string()
        content = f"**Final answer:**\n[Audio]({path})"
    else:
        content = f"**Final answer:** {str(final_answer)}"

    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=content,
        metadata={
            "component": "chat",
            "message_type": "final_answer",
            "step_type": "final_answer",
            "status": "done",
            "is_final_answer": True
        },
        session_id=session_id,
        step_number=step_number
    )


async def stream_agent_messages(
    agent,
    task: str,
    task_images: Optional[List] = None,
    reset_agent_memory: bool = False,
    additional_args: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> AsyncGenerator[DSAgentRunMessage, None]:
    """
    Run an agent and stream DSAgentRunMessage objects.

    This is the main entry point that processes all agent events and yields
    properly formatted DSAgentRunMessage objects with component routing metadata.

    Args:
        agent: The agent instance to run.
        task: The task/query to execute.
        task_images: Optional images for the task.
        reset_agent_memory: Whether to reset agent memory.
        additional_args: Additional arguments for agent.
        session_id: Session ID for messages.

    Yields:
        DSAgentRunMessage objects with proper metadata.
    """
    # Track state
    current_step = 0
    accumulated_deltas: List[ChatMessageStreamDelta] = []
    skip_model_outputs = getattr(agent, "stream_outputs", False)

    # Streaming context tracking
    current_streaming_message_id = None
    current_streaming_step = None
    current_streaming_type = None

    try:
        # Note: User message is handled by the session layer

        # Run the agent
        event_generator = agent.run(
            task,
            images=task_images,
            stream=True,
            reset=reset_agent_memory,
            additional_args=additional_args
        )

        # Process events
        # Handle both async and sync generators
        if hasattr(event_generator, '__aiter__'):
            # Async generator
            async for event in event_generator:
                # Process different event types
                if isinstance(event, PlanningStep):
                    # Planning happens before the step it plans for
                    planning_for_step = current_step + 1

                    # Set streaming context for planning BEFORE yielding messages
                    if skip_model_outputs:
                        current_streaming_step = planning_for_step
                        current_streaming_type = "planning_content"
                        current_streaming_message_id = f"msg-{current_streaming_step}-{current_streaming_type}-stream"

                    for message in process_planning_step(
                        event, planning_for_step, session_id, skip_model_outputs,
                        is_streaming=skip_model_outputs  # If skipping outputs, we're streaming
                    ):
                        yield message
                    accumulated_deltas = []
                    # Don't reset streaming context here - wait for next non-delta event
                    logger.debug(f"Planning step complete. Streaming context: {current_streaming_message_id}")

                elif isinstance(event, ActionStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    # Update current step
                    current_step = event.step_number
                    for message in process_action_step(
                        event, session_id, skip_model_outputs
                    ):
                        yield message
                    accumulated_deltas = []

                elif isinstance(event, FinalAnswerStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    for message in process_final_answer_step(
                        event, session_id, current_step
                    ):
                        yield message
                    accumulated_deltas = []

                elif isinstance(event, ChatMessageStreamDelta):
                    # Accumulate streaming deltas
                    accumulated_deltas.append(event)
                    text = agglomerate_stream_deltas(accumulated_deltas).render_as_markdown()

                    # Determine streaming context if not set
                    if not current_streaming_message_id:
                        # Create initial streaming message context
                        # For planning, we're already at the correct step number
                        current_streaming_step = current_step + 1 if skip_model_outputs else current_step
                        current_streaming_type = "planning_content" if skip_model_outputs else "action_thought"
                        current_streaming_message_id = f"msg-{current_streaming_step}-{current_streaming_type}-stream"
                        logger.warning(f"ChatMessageStreamDelta without context. Creating new: {current_streaming_message_id}")

                    logger.info(f"Sending streaming delta: stream_id={current_streaming_message_id}, content_length={len(text)}, step={current_streaming_step}")

                    # Yield DSAgentRunMessage with streaming metadata
                    yield DSAgentRunMessage(
                        role=MessageRole.ASSISTANT,
                        content=text,
                        metadata={
                            "component": "chat",
                            "message_type": current_streaming_type,
                            "step_type": "planning" if skip_model_outputs else "action",
                            "status": "streaming",
                            "streaming": True,
                            "is_delta": True,  # Key indicator for frontend
                            "stream_id": current_streaming_message_id
                        },
                        message_id=current_streaming_message_id,
                        session_id=session_id,
                        step_number=current_streaming_step
                    )

                else:
                    logger.warning(f"Unknown event type: {type(event)}")
        else:
            # Sync generator - convert to async
            for event in event_generator:
                # Same processing logic as above
                if isinstance(event, PlanningStep):
                    planning_for_step = current_step + 1

                    # Set streaming context for planning BEFORE yielding messages
                    if skip_model_outputs:
                        current_streaming_step = planning_for_step
                        current_streaming_type = "planning_content"
                        current_streaming_message_id = f"msg-{current_streaming_step}-{current_streaming_type}-stream"

                    for message in process_planning_step(
                        event, planning_for_step, session_id, skip_model_outputs,
                        is_streaming=skip_model_outputs  # If skipping outputs, we're streaming
                    ):
                        yield message
                    accumulated_deltas = []
                    # Don't reset streaming context here - wait for next non-delta event
                    logger.debug(f"Planning step complete. Streaming context: {current_streaming_message_id}")

                elif isinstance(event, ActionStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    current_step = event.step_number
                    for message in process_action_step(
                        event, session_id, skip_model_outputs
                    ):
                        yield message
                    accumulated_deltas = []

                elif isinstance(event, FinalAnswerStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    for message in process_final_answer_step(
                        event, session_id, current_step
                    ):
                        yield message
                    accumulated_deltas = []

                elif isinstance(event, ChatMessageStreamDelta):
                    # Accumulate streaming deltas
                    accumulated_deltas.append(event)
                    text = agglomerate_stream_deltas(accumulated_deltas).render_as_markdown()

                    # Determine streaming context if not set
                    if not current_streaming_message_id:
                        # Create initial streaming message context
                        # For planning, we're already at the correct step number
                        current_streaming_step = current_step + 1 if skip_model_outputs else current_step
                        current_streaming_type = "planning_content" if skip_model_outputs else "action_thought"
                        current_streaming_message_id = f"msg-{current_streaming_step}-{current_streaming_type}-stream"
                        logger.warning(f"ChatMessageStreamDelta without context. Creating new: {current_streaming_message_id}")

                    logger.info(f"Sending streaming delta: stream_id={current_streaming_message_id}, content_length={len(text)}, step={current_streaming_step}")

                    # Yield DSAgentRunMessage with streaming metadata
                    yield DSAgentRunMessage(
                        role=MessageRole.ASSISTANT,
                        content=text,
                        metadata={
                            "component": "chat",
                            "message_type": current_streaming_type,
                            "step_type": "planning" if skip_model_outputs else "action",
                            "status": "streaming",
                            "streaming": True,
                            "is_delta": True,  # Key indicator for frontend
                            "stream_id": current_streaming_message_id
                        },
                        message_id=current_streaming_message_id,
                        session_id=session_id,
                        step_number=current_streaming_step
                    )

                else:
                    logger.warning(f"Unknown event type: {type(event)}")

    except Exception as e:
        logger.error(f"Error in stream_agent_messages: {e}", exc_info=True)
        # Yield error message
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=f"Error: {str(e)}",
            metadata={
                "component": "chat",
                "message_type": "error",
                "error": True,
                "error_type": type(e).__name__,
                "status": "done"
            },
            session_id=session_id,
            step_number=current_step
        )

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
import json
import ast
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator, Generator, Union

# Import agent event types
try:
    from smolagents.agents import PlanningStep
    from smolagents.memory import ActionStep, FinalAnswerStep
    from smolagents.models import (
        ChatMessageStreamDelta,
        MessageRole,
        agglomerate_stream_deltas,
    )
    from smolagents.agent_types import AgentAudio, AgentImage, AgentText
except ImportError as e:
    logging.error(f"Failed to import smolagents types: {e}")
    raise

from .models import DSAgentRunMessage

logger = logging.getLogger(__name__)


def get_step_footnote_content(
    step_log: Union[ActionStep, PlanningStep], step_name: str
) -> str:
    """Get a footnote string for step log with duration and token info."""
    step_footnote = f"**{step_name}**"
    if hasattr(step_log, "token_usage") and step_log.token_usage is not None:
        step_footnote += (
            f" | Input tokens: {step_log.token_usage.input_tokens:,} | "
            f"Output tokens: {step_log.token_usage.output_tokens:,}"
        )
    if (hasattr(step_log, "timing") and step_log.timing and
        step_log.timing.duration):
        duration = round(float(step_log.timing.duration), 2)
        step_footnote += f" | Duration: {duration}s"
    step_footnote_content = (
        f'<span style="color: #bbbbc2; font-size: 12px;">'
        f'{step_footnote}</span>'
    )
    return step_footnote_content


def get_step_metadata(
    step_log: Union[ActionStep, PlanningStep], step_name: str
) -> Dict[str, Any]:
    """Extract structured metadata from step log."""
    metadata = {
        "step_name": step_name,
    }

    # Token usage
    if hasattr(step_log, "token_usage") and step_log.token_usage is not None:
        metadata["token_usage"] = {
            "input_tokens": step_log.token_usage.input_tokens,
            "output_tokens": step_log.token_usage.output_tokens,
            "total_tokens": (
                step_log.token_usage.input_tokens +
                step_log.token_usage.output_tokens
            ),
        }

    # Timing information
    if hasattr(step_log, "timing") and step_log.timing:
        if hasattr(step_log.timing, "duration") and step_log.timing.duration:
            metadata["timing"] = {
                "duration": round(float(step_log.timing.duration), 2),
            }

    # Error information
    if hasattr(step_log, "error") and step_log.error:
        metadata["error"] = {
            "message": str(step_log.error),
            "type": type(step_log.error).__name__,
        }

    return metadata


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


def _extract_tools_from_code(code: str) -> List[str]:
    """
    Extract tool names from Python code.

    Args:
        code: Python code to analyze.

    Returns:
        List of tool names found in the code.
    """
    if not code:
        return []

    # Known tool names from toolbox.py
    known_tools = [
        "search_links", "search_fast", "read_url", "github_repo_qa",
        "xcom_deep_qa", "chunk_text", "embed_texts", "rerank_texts",
        "wolfram", "academic_retrieval", "final_answer"
    ]

    tool_calls = []

    # Check for tool calls using various patterns
    for tool in known_tools:
        # Pattern 1: Direct function call: tool_name(...)
        pattern1 = rf'\b{tool}\s*\('
        # Pattern 2: Variable assignment: var = tool_name(...)
        pattern2 = rf'=\s*{tool}\s*\('
        # Pattern 3: Method call: obj.tool_name(...)
        pattern3 = rf'\.{tool}\s*\('
        # Pattern 4: In list: [tool_name(...)]
        pattern4 = rf'\[\s*{tool}\s*\('

        if (re.search(pattern1, code) or re.search(pattern2, code) or
                re.search(pattern3, code) or re.search(pattern4, code)):
            if tool not in tool_calls:  # Avoid duplicates
                tool_calls.append(tool)
                logger.debug(f"Found tool in code: {tool}")

    return tool_calls


def process_planning_step(
    step_log: PlanningStep,
    step_number: int,
    session_id: Optional[str] = None,
    skip_model_outputs: bool = False,
    is_streaming: bool = False,
    planning_interval: Optional[int] = None,
) -> Generator[DSAgentRunMessage, None, None]:
    """
    Process a PlanningStep and yield DSAgentRunMessage objects.

    Args:
        step_log: PlanningStep to process.
        step_number: The step number this planning is for.
        session_id: Session ID for the messages.
        skip_model_outputs: Whether to skip model outputs.
        is_streaming: Whether we're in streaming mode.
        planning_interval: Planning interval from agent config.

    Yields:
        DSAgentRunMessage objects.
    """
    # Determine planning type
    is_initial = step_number == 1
    # is_update = (not is_initial and planning_interval and
    #              ((step_number - 1) % planning_interval == 0))
    planning_type = "initial" if is_initial else "update"

    # Planning header with type indicator - always send
    # Header is metadata, not model output, so should always be sent
    # Send empty content - the frontend will render based on metadata
    header_metadata = {
        "component": "chat",
        "message_type": "planning_header",
        "step_type": "planning",
        "planning_type": planning_type,
        "is_update_plan": not is_initial,
        "planning_step_number": step_number,
        "agent_status": "initial_planning" if is_initial else "update_planning",
        "is_active": is_streaming,
        "status": "done",
    }

    # Add error info if present
    if hasattr(step_log, "error") and step_log.error:
        header_metadata["error"] = {
            "message": str(step_log.error),
            "type": type(step_log.error).__name__,
        }

    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="",  # Empty - frontend renders badge based on metadata
        metadata=header_metadata,
        session_id=session_id,
        step_number=step_number,
    )

    # Planning content - always send initial message when streaming
    if not skip_model_outputs and step_log.plan:
        # Clean planning content - handle multiple edge cases
        plan_content = step_log.plan.strip()

        # Check if the entire content is wrapped in code blocks
        if plan_content.startswith("```") and plan_content.endswith("```"):
            # Extract content between first ``` and last ```
            # Handle cases like ```markdown, ```md, or just ```
            lines = plan_content.split("\n")
            if len(lines) > 2:
                # Remove first line (```language) and last line (```)
                inner_content = "\n".join(lines[1:-1])
                # Only use inner content if it's not empty
                if inner_content.strip():
                    plan_content = inner_content.strip()

        # Non-streaming mode - send complete content
        content_metadata = {
            "component": "chat",
            "message_type": "planning_content",
            "step_type": "planning",
            "planning_type": planning_type,
            "planning_step_number": step_number,
            "agent_status": "initial_planning" if is_initial else "update_planning",
            "is_active": False,
            "status": "done",
            "streaming": False,
            "thoughts_content": (plan_content[:120] + "...") if len(plan_content) > 120 else plan_content,  # First 120 chars with ellipsis
            "content_length": len(plan_content),
        }

        # Add step metadata (tokens, timing, etc.)
        content_metadata.update(get_step_metadata(step_log, 
                                                  "Planning content"))

        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=plan_content,
            metadata=content_metadata,
            session_id=session_id,
            step_number=step_number,
        )
    elif skip_model_outputs and is_streaming:
        # In streaming mode but also check if we have plan content
        # If we have plan content, send it even in streaming mode
        if step_log.plan:
            # Clean planning content - handle multiple edge cases
            plan_content = step_log.plan.strip()

            # Check if the entire content is wrapped in code blocks
            if plan_content.startswith("```") and plan_content.endswith("```"):
                # Extract content between first ``` and last ```
                # Handle cases like ```markdown, ```md, or just ```
                lines = plan_content.split("\n")
                if len(lines) > 2:
                    # Remove first line (```language) and last line (```)
                    inner_content = "\n".join(lines[1:-1])
                    # Only use inner content if it's not empty
                    if inner_content.strip():
                        plan_content = inner_content.strip()

            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=plan_content,
                metadata={
                    "component": "chat",
                    "message_type": "planning_content",
                    "step_type": "planning",
                    "planning_type": planning_type,
                    "agent_status": "initial_planning" if is_initial else "update_planning",
                    "is_active": False,
                    "status": "done",
                    "streaming": False,
                },
                session_id=session_id,
                step_number=step_number,
            )
        else:
            # Streaming mode - send initial empty message with stream_id
            stream_id = f"msg-{step_number}-planning_content-stream"
            logger.info(
                f"BACKEND: Creating initial streaming message "
                f"with ID: {stream_id}, step: {step_number}"
            )
            msg = DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content="",  # Start with empty content
                metadata={
                    "component": "chat",
                    "message_type": "planning_content",
                    "step_type": "planning",
                    "planning_type": planning_type,
                    "agent_status": "initial_planning" if is_initial else "update_planning",
                    "is_active": True,
                    "status": "streaming",
                    "streaming": True,
                    "stream_id": stream_id,
                    "is_initial_stream": True,
                },
                message_id=stream_id,
                session_id=session_id,
                step_number=step_number,
            )
            logger.info(
                f"BACKEND: Initial streaming message details: "
                f"{msg.model_dump()}"
            )
            yield msg

    # Planning footer with timing info
    footer_label = (
        "Initial planning step" if is_initial else "Updated planning step"
    )

    footer_metadata = {
        "component": "chat",
        "message_type": "planning_footer",
        "step_type": "planning",
        "planning_type": planning_type,
        "planning_step_number": step_number,
        "status": "done",
        "footer_label": footer_label,
    }

    # Add structured step metadata
    footer_metadata.update(get_step_metadata(step_log, footer_label))

    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, footer_label),
        metadata=footer_metadata,
        session_id=session_id,
        step_number=step_number,
    )

    # Separator
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="-----",
        metadata={
            "component": "chat",
            "message_type": "separator",
            "step_type": "planning",
            "status": "done",
        },
        session_id=session_id,
        step_number=step_number,
    )


def process_action_step(
    step_log: ActionStep,
    session_id: Optional[str] = None,
    skip_model_outputs: bool = False,
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
                "status": "done",
            },
            session_id=session_id,
            step_number=step_number,
        )

    # Process and send thought/reasoning from the LLM - always send
    # Send raw model output, let frontend handle display
    if getattr(step_log, "model_output", "") and not skip_model_outputs:
        model_output = _clean_model_output(step_log.model_output)

        # Log what we're processing
        logger.debug(f"Processing model_output (length: {len(model_output)})")

        # Send raw output, limited to 500 chars for safety
        # Frontend will show first 60 chars
        if model_output:
            thought_metadata = {
                "component": "chat",
                "message_type": "action_thought",
                "step_type": "action",
                "agent_status": "thinking",
                "is_active": False,
                "status": "done",
                "is_raw_thought": True,  # Indicate raw content
                "thoughts_content": (model_output[:120] + "...") if len(model_output) > 120 else model_output,  # First 120 chars with ellipsis
                "full_thought_length": len(model_output),
            }

            # Add error info if present
            if hasattr(step_log, "error") and step_log.error:
                thought_metadata["error"] = {
                    "message": str(step_log.error),
                    "type": type(step_log.error).__name__,
                }

            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=model_output[:500],  # Limit for safety
                metadata=thought_metadata,
                session_id=session_id,
                step_number=step_number,
            )
    elif skip_model_outputs and getattr(step_log, "model_output", ""):
        # In streaming mode - send initial empty message for action_thought
        stream_id = f"msg-{step_number}-action_thought-stream"
        logger.info(
            f"BACKEND: Creating initial streaming message for action_thought "
            f"with ID: {stream_id}, step: {step_number}"
        )
        
        # Get first 120 chars for preview
        model_output = _clean_model_output(step_log.model_output)
        thoughts_preview = (model_output[:120] + "...") if len(model_output) > 120 else model_output if model_output else "Thinking..."
        
        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content="",  # Start with empty content
            metadata={
                "component": "chat",
                "message_type": "action_thought",
                "step_type": "action",
                "agent_status": "thinking",
                "is_active": True,
                "status": "streaming",
                "streaming": True,
                "stream_id": stream_id,
                "is_initial_stream": True,
                "thoughts_content": thoughts_preview,  # Preview for UI
                "is_raw_thought": True,
            },
            message_id=stream_id,
            session_id=session_id,
            step_number=step_number,
        )

    # Tool calls
    if getattr(step_log, "tool_calls", []):
        # Send a tool_call message for each tool invocation
        for i, tool_call in enumerate(step_log.tool_calls):
            tool_name = tool_call.name
            tool_id = getattr(tool_call, "id", f"tool-{step_number}-{i}")

            # Create a summary of arguments
            args = tool_call.arguments
            if isinstance(args, dict):
                # For final_answer tool, show title if available
                if tool_name == "final_answer" and "answer" in args:
                    if isinstance(args["answer"], str) and args["answer"].strip().startswith("{"):
                        try:
                            answer_data = json.loads(args["answer"])
                            args_summary = f"Title: {answer_data.get('title', 'Final Answer')}"
                        except:
                            args_summary = "Generating final answer..."
                    else:
                        args_summary = "Generating final answer..."
                else:
                    # Show key-value pairs for other tools
                    args_summary = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
                    if len(args) > 3:
                        args_summary += f" ... ({len(args)} total args)"
            else:
                args_summary = str(args)[:100]

            # Send tool call badge message
            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content="",  # Empty content, frontend renders badge
                metadata={
                    "component": "chat",
                    "message_type": "tool_call",
                    "step_type": "action",
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "tool_args_summary": args_summary,
                    "is_python_interpreter": tool_name == "python_interpreter",
                    "status": "done",
                },
                session_id=session_id,
                step_number=step_number,
            )

        # Now process the first tool call for actual invocation
        first_tool_call = step_log.tool_calls[0]
        tool_name = first_tool_call.name

        # Process arguments and get code content
        if tool_name == "python_interpreter" and hasattr(step_log, "code_action") and step_log.code_action:
            # Use the more accurate code_action field for python_interpreter
            content = step_log.code_action
            code_only = content  # code_action is already clean code

            # Extract tools from the code and generate additional badges
            extracted_tools = _extract_tools_from_code(code_only)
            for extracted_tool in extracted_tools:
                yield DSAgentRunMessage(
                    role=MessageRole.ASSISTANT,
                    content="",  # Empty content, frontend renders badge
                    metadata={
                        "component": "chat",
                        "message_type": "tool_call",
                        "step_type": "action",
                        "tool_name": extracted_tool,
                        "tool_id": f"tool-{step_number}-extracted-{extracted_tool}",
                        "tool_args_summary": "Called from Python code",
                        "is_python_interpreter": False,
                        "status": "done",
                    },
                    session_id=session_id,
                    step_number=step_number,
                )
        else:
            # Fallback to original logic for non-python_interpreter tools
            args = first_tool_call.arguments
            if isinstance(args, dict):
                content = str(args.get("answer", str(args)))
            else:
                content = str(args).strip()

        # Determine component based on tool
        if tool_name == "python_interpreter":
            # Format as code block
            content = _format_code_content(content)
            # Extract just the code for the code editor (already have it from above)
            if not (hasattr(step_log, "code_action") and step_log.code_action):
                code_only = _extract_code_from_content(content)

            # Count code lines and check for imports
            code_lines = code_only.count('\n') + 1 if code_only else 0
            has_imports = bool(re.search(r'^\s*(import|from)\s+', code_only, re.MULTILINE)) if code_only else False

            yield DSAgentRunMessage(
                role=MessageRole.ASSISTANT,
                content=content,  # Full markdown for display
                metadata={
                    "component": "webide",
                    "message_type": "tool_invocation",
                    "tool_name": tool_name,
                    "step_type": "action",
                    "agent_status": "coding",
                    "is_active": False,
                    "title": f"🛠️ Used tool {tool_name}",
                    "status": "done",
                    "code": code_only,  # Just the code for the editor
                    "language": "python",
                    "code_lines": code_lines,
                    "has_imports": has_imports,
                },
                session_id=session_id,
                step_number=step_number,
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
                    "agent_status": "actions_running",
                    "is_active": False,
                    "title": f"🛠️ Used tool {tool_name}",
                    "status": "done",
                },
                session_id=session_id,
                step_number=step_number,
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

        # Count output lines and check for errors
        output_lines = log_content.count('\n') + 1
        has_error = bool(re.search(r'(error|exception|traceback|failed)', log_content, re.IGNORECASE))

        terminal_metadata = {
            "component": "terminal",
            "message_type": "execution_logs",
            "tool_name": tool_name,
            "step_type": "action",
            "agent_status": "actions_running",
            "is_active": False,
            "title": "📝 Execution Logs",
            "status": "done",
            "output_lines": output_lines,
            "has_error": has_error,
        }

        # Add execution duration if available from timing
        if hasattr(step_log, "timing") and step_log.timing and hasattr(step_log.timing, "duration"):
            terminal_metadata["execution_duration"] = round(float(step_log.timing.duration), 2)

        yield DSAgentRunMessage(
            role=MessageRole.ASSISTANT,
            content=f"```bash\n{log_content}\n```",
            metadata=terminal_metadata,
            session_id=session_id,
            step_number=step_number,
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
                    "mime_type": f"image/{path_image.split('.')[-1]}",
                },
                session_id=session_id,
                step_number=step_number,
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
                "status": "done",
            },
            session_id=session_id,
            step_number=step_number,
        )

    # Step footer
    footer_metadata = {
        "component": "chat",
        "message_type": "action_footer",
        "step_type": "action",
        "status": "done",
        "footer_label": f"Step {step_number}",
    }

    # Add structured step metadata
    footer_metadata.update(get_step_metadata(step_log, f"Step {step_number}"))

    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, f"Step {step_number}"),
        metadata=footer_metadata,
        session_id=session_id,
        step_number=step_number,
    )

    # Separator
    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content="-----",
        metadata={
            "component": "chat",
            "message_type": "separator",
            "step_type": "action",
            "status": "done",
        },
        session_id=session_id,
        step_number=step_number,
    )


def process_final_answer_step(
    step_log: FinalAnswerStep,
    session_id: Optional[str] = None,
    step_number: Optional[int] = None,
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

    # Default values
    content = ""
    metadata_extra = {}

    logger.info(f"=== PROCESSING FINAL ANSWER STEP ===")
    logger.info(f"Final answer type: {type(final_answer)}")

    if isinstance(final_answer, AgentText):
        content_str = final_answer.to_string()

        # Debug logging
        logger.info(
            f"Final answer content: "
            f"length={len(content_str)}, "
            f"starts_with_brace={content_str.strip().startswith('{')}, "
            f"preview={content_str[:200]}..."
        )
        logger.info(f"Content string repr: {repr(content_str[:100])}")

        # Check if content has the **Final answer:** prefix
        # and extract the JSON part
        json_content = content_str
        if content_str.startswith("**Final answer:**"):
            # Extract content after the prefix
            json_content = content_str[len("**Final answer:**"):].strip()
            logger.info(f"Removed Final answer prefix, json_content starts with: {json_content[:50]}")
        elif content_str.startswith("Final answer:"):
            # Handle case without asterisks
            json_content = content_str[len("Final answer:"):].strip()
            logger.info(f"Removed Final answer prefix (no asterisks), json_content starts with: {json_content[:50]}")

        # Try to parse JSON content from final_answer tool
        if json_content.strip().startswith("{"):
            try:
                # First try direct JSON parsing
                try:
                    data = json.loads(json_content)
                except json.JSONDecodeError:
                    # If that fails, try to convert Python dict string to JSON
                    # This handles cases where the tool returns str(dict)
                    # instead of json.dumps(dict)
                    # Parse as Python literal
                    data = ast.literal_eval(json_content)
                    logger.info(
                        "Converted Python dict string to proper dict"
                    )

                # Extract structured data
                title = data.get("title", "Final Answer")
                answer_content = data.get("content", "")
                sources = data.get("sources", [])

                # Send empty content when we have structured data
                # Frontend will use metadata fields instead
                # This prevents raw JSON from being displayed
                content = ""

                # Add structured data to metadata for direct use
                metadata_extra = {
                    "answer_title": title,
                    "answer_content": answer_content,  # Markdown content
                    "answer_sources": sources,
                    "has_structured_data": True,
                    "answer_format": "json",  # Indicate JSON format
                }

                logger.info(
                    f"Final answer parsed successfully: "
                    f"title='{title}', "
                    f"content_length={len(answer_content)}, "
                    f"sources_count={len(sources)}"
                )
                logger.info(f"Formatted content being sent: {content[:200]}...")
            except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                logger.error(f"Failed to parse final answer JSON: {e}")
                logger.error(f"JSON content that failed: {json_content[:200]}")
                # Fallback to raw content
                content = f"**Final answer:**\n{content_str}\n"
        else:
            logger.info(f"JSON content doesn't start with '{{', it starts with: {json_content[:50]}")
            content = f"**Final answer:**\n{content_str}\n"
    elif isinstance(final_answer, AgentImage):
        path = final_answer.to_string()
        content = f"**Final answer:**\n![Image]({path})"
    elif isinstance(final_answer, AgentAudio):
        path = final_answer.to_string()
        content = f"**Final answer:**\n[Audio]({path})"
    elif isinstance(final_answer, dict):
        # Handle dict type final answers
        logger.info(f"Processing dict final answer with keys: {list(final_answer.keys())}")
        try:
            # Extract structured data from dict
            title = final_answer.get("title", "Final Answer")
            answer_content = final_answer.get("content", "")
            sources = final_answer.get("sources", [])

            # Send empty content when we have structured data
            content = ""

            # Add structured data to metadata
            metadata_extra = {
                "answer_title": title,
                "answer_content": answer_content,
                "answer_sources": sources,
                "has_structured_data": True,
                "answer_format": "json",
            }

            logger.info(
                f"Dict final answer parsed: title='{title}', "
                f"content_length={len(answer_content)}, sources_count={len(sources)}"
            )
        except Exception as e:
            logger.error(f"Failed to parse dict final answer: {e}")
            content = f"**Final answer:** {str(final_answer)}"
    else:
        content = f"**Final answer:** {str(final_answer)}"

    yield DSAgentRunMessage(
        role=MessageRole.ASSISTANT,
        content=content,
        metadata={
            "component": "chat",
            "message_type": "final_answer",
            "step_type": "final_answer",
            "agent_status": "writing",
            "is_active": False,
            "status": "done",
            "is_final_answer": True,
            **metadata_extra,
        },
        session_id=session_id,
        step_number=step_number,
    )


async def stream_agent_messages(
    agent,
    task: str,
    task_images: Optional[List] = None,
    reset_agent_memory: bool = False,
    additional_args: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> AsyncGenerator[DSAgentRunMessage, None]:
    """
    Run an agent and stream DSAgentRunMessage objects.

    This is the main entry point that processes all agent events and yields
    properly formatted DSAgentRunMessage objects with component routing
    metadata.

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
    planning_interval = getattr(agent, "planning_interval", None)

    # Streaming context tracking
    current_streaming_message_id = None
    current_streaming_step = None
    current_streaming_type = None
    current_phase = None  # Track whether we're in 'planning' or 'action' phase

    try:
        # Note: User message is handled by the session layer

        # Run the agent
        event_generator = agent.run(
            task,
            images=task_images,
            stream=True,
            reset=reset_agent_memory,
            additional_args=additional_args,
        )

        # Process events
        # Handle both async and sync generators
        if hasattr(event_generator, "__aiter__"):
            # Async generator
            async for event in event_generator:
                # Process different event types
                if isinstance(event, PlanningStep):
                    # Planning happens before the step it plans for
                    planning_for_step = current_step + 1

                    # Update phase to planning
                    current_phase = "planning"

                    # Set streaming context for planning
                    # BEFORE yielding messages
                    if skip_model_outputs:
                        current_streaming_step = planning_for_step
                        current_streaming_type = "planning_content"
                        current_streaming_message_id = (
                            f"msg-{current_streaming_step}-"
                            f"{current_streaming_type}-stream"
                        )

                    for message in process_planning_step(
                        event,
                        planning_for_step,
                        session_id,
                        skip_model_outputs,
                        # If skipping outputs, we're streaming
                        is_streaming=skip_model_outputs,
                        planning_interval=planning_interval,
                    ):
                        yield message
                    accumulated_deltas = []
                    # Don't reset streaming context here - wait for
                    # next non-delta event
                    logger.debug(
                        f"Planning step complete. Streaming context: "
                        f"{current_streaming_message_id}"
                    )

                elif isinstance(event, ActionStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    # Update phase to action
                    current_phase = "action"

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
                    text = agglomerate_stream_deltas(
                        accumulated_deltas
                    ).render_as_markdown()

                    # Determine streaming context if not set
                    if not current_streaming_message_id:
                        # Create initial streaming message context
                        # For planning, we're already at
                        # the correct step number
                        current_streaming_step = (
                            current_step + 1 
                            if skip_model_outputs else current_step
                        )
                        current_streaming_type = (
                            "planning_content"
                            if current_phase == "planning"
                            else "action_thought"
                        )
                        current_streaming_message_id = (
                            f"msg-{current_streaming_step}-"
                            f"{current_streaming_type}-stream"
                        )
                        logger.warning(
                            f"ChatMessageStreamDelta without context. "
                            f"Creating new: {current_streaming_message_id}"
                        )

                    logger.info(
                        f"Sending streaming delta: "
                        f"stream_id={current_streaming_message_id}, "
                        f"content_length={len(text)}, "
                        f"step={current_streaming_step}"
                    )

                    # Determine agent status based on phase and type
                    # More accurate status mapping
                    if current_phase == "planning":
                        # Check if this is initial or update planning
                        agent_status = "initial_planning" if current_step == 0 else "update_planning"
                    elif current_streaming_type == "action_thought":
                        agent_status = "thinking"
                    elif current_streaming_type == "tool_invocation":
                        # Could be coding or other actions
                        agent_status = "actions_running"
                    else:
                        agent_status = "working"

                    logger.info(
                        f"Streaming delta status: phase={current_phase}, "
                        f"type={current_streaming_type}, status={agent_status}"
                    )

                    # Yield DSAgentRunMessage with streaming metadata
                    yield DSAgentRunMessage(
                        role=MessageRole.ASSISTANT,
                        content=text,
                        metadata={
                            "component": "chat",
                            "message_type": current_streaming_type,
                            "step_type": (
                                "planning" if current_phase == "planning" else "action"
                            ),
                            "agent_status": agent_status,
                            "is_active": True,
                            "status": "streaming",
                            "streaming": True,
                            "is_delta": True,  # Key indicator for frontend
                            "stream_id": current_streaming_message_id,
                        },
                        message_id=current_streaming_message_id,
                        session_id=session_id,
                        step_number=current_streaming_step,
                    )

                else:
                    logger.warning(f"Unknown event type: {type(event)}")
        else:
            # Sync generator - convert to async
            for event in event_generator:
                # Same processing logic as above
                if isinstance(event, PlanningStep):
                    planning_for_step = current_step + 1

                    # Update phase to planning
                    current_phase = "planning"

                    # Set streaming context for planning
                    # BEFORE yielding messages
                    if skip_model_outputs:
                        current_streaming_step = planning_for_step
                        current_streaming_type = "planning_content"
                        current_streaming_message_id = (
                            f"msg-{current_streaming_step}-"
                            f"{current_streaming_type}-stream"
                        )

                    for message in process_planning_step(
                        event,
                        planning_for_step,
                        session_id,
                        skip_model_outputs,
                        # If skipping outputs, we're streaming
                        is_streaming=skip_model_outputs,
                        planning_interval=planning_interval,
                    ):
                        yield message
                    accumulated_deltas = []
                    # Don't reset streaming context here - wait for
                    # next non-delta event
                    logger.debug(
                        f"Planning step complete. Streaming context: "
                        f"{current_streaming_message_id}"
                    )

                elif isinstance(event, ActionStep):
                    # Reset streaming context from previous event
                    current_streaming_message_id = None
                    current_streaming_step = None
                    current_streaming_type = None

                    # Update phase to action
                    current_phase = "action"

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
                    text = agglomerate_stream_deltas(
                        accumulated_deltas
                    ).render_as_markdown()

                    # Determine streaming context if not set
                    if not current_streaming_message_id:
                        # Create initial streaming message context
                        # For planning, we're already at
                        # the correct step number
                        current_streaming_step = (
                            current_step + 1 
                            if skip_model_outputs else current_step
                        )
                        current_streaming_type = (
                            "planning_content"
                            if current_phase == "planning"
                            else "action_thought"
                        )
                        current_streaming_message_id = (
                            f"msg-{current_streaming_step}-"
                            f"{current_streaming_type}-stream"
                        )
                        logger.warning(
                            f"ChatMessageStreamDelta without context. "
                            f"Creating new: {current_streaming_message_id}"
                        )

                    logger.info(
                        f"Sending streaming delta: "
                        f"stream_id={current_streaming_message_id}, "
                        f"content_length={len(text)}, "
                        f"step={current_streaming_step}"
                    )

                    # Determine agent status based on phase and type
                    # More accurate status mapping
                    if current_phase == "planning":
                        # Check if this is initial or update planning
                        agent_status = "initial_planning" if current_step == 0 else "update_planning"
                    elif current_streaming_type == "action_thought":
                        agent_status = "thinking"
                    elif current_streaming_type == "tool_invocation":
                        # Could be coding or other actions
                        agent_status = "actions_running"
                    else:
                        agent_status = "working"

                    logger.info(
                        f"Streaming delta status: phase={current_phase}, "
                        f"type={current_streaming_type}, status={agent_status}"
                    )

                    # Yield DSAgentRunMessage with streaming metadata
                    yield DSAgentRunMessage(
                        role=MessageRole.ASSISTANT,
                        content=text,
                        metadata={
                            "component": "chat",
                            "message_type": current_streaming_type,
                            "step_type": (
                                "planning" if current_phase == "planning" else "action"
                            ),
                            "agent_status": agent_status,
                            "is_active": True,
                            "status": "streaming",
                            "streaming": True,
                            "is_delta": True,  # Key indicator for frontend
                            "stream_id": current_streaming_message_id,
                        },
                        message_id=current_streaming_message_id,
                        session_id=session_id,
                        step_number=current_streaming_step,
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
                "status": "done",
            },
            session_id=session_id,
            step_number=current_step,
        )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/agent_callbacks.py
# code style: PEP 8
# code-related content: MUST be in English
"""
Agent Step Callbacks - monitoring agent run steps events & get steps data
for packaging into agent run events & steps data stream for MQ Server

This module extracts data from smolagents.memory objects and packages it
for event notifications and streaming data transfer.

NOTE: Agent Callbacks &  Stream Real-Time Data(Streamable HTTP & SSE)
      FastAPI are not working.
"""

import logging
import time
import json
import os
from datetime import datetime
import traceback
import uuid
from typing import Dict, Any, Optional, List
import asyncio

from smolagents.memory import (
    ActionStep, PlanningStep, TaskStep, SystemPromptStep,
    FinalAnswerStep, MemoryStep
)
from smolagents import ChatMessage
from .agent_response import agent_observer, EventType

# Comment out direct agent_observer usage until MQ reconstruction
# from .agent_response import agent_observer, EventType

logger = logging.getLogger(__name__)

# Create log directory for debugging - use relative path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
LOG_DIR = os.path.join(project_root, "callback_logs")
os.makedirs(LOG_DIR, exist_ok=True)


class AgentStepCallback:
    """Callback for tracking agent execution steps

    Extracts data from smolagents.memory objects and packages it
    for event notifications and streaming data transfer.
    """

    def __init__(self, session_id: str):
        """Initialize step callback

        Args:
            session_id: Session ID associated with steps
        """
        self.session_id = session_id
        self.last_step_time = time.time()
        self.step_counter = 0
        self.tool_calls_history: List[Dict[str, Any]] = []
        self.steps_stats = {
            "total": 0,
            "by_type": {},
            "tools_used": set()
        }

        # Create debug log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debug_log_path = os.path.join(
            LOG_DIR,
            f"callback_{session_id}_{timestamp}.log"
        )
        self._log(
            f"=== AgentStepCallback initialized for session {session_id} ==="
        )

        logger.info(f"🔧 Created step callback for session ID: {session_id}")

    def _serialize_chatmessage(self, obj: Any) -> Any:
        """serialize object, handle ChatMessage special case

        Args:
            obj: object to serialize

        Returns:
            serialized object
        """
        if isinstance(obj, ChatMessage):
            # convert ChatMessage to dict
            return {
                "role": obj.role,
                "content": obj.content,
                "name": getattr(obj, "name", None),
                "tool_calls": getattr(obj, "tool_calls", None),
                "_type": "ChatMessage"  # add type tag for debugging
            }
        elif isinstance(obj, dict):
            # recursively process all values in the dictionary
            return {k: self._serialize_chatmessage(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # recursively process all items in the list
            return [self._serialize_chatmessage(item) for item in obj]
        else:
            # other types return directly
            return obj

    def _prepare_json_serializable(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ensure data is JSON serializable

        Args:
            data: original data

        Returns:
            JSON serializable data
        """
        try:
            # first try direct serialization
            json.dumps(data)
            return data
        except (TypeError, OverflowError):
            # if fails, apply custom serialization
            return self._serialize_chatmessage(data)

    def _log(self, message: str, add_timestamp: bool = True) -> None:
        """Write message to debug log file

        Args:
            message: Message to log
            add_timestamp: Whether to add timestamp to message
        """
        try:
            with open(self.debug_log_path, "a", encoding="utf-8") as f:
                if add_timestamp:
                    timestamp = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )[:-3]
                    f.write(f"[{timestamp}] {message}\n")
                else:
                    f.write(f"{message}\n")
        except Exception as e:
            logger.error(f"Error writing to debug log: {e}")

    def __call__(self, memory_step: MemoryStep, agent=None) -> None:
        """Process memory step callback

        Args:
            memory_step: Memory step object from smolagents
            agent: Optional agent instance for additional context
        """
        step_start_time = time.time()
        step_interval = step_start_time - self.last_step_time
        self.last_step_time = step_start_time
        self.step_counter += 1

        # Basic logging
        step_type = type(memory_step).__name__
        self._log(f"===== STEP {self.step_counter} ({step_type}) =====")
        self._log(f"Step interval: {step_interval:.2f}s")

        # Update stats
        self.steps_stats["total"] += 1
        if step_type not in self.steps_stats["by_type"]:
            self.steps_stats["by_type"][step_type] = 0
        self.steps_stats["by_type"][step_type] += 1

        # console output, help debug
        print(f"\n⚡ [CALLBACK] Step #{self.step_counter} started: "
              f"session={self.session_id}, type={step_type}, "
              f"interval={step_interval:.2f}s")

        # publish step start event immediately
        self._publish_simple_step_event(step_type)

        try:
            # Extract step data using smolagents.memory built-in methods
            # Use dict() to get structured data
            step_data = self._extract_step_data(memory_step)

            # Process specific step types
            if isinstance(memory_step, SystemPromptStep):
                self._process_system_step(memory_step, step_data)
            elif isinstance(memory_step, TaskStep):
                self._process_task_step(memory_step, step_data)
            elif isinstance(memory_step, ActionStep):
                self._process_action_step(memory_step, step_data)
            elif isinstance(memory_step, PlanningStep):
                self._process_planning_step(memory_step, step_data)
            elif isinstance(memory_step, FinalAnswerStep):
                self._process_final_answer_step(memory_step, step_data)

            # Process final answer
            if isinstance(memory_step, FinalAnswerStep):
                self._publish_final_answer(memory_step.final_answer)

            step_total_time = time.time() - step_start_time
            logger.info(
                f"Step #{self.step_counter} completed in "
                f"{step_total_time:.2f}s"
            )
            self._log(f"Step completed in {step_total_time:.2f}s")

            # console output, help debug
            print(f"✅ [CALLBACK] Step #{self.step_counter} completed in "
                  f"{step_total_time:.2f}s")

        except Exception as e:
            error_msg = f"❌ Step callback error: {e}"
            stack_trace = traceback.format_exc()
            logger.error(error_msg, exc_info=True)
            self._log(f"ERROR: {error_msg}")
            self._log(f"Stack trace: {stack_trace}")

            # Publish error to MQ
            self._publish_error(str(e))

            # console output, help debug
            print(f"❌ [CALLBACK] Step #{self.step_counter} failed: {str(e)}")

        self._log(f"===== STEP {self.step_counter} COMPLETED =====")

    def _publish_simple_step_event(self, step_type: str) -> None:
        """publish simple step update event, ensure each step has an event

        Args:
            step_type: step type
        """
        try:
            # create simple step data
            basic_step_data = {
                "session_id": self.session_id,
                "step_counter": self.step_counter,
                "step_type": step_type,
                "timestamp": time.time(),
                "event_type": "step",
                "step_status": "started"
            }

            self._log(f"Publishing simple step event for #{self.step_counter}")

            # use create_task to publish immediately asynchronously
            asyncio.create_task(
                agent_observer.publish_step(
                    session_id=self.session_id,
                    step_data=basic_step_data
                )
            )

            # use asyncio.create_task to publish event notification immediately
            asyncio.create_task(
                agent_observer.publish_event(
                    session_id=self.session_id,
                    event_type=EventType.STEP_UPDATE,
                    data={
                        "step_number": self.step_counter,
                        "step_type": step_type,
                        "timestamp": time.time()
                    }
                )
            )

            self._log(f"Simple step event for #{self.step_counter} queued")

        except Exception as e:
            logger.error(f"Error publishing simple step event: {e}")
            self._log(f"ERROR: {str(e)}")

    def _extract_step_data(self, step: MemoryStep) -> Dict[str, Any]:
        """Extract structured data from memory step

        Uses the built-in dict() method and adds metadata

        Args:
            step: Memory step object

        Returns:
            Dict with structured step data
        """
        # Use step's built-in dict() method to get structured data
        try:
            # Get base data using step's own dict method
            step_data = step.dict()

            # ensure data is JSON serializable
            step_data = self._prepare_json_serializable(step_data)

            # Add our metadata
            step_data.update({
                "step_counter": self.step_counter,
                "step_type": type(step).__name__,
                "timestamp": time.time(),
                "session_id": self.session_id
            })

            self._log(
                f"Extracted data: "
                f"{json.dumps(step_data, default=str)[:200]}..."
            )
            return step_data

        except Exception as e:
            logger.error(f"Error extracting step data: {e}")
            self._log(f"Error extracting step data: {e}")
            # Fallback to basic data
            return {
                "step_counter": self.step_counter,
                "step_type": type(step).__name__,
                "timestamp": time.time(),
                "session_id": self.session_id,
                "error": str(e)
            }

    def _process_system_step(
        self,
        step: SystemPromptStep,
        step_data: Dict[str, Any]
    ) -> None:
        """Process system prompt step

        Args:
            step: System prompt step
            step_data: Extracted step data
        """
        self._log(
            f"Processing system prompt: {step.system_prompt[:100]}..."
        )

        # Add event-specific data to step_data
        step_data.update({
            "event_type": "system_prompt",
            "content": step.system_prompt
        })

        # Publish enriched step data to MQ
        self._publish_to_mq(step_data)

        logger.info(f"Processed system prompt for session {self.session_id}")

    def _process_task_step(
        self,
        step: TaskStep,
        step_data: Dict[str, Any]
    ) -> None:
        """Process task step

        Args:
            step: Task step
            step_data: Extracted step data
        """
        self._log(f"Processing task: {step.task[:100]}...")

        # Add event-specific data to step_data
        step_data.update({
            "event_type": "task",
            "content": step.task,
            "has_images": bool(step.task_images)
        })

        # Publish enriched step data to MQ
        self._publish_to_mq(step_data)

        logger.info(f"Processed task step for session {self.session_id}")

    def _process_action_step(
        self,
        step: ActionStep,
        step_data: Dict[str, Any]
    ) -> None:
        """Process action step

        Args:
            step: Action step
            step_data: Extracted step data
        """
        # ensure step_counter exists
        if "step_counter" not in step_data:
            step_data["step_counter"] = self.step_counter

        self._log(
            f"Processing action step #{step.step_number} "
            f"(counter: {self.step_counter})"
        )

        # ensure action step type identifier
        step_data["step_type"] = "ActionStep"
        step_data["detailed_type"] = type(step).__name__

        # process tool calls - ensure each tool call is recorded
        if step.tool_calls:
            self._log(f"Action has {len(step.tool_calls)} tool calls")

            for i, tool_call in enumerate(step.tool_calls):
                # extract tool call data
                tool_name = tool_call.name

                # update stats
                if tool_name:
                    self.steps_stats["tools_used"].add(tool_name)

                # create tool call event data
                tool_data = {
                    "event_type": "tool_call",
                    "name": tool_name,
                    "arguments": tool_call.arguments,
                    "id": tool_call.id,
                    "step_number": step.step_number,
                    "call_index": i,
                    "observations": (
                        step.observations
                        if i == len(step.tool_calls) - 1
                        else None
                    )
                }

                # add to history
                self.tool_calls_history.append(tool_data)

                # add tool call data to step_data
                step_data["tool_call"] = tool_data

                # publish tool call step directly - ensure each tool can be
                # tracked independently
                self._publish_tool_call(tool_data)

        # process model output (may contain code)
        if step.model_output and isinstance(step.model_output, str):
            step_data["model_output"] = step.model_output
            # check for Python code blocks
            if "```python" in step.model_output:
                self._process_code_blocks(
                    step.model_output,
                    step.observations,
                    step_data
                )

        # process errors
        if step.error:
            # add error data
            step_data.update({
                "error_event": "error",
                "error_message": str(step.error)
            })

            # publish error event
            self._publish_error(str(step.error))

        # publish full step data to MQ
        self._log(f"Publishing full step data for step #{self.step_counter}")
        self._publish_to_mq(step_data)

        logger.info(f"Processed action step for session {self.session_id}")

    def _publish_tool_call(self, tool_data: Dict[str, Any]) -> None:
        """publish tool call event separately

        Args:
            tool_data: tool call data
        """
        try:
            tool_name = tool_data.get("name", "unknown_tool")
            self._log(f"Publishing tool call: {tool_name}")

            # create tool call specific step data
            tool_step_data = {
                "step_counter": self.step_counter,
                "step_type": "ToolCallStep",
                "timestamp": time.time(),
                "session_id": self.session_id,
                "tool_call": tool_data,
                "tool_name": tool_name,
                "tool_args": tool_data.get("arguments", {})
            }

            # publish tool call step
            asyncio.create_task(
                agent_observer.publish_step(
                    session_id=self.session_id,
                    step_data=tool_step_data
                )
            ).add_done_callback(
                lambda t: self._log_task_result(t, f"Tool call {tool_name}")
            )

            self._log(f"Tool call {tool_name} queued for publishing")

        except Exception as e:
            error_msg = f"Error publishing tool call: {e}"
            logger.error(error_msg, exc_info=True)
            self._log(f"ERROR: {error_msg}")
            self._log(f"Stack trace: {traceback.format_exc()}")

    def _process_planning_step(
        self,
        step: PlanningStep,
        step_data: Dict[str, Any]
    ) -> None:
        """Process planning step

        Args:
            step: Planning step
            step_data: Extracted step data
        """
        self._log(f"Processing planning step: {step.plan[:100]}...")

        # Add event-specific data to step_data
        step_data.update({
            "event_type": "planning",
            "content": step.plan
        })

        # Publish enriched step data to MQ
        self._publish_to_mq(step_data)

        logger.info(f"Processed planning step for session {self.session_id}")

    def _process_final_answer_step(
        self,
        step: FinalAnswerStep,
        step_data: Dict[str, Any]
    ) -> None:
        """Process final answer step

        Args:
            step: Final answer step
            step_data: Extracted step data
        """
        self._log("Processing final answer step")

        # Add event-specific data to step_data
        step_data.update({
            "event_type": "final_answer",
            "content": step.final_answer
        })

        # Publish enriched step data to MQ
        self._publish_to_mq(step_data)

        logger.info(f"Processed final answer for session {self.session_id}")

    def _process_code_blocks(
        self,
        model_output: str,
        observations: Optional[str],
        step_data: Dict[str, Any]
    ) -> None:
        """Extract and process Python code blocks from model output

        Args:
            model_output: Model output text
            observations: Results of code execution
            step_data: Step data to update with code blocks
        """
        # Extract Python code blocks
        code_blocks = []
        lines = model_output.split("\n")
        in_code_block = False
        current_block = []

        for line in lines:
            if line.strip().startswith("```python"):
                in_code_block = True
                current_block = []
            elif line.strip() == "```" and in_code_block:
                in_code_block = False
                if current_block:
                    code_blocks.append("\n".join(current_block))
            elif in_code_block:
                current_block.append(line)

        if code_blocks:
            self._log(f"Found {len(code_blocks)} Python code blocks")

            # Add code execution data to step_data
            step_data.update({
                "code_event": "code_execution",
                "code": "\n\n".join(code_blocks),
                "code_output": observations,
                "code_error": None,
                "code_timestamp": time.time(),
                "code_event_id": str(uuid.uuid4())[:8]
            })

    def get_statistics(self) -> Dict[str, Any]:
        """Get step execution statistics

        Returns:
            Dict with execution statistics
        """
        return {
            "steps_count": self.steps_stats["total"],
            "steps_by_type": self.steps_stats["by_type"],
            "tools_used": list(self.steps_stats["tools_used"]),
            "tool_calls": len(self.tool_calls_history)
        }

    def _publish_to_mq(self, step_data: Dict[str, Any]) -> None:
        """publish step data to MQ, ensure real-time synchronization

        This function ensures that each step is published immediately when
        generated, without waiting for subsequent steps.
        Use synchronous Redis client to ensure message is sent immediately.
        """
        try:
            # record step metadata
            step_num = self.step_counter
            step_type = step_data.get("step_type", "unknown")
            self._log(f"Publishing step #{step_num} type={step_type} to MQ")

            # console output, ensure visibility
            print(f"🚀 [CALLBACK] Publishing step #{step_num} type={step_type}")

            # ensure important fields exist
            step_data["session_id"] = self.session_id
            step_data["timestamp"] = time.time()
            step_data["step_counter"] = step_num

            # ensure data is JSON serializable
            step_data = self._prepare_json_serializable(step_data)

            # create a synchronous Redis client, ensure message is
            # sent immediately
            import redis as sync_redis
            r = sync_redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", "yourpassword"),
                decode_responses=True
            )

            # convert step_data to Redis compatible format
            # (all values must be strings)
            redis_compatible_data = {}
            for key, value in step_data.items():
                if isinstance(value, (dict, list)):
                    redis_compatible_data[key] = json.dumps(value)
                elif value is None:
                    redis_compatible_data[key] = ""
                else:
                    redis_compatible_data[key] = str(value)

            # use processed data to add to stream
            step_id = r.xadd(
                f"agent_steps:{self.session_id}",
                redis_compatible_data,
                maxlen=500
            )
            self._log(
                f"Step #{step_num} added to stream "
                f"agent_steps:{self.session_id}, ID={step_id}"
            )

            # publish event notification - use synchronous redis client
            r.publish(
                f"agent_event_notifications:{self.session_id}",
                json.dumps({
                    "event_type": "step",
                    "step_type": step_type,
                    "step_id": f"{time.time()}-{uuid.uuid4().hex[:8]}",
                    "session_id": self.session_id,
                    "timestamp": time.time(),
                    "step_counter": step_num
                })
            )

            # close Redis connection
            r.close()

            # publish event notification - use agent_observer asynchronously
            # (as backup)
            try:
                # when using asynchronous publishing, do not wait for results
                asyncio.create_task(
                    agent_observer.publish_step(
                        session_id=self.session_id,
                        step_data=step_data
                    )
                )
            except Exception as async_err:
                self._log(f"Asynchronous publishing failed: {async_err}")

            self._log(f"Step #{step_num} published")
            print(f"✅ [CALLBACK] Step #{step_num} published")

        except Exception as e:
            error_msg = f"Error in _publish_to_mq: {e}"
            logger.error(error_msg, exc_info=True)
            self._log(f"Error: {error_msg}")
            self._log(f"Stack trace: {traceback.format_exc()}")

    def _log_task_result(self, task, description):
        """log the result of asynchronous tasks"""
        try:
            # get task result
            task.result()
            self._log(f"Task '{description}' completed successfully")
        except asyncio.CancelledError:
            self._log(f"Task '{description}' was cancelled")
        except Exception as e:
            self._log(f"Task '{description}' failed with error: {e}")
            self._log(f"Stack trace: {traceback.format_exc()}")

    def _publish_final_answer(self, answer_data: Any) -> None:
        """publish final answer to MQ"""
        try:
            self._log(f"Publishing final answer for session {self.session_id}")

            # create asynchronous task to publish final answer
            asyncio.create_task(
                agent_observer.record_final_answer(
                    session_id=self.session_id,
                    answer_data=answer_data
                )
            ).add_done_callback(
                lambda t: self._log_task_result(t, "Final answer")
            )

            self._log("Final answer queued for publishing")

        except Exception as e:
            error_msg = f"Error publishing final answer to MQ: {e}"
            logger.error(error_msg, exc_info=True)
            self._log(f"ERROR: {error_msg}")
            self._log(f"Stack trace: {traceback.format_exc()}")

    def _publish_error(self, error_message: str) -> None:
        """Publish error to MQ"""
        try:
            self._log(f"Publishing error: {error_message}")

            # create asynchronous task to publish error
            asyncio.create_task(
                agent_observer.publish_event(
                    session_id=self.session_id,
                    event_type=EventType.ERROR,
                    data={"message": error_message}
                )
            ).add_done_callback(
                lambda t: self._log_task_result(t, "Error event")
            )

            self._log("Error event queued for publishing")

        except Exception as e:
            error_msg = f"Error publishing error to MQ: {e}"
            logger.error(error_msg, exc_info=True)
            self._log(f"ERROR: {error_msg}")
            self._log(f"Stack trace: {traceback.format_exc()}")

    def _process_step_data(self, data):
        """process step data, ensure synchronous immediate publishing
        to Redis"""
        # create step event data
        step_event = {
            "session_id": self.session_id,
            "step_counter": self.step_counter,
            "step_type": data.get("step_type", "unknown"),
            "timestamp": time.time(),
            "event_type": "step",  # explicitly identify event type
            "data": data  # include complete step data
        }

        try:
            # use synchronous Redis client to ensure immediate publishing
            import redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", "yourpassword"),
                decode_responses=True
            )

            all_channels = [
                f"agent_step_notifications:{self.session_id}",
                f"agent_direct_notifications:{self.session_id}",
                f"agent_runtime_events:{self.session_id}",
                f"agent_event_notifications:{self.session_id}"
            ]

            for channel in all_channels:
                result = r.publish(channel, json.dumps(step_event))
                self._log(
                    f"Synchronously published to channel {channel}: "
                    f"{result} receivers"
                )

            # add to step stream
            stream_key = f"agent_steps:{self.session_id}"
            r.xadd(
                stream_key,
                {
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in step_event.items()
                },
                maxlen=500
            )

            r.close()
            return True
        except Exception as e:
            self._log(f"Failed to publish step event: {e}")
            return False

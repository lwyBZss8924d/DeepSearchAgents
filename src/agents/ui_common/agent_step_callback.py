#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/agent_step_callback.py
# code style: PEP 8

"""
Agent Step Callback for CLI
Implements accurate step tracking using smolagents.memory objects

TODO: clean up redundant and invalid token stats code
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List, Callable, Set, DefaultDict
from collections import defaultdict

from smolagents.memory import (
    ActionStep, PlanningStep, TaskStep, SystemPromptStep,
    FinalAnswerStep, MemoryStep
)
from smolagents.monitoring import AgentLogger, Monitor, LogLevel
from smolagents import TokenUsage
from rich.console import Console


logger = logging.getLogger(__name__)


class AgentStepCallback:
    """Callback for tracking agent execution steps

    Uses smolagents.memory objects to accurately capture agent steps,
    tool calls, and execution results for CLI display.
    """

    def __init__(
        self,
        on_step_callback: Optional[Callable] = None,
        debug_mode: bool = False,
        model=None
    ):
        """Initialize step callback

        Args:
            on_step_callback: Optional callback function to receive step data
            debug_mode: Whether to enable debug mode
            model: reference to LLM model instance, for token counting
        """
        self.on_step_callback = on_step_callback
        self.debug_mode = debug_mode
        self.last_step_time = time.time()
        self.step_counter = 0
        self.tool_calls_history: List[Dict[str, Any]] = []
        self.tools_used: Set[str] = set()
        self.steps_stats = {
            "total": 0,
            "by_type": {},
            "tools_used": set(),
            "tool_call_count": 0
        }

        # New performance monitoring stats
        self.llm_times: DefaultDict[str, List[float]] = defaultdict(list)
        self.tool_times: DefaultDict[str, List[float]] = defaultdict(list)
        self.total_llm_time = 0.0
        self.total_tool_time = 0.0
        self.token_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "step_tokens": {}
        }

        # Common tool names used in both React and CodeAct modes
        self.known_tools = [
            "search_links", "search_fast", "read_url", "chunk_text",
            "embed_texts", "rerank_texts", "wolfram", "final_answer",
            "xcom_deep_qa", "github_repo_qa", "python_interpreter"
        ]

        # use smolagents' Monitor to track token
        self.model = model
        self.monitor = None
        if model:
            # create a console object, for AgentLogger
            console_obj = Console()
            # set AgentLogger instance
            agent_logger = AgentLogger(
                level=LogLevel.INFO,
                console=console_obj
            )
            self.monitor = Monitor(tracked_model=model, logger=agent_logger)

        logger.info("🔧 Created CLI step callback")

    def __call__(self, memory_step: MemoryStep) -> None:
        """Process memory step callback

        Args:
            memory_step: Memory step object from smolagents
        """
        step_start_time = time.time()
        step_interval = step_start_time - self.last_step_time
        self.last_step_time = step_start_time
        self.step_counter += 1

        # Basic logging
        step_type = type(memory_step).__name__

        # Update stats
        self.steps_stats["total"] += 1
        if step_type not in self.steps_stats["by_type"]:
            self.steps_stats["by_type"][step_type] = 0
        self.steps_stats["by_type"][step_type] += 1

        logger.debug(
            f"Step #{self.step_counter} started: type={step_type}, "
            f"interval={step_interval:.2f}s"
        )

        try:
            # check model token counting capabilities
            if self.model and self.step_counter == 1:
                if hasattr(self.model, "last_input_token_count"):
                    logger.info(
                        "Token counting enabled: "
                        "Model has token counting capabilities"
                    )
                else:
                    logger.warning(
                        "Token counting may not work: "
                        "Model lacks token counting attributes"
                    )

            # Extract step data based on step type
            step_data = self._extract_step_data(memory_step)

            # Extract token counting from the step if available
            self._extract_token_stats(memory_step, step_data)

            # Notify callback if available
            if self.on_step_callback:
                self.on_step_callback(step_data)

            step_total_time = time.time() - step_start_time
            logger.debug(
                f"Step #{self.step_counter} completed in "
                f"{step_total_time:.2f}s"
            )

            # update monitor metrics, for all step types
            if self.monitor:
                self.monitor.update_metrics(memory_step)
                logger.debug(
                    f"Updated monitor metrics for step #{self.step_counter}"
                )
                has_tokens = (hasattr(self.model, "last_input_token_count") or
                              hasattr(self.model, "last_output_token_count"))
                if self.model and has_tokens:
                    logger.debug(
                        f"Model token counts: "
                        f"input={self.model.last_input_token_count}, "
                        f"output={self.model.last_output_token_count}"
                    )

            # record token stats log
            logger.debug(
                f"Token stats for step #{self.step_counter}: "
                f"input={step_data.get('input_tokens', 0)}, "
                f"output={step_data.get('output_tokens', 0)}, "
                f"total={step_data.get('total_tokens', 0)}"
            )

        except Exception as e:
            error_msg = f"Step callback error: {e}"
            logger.error(error_msg, exc_info=True)

            # Still notify callback with error information
            if self.on_step_callback:
                error_data = {
                    "error": True,
                    "error_message": str(e),
                    "message": f"Error processing step: {e}",
                    "step_counter": self.step_counter,
                    "step_type": step_type,
                    "detailed_type": "error"
                }
                self.on_step_callback(error_data)

    def _extract_token_stats(
        self, memory_step: MemoryStep, step_data: Dict[str, Any]
    ) -> None:
        """Extract token stats information using smolagents v1.19.0 TokenUsage API

        Args:
            memory_step: Memory step object
            step_data: step data dictionary
        """
        step_id = str(self.step_counter)

        # initialize token stats
        self.token_stats["step_tokens"][step_id] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "type": type(memory_step).__name__
        }

        # record step type
        logger.debug(
            f"Token extraction for step #{step_id}, "
            f"type: {type(memory_step).__name__}"
        )

        # get token counts from memory step's token_usage attribute
        input_tokens = 0
        output_tokens = 0

        # Check if step has token_usage attribute (ActionStep, PlanningStep)
        if hasattr(memory_step, "token_usage") and memory_step.token_usage:
            token_usage = memory_step.token_usage
            if isinstance(token_usage, TokenUsage):
                input_tokens = token_usage.input_tokens or 0
                output_tokens = token_usage.output_tokens or 0
                logger.debug(
                    f"Got tokens from TokenUsage: "
                    f"in={input_tokens}, out={output_tokens}"
                )
            elif isinstance(token_usage, dict):
                # Fallback for dict-based token usage
                input_tokens = token_usage.get("input_tokens", 0)
                output_tokens = token_usage.get("output_tokens", 0)
                logger.debug(
                    f"Got tokens from dict: "
                    f"in={input_tokens}, out={output_tokens}"
                )
        else:
            logger.debug(
                f"Step type {type(memory_step).__name__} has no token_usage"
            )

        # update step token counts
        self.token_stats["step_tokens"][step_id]["input_tokens"] = input_tokens
        self.token_stats["step_tokens"][
            "output_tokens"
        ] = output_tokens

        # update total token counts
        self.token_stats["total_input_tokens"] += input_tokens
        self.token_stats["total_output_tokens"] += output_tokens

        # add to step_data for UI display
        step_data["token_counts"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

        step_data["input_tokens"] = input_tokens
        step_data["output_tokens"] = output_tokens
        step_data["total_tokens"] = input_tokens + output_tokens

        # record final extracted token data
        logger.debug(
            f"Final tokens for step #{step_id}: "
            f"in={input_tokens}, out={output_tokens}, "
            f"total={input_tokens + output_tokens}"
        )

        # add cumulative token info
        step_data["total_token_counts"] = {
            "input": self.token_stats["total_input_tokens"],
            "output": self.token_stats["total_output_tokens"],
            "total": (
                self.token_stats["total_input_tokens"] +
                self.token_stats["total_output_tokens"]
            )
        }

    def _extract_step_data(self, step: MemoryStep) -> Dict[str, Any]:
        """Extract relevant data from memory step based on step type

        Args:
            step: Memory step object

        Returns:
            Dict with structured step data
        """
        # Base step data common to all types
        base_data = {
            "step_counter": self.step_counter,
            "step_type": type(step).__name__,
            "timestamp": time.time()
        }

        # Process specific step types
        if isinstance(step, SystemPromptStep):
            return self._process_system_step(step, base_data)
        elif isinstance(step, TaskStep):
            return self._process_task_step(step, base_data)
        elif isinstance(step, ActionStep):
            return self._process_action_step(step, base_data)
        elif isinstance(step, PlanningStep):
            return self._process_planning_step(step, base_data)
        elif isinstance(step, FinalAnswerStep):
            return self._process_final_answer_step(step, base_data)
        else:
            # Default for unknown step types
            base_data["content"] = str(step)
            return base_data

    def _process_system_step(
        self,
        step: SystemPromptStep,
        base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process system prompt step

        Args:
            step: System prompt step
            base_data: Base step data

        Returns:
            Dict with processed step data
        """
        base_data.update({
            "content": step.system_prompt,
            "detailed_type": "system_prompt"
        })
        return base_data

    def _process_task_step(
        self,
        step: TaskStep,
        base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process task step

        Args:
            step: Task step
            base_data: Base step data

        Returns:
            Dict with processed step data
        """
        base_data.update({
            "content": step.task,
            "has_images": bool(step.task_images),
            "detailed_type": "task"
        })
        return base_data

    def _process_action_step(
        self,
        step: ActionStep,
        base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process action step

        Args:
            step: Action step
            base_data: Base step data

        Returns:
            Dict with processed step data
        """
        # Base action step data
        base_data.update({
            "step_number": getattr(step, 'step_number', self.step_counter),
            "detailed_type": "action",
            "model_output": getattr(step, 'model_output', None)
        })

        # Add timing data if available
        if hasattr(step, 'start_time'):
            base_data["start_time"] = step.start_time
        if hasattr(step, 'end_time'):
            base_data["end_time"] = step.end_time
        if hasattr(step, 'duration'):
            base_data["duration"] = step.duration

        # Calculate LLM thinking time vs tool execution time
        if hasattr(step, 'start_time') and hasattr(step, 'end_time') and step.start_time and step.end_time:
            # Track timing details - if there are observations,
            # assume part of the time was spent executing the tool
            tool_execution_time = 0
            duration = getattr(step, 'duration', 0)
            llm_thinking_time = duration

            if step.tool_calls and step.observations:
                # TODO: need to be calculated based on actual timing
                tool_execution_time = duration * 0.7
                llm_thinking_time = duration - tool_execution_time

                # Record timing stats for the first tool
                first_tool = (step.tool_calls[0].name
                              if step.tool_calls else "unknown_tool")
                self.llm_times[first_tool].append(llm_thinking_time)
                self.tool_times[first_tool].append(tool_execution_time)

                self.total_llm_time += llm_thinking_time
                self.total_tool_time += tool_execution_time

            # Add timing information to step data
            base_data.update({
                "llm_thinking_time": llm_thinking_time,
                "tool_execution_time": tool_execution_time,
                "total_llm_time": self.total_llm_time,
                "total_tool_time": self.total_tool_time
            })

        # Process tool calls
        if step.tool_calls:
            self.steps_stats["tool_call_count"] += len(step.tool_calls)
            tool_calls_data = []

            for i, tool_call in enumerate(step.tool_calls):
                # Extract tool call information
                tool_name = tool_call.name

                # Update tools used set
                if tool_name:
                    self.tools_used.add(tool_name)
                    self.steps_stats["tools_used"].add(tool_name)

                # Format tool call data
                tool_data = {
                    "name": tool_name,
                    "arguments": tool_call.arguments,
                    "id": tool_call.id or f"tool_{i}",
                    "call_index": i
                }

                # Handle CodeAct mode - check if this is
                # python_interpreter tool
                if tool_name == "python_interpreter":
                    # Extract tools used in Python code
                    code_tools = self._extract_tools_from_code(
                        step.model_output
                    )
                    if code_tools:
                        tool_data["code_tools"] = code_tools
                        # Add these tools to our statistics
                        for code_tool in code_tools:
                            self.tools_used.add(code_tool)
                            self.steps_stats["tools_used"].add(code_tool)

                tool_calls_data.append(tool_data)

                # Add to tool history
                self.tool_calls_history.append(tool_data)

            base_data["tool_calls"] = tool_calls_data

            # Add computed field for ConsoleFormatter compatibility
            has_tools = len(tool_calls_data) > 0
            if has_tools:
                base_data["action"] = tool_calls_data[0]["name"]

        # Include observations if present
        if step.observations is not None:
            base_data["observations"] = step.observations

        # Add action_output for compatibility
        if step.action_output is not None:
            base_data["action_output"] = step.action_output

        # Include error if present
        if step.error:
            error_str = str(step.error)
            base_data["error"] = error_str
            base_data["error_message"] = error_str

            # when the tool is python_interpreter, set detailed_type to error
            if "tool_calls" in base_data and len(base_data["tool_calls"]) > 0:
                if base_data["tool_calls"][0]["name"] == "python_interpreter":
                    base_data["detailed_type"] = "error"
                    logger.error(f"Python interpreter error: {error_str}")

        return base_data

    def _extract_tools_from_code(self, model_output) -> List[str]:
        """Extract tools from Python code

        Args:
            model_output: model output, may contain Python code

        Returns:
            List[str]: tool names list
        """
        if not model_output:
            return []

        # extract Python code
        model_output_str = str(model_output)
        # Support both markdown and XML formats
        markdown_blocks = re.findall(
            r'```python\s*(.*?)\s*```',
            model_output_str,
            re.DOTALL
        )
        xml_blocks = re.findall(
            r'<code>\s*(.*?)\s*</code>',
            model_output_str,
            re.DOTALL
        )
        code_blocks = markdown_blocks + xml_blocks

        if not code_blocks:
            return []

        code = code_blocks[0]
        tool_calls = []

        # agent tool extraction logic enhancement
        # 1. check direct function call: tool_name(...)
        # 2. check variable assignment: var = tool_name(...)
        # 3. check object method call: obj.tool_name(...)
        # 4. check object in list: [tool_name(...)]
        for tool in self.known_tools:
            # 1. direct function call: tool_name(...)
            pattern1 = fr'\b{tool}\s*\('
            # 2. variable assignment: var = tool_name(...)
            pattern2 = fr'=\s*{tool}\s*\('
            # 3. object method call: obj.tool_name(...)
            pattern3 = fr'\.{tool}\s*\('
            # 4. object in list: [tool_name(...)]
            pattern4 = fr'\[\s*{tool}\s*\('

            if (re.search(pattern1, code) or re.search(pattern2, code) or
                    re.search(pattern3, code) or re.search(pattern4, code)):
                tool_calls.append(tool)
                logger.debug(f"Found tool in code: {tool}")

        # record scan results
        if tool_calls:
            logger.debug(f"Extracted tools from code: {tool_calls}")
        else:
            logger.debug("No tools found in code")

        return tool_calls

    def _process_planning_step(
        self,
        step: PlanningStep,
        base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process planning step

        Args:
            step: Planning step
            base_data: Base step data

        Returns:
            Dict with processed step data
        """
        base_data.update({
            "content": step.plan,
            "detailed_type": "planning",
            # Add compatible field for ConsoleFormatter
            "plan": step.plan
        })
        return base_data

    def _process_final_answer_step(
        self,
        step: FinalAnswerStep,
        base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process final answer step

        Args:
            step: Final answer step
            base_data: Base step data

        Returns:
            Dict with processed step data
        """
        base_data.update({
            "content": step.final_answer,
            "detailed_type": "final_answer",
            # Add compatible field for ConsoleFormatter
            "answer": step.final_answer
        })
        return base_data

    def get_statistics(self) -> Dict[str, Any]:
        """Get step execution statistics

        Returns:
            Dict with execution statistics
        """
        # Calculate average LLM and tool times for each tool
        avg_llm_times = {}
        avg_tool_times = {}

        for tool_name, times in self.llm_times.items():
            if times:
                avg_llm_times[tool_name] = sum(times) / len(times)

        for tool_name, times in self.tool_times.items():
            if times:
                avg_tool_times[tool_name] = sum(times) / len(times)

        # first use our own collected token stats
        token_stats = {
            "total_input": self.token_stats["total_input_tokens"],
            "total_output": self.token_stats["total_output_tokens"],
            "total": (
                self.token_stats["total_input_tokens"] +
                self.token_stats["total_output_tokens"]
            )
        }

        # TODO: clean up redundant and invalid token stats code
        # try to get token stats from smolagents Monitor (if available)
        if self.monitor:
            try:
                # get token data via get_total_token_counts method
                monitor_tokens = self.monitor.get_total_token_counts()

                # check if the returned token data is valid
                if (isinstance(monitor_tokens, dict) and
                        "input" in monitor_tokens):
                    # only use Monitor data when our own token stats are 0,
                    # but Monitor has data
                    if (token_stats["total_input"] == 0 and
                            token_stats["total_output"] == 0 and
                            (monitor_tokens["input"] > 0 or
                             monitor_tokens["output"] > 0)):
                        logger.info("Using token statistics from Monitor")
                        token_stats = {
                            "total_input": monitor_tokens["input"],
                            "total_output": monitor_tokens["output"],
                            "total": (
                                monitor_tokens["input"] +
                                monitor_tokens["output"]
                            )
                        }

                    # record Monitor's token stats, for debugging
                    logger.debug(
                        f"Monitor token counts - "
                        f"input: {monitor_tokens['input']}, "
                        f"output: {monitor_tokens['output']}"
                    )
            except Exception as e:
                # handle possible errors, record errors and continue
                # using default token stats
                logger.warning(
                    f"Error getting token counts from Monitor: {e}"
                )
                # try to get token counts directly from model object
                if self.model:
                    try:
                        has_input = hasattr(
                            self.model, "last_input_token_count")
                        has_output = hasattr(
                            self.model, "last_output_token_count")
                        if has_input and has_output:
                            token_stats["total_input"] = getattr(
                                self.model, "last_input_token_count", 0
                            )
                            token_stats["total_output"] = getattr(
                                self.model, "last_output_token_count", 0
                            )
                            token_stats["total"] = (
                                token_stats["total_input"] +
                                token_stats["total_output"]
                            )
                            logger.info(
                                f"Retrieved tokens directly from model: "
                                f"{token_stats}"
                            )
                    except Exception as model_err:
                        logger.warning(
                            f"Failed to get token counts from model: "
                            f"{model_err}"
                        )
        return {
            "steps_count": self.steps_stats["total"],
            "steps_by_type": self.steps_stats["by_type"],
            "tools_used": list(self.tools_used),
            "tool_calls": len(self.tool_calls_history),
            "tool_call_count": self.steps_stats["tool_call_count"],
            # Add timing statistics
            "total_llm_time": self.total_llm_time,
            "total_tool_time": self.total_tool_time,
            "avg_llm_times": avg_llm_times,
            "avg_tool_times": avg_tool_times,
            # Add token statistics
            "token_counts": token_stats
        }

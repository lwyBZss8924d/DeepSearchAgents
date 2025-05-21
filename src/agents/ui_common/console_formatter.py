#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/console_formatter.py
# code style: PEP 8

"""
Agent UI Console Formatter
Formats agent execution steps for console display
Provides terminal-friendly visualization and logging

TODO: clean up get redundant and invalid token stats use to
TUI display code
"""

import shutil
import json
import re
from typing import Dict, Any, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from .constants import (
    THINKING_EMOJI, PLANNING_EMOJI, ACTION_EMOJI, FINAL_EMOJI,
    CODE_EXECUTION_EMOJI, ERROR_EMOJI,
    THINKING_COLOR, PLANNING_COLOR, ACTION_COLOR, FINAL_COLOR,
    CODE_EXECUTION_COLOR, ERROR_COLOR, TOOL_ICONS, TOOL_COLORS
)

# Status text dictionary
STATUS_TEXT = {
    "thinking": "Thinking",
    "action": "Action",
    "observation": "Observation",
    "error": "Error",
    "code": "Code Execution",
    "final": "Completed"
}


class ConsoleFormatter:
    """Formats agent steps for terminal display"""

    def __init__(self, agent_type="react", console=None, status_callback=None,
                 step_callback=None, debug_mode=False):
        """Initialize the console formatter

        Args:
            agent_type: Type of agent ("react" or "codact")
            console: Optional Rich console instance
            status_callback: Optional callback for status changes
            step_callback: Optional callback for step updates
            debug_mode: Whether to enable debug mode
        """
        self.agent_type = agent_type
        self.console = console
        self.status_callback = status_callback
        self.step_callback = step_callback
        self.steps_count = 0
        self.tools_used = set()
        self.execution_times = {}
        self.current_tool = None
        self.tool_start_time = None
        self.display_width = shutil.get_terminal_size().columns
        self.current_step_content = Group()

        # safe default content
        self.default_content = Text("🤔 Thinking...", style=THINKING_COLOR)

        # whether to enable debug mode
        self.debug_mode = debug_mode

        # debug mode background and text colors
        self.debug_bg_color = "grey7"
        self.debug_text_color = "grey70"
        self.debug_title_color = "grey85"
        self.debug_panel_color = "grey23"

    def _get_terminal_width(self):
        """Dynamic get terminal width"""
        try:
            width = shutil.get_terminal_size().columns
            # limit minimum width, avoid narrow display
            return max(width, 80)
        except Exception:
            # when error, return default width
            return self.display_width

    def on_step_update(self, step=None) -> RenderableType:
        """Process step updates and return rendering content

        Args:
            step: Step data to process

        Returns:
            RenderableType: Rich-renderable content
        """
        # step count increment
        self.steps_count += 1
        safety_group = Group(
            Text(f"Step {self.steps_count}: 🤔 Thinking & Action Processing...",
                 style=THINKING_COLOR)
        )

        # default group content
        content_group = safety_group

        try:
            # defensive check: if step is None, create a default thinking step
            if step is None:
                emoji = THINKING_EMOJI
                status_text = "🤔 Thinking & Action Processing..."
                color = THINKING_COLOR

                # notify status callback - defensive check
                if self.status_callback:
                    try:
                        self.status_callback(emoji, status_text, color)
                    except Exception as e:
                        if self.console:
                            self.console.print(
                                f"[red]Status callback error: {e}[/red]")

                # print to console
                if self.console:
                    self.console.print(
                        f"[{color}]{emoji} {status_text}[/{color}]"
                    )

                # execute callback - defensive check
                if self.step_callback:
                    try:
                        self.step_callback(content_group)
                    except Exception as e:
                        if self.console:
                            self.console.print(
                                f"[red]Step callback error: {e}[/red]")

                return content_group

            # handle explicit error steps
            if hasattr(step, 'error') and step.error:
                error_panel = self._format_error(step.error)
                if error_panel:
                    return error_panel

            # handle steps with error_message field
            if hasattr(step, 'error_message') and step.error_message:
                error_panel = self._format_error(step.error_message)
                if error_panel:
                    return error_panel

            # if debug mode is enabled, add debug info panel
            if self.debug_mode:
                debug_panel = self._format_debug_info(step)
                if debug_panel:
                    content_group.renderables.append(debug_panel)
                    if self.console:
                        self.console.print(debug_panel)

            # determine step type based on step object properties
            step_type = self._determine_step_type(step)

            # format content based on step type
            formatted_content = self._format_step_content(step, step_type)

            if formatted_content:
                # Replace with the actual formatted content
                if isinstance(content_group, Group):
                    # Clean up the default safety content
                    content_group = Group()
                content_group = formatted_content

                # notify status callback if available
                if self.status_callback:
                    try:
                        # Get emoji and text based on step type
                        if step_type == "thinking":
                            emoji = THINKING_EMOJI
                            status_text = "Thinking..."
                            color = THINKING_COLOR
                        elif step_type == "planning":
                            emoji = PLANNING_EMOJI
                            status_text = "Planning..."
                            color = PLANNING_COLOR
                        elif step_type == "action":
                            emoji = ACTION_EMOJI
                            # Get tool name for more specific status
                            tool_name = None
                            if hasattr(step, 'action') and step.action:
                                tool_name = step.action
                            elif (hasattr(step, 'tool_calls') and
                                  step.tool_calls):
                                if (isinstance(step.tool_calls, list) and
                                        step.tool_calls):
                                    if (isinstance(step.tool_calls[0], dict)
                                            and 'name' in step.tool_calls[0]):
                                        tool_name = step.tool_calls[0]['name']
                            status_text = (f"Executing {tool_name or 'tool'}"
                                           f"...")
                            color = ACTION_COLOR
                        elif step_type == "final_answer":
                            emoji = FINAL_EMOJI
                            status_text = "Final Answer"
                            color = FINAL_COLOR
                        elif step_type == "code":
                            emoji = CODE_EXECUTION_EMOJI
                            status_text = "Executing code..."
                            color = CODE_EXECUTION_COLOR
                        else:
                            emoji = THINKING_EMOJI
                            status_text = "Processing..."
                            color = THINKING_COLOR

                        self.status_callback(emoji, status_text, color)
                    except Exception as e:
                        if self.console:
                            self.console.print(
                                f"[red]Status callback error: {e}[/red]")

                # print to console if available
                if self.console:
                    self.console.print(content_group)

            # notify step callback if available
            if self.step_callback:
                try:
                    self.step_callback(content_group)
                except Exception as e:
                    if self.console:
                        self.console.print(
                            f"[red]Step callback error: {e}[/red]")

            # return the formatted content
            return content_group

        except Exception as e:
            error_msg = f"Error formatting step: {e}"
            if self.console:
                self.console.print(f"[red]{error_msg}[/red]")
            if self.status_callback:
                self.status_callback(
                    ERROR_EMOJI, f"Error: {e}", ERROR_COLOR)
            return safety_group

    def _determine_step_type(self, step) -> str:
        """Determine the type of step

        Args:
            step: Step data

        Returns:
            str: Step type
        """
        # First check for detailed_type field (from new AgentStepCallback)
        if hasattr(step, "detailed_type") and step.detailed_type:
            return step.detailed_type

        # Check for step_type from new callback system
        if hasattr(step, "step_type") and step.step_type:
            # Map smolagents.memory class names to step types
            type_mapping = {
                "ActionStep": "action",
                "PlanningStep": "planning",
                "FinalAnswerStep": "final_answer",
                "SystemPromptStep": "system_prompt",
                "TaskStep": "task"
            }
            return type_mapping.get(step.step_type, step.step_type.lower())

        # Check for common step types (legacy)
        if hasattr(step, "type") and step.type:
            return step.type

        # Check model output for clues (legacy)
        if hasattr(step, 'model_output') and step.model_output:
            model_output = step.model_output
            model_output_str = str(model_output)

            # Check different mode identifiers by priority
            if ("Plan:" in model_output_str or
                    "规划:" in model_output_str):
                return "planning"
            elif ("final_answer" in model_output_str or
                    "Final Answer:" in model_output_str):
                return "final_answer"
            elif ("```python" in model_output_str and
                    self.agent_type == "codact"):
                return "code"
            elif ("Action:" in model_output_str and
                    self.agent_type == "react"):
                return "action"

        # Default to thinking
        return "thinking"

    def _format_step_content(
        self, step, step_type: str
    ) -> Optional[RenderableType]:
        """Format step content based on step type

        Args:
            step: Step data
            step_type: Determined step type

        Returns:
            Optional[RenderableType]: Formatted content

        TODO: clean up get redundant and invalid token stats use to
        TUI display code
        """
        # create a rendering group, containing step content and
        # performance metrics
        step_content_group = Group()

        # add performance stats panel function
        def add_performance_stats():
            # if not enough performance data, do not show stats panel
            if not hasattr(step, 'timestamp'):
                return None

            stats_table = Table(
                "Metric", "Value",
                show_header=True,
                header_style="bold",
                box=box.SIMPLE
            )

            # add execution time stats
            if hasattr(step, 'duration') and step.duration is not None:
                stats_table.add_row(
                    "Execution Time",
                    f"{step.duration:.2f} seconds"
                )

            # add LLM thinking time and tool execution time (if exists)
            if (hasattr(step, 'llm_thinking_time') and
                    step.llm_thinking_time is not None):
                stats_table.add_row(
                    "LLM Thinking Time",
                    f"{step.llm_thinking_time:.2f} seconds"
                )

            if (hasattr(step, 'tool_execution_time') and
                    step.tool_execution_time is not None):
                stats_table.add_row(
                    "Tool Execution Time",
                    f"{step.tool_execution_time:.2f} seconds"
                )

            # add tokens stats (if exists)
            if (hasattr(step, 'input_tokens') and
                    step.input_tokens is not None or
                    hasattr(step, 'token_counts') and step.token_counts):

                # try multiple ways to get token data
                input_tokens = 0
                output_tokens = 0

                # way 1: get token data from step.input_tokens
                if hasattr(step, 'input_tokens') and step.input_tokens:
                    input_tokens = step.input_tokens
                # way 2: get token data from token_counts dictionary
                elif hasattr(step, 'token_counts') and step.token_counts:
                    input_tokens = step.token_counts.get('input_tokens', 0)

                # handle output_tokens
                if hasattr(step, 'output_tokens') and step.output_tokens:
                    output_tokens = step.output_tokens
                elif hasattr(step, 'token_counts') and step.token_counts:
                    output_tokens = step.token_counts.get('output_tokens', 0)

                total_tokens = input_tokens + output_tokens

                if input_tokens > 0:
                    stats_table.add_row(
                        "Input Tokens",
                        f"{input_tokens:,}"
                    )

                if output_tokens > 0:
                    stats_table.add_row(
                        "Output Tokens",
                        f"{output_tokens:,}"
                    )

                if total_tokens > 0:
                    stats_table.add_row(
                        "Total Tokens",
                        f"{total_tokens:,}"
                    )

            return Panel(
                stats_table,
                title="Step Performance Metrics",
                border_style="blue",
                padding=(1, 2),
                expand=True
            )

        if step_type == "planning":
            emoji = PLANNING_EMOJI
            color = PLANNING_COLOR
            status_text = "Planning..."

            # Plan content - check for both 'plan' and 'content'
            plan_text = None
            if hasattr(step, 'plan') and step.plan is not None:
                plan_text = step.plan
            elif hasattr(step, 'content') and step.content is not None:
                plan_text = step.content
            else:
                plan_text = "Generating plan..."

            try:
                # Try to format as markdown
                plan_panel = Panel(
                    Markdown(str(plan_text)),
                    title=f"[{PLANNING_COLOR}]{PLANNING_EMOJI} "
                          f"Planning[/{PLANNING_COLOR}]",
                    border_style="green",
                    expand=False
                )
                step_content_group.renderables.append(plan_panel)
            except Exception:
                # Fallback to text
                plan_panel = Panel(
                    Text(str(plan_text), style=PLANNING_COLOR),
                    title=f"[{PLANNING_COLOR}]{PLANNING_EMOJI} "
                          f"Planning[/{PLANNING_COLOR}]",
                    border_style="green",
                    expand=False
                )
                step_content_group.renderables.append(plan_panel)

            # add performance stats
            stats_panel = add_performance_stats()
            if stats_panel:
                step_content_group.renderables.append(stats_panel)
            return step_content_group

        elif step_type == "action":
            emoji = ACTION_EMOJI
            color = ACTION_COLOR
            status_text = "Executing..."

            # Format the thinking/reasoning section first
            thinking_content = None
            if hasattr(step, 'model_output') and step.model_output:
                thinking_content = step.model_output
            elif hasattr(step, 'thinking') and step.thinking:
                thinking_content = step.thinking

            thinking_panel = None
            if thinking_content:
                title_text = (f"[{THINKING_COLOR}]{THINKING_EMOJI} "
                              f"Thinking[/{THINKING_COLOR}]")
                thinking_panel = Panel(
                    Markdown(str(thinking_content)),
                    title=title_text,
                    border_style="cyan",
                    expand=False
                )
                step_content_group.renderables.append(thinking_panel)

            # Get tool name
            tool_name = "Unknown tool"
            if hasattr(step, 'action') and step.action:
                tool_name = step.action
                self.tools_used.add(step.action)

            # Check for tool_calls field from new callback
            tool_calls = getattr(step, 'tool_calls', None)
            if (tool_calls and isinstance(tool_calls, list) and
                    len(tool_calls) > 0):
                first_tool = tool_calls[0]
                if (isinstance(first_tool, dict) and
                        'name' in first_tool):
                    tool_name = first_tool['name']
                    self.tools_used.add(tool_name)

            # Get observation
            observation = None
            if (hasattr(step, 'observations') and
                    step.observations is not None):
                observation = step.observations
            elif (hasattr(step, 'observation') and
                  step.observation is not None):
                observation = step.observation
            elif (
                hasattr(step, 'action_output') and
                step.action_output is not None
            ):
                observation = step.action_output

            # If error exists, use as observation
            if observation is None and hasattr(step, 'error') and step.error:
                observation = f"Execution error: {step.error}"

            # Format tool call
            # create Text object with style for tool title
            tool_title_text = Text()

            tool_icon = TOOL_ICONS.get(tool_name, "🔧")
            tool_color = TOOL_COLORS.get(tool_name, "white")

            if tool_name == "python_interpreter":
                tool_title_text.append(
                    f"Tool call: {tool_name} ",
                    style=tool_icon
                )
                tool_title_text.append(tool_icon)
            else:
                tool_title_text.append(
                    f"Tool call: {tool_name}",
                    style=tool_icon
                )

            # create Rich Text object for panel title
            title_text = Text()
            title_text.append(ACTION_EMOJI, style=color)
            title_text.append(" Tool call")

            term_width = self._get_terminal_width()
            panel_width = min(60, term_width - 4)

            content_text = Text()
            icon_display = tool_icon + " " if tool_icon else ""

            if tool_name == "python_interpreter":
                content_text.append("Tool call: ", style="bold cyan")
                content_text.append(f"{tool_name} ", style=tool_icon)
                content_text.append(icon_display, style=tool_icon)
            else:
                content_text.append("Tool call: ", style="bold cyan")
                content_text.append(f"{tool_name}", style=tool_icon)

            tool_panel = Panel(
                content_text,
                border_style="cyan",
                expand=False,
                padding=(1, 2),
                width=panel_width
            )
            step_content_group.renderables.append(tool_panel)

            # handle tool calls in Python code (CodeAct mode)
            code_tools_panel = None
            if tool_name == "python_interpreter":
                # get tools used in Python code
                code_tools = []

                # method 1: extract code_tools from tool_calls
                if (tool_calls and isinstance(tool_calls, list) and
                        len(tool_calls) > 0):
                    first_tool = tool_calls[0]
                    if (isinstance(first_tool, dict) and
                            'code_tools' in first_tool):
                        code_tools = first_tool['code_tools']

                # method 2: extract code_tools from model_output
                if not code_tools and hasattr(step, 'model_output'):
                    model_output = step.model_output
                    if model_output:
                        # extract code_tools from Python code
                        code_pattern = r'```python\s*(.*?)\s*```'
                        code_blocks = re.findall(
                            code_pattern, str(model_output), re.DOTALL
                        )

                        if code_blocks and len(code_blocks) > 0:
                            # check system available agent tools names
                            common_tools = [
                                "search_links", "read_url", "chunk_text",
                                "embed_texts", "rerank_texts", "wolfram",
                                "final_answer"
                            ]

                            code_block = code_blocks[0]
                            for tool in common_tools:
                                # check function call pattern: tool_name(...)
                                if re.search(fr'\b{tool}\s*\(', code_block):
                                    code_tools.append(tool)
                                # check object call pattern: obj.tool_name(...)
                                elif re.search(fr'\.{tool}\s*\(', code_block):
                                    code_tools.append(tool)

                # if tools found, display tools panel
                if code_tools:
                    # build tools icon display
                    tools_text = []
                    for code_tool in code_tools:
                        tool_icon = TOOL_ICONS.get(code_tool, "⌨️")
                        tool_color = TOOL_COLORS.get(
                            code_tool, "white"
                        )
                        # use Text object instead of string style marking
                        tool_text = Text()
                        tool_text.append(
                            f"{tool_icon} {code_tool}",
                            style=tool_color
                        )
                        tools_text.append(tool_text)

                    if tools_text:
                        # create Text object combination
                        combined_text = Text(" ")
                        for text in tools_text:
                            combined_text.append_text(text)
                            combined_text.append(" ")

                        # create panel title
                        tools_title = Text()
                        tools_title.append(
                            "Python code using tools", style="blue"
                        )

                        code_tools_panel = Panel(
                            combined_text,
                            title=tools_title,
                            border_style="blue",
                            expand=False
                        )
                        step_content_group.renderables.append(
                            code_tools_panel
                        )

            # Format observation if exists
            obs_panel = None
            if observation is not None:
                obs_panel = self._format_observation(observation)
                if obs_panel:
                    step_content_group.renderables.append(obs_panel)

            # add performance stats
            stats_panel = add_performance_stats()
            if stats_panel:
                step_content_group.renderables.append(stats_panel)
            return step_content_group

        elif step_type == "final_answer":
            emoji = FINAL_EMOJI
            color = FINAL_COLOR
            status_text = STATUS_TEXT.get("final", "Completed")
            step_content_group = Group()

            # Try to extract result from step
            if hasattr(step, 'action_output'):
                answer_text = step.action_output
            elif hasattr(step, 'result'):
                answer_text = step.result
            else:
                answer_text = str(step)

            def add_performance_stats():
                # Add performance stats
                if hasattr(step, 'step_stats'):
                    stats_table = self._format_step_stats(step.step_stats)
                    if stats_table:
                        step_content_group.renderables.append(stats_table)

            # Check for direct final_answer type format
            # (new format - added for Gradio)
            if (isinstance(answer_text, dict) and
                    answer_text.get('type') == 'final_answer'):
                if answer_text.get('format') == 'markdown':
                    content = answer_text.get('content', '')
                    title = (
                        f"[{FINAL_COLOR}]{FINAL_EMOJI} "
                        f"{answer_text.get('title', 'Final Answer')}"
                        f"[/{FINAL_COLOR}]"
                    )
                    final_panel = Panel(
                        Markdown(content),
                        title=title,
                        border_style="green",
                        expand=False
                    )
                    step_content_group.renderables.append(final_panel)
                    add_performance_stats()
                    return step_content_group

            # Try to parse as JSON
            if (isinstance(answer_text, str) and
                    answer_text.strip().startswith('{') and
                    answer_text.strip().endswith('}')):
                try:
                    json_data = json.loads(answer_text)
                    # Check for new final_answer type in JSON
                    if json_data.get('type') == 'final_answer':
                        if json_data.get('format') == 'markdown':
                            content = json_data.get('content', '')
                            title = (
                                f"[{FINAL_COLOR}]{FINAL_EMOJI} "
                                f"{json_data.get('title', 'Final Answer')}"
                                f"[/{FINAL_COLOR}]"
                            )
                            final_panel = Panel(
                                Markdown(content),
                                title=title,
                                border_style="green",
                                expand=False
                            )
                            step_content_group.renderables.append(final_panel)
                            add_performance_stats()
                            return step_content_group

                    # Handle legacy JSON format
                    if 'content' in json_data:
                        final_panel = Panel(
                            Markdown(json_data['content']),
                            title=f"[{FINAL_COLOR}]{FINAL_EMOJI} "
                                  f"{json_data.get('title', 'Final answer')}"
                                  f"[/{FINAL_COLOR}]",
                            border_style="green",
                            expand=False
                        )
                        step_content_group.renderables.append(final_panel)
                        add_performance_stats()
                        return step_content_group
                except json.JSONDecodeError:
                    pass

            # Try to identify as Markdown
            if '##' in str(answer_text) or '*' in str(answer_text):
                try:
                    final_panel = Panel(
                        Markdown(str(answer_text)),
                        title=f"[{FINAL_COLOR}]{FINAL_EMOJI} "
                              f"Final answer[/{FINAL_COLOR}]",
                        border_style="green",
                        expand=False
                    )
                    step_content_group.renderables.append(final_panel)
                    add_performance_stats()
                    return step_content_group
                except Exception:
                    pass

            # Default text display
            final_panel = Panel(
                Text(str(answer_text)),
                title=f"[{FINAL_COLOR}]{FINAL_EMOJI} "
                      f"Final answer[/{FINAL_COLOR}]",
                border_style="green",
                expand=False
            )
            step_content_group.renderables.append(final_panel)
            add_performance_stats()
            return step_content_group

        elif step_type == "code":
            emoji = CODE_EXECUTION_EMOJI
            color = CODE_EXECUTION_COLOR
            status_text = "Generating code..."

            # Extract code block
            model_output = getattr(step, 'model_output', "")
            model_output_str = str(model_output)

            if "```python" in model_output_str:
                code_blocks = re.findall(
                    r'```python\s*(.*?)\s*```',
                    model_output_str,
                    re.DOTALL
                )
                if code_blocks:
                    code_content = code_blocks[0]
                    code_panel = Panel(
                        Syntax(
                            code_content, "python",
                            theme="monokai",
                            line_numbers=True
                        ),
                        title="[bold blue]Executing code[/bold blue]",
                        border_style="blue",
                        expand=False
                    )
                    step_content_group.renderables.append(code_panel)
                    add_performance_stats()
                    return step_content_group

            # Fallback to displaying model output
            output_panel = Panel(
                Text(model_output_str[:1000] + "..."
                     if len(model_output_str) > 1000
                     else model_output_str),
                title=f"[{THINKING_COLOR}]{THINKING_EMOJI} "
                      f"Model output[/{THINKING_COLOR}]",
                border_style="cyan",
                expand=False
            )
            step_content_group.renderables.append(output_panel)
            add_performance_stats()
            return step_content_group

        else:  # Default to thinking type
            emoji = THINKING_EMOJI
            color = THINKING_COLOR
            status_text = "Thinking..."

            # Display model output if available
            if hasattr(step, 'model_output') and step.model_output:
                model_output_str = str(step.model_output)
                thinking_panel = Panel(
                    Text(model_output_str[:1000] + "..."
                         if len(model_output_str) > 1000
                         else model_output_str),
                    title=f"[{THINKING_COLOR}]{THINKING_EMOJI} "
                          f"Model output[/{THINKING_COLOR}]",
                    border_style="cyan",
                    expand=False
                )
                step_content_group.renderables.append(thinking_panel)
                add_performance_stats()
                return step_content_group

            # Default content
            thinking_text = Text(f"{emoji} {status_text}", style=color)
            step_content_group.renderables.append(thinking_text)
            add_performance_stats()
            return step_content_group

    def _format_debug_info(self, step) -> Optional[RenderableType]:
        """Format step debug info to Rich renderable object

        Args:
            step: Step data

        Returns:
            Optional[RenderableType]: Debug panel
        """
        if step is None:
            return None

        try:
            # create a table to display debug info
            table = Table(
                title=(f"[{self.debug_title_color}]Step debug info"
                       f"[/{self.debug_title_color}]"),
                title_style=f"bold {self.debug_title_color}",
                border_style=self.debug_panel_color,
                box=None,
                highlight=True,
                show_header=True,
                header_style=f"bold {self.debug_title_color}",
                min_width=40,
                expand=False
            )

            # add table columns
            table.add_column(
                "Attribute", style=f"bold {self.debug_text_color}"
            )
            table.add_column(
                "Value", style=self.debug_text_color
            )

            # step type
            step_type = type(step).__name__
            table.add_row("Step type", step_type)

            # important attributes
            key_attrs = {
                'step_number': 'Step number',
                'action': 'Action',
                'error': 'Error',
                'duration': 'Execution time (seconds)'
            }

            for attr, label in key_attrs.items():
                if hasattr(step, attr):
                    value = getattr(step, attr)
                    if value is not None:
                        # format execution time to 2 decimal places
                        if (attr == 'duration' and
                                isinstance(value, (int, float))):
                            value = f"{value:.2f}"
                        table.add_row(label, str(value))

            # observation type
            if hasattr(step, 'observations') and step.observations is not None:
                obs_type = type(step.observations).__name__
                table.add_row("Observation type", obs_type)

            # model output type
            if hasattr(step, 'model_output') and step.model_output is not None:
                output_type = type(step.model_output).__name__
                table.add_row("Model output type", output_type)

            # wrap table in panel
            return Panel(
                table,
                title=(f"[{self.debug_title_color}]"
                       "DEBUG INFO[/{self.debug_title_color}]"),
                title_align="left",
                border_style=self.debug_panel_color,
                padding=(1, 2),
                style=f"on {self.debug_bg_color}"
            )
        except Exception as e:
            # if formatting fails, return simple error info
            if self.console:
                self.console.print(
                    f"[red]Debug info formatting error: {e}[/red]"
                )
            return None

    def _format_observation(self, observation) -> RenderableType:
        """Format observation to Rich renderable object

        Args:
            observation: Observation data

        Returns:
            RenderableType: Formatted observation
        """
        # defensive check, ensure observation is not None
        if observation is None:
            return Panel(
                Text("No observation", style="dim"),
                title="[dim]Observation[/dim]",
                border_style="yellow",
                expand=False
            )

        # convert to string
        observation_text = str(observation)

        # check if it contains execution error
        if observation_text.startswith("Execution error:"):
            return Panel(
                Text(observation_text, style=ERROR_COLOR),
                title=f"[{ERROR_COLOR}]{ERROR_EMOJI} Error[/{ERROR_COLOR}]",
                border_style="red",
                expand=False
            )

        # try to parse as JSON
        try:
            # check if it is a JSON object
            if (observation_text.strip().startswith('{')
                    and observation_text.strip().endswith('}')):
                try:
                    json_data = json.loads(observation_text)

                    # check if JSON contains error information
                    if 'error' in json_data and json_data['error']:
                        error_msg = f"Error: {json_data['error']}"
                        title_text = (f"[{ERROR_COLOR}]{ERROR_EMOJI} "
                                      f"Error[/{ERROR_COLOR}]")
                        return Panel(
                            Text(error_msg, style=ERROR_COLOR),
                            title=title_text,
                            border_style="red",
                            expand=False
                        )

                    json_str = json.dumps(
                        json_data, indent=2, ensure_ascii=False
                    )
                    return Panel(
                        Syntax(json_str, "json", theme="monokai"),
                        title="[yellow]Observation (JSON)[/yellow]",
                        border_style="yellow",
                        expand=False
                    )
                except json.JSONDecodeError:
                    pass

            # check if it is a JSON array
            if (observation_text.strip().startswith('[')
                    and observation_text.strip().endswith(']')):
                try:
                    json_data = json.loads(observation_text)
                    json_str = json.dumps(
                        json_data, indent=2, ensure_ascii=False
                    )
                    return Panel(
                        Syntax(json_str, "json", theme="monokai"),
                        title="[yellow]Observation (Array)[/yellow]",
                        border_style="yellow",
                        expand=False
                    )
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        # check if it is execution logs
        if observation_text.startswith("Execution logs:"):
            return Panel(
                Text(observation_text),
                title="[yellow]Execution logs[/yellow]",
                border_style="yellow",
                expand=False
            )

        # check if it contains code blocks
        code_block_match = re.search(
            r'```(\w*)\n(.*?)\n```',
            observation_text,
            re.DOTALL
        )
        if code_block_match:
            lang = code_block_match.group(1) or "text"
            code = code_block_match.group(2)
            return Panel(
                Syntax(code, lang, theme="monokai"),
                title="[yellow]Observation (code)[/yellow]",
                border_style="yellow",
                expand=False
            )

        # check if it is Markdown format
        if ('##' in observation_text or '*' in observation_text or
                '>' in observation_text):
            try:
                return Panel(
                    Markdown(observation_text),
                    title="[yellow]Observation (markdown)[/yellow]",
                    border_style="yellow",
                    expand=False
                )
            except Exception:
                pass

        # if content is too long, truncate display
        if len(observation_text) > 1000:
            return Panel(
                Group(
                    Text(observation_text[:1000] + "...", style="dim"),
                    Text(
                        f"(showing 1000/{len(observation_text)} characters)",
                        style="dim"
                    )
                ),
                title="[yellow]Observation (truncated)[/yellow]",
                border_style="yellow",
                expand=False
            )

        # default text display
        return Panel(
            Text(observation_text, style="dim"),
            title="[yellow]Observation[/yellow]",
            border_style="yellow",
            expand=False
        )

    def _format_error(self, error_message) -> Optional[RenderableType]:
        """Format error message to Rich renderable object

        Args:
            error_message: error message

        Returns:
            Optional[RenderableType]: formatted error panel
        """
        if not error_message:
            return None

        try:
            # create error text
            error_text = Text()
            error_text.append(
                f"Execution error: {error_message}", style=ERROR_COLOR
            )

            # create error panel title
            title_text = (f"[{ERROR_COLOR}]{ERROR_EMOJI} "
                          f"Error[/{ERROR_COLOR}]")

            # return error panel
            return Panel(
                error_text,
                title=title_text,
                border_style="red",
                expand=False
            )
        except Exception as e:
            # if formatting fails, return simple error info
            if self.console:
                self.console.print(
                    f"[red]Error formatting error: {e}[/red]"
                )
            return Panel(
                Text(f"Error: {error_message}", style=ERROR_COLOR),
                title=f"[{ERROR_COLOR}]{ERROR_EMOJI} Error[/{ERROR_COLOR}]",
                border_style="red",
                expand=False
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent execution statistics

        Returns:
            Dict[str, Any]: Execution statistics
        """
        # calculate average execution time
        avg_execution_times = {}
        for tool, times in self.execution_times.items():
            if times:
                avg_execution_times[tool] = sum(times) / len(times)

        return {
            "agent_type": self.agent_type,
            "steps_count": self.steps_count,
            "tools_used": list(self.tools_used) if self.tools_used else [],
            "tools_count": len(self.tools_used),
            "avg_execution_times": avg_execution_times
        }

    def format_statistics(self, stats: Dict[str, Any]) -> RenderableType:
        """Format agent statistics into a rich renderable table

        Args:
            stats: Statistics dictionary
            from agent_step_callback.get_statistics()

        Returns:
            RenderableType: Rich renderable table
        """
        # Create main table for statistics
        stats_table = Table(
            title="[bold]Agent Execution Statistics[/bold]",
            show_header=True,
            header_style="bold blue",
            border_style="blue",
            box=None,
            expand=False
        )

        # Add basic columns
        stats_table.add_column("Metric", style="bold cyan")
        stats_table.add_column("Value", style="white")

        # Add basic statistics
        stats_table.add_row("Total steps", str(stats.get("steps_count", 0)))
        stats_table.add_row(
            "Tools used",
            ", ".join(stats.get("tools_used", []))
        )
        stats_table.add_row("Tool calls", str(stats.get("tool_call_count", 0)))

        # Add timing statistics if available
        if "total_llm_time" in stats:
            total_time = (stats.get("total_llm_time", 0) +
                          stats.get("total_tool_time", 0))
            stats_table.add_row(
                "Total execution time",
                f"{total_time:.2f}s"
            )
            stats_table.add_row(
                "LLM thinking time",
                f"{stats.get('total_llm_time', 0):.2f}s " +
                f"({stats.get('total_llm_time', 0)/total_time*100:.1f}%)"
            )
            stats_table.add_row(
                "Tool execution time",
                f"{stats.get('total_tool_time', 0):.2f}s " +
                f"({stats.get('total_tool_time', 0)/total_time*100:.1f}%)"
            )

        # Add token statistics if available
        token_counts = stats.get("token_counts", {})
        if token_counts:
            total_tokens = (token_counts.get("total_input", 0) +
                            token_counts.get("total_output", 0))
            if total_tokens > 0:
                stats_table.add_row(
                    "Total tokens used",
                    str(total_tokens)
                )
                stats_table.add_row(
                    "Input tokens",
                    f"{token_counts.get('total_input', 0)} " +
                    f"({(token_counts.get('total_input', 0) /
                         total_tokens * 100):.1f}%)"
                )
                stats_table.add_row(
                    "Output tokens",
                    f"{token_counts.get('total_output', 0)} " +
                    f"({(token_counts.get('total_output', 0) /
                         total_tokens * 100):.1f}%)"
                )

        # Create second table for per-tool statistics if available
        if stats.get("avg_llm_times") or stats.get("avg_tool_times"):
            tool_table = Table(
                title="[bold]Per-Tool Performance[/bold]",
                show_header=True,
                header_style="bold green",
                border_style="green",
                box=None,
                expand=False
            )

            tool_table.add_column("Tool", style="bold yellow")
            tool_table.add_column("LLM Time (avg)", style="cyan")
            tool_table.add_column("Tool Time (avg)", style="magenta")
            tool_table.add_column("Total Time (avg)", style="white")

            avg_llm_times = stats.get("avg_llm_times", {})
            avg_tool_times = stats.get("avg_tool_times", {})

            # Merge tool names from both dictionaries
            all_tools = set(avg_llm_times.keys()) | set(avg_tool_times.keys())

            for tool_name in sorted(all_tools):
                llm_time = avg_llm_times.get(tool_name, 0)
                tool_time = avg_tool_times.get(tool_name, 0)
                total_time = llm_time + tool_time

                # Get tool icon if available
                tool_icon = TOOL_ICONS.get(tool_name, "🔧")
                tool_color = TOOL_COLORS.get(tool_name, "white")

                # Use tool_color in the row display
                colored_name = Text(
                    f"{tool_icon} {tool_name}",
                    style=tool_color
                )

                tool_table.add_row(
                    colored_name,
                    f"{llm_time:.2f}s",
                    f"{tool_time:.2f}s",
                    f"{total_time:.2f}s"
                )

            # Return both tables as a group
            return Group(stats_table, tool_table)

        # Return just the main stats table if no per-tool stats
        return stats_table

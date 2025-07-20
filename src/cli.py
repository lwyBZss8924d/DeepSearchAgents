#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/cli.py
# code style: PEP 8

"""DeepSearchAgent CLI development version
Provide interactive and single query modes, supporting React and CodeAct
two agent types
"""

import argparse
import asyncio
import json
import logging
import re
import shutil
import traceback
from pathlib import Path

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.console import Group

from src.agents.runtime import agent_runtime
from src.agents.ui_common.console_formatter import ConsoleFormatter
from src.agents.ui_common.streaming_formatter import StreamingConsoleFormatter
from src.agents.ui_common.agent_step_callback import AgentStepCallback
from src.agents.ui_common.constants import (
    COLORS, FINAL_COLOR, FINAL_EMOJI, ERROR_COLOR, ERROR_EMOJI,
    TOOL_ICONS, TOOL_COLORS, THINKING_COLOR, THINKING_EMOJI,
    STATUS_TEXT, DISPLAY_WIDTH
)
from src.core.config.settings import settings

load_dotenv()

logger = logging.getLogger(__name__)

# Global settings
REACT_PLANNING_INTERVAL = None
CODACT_PLANNING_INTERVAL = None
CODACT_EXECUTOR_KWARGS = None
CODACT_ADDITIONAL_IMPORTS = None

# Configure console and logging settings
console = Console()


def _initialize_globals():
    """Initialize global variables"""
    global REACT_PLANNING_INTERVAL, CODACT_PLANNING_INTERVAL
    global CODACT_EXECUTOR_KWARGS, CODACT_ADDITIONAL_IMPORTS

    # Get values from settings
    REACT_PLANNING_INTERVAL = settings.REACT_PLANNING_INTERVAL
    CODACT_PLANNING_INTERVAL = settings.CODACT_PLANNING_INTERVAL
    CODACT_EXECUTOR_KWARGS = settings.CODACT_EXECUTOR_KWARGS
    CODACT_ADDITIONAL_IMPORTS = settings.CODACT_ADDITIONAL_IMPORTS

    console.print(
        f"[dim]Initialized planning intervals: "
        f"[blue]React={REACT_PLANNING_INTERVAL}[/blue], "
        f"[green]CodeAct={CODACT_PLANNING_INTERVAL}[/green][/dim]"
    )


# Custom log formatter
class DomainMaskingFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        if record.name == 'httpx':
            message = re.sub(r'(https?://)[^/\s]+', r'\1******', message)
        return message


# Get tool display information - keep
def get_tool_display_info(tool_name):
    """Get tool display information - keep"""
    icon = TOOL_ICONS.get(tool_name, "🔧")
    color = TOOL_COLORS.get(tool_name, "bold white")
    return icon, color


def handle_slash_command(command, multiline, console):
    """Handle slash commands in CLI, e.g. /exit, /quit, /multiline"""
    if command in ['/exit', '/quit']:
        return 0, multiline
    elif command == '/multiline':
        new_state = not multiline
        mode_text = "enabled" if new_state else "disabled"
        console.print(f"[green]Multiline mode is now {mode_text}[/green]")
        return None, new_state
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        return None, multiline


# Display welcome information
def display_welcome(args, console):
    """Display welcome information and configuration information"""
    # Title
    title = "DeepSearchAgent"
    if args.agent_type == "react":
        subtitle = "[blue]REACT[/blue] 🤠⚙️"
        border_color = "blue"
        agent_icon = "🤠⚙️"
        highlight_color = "bold blue"
    elif args.agent_type == "codact":
        subtitle = "[green]CODACT[/green] 👻⌨️"
        border_color = "green"
        agent_icon = "👻⌨️"
        highlight_color = "bold green"
    else:  # manager
        subtitle = "[cyan]MANAGER[/cyan] 🎯🤝"
        border_color = "cyan"
        agent_icon = "🎯🤝"
        highlight_color = "bold cyan"

    welcome_title = Text("Welcome to DeepSearch Agent", style="bold")
    title_line = Text()
    title_line.append(welcome_title)

    # Create description paragraphs
    paragraph1 = Text()
    paragraph1.append(f"{agent_icon} DeepSearchAgent built on ")
    paragraph1.append("ReAct", style="bold")
    paragraph1.append(" (Reasoning + Acting) and ")
    paragraph1.append("CodeAct", style="bold")
    paragraph1.append(" (write and execute programming code Action) ")
    paragraph1.append("\nLLM-Agent architecture realize web search and ")
    paragraph1.append("reasoning ability to complete deep web search task.")

    paragraph2 = Text(
        "It uses LLM for lang CoT reasoning and external dynamic tools, "
        "through multi-step search, reading and calculation, "
        "provide complex query answers with traceable references. "
        "\nBased on the smolagents library from Hugging Face, "
        "this product implements a dual-mode agent that supports "
        "standard ReAct or CodeAct to compare the effect of different "
        "mode mechanisms."
    )

    paragraph3 = Text(
        "Product provides CLI and API service, convenient for integration "
        "and use in various systems."
    )

    # Combine all text elements with proper spacing
    welcome_content = Group(
        title_line,
        Text(),  # Empty line
        paragraph1,
        Text(),  # Empty line
        paragraph2,
        Text(),  # Empty line
        paragraph3
    )

    # Create welcome panel using the Group
    welcome_panel = Panel(
        welcome_content,
        title=f"[bold]{title} {subtitle}[/bold]",
        border_style=border_color,
        width=DISPLAY_WIDTH,
        expand=False
    )

    # Project info remains the same
    project_info = Table.grid(padding=(0, 1))
    project_info.add_column(style="bold")
    project_info.add_column(style="bright_white")

    project_info.add_row(
        "[bold]GitHub:[/bold]",
        "[link=https://github.com/lwyBZss8924d/DeepSearchAgents]"
        "github.com/lwyBZss8924d/DeepSearchAgents[/link]"
    )

    version = settings.VERSION or "0.3.1"
    project_info.add_row(
        "[bold]Version:[/bold]",
        f"[dim]{version}[/dim]"
    )

    info_panel = Panel(
        project_info,
        title=f"[{highlight_color}]Project Information[/{highlight_color}]",
        border_style=border_color,
        width=DISPLAY_WIDTH,
        expand=False
    )

    console.print(welcome_panel)
    console.print(info_panel)

    config_table = Table(
        show_header=True,
        header_style=highlight_color,
        border_style=border_color,
        box=None,
        padding=(0, 2, 0, 0),
        expand=False
    )

    config_table.add_column("Configuration item", style=highlight_color)
    config_table.add_column("Value", style="bright_white")

    config_table.add_row(
        "Agent type",
        f"[{highlight_color}]{args.agent_type.upper()}[/{highlight_color}]"
    )

    config_table.add_row("Search model", f"{settings.SEARCH_MODEL_NAME}")
    model_id = f"{settings.ORCHESTRATOR_MODEL_ID}"
    config_table.add_row("Orchestrator model", model_id)
    config_table.add_row("Reranker type", f"{settings.RERANKER_TYPE}")

    if args.agent_type == "react":
        config_table.add_row("Maximum steps", f"{settings.REACT_MAX_STEPS}")
        planning_text = (
            f"Every [yellow]{settings.REACT_PLANNING_INTERVAL}[/yellow] steps"
            if settings.REACT_PLANNING_INTERVAL
            else '[dim]Not set[/dim]'
        )
        config_table.add_row("Planning interval", planning_text)
        stream_text = (
            '[green]Enabled[/green]' if settings.REACT_ENABLE_STREAMING
            else '[dim]Disabled[/dim]'
        )
        config_table.add_row("Streaming output", stream_text)

        if hasattr(agent_runtime, 'react_agent') and agent_runtime.react_agent:
            # Access the inner agent's tools dictionary (smolagents v1.19.0)
            if hasattr(agent_runtime.react_agent, 'agent') and agent_runtime.react_agent.agent:
                if hasattr(agent_runtime.react_agent.agent, 'tools'):
                    tools_dict = agent_runtime.react_agent.agent.tools
                    if tools_dict:
                        tool_names = list(tools_dict.keys())
                        tools_text = Text()
                        for i, tool_name in enumerate(tool_names):
                            icon, color = get_tool_display_info(tool_name)
                            if i > 0:
                                tools_text.append(" • ")
                            tools_text.append(f"{icon} ", style=color)
                            tools_text.append(f"{tool_name}", style=color)

                        config_table.add_row("Configured tools", tools_text)

    elif args.agent_type == "codact":  # codact
        # Add executor type
        executor_type_map = {
            "local": "Local environment",
            "docker": "Docker container",
            "e2b": "E2B cloud service"
        }
        executor_display = executor_type_map.get(
            settings.CODACT_EXECUTOR_TYPE,
            settings.CODACT_EXECUTOR_TYPE
        )

        config_table.add_row(
            "Executor type", f"[cyan]{executor_display}[/cyan]")
        config_table.add_row("Maximum steps", f"{settings.CODACT_MAX_STEPS}")
        planning_text = (
            f"Every [yellow]{settings.CODACT_PLANNING_INTERVAL}[/yellow] steps"
            if settings.CODACT_PLANNING_INTERVAL
            else '[dim]Not set[/dim]'
        )
        config_table.add_row("Planning interval", planning_text)
        config_table.add_row(
            "Verbosity level", f"{settings.CODACT_VERBOSITY_LEVEL}"
        )
        stream_text = (
            '[green]Enabled[/green]' if settings.CODACT_ENABLE_STREAMING
            else '[dim]Disabled[/dim]'
        )
        config_table.add_row("Streaming output", stream_text)

        codact_agent = None
        if hasattr(agent_runtime, 'codact_agent'):
            codact_agent = agent_runtime.codact_agent
        elif hasattr(agent_runtime, 'code_agent'):
            codact_agent = agent_runtime.code_agent

        if (hasattr(settings, 'CODACT_ADDITIONAL_IMPORTS') and
                settings.CODACT_ADDITIONAL_IMPORTS):
            imports_text = Text()
            for i, module in enumerate(
                    sorted(settings.CODACT_ADDITIONAL_IMPORTS)):
                if i > 0 and i % 5 == 0:  # Line break every 5 modules
                    imports_text.append("\n")
                elif i > 0:
                    imports_text.append(", ")
                imports_text.append(module, style="yellow")

            config_table.add_row("Allowed imports", imports_text)

        if codact_agent is not None:
            # Access the inner agent's tools dictionary (smolagents v1.19.0)
            if hasattr(codact_agent, 'agent') and codact_agent.agent:
                if hasattr(codact_agent.agent, 'tools'):
                    tools_dict = codact_agent.agent.tools
                    if tools_dict:
                        tool_names = list(tools_dict.keys())
                        tools_text = Text()
                        for i, tool_name in enumerate(tool_names):
                            icon, color = get_tool_display_info(tool_name)
                            if i > 0:
                                tools_text.append(" • ")
                            tools_text.append(f"{icon} ", style=color)
                            tools_text.append(f"{tool_name}", style=color)

                        config_table.add_row("Configured tools", tools_text)

    else:  # manager
        config_table.add_row("Maximum steps", f"{getattr(settings, 'MANAGER_MAX_STEPS', 30)}")
        planning_text = (
            f"Every [yellow]{getattr(settings, 'MANAGER_PLANNING_INTERVAL', 10)}[/yellow] steps"
        )
        config_table.add_row("Planning interval", planning_text)

        # Display team configuration
        team_type = getattr(args, 'team', 'research')
        config_table.add_row("Team type", f"[cyan]{team_type.capitalize()}[/cyan]")

        if team_type == "research":
            # Show research team composition
            team_text = Text()
            team_text.append("🔍 ", style="blue")
            team_text.append("Web Search Agent", style="blue")
            team_text.append(" (React)\n", style="dim")
            team_text.append("📊 ", style="green")
            team_text.append("Analysis Agent", style="green")
            team_text.append(" (CodeAct)", style="dim")
            config_table.add_row("Team members", team_text)
        elif team_type == "custom" and hasattr(args, 'managed_agents') and args.managed_agents:
            # Show custom team composition
            team_text = Text()
            for i, agent_type in enumerate(args.managed_agents):
                if i > 0:
                    team_text.append("\n")
                icon = "🤠" if agent_type == "react" else "👻"
                color = "blue" if agent_type == "react" else "green"
                team_text.append(f"{icon} ", style=color)
                team_text.append(f"{agent_type.capitalize()} Agent", style=color)
            config_table.add_row("Team members", team_text)

        # Show delegation settings
        config_table.add_row("Max delegation depth", "3")
        config_table.add_row("Coordination mode", "Hierarchical task delegation")

    # Display configuration table panel
    console.print(Panel(
        config_table,
        title=(f"[{highlight_color}]System Configuration Information"
               f"[/{highlight_color}]"),
        border_style=border_color,
        width=DISPLAY_WIDTH,
        expand=False
    ))

    if args.agent_type == "react":
        agent_name = "React"
    elif args.agent_type == "codact":
        agent_name = "CodeAct"
    else:
        agent_name = "Research Team"
    console.print(f"[dim]{agent_name} mode is ready![/dim]")


def render_json_as_markdown(final_result_str, console):
    """Render final JSON result as Markdown and display it"""
    try:
        # handle Python dictionary objects, including new type markers
        if (isinstance(final_result_str, dict) and
                final_result_str.get("type") == "final_answer"):
            if final_result_str.get("format") == "markdown":
                # use content field as Markdown content
                markdown_content = final_result_str.get("content", "")
                title = (f"[{FINAL_COLOR}]"
                         f"{final_result_str.get('title', 'Final Answer')}"
                         f"[/{FINAL_COLOR}]")
                console.print(Panel(
                    Markdown(markdown_content),
                    title=title,
                    border_style="green",
                    width=shutil.get_terminal_size().columns,
                    expand=False
                ))
                return True

        # Try to parse JSON
        if isinstance(final_result_str, dict):
            json_data = final_result_str
        elif (isinstance(final_result_str, str) and
              final_result_str.strip().startswith('{') and
              final_result_str.strip().endswith('}')):
            try:
                json_data = json.loads(final_result_str)
            except json.JSONDecodeError:
                # Not valid JSON, display original result
                console.print(Markdown(str(final_result_str)))
                return True
        else:
            # Not valid JSON, display original result
            console.print(Markdown(str(final_result_str)))
            return True

        # Check for type:final_answer format (new format)
        if (json_data.get("type") == "final_answer" and
                json_data.get("format") == "markdown"):
            markdown_content = json_data.get("content", "")
            title = (f"[{FINAL_COLOR}]"
                     f"{json_data.get('title', 'Final Answer')}"
                     f"[/{FINAL_COLOR}]")
            console.print(Panel(
                Markdown(markdown_content),
                title=title,
                border_style="green",
                width=shutil.get_terminal_size().columns,
                expand=False
            ))
            return True

        # Extract content and sources from legacy format
        markdown_content = ""
        if 'content' in json_data:
            markdown_content = json_data['content']

        sources = []
        if 'sources' in json_data:
            sources = json_data['sources']

        # Add Sources section
        has_sources_section = '## Sources' in markdown_content
        if sources and not has_sources_section:
            # Ensure appropriate line breaks
            if not markdown_content.endswith('\n\n'):
                if markdown_content.endswith('\n'):
                    markdown_content += '\n'
                else:
                    markdown_content += '\n\n'

            markdown_content += "## Sources\n\n"

            # Add numbered references to each source
            for i, url in enumerate(sources):
                # Try to extract title from URL
                url_parts = url.split("/")
                title = ""
                if len(url_parts) > 2:
                    raw_title = (url_parts[-1]
                                 if url_parts[-1]
                                 else url_parts[-2])
                    title = (raw_title.split('.')[0]
                             .replace('-', ' ')
                             .replace('_', ' ')
                             .capitalize())
                if not title:
                    title = f"Source {i+1}"

                markdown_content += f"{i+1}. [{title}]({url})\n"

        # Prepare title
        title = f"[{FINAL_COLOR}]Final Markdown Output[/{FINAL_COLOR}]"
        if 'title' in json_data and json_data['title']:
            title = f"[{FINAL_COLOR}]{json_data['title']}[/{FINAL_COLOR}]"

        # Get terminal width and display result
        term_width = shutil.get_terminal_size().columns
        report_text = f"\n[{FINAL_COLOR}]{FINAL_EMOJI} Final Answer Report:"
        report_text += f"[/{FINAL_COLOR}]"
        console.print(report_text)
        console.print(Panel(
            Markdown(markdown_content),
            title=title,
            border_style="green",
            width=term_width,  # Use dynamic width
            expand=False
        ))

        return True

    except Exception as e:
        console.print(f"[red]Error rendering result: {e}[/red]")
        console.print(final_result_str)
        return False


# Agent Step Callback - handle Agent step updates
def handle_step_update(step_data, console, formatter):
    """Handle step update event from AgentStepCallback

    Args:
        step_data: Step data from callback
        console: Console object
        formatter: Formatter instance

    """
    try:
        # create a step object for formatter use
        class StepObject:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        step_obj = StepObject(step_data)

        # check and record token statistics (if exists)
        if step_data.get('token_counts'):
            token_counts = step_data['token_counts']
            # Handle both dict and TokenUsage object formats
            if hasattr(token_counts, 'input_tokens'):
                # TokenUsage object
                input_tokens = token_counts.input_tokens or 0
                output_tokens = token_counts.output_tokens or 0
            else:
                # Dictionary format (fallback)
                input_tokens = token_counts.get('input_tokens', 0)
                output_tokens = token_counts.get('output_tokens', 0)

            logger.debug(
                f"Found token statistics - input: {input_tokens}, "
                f"output: {output_tokens}"
            )

            # add token statistics attributes to step object
            step_obj.input_tokens = input_tokens
            step_obj.output_tokens = output_tokens
            step_obj.total_tokens = input_tokens + output_tokens
            logger.debug(
                f"Added token stats to step object: "
                f"{input_tokens}+{output_tokens}"
            )

        # enhance tool usage information transfer
        # ensure code_tools information is extracted from tool_calls
        if 'tool_calls' in step_data and step_data['tool_calls']:
            tool_calls = step_data['tool_calls']
            if isinstance(tool_calls, list) and len(tool_calls) > 0:
                first_tool = tool_calls[0]
                # record tool call details
                if 'name' in first_tool:
                    logger.debug(f"Tool call: {first_tool['name']}")
                # handle tool calls in Python code
                if ('name' in first_tool and
                        first_tool['name'] == 'python_interpreter' and
                        'code_tools' in first_tool):
                    logger.debug(
                        f"Python code uses tools: {first_tool['code_tools']}"
                    )

        # check step type, record more detailed logs
        if 'detailed_type' in step_data:
            logger.debug(f"Step type: {step_data['detailed_type']}")
            # if action step, record observations
            if (step_data['detailed_type'] == 'action' and
                    'observations' in step_data):
                logger.debug("Step has observations")

        # check error information
        if "error" in step_data:
            error_msg = step_data.get(
                "error_message",
                step_data.get("message", "Unknown error")
            )
            console.print(
                f"[red]Error in step {step_data.get('step_counter', 0)}: "
                f"{error_msg}[/red]"
            )
            return

        # use formatter to process step updates
        formatter.on_step_update(step_obj)
    except Exception as ex:
        logger.error(f"Error in step update handler: {ex}")
        if logger.level <= logging.DEBUG:
            logger.debug(f"Step data: {step_data}")
            logger.debug(traceback.format_exc())


# modified query processing function, using new callback system
async def process_query_async(query, agent_instance, verbose_mode, console):
    """process query and display results -
    using new smolagents.memory callback system

    Args:
        query: query string
        agent_instance: agent instance
        verbose_mode: verbose mode
        console: console object

    """
    console.print(
        f"[bold cyan]⏳ Processing query: {query[:50]}...[/bold cyan]"
    )

    # Check if streaming is enabled
    streaming_enabled = (
        settings.CLI_STREAMING_ENABLED and
        (
            (agent_instance.agent_type == "react" and settings.REACT_ENABLE_STREAMING) or
            (agent_instance.agent_type == "codact" and settings.CODACT_ENABLE_STREAMING) or
            (agent_instance.agent_type == "manager" and settings.MANAGER_ENABLE_STREAMING)
        )
    )

    # create UI formatter (use streaming formatter if streaming is enabled)
    if streaming_enabled:
        formatter = StreamingConsoleFormatter(
            agent_type=agent_instance.agent_type,
            console=console,
            debug_mode=verbose_mode
        )
        logger.debug("Using StreamingConsoleFormatter")
    else:
        formatter = ConsoleFormatter(
            agent_type=agent_instance.agent_type,
            console=console,
            debug_mode=verbose_mode
        )
        logger.debug("Using standard ConsoleFormatter")

    # get agent_instance's model, ensure correct retrieval
    llm_model = None
    if hasattr(agent_instance, 'agent') and agent_instance.agent:
        # directly get agent object's model attribute
        if hasattr(agent_instance.agent, 'model'):
            llm_model = agent_instance.agent.model
            logger.debug(f"Found model instance: {type(llm_model).__name__}")

            # check model token counting capabilities
            if hasattr(llm_model, 'last_input_token_count'):
                logger.debug(
                    f"Model has token count attributes: "
                    f"last_input_token_count="
                    f"{getattr(llm_model, 'last_input_token_count', None)}, "
                    f"last_output_token_count="
                    f"{getattr(llm_model, 'last_output_token_count', None)}"
                )
            else:
                logger.warning(
                    "Model lacks token count attributes - "
                    f"model type: {type(llm_model).__name__}"
                )

                # try to print all model attributes for diagnosis
                if verbose_mode:
                    try:
                        model_attrs = [attr for attr in dir(llm_model)
                                       if not attr.startswith('__')]
                        logger.debug(
                            f"Available model attributes: {model_attrs}"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Couldn't inspect model attributes: {e}"
                        )

    # create new step callback processor
    step_callback = AgentStepCallback(
        on_step_callback=lambda step_data: handle_step_update(
            step_data, console, formatter
        ),
        debug_mode=verbose_mode,
        model=llm_model
    )

    # Recreate agent with step callback for smolagents 1.20.0 compatibility
    agent_type = getattr(agent_instance, 'agent_type', 'codact')
    agent_instance = agent_runtime.get_or_create_agent(
        agent_type=agent_type,
        step_callback=step_callback,
        debug_mode=verbose_mode
    )

    # use safe error handling logic to execute agent
    final_result = None

    try:
        # display processing status
        console.print(
            f"[{THINKING_COLOR}]{THINKING_EMOJI} Thinking & Action..."
            f"[/{THINKING_COLOR}]"
        )

        # check if we should enable streaming
        if streaming_enabled:
            console.print(
                f"[dim]Streaming mode enabled for {agent_instance.agent_type} agent[/dim]"
            )

            # Start streaming display
            if hasattr(formatter, 'on_stream_start'):
                formatter.on_stream_start()

            try:
                # Run agent with streaming enabled
                if asyncio.iscoroutinefunction(agent_instance.run):
                    # directly call asynchronous method with stream=True
                    result = await agent_instance.run(query, stream=True)
                else:
                    # use run_in_executor to run synchronous method
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None, agent_instance.run, query, True  # stream=True
                    )

                # Check if result is a generator (streaming response)
                if hasattr(result, '__aiter__'):
                    # Handle async generator
                    final_result = ""
                    async for chunk in result:
                        # Convert chunk to string if needed
                        if hasattr(chunk, 'content'):
                            chunk_str = chunk.content
                        elif hasattr(chunk, 'text'):
                            chunk_str = chunk.text
                        else:
                            chunk_str = str(chunk)

                        # Skip None chunks
                        if chunk_str is None:
                            continue

                        if hasattr(formatter, 'on_stream_chunk'):
                            formatter.on_stream_chunk(chunk)
                        final_result += chunk_str
                elif hasattr(result, '__iter__') and not isinstance(result, str):
                    # Handle sync generator
                    final_result = ""
                    for chunk in result:
                        # Convert chunk to string if needed
                        if hasattr(chunk, 'content'):
                            chunk_str = chunk.content
                        elif hasattr(chunk, 'text'):
                            chunk_str = chunk.text
                        else:
                            chunk_str = str(chunk)

                        # Skip None chunks
                        if chunk_str is None:
                            continue

                        if hasattr(formatter, 'on_stream_chunk'):
                            formatter.on_stream_chunk(chunk)
                        final_result += chunk_str
                else:
                    # Not a generator, just regular result
                    final_result = result

                # End streaming display
                if hasattr(formatter, 'on_stream_end'):
                    formatter.on_stream_end()

            except Exception as e:
                # Handle streaming error
                if hasattr(formatter, 'on_stream_error'):
                    formatter.on_stream_error(str(e))
                raise

        else:
            # Non-streaming execution
            # check run method whether it's asynchronous or not
            if asyncio.iscoroutinefunction(agent_instance.run):
                # directly call asynchronous method
                final_result = await agent_instance.run(query)
            else:
                # use run_in_executor to run synchronous method
                loop = asyncio.get_running_loop()
                final_result = await loop.run_in_executor(
                    None, agent_instance.run, query
                )

        # display completion message
        final_text = STATUS_TEXT.get("final", "Completed")
        console.print(
            f"[{FINAL_COLOR}]{FINAL_EMOJI} {final_text}"
            f"[/{FINAL_COLOR}]"
        )

    except Exception as e:
        console.print(f"[red]Error executing agent: {e}[/red]")
        console.print(traceback.format_exc())
    finally:
        # try to render final result whether execution is successful or not
        if final_result:
            try:
                render_json_as_markdown(final_result, console)
            except Exception as render_error:
                console.print(
                    f"[red]Error rendering final result: {render_error}[/red]"
                )
                # try alternative way to display result
                console.print("[yellow]Original result:[/yellow]")
                result_str = str(final_result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "..."
                console.print(result_str)
        else:
            console.print("[red]Warning: Agent did not return a result[/red]")

        # display enhanced statistics
        try:
            stats = step_callback.get_statistics()
            console.print("\n[bold]Execution statistics:[/bold]")

            # Use the console formatter to display rich statistics
            if hasattr(formatter, 'format_statistics'):
                # Use the enhanced statistics formatter if available
                stats_display = formatter.format_statistics(stats)
                console.print(stats_display)
            else:
                # Fallback to basic statistics display
                console.print(f"Total steps: {stats['steps_count']}")
                if stats.get('tools_used'):
                    console.print(
                        f"Used tools: {', '.join(stats['tools_used'])}"
                    )
                else:
                    console.print("Used tools: None")

                # Display timing information if available
                if 'total_llm_time' in stats:
                    total_time = (
                        stats['total_llm_time'] + stats['total_tool_time']
                    )
                    console.print(f"Total execution time: {total_time:.2f}s")
                    console.print(
                        f"LLM thinking time: {stats['total_llm_time']:.2f}s"
                    )
                    console.print(
                        f"Tool execution time: {stats['total_tool_time']:.2f}s"
                    )

                # Display token information if available
                token_counts = stats.get('token_counts', {})
                if token_counts:
                    # Handle both TokenUsage object and dict formats
                    if hasattr(token_counts, 'input_tokens'):
                        # TokenUsage object
                        input_tokens = token_counts.input_tokens or 0
                        output_tokens = token_counts.output_tokens or 0
                    else:
                        # Dictionary format
                        input_tokens = token_counts.get('total_input', 0)
                        output_tokens = token_counts.get('total_output', 0)

                    total_tokens = input_tokens + output_tokens
                    if total_tokens > 0:
                        console.print(f"Total tokens: {total_tokens}")
                        console.print(f"Input tokens: {input_tokens}")
                        console.print(f"Output tokens: {output_tokens}")

        except Exception as stats_error:
            console.print(
                f"[red]Error getting statistics: {stats_error}[/red]"
            )

        return final_result


# Interactive CLI loop - keep and optimize
async def run_interactive_cli(
    agent_instance, args, console, skip_ready_message=False
):
    """Run interactive CLI loop"""
    # Get agent type
    agent_type = args.agent_type.lower()

    # Prepare history file
    history_path = Path.home() / ".deepsearch-agent-history.txt"
    session = PromptSession(history=FileHistory(str(history_path)))
    multiline = False

    # Display welcome information for specific agent type
    if agent_type == "react":
        agent_emoji = "🤠⚙️"
        agent_style = "blue"
    elif agent_type == "codact":
        agent_emoji = "👻⌨️"
        agent_style = "green"
    else:  # manager
        agent_emoji = "🎯🤝"
        agent_style = "cyan"
    if not skip_ready_message:
        console.print(
            f"\n[bold {agent_style}]{agent_emoji} {agent_type.upper()} "
            f"mode is ready![/bold {agent_style}]"
        )

    while True:
        try:
            # Customize prompt to display different agent types
            if agent_type == "react":
                agent_emoji = "🤠⚙️"
                prompt_text = HTML(
                    "<b><ansiblue>DeepSearchAgent</ansiblue></b> 🤠⚙️ "
                )
            elif agent_type == "codact":
                agent_emoji = "👻⌨️"
                prompt_text = HTML(
                    "<b><ansigreen>DeepSearchAgent</ansigreen></b> 👻⌨️ "
                )
            else:  # manager
                agent_emoji = "🎯🤝"
                prompt_text = HTML(
                    "<b><ansicyan>DeepSearchAgent</ansicyan></b> 🎯🤝 "
                )
            text = await session.prompt_async(prompt_text, multiline=multiline)

        except (KeyboardInterrupt, EOFError):
            console.print("[dim]Received exit signal.[/dim]")
            break

        if not text.strip():
            continue

        command = text.strip()
        if command.startswith('/'):
            exit_code, multiline = handle_slash_command(
                command, multiline, console
            )
            if exit_code is not None:
                break  # If return exit code, exit loop
        else:
            # Display separator before processing query
            # to make interaction clearer
            border = COLORS[agent_type]['border']
            sep_line = f"[{border}]{'═' * DISPLAY_WIDTH}[/{border}]"
            console.print(sep_line)

            # Display new query prompt
            console.print(
                f"[bold {agent_style}]{agent_emoji} Starting new query..."
                f"[/bold {agent_style}]"
            )

            # Process query
            await process_query_async(
                text, agent_instance, args.verbose, console
            )

            # Display separator to indicate query completion
            console.print(sep_line)
            console.print(
                "[dim]Query processed, continue with new queries...[/dim]"
            )

    # Display exit message
    console.print(
        f"[bold {agent_style}]{agent_emoji} Thank you for using "
        f"DeepSearchAgent![/bold {agent_style}]"
    )
    return 0  # Normal exit


# Select team type for manager
def select_team_type(console):
    """Select team type for manager agent"""
    # create selection table
    team_table = Table(
        show_header=False,
        box=None,
        border_style="cyan",
        padding=(0, 1, 0, 1),
        expand=False
    )

    # add columns
    team_table.add_column(
        "Option", style="bold cyan", justify="center", width=3
    )
    team_table.add_column(
        "Team Type", style="bold white", width=30
    )
    team_table.add_column("Description", style="bright_white")

    # Research team option
    research_title = Text("", style="bold green")
    research_title.append("Research Team ", style="bold green")
    research_title.append("🔍📊", style="bold")

    research_desc = Text("Specialized team for deep research tasks\n")
    research_desc.append("• ", style="dim")
    research_desc.append("Web Research Specialist", style="blue")
    research_desc.append(" (React): Search & retrieve information\n", style="dim")
    research_desc.append("• ", style="dim")
    research_desc.append("Data Analysis Specialist", style="green")
    research_desc.append(" (CodeAct): Process & synthesize data", style="dim")

    # Custom team option
    custom_title = Text("", style="bold yellow")
    custom_title.append("Custom Team ", style="bold yellow")
    custom_title.append("⚙️🔧", style="bold")

    custom_desc = Text("Build your own team composition\n")
    custom_desc.append("Select which agents to include and configure their roles", style="dim")

    # add rows
    team_table.add_row("[1]", research_title, research_desc)
    team_table.add_row("[2]", custom_title, custom_desc)

    # display selection table
    console.print(Panel(
        team_table,
        title="[bold cyan]Select Team Configuration[/bold cyan]",
        border_style="cyan",
        expand=False
    ))

    # add selection prompt
    choice = Prompt.ask(
        "[bold cyan]Please select team type[/bold cyan]",
        choices=["1", "2"],
        default="1"
    )

    return "research" if choice == "1" else "custom"


# Select agent type
def select_agent_type(console):
    """Select agent type: React, CodeAct, or Manager"""
    react_name = COLORS['react']['name']
    codact_name = COLORS['codact']['name']

    # create selection type table
    selection_table = Table(
        show_header=False,
        box=None,
        border_style="cyan",
        padding=(0, 1, 0, 1),
        expand=False
    )

    # add columns
    selection_table.add_column(
        "Option", style="bold cyan", justify="center", width=3
    )
    selection_table.add_column(
        "Agent type", style="bold white", width=30
    )
    selection_table.add_column("Description", style="bright_white")

    # CodeAct option
    codact_title = Text("", style=codact_name)
    codact_title.append("CodeAct ", style=codact_name)
    codact_title.append("👻⌨️", style="bold")
    codact_title.append(" <Deep Search Agent>", style="bright_white")

    # create description text, avoid single line too long
    codact_desc = Text("For complex queries, you can write any Python code "
                       "to implement more flexible search strategies\n")
    codact_desc.append("📌 ", style="yellow")
    codact_desc.append("Features: ", style="dim")
    codact_desc.append("High flexibility", style="green")
    codact_desc.append(" • ", style="dim")
    codact_desc.append("Customizable", style="blue")
    codact_desc.append(" • ", style="dim")
    codact_desc.append("Support complex logic", style="magenta")

    # React option
    react_title = Text("", style=react_name)
    react_title.append("React ", style=react_name)
    react_title.append("🤠⚙️", style="bold")
    react_title.append(" <Standard Search Agent>", style="bright_white")

    # create description text, avoid single line too long
    react_desc = Text("For simple queries, think about the next step "
                      "after each tool call\n")
    react_desc.append("📌 ", style="yellow")
    react_desc.append("Features: ", style="dim")
    react_desc.append("Structured reasoning", style="green")
    react_desc.append(" • ", style="dim")
    react_desc.append("Clear steps", style="blue")
    react_desc.append(" • ", style="dim")
    react_desc.append("Easy to track", style="magenta")

    # Manager option
    manager_title = Text("", style="bold cyan")
    manager_title.append("Research Multi-Agent Team ", style="bold cyan")
    manager_title.append("🎯🤝", style="bold")
    manager_title.append(" <Code Orchestrator>", style="bright_white")

    # create description text
    manager_desc = Text("For complex tasks requiring multiple perspectives, "
                       "dynamically orchestrates agents through code execution\n")
    manager_desc.append("📌 ", style="yellow")
    manager_desc.append("Features: ", style="dim")
    manager_desc.append("Code-based orchestration", style="green")
    manager_desc.append(" • ", style="dim")
    manager_desc.append("Dynamic delegation", style="blue")
    manager_desc.append(" • ", style="dim")
    manager_desc.append("Team collaboration", style="magenta")

    # add row
    selection_table.add_row("[1]", codact_title, codact_desc)
    selection_table.add_row("[2]", react_title, react_desc)
    selection_table.add_row("[3]", manager_title, manager_desc)

    # display selection table
    console.print(Panel(
        selection_table,
        title="[bold cyan]Please select agent type[/bold cyan]",
        border_style="cyan",
        expand=False
    ))

    # add selection prompt
    choice = Prompt.ask(
        "[bold cyan]Please enter the option number[/bold cyan]",
        choices=["1", "2", "3"],
        default="1"
    )
    if choice == "1":
        agent_type = "codact"
    elif choice == "2":
        agent_type = "react"
    else:  # choice == "3"
        agent_type = "manager"
    return agent_type


# Main function
def main():
    """CLI main entry function"""
    parser = argparse.ArgumentParser(description="DeepSearchAgent CLI")

    # Select agent type
    parser.add_argument(
        "--agent-type", "-a", type=str, choices=["react", "codact", "manager"],
        help="Agent type (react, codact, or manager)"
    )

    # Query parameter (one-time mode)
    parser.add_argument(
        "--query", "-q", type=str,
        help="Query to process (non-interactive mode)"
    )

    # Verbose mode
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose mode, show more logs"
    )

    # ReAct specific settings
    parser.add_argument(
        "--react-planning-interval", type=int, default=None,
        help="ReAct agent planning interval (default: 7)"
    )

    # CodeAct specific settings
    parser.add_argument(
        "--codact-planning-interval", type=int, default=None,
        help="CodeAct agent planning interval (default: 4)"
    )
    parser.add_argument(
        "--max-steps", type=int, default=None,
        help="Maximum steps for the agent (default: 25)"
    )
    parser.add_argument(
        "--executor-type", type=str,
        choices=["local", "docker", "e2b"], default=None,
        help="CodeAct code executor type (default: local)"
    )

    # Manager specific settings
    parser.add_argument(
        "--team", "-t", type=str,
        choices=["research", "custom"], default="research",
        help="Preset team configuration for manager mode"
    )
    parser.add_argument(
        "--managed-agents", type=str, nargs="+",
        help="List of agent types to manage (for custom team)"
    )
    parser.add_argument(
        "--manager-planning-interval", type=int, default=None,
        help="Manager agent planning interval (default: 10)"
    )

    parser.add_argument(
        "--enable-streaming", action="store_true",
        help="Enable streaming output (not recommended)"
    )

    args = parser.parse_args()

    try:
        # Prepare console
        console = Console()

        # Initialize global variables
        _initialize_globals()

        # Prompt to select agent type (if not specified)
        if not args.agent_type:
            args.agent_type = select_agent_type(console)
            if args.agent_type == "react":
                agent_style = "blue"
            elif args.agent_type == "codact":
                agent_style = "green"
            else:  # manager
                agent_style = "cyan"
            msg = (f"[green]Selected:[/green] [bold {agent_style}]"
                   f"{args.agent_type.upper()}[/bold {agent_style}] "
                   f"agent mode")
            console.print(msg)

            # If manager mode selected, also select team type
            if args.agent_type == "manager" and not args.team:
                args.team = select_team_type(console)
                console.print(f"[green]Selected team:[/green] [bold cyan]{args.team.upper()}[/bold cyan]")

        # Set specific configurations based on agent type
        if args.agent_type == 'react':
            # React specific settings -
            # only override default values if not None
            if args.react_planning_interval is not None:
                settings.REACT_PLANNING_INTERVAL = args.react_planning_interval
            if args.enable_streaming is not None:
                settings.REACT_ENABLE_STREAMING = args.enable_streaming
            if args.max_steps is not None:
                settings.REACT_MAX_STEPS = args.max_steps
        elif args.agent_type == 'codact':
            # CodeAct specific settings - only override default values
            # if not None
            if args.codact_planning_interval is not None:
                interval = args.codact_planning_interval
                settings.CODACT_PLANNING_INTERVAL = interval
            if args.executor_type is not None:
                settings.CODACT_EXECUTOR_TYPE = args.executor_type
            if args.max_steps is not None:
                settings.CODACT_MAX_STEPS = args.max_steps
            if args.enable_streaming is not None:
                settings.CODACT_ENABLE_STREAMING = args.enable_streaming
        else:  # manager
            # Manager specific settings
            if args.manager_planning_interval is not None:
                settings.MANAGER_PLANNING_INTERVAL = args.manager_planning_interval
            else:
                settings.MANAGER_PLANNING_INTERVAL = 10  # default
            if args.max_steps is not None:
                settings.MANAGER_MAX_STEPS = args.max_steps
            else:
                settings.MANAGER_MAX_STEPS = 30  # default
            if args.enable_streaming is not None:
                settings.MANAGER_ENABLE_STREAMING = args.enable_streaming
            # Set team configuration
            settings.MANAGER_TEAM = args.team
            settings.MANAGER_CUSTOM_AGENTS = args.managed_agents

        # Common settings
        settings.VERBOSE_TOOL_CALLBACKS = args.verbose

        # Get agent instance from agent_runtime
        agent_instance = agent_runtime.get_or_create_agent(args.agent_type)

        if agent_instance is None:
            console.print(
                f"[{ERROR_COLOR}]{ERROR_EMOJI} Error:[/{ERROR_COLOR}] "
                f"Failed to initialize {args.agent_type.upper()} agent, "
                f"missing required API keys."
            )
            exit(1)

        # Display welcome information
        display_welcome(args, console)

        # Run mode
        if args.query:
            console.print(
                f"[yellow]Executing single query:[/yellow] {args.query}"
            )
            try:
                asyncio.run(process_query_async(
                    args.query, agent_instance, args.verbose, console
                ))
                exit_code = 0
            except KeyboardInterrupt:
                console.print("[dim]Received interrupt signal.[/dim]")
                exit_code = 1
            except Exception as e:
                console.print(
                    f"[{ERROR_COLOR}]{ERROR_EMOJI} Error:[/{ERROR_COLOR}] "
                    f"Unexpected error occurred while processing single "
                    f"query: {e}"
                )
                exit_code = 1
            exit(exit_code)
        else:
            # Start interactive loop
            try:
                # Skip the message in run_interactive_cli because we already
                # showed it
                if args.agent_type == "react":
                    agent_style = "blue"
                elif args.agent_type == "codact":
                    agent_style = "green"
                else:  # manager
                    agent_style = "cyan"

                exit_code = asyncio.run(
                    run_interactive_cli(
                        agent_instance, args, console, skip_ready_message=True
                    )
                )
                exit(exit_code)
            except KeyboardInterrupt:
                console.print("[dim]Interactive session interrupted.[/dim]")
                exit(1)
            except Exception as e:
                console.print(
                    f"[{ERROR_COLOR}]{ERROR_EMOJI} Error:[/{ERROR_COLOR}] "
                    f"Unexpected error occurred while running interactive "
                    f"CLI: {e}"
                )
                console.print(traceback.format_exc())
                exit(1)
    except Exception as e:
        console.print(f"[red]Error during initialization: {e}[/red]")
        console.print(traceback.format_exc())
        exit(1)


if __name__ == "__main__":
    main()

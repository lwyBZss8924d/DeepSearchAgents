#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/cli.py

import logging
import os
import sys


class LiteLLMStrictFilter(logging.Filter):
    """Filter to strictly filter out all duplicate and redundant LiteLLM logs"""

    def __init__(self):
        super().__init__()
        self.last_message = None

    def filter(self, record):
        # If not a LiteLLM log, let it pass
        if not record.name.startswith('litellm'):
            return True

        # Filter out cost calculation and token count logs
        if ('cost_calculator' in record.msg or 
                'selected model name for cost calculation' in record.msg or
                'token_counter' in record.msg):
            return False

        # Filter out duplicate messages
        if record.msg == self.last_message:
            return False

        self.last_message = record.msg
        return True


# 1. Configure root logger
root_logger = logging.getLogger()

# 2. Remove all existing handlers to avoid duplicate logs
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 3. Add a custom console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)  # Default only shows WARNING and above
console_handler.setFormatter(logging.Formatter('%(message)s'))
root_logger.addHandler(console_handler)

# 4. Apply filter to root logger
litellm_filter = LiteLLMStrictFilter()
root_logger.addFilter(litellm_filter)

# 5. Set level for litellm logger
litellm_logger = logging.getLogger("litellm")
litellm_logger.setLevel(logging.WARNING)
litellm_logger.propagate = False

# 6. Add a separate handler for litellm and apply filter
litellm_handler = logging.StreamHandler(sys.stdout)
litellm_handler.setFormatter(logging.Formatter('LITELLM: %(message)s'))
litellm_handler.addFilter(litellm_filter)
litellm_logger.addHandler(litellm_handler)

# 7. Apply same settings to all litellm submodules
for submodule in ["utils", "llms", "proxy"]:
    sublogger = logging.getLogger(f"litellm.{submodule}")
    sublogger.setLevel(logging.WARNING)
    sublogger.propagate = False
    sublogger.addFilter(litellm_filter)
    sub_handler = logging.StreamHandler(sys.stdout)
    sub_handler.setFormatter(logging.Formatter(f'LITELLM.{submodule}: %(message)s'))
    sub_handler.addFilter(litellm_filter)
    sublogger.addHandler(sub_handler)

# 8. Set httpx logger
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
httpx_logger.propagate = False


# Import other modules now
import argparse
import traceback
import asyncio
import time
import json
import re
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

from .agent import create_react_agent
from .codact_agent import create_codact_agent
from .config_loader import APP_CONFIG, get_config_value, get_api_key

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.text import Text
    from rich.console import Group
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn,
        BarColumn, TimeElapsedColumn
    )
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

except ImportError as e:
    error_message = (
        f"Error: Required CLI dependencies are missing ({e}).\n"
        "Please install them using:\n"
        'uv pip install "DeepSearch-AgentTeam[cli]"\n'
    )
    print(error_message)
    exit(1)


REACT_PLANNING_INTERVAL = get_config_value(
    APP_CONFIG, 'agents.react.planning_interval', 7
)

# Load CodeAct specific configuration
CODACT_ENABLE_STREAMING = get_config_value(
    APP_CONFIG, 'agents.codact.enable_streaming', True
)
CODACT_PLANNING_INTERVAL = get_config_value(
    APP_CONFIG, 'agents.codact.planning_interval', 5
)
CODACT_EXECUTOR_KWARGS = get_config_value(
    APP_CONFIG, 'agents.codact.executor_kwargs', {}
)
CODACT_ADDITIONAL_IMPORTS = get_config_value(
    APP_CONFIG, 'agents.codact.additional_authorized_imports', []
)


# --- Custom domain name masking formatter ---
class DomainMaskingFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        if record.name == 'httpx':
            message = re.sub(
                r'(https?://)[^/\s]+',
                r'\1******',
                message
            )
        return message


# --- CLI Helper Functions ---

def display_welcome(args, console: Console):
    """
    Display welcome information
    """
    readme_path = 'README.md'
    description = ""
    try:
        with open(readme_path, "r") as f:
            readme_content = f.read()
        description_match = readme_content.split("## 1. Introduction")
        if len(description_match) > 1:
            description_content = description_match[1].split("##")[0].strip()
            description = (
                description_content if description_content else ""
            )
        else:
            description_section = readme_content.split("## Description")
            if len(description_section) > 1:
                description_content = description_section[1].split(
                    "##"
                )[0].strip()
                description = (
                    description_content if description_content else ""
                )

    except FileNotFoundError:
        console.print(
            f"[yellow] Warning:[/yellow] README.md not found at "
            f"expected location: {readme_path}"
        )
    except Exception as e:
        console.print(
            f"[yellow] Warning:[/yellow] Unable to read or parse "
            f"README.md: {e}"
        )

    console.print(Panel(
        Markdown(description) if description else
        "DeepSearchAgent (ReAct-CodeAct Agent) is an AI agent team that "
        "can perform iterative web deep search and deep research.",
        title="[bold cyan]DeepSearchAgent React 🚀[/bold cyan]",
        border_style="cyan",
    ))

    config_text = (
        f"Agent Type: [bold cyan]{args.agent_type.upper()}[/bold cyan]\n"
        f"Search Model: [cyan]{args.search_id}[/cyan]\n"
        f"Orchestrator Model: [cyan]{args.orchestrator_id}[/cyan]\n"
        f"Reranker: [cyan]{args.reranker_type}[/cyan]\n"
        f"Verbose (Tool Logs): [cyan]"
        f"{'Enabled' if args.verbose else 'Disabled'}[/cyan]"
    )

    if args.agent_type == "codact":
        streaming_status = "Enabled" if args.enable_streaming else "Disabled"
        config_text += (
            f"\nExecutor Type: [cyan]{args.executor_type}[/cyan]\n"
            f"Max Steps: [cyan]{args.max_steps}[/cyan]\n"
            f"Verbosity Level: [cyan]{args.verbosity_level}[/cyan]\n"
            f"Streaming Mode: [cyan]{streaming_status}[/cyan]"
        )

    console.print(Panel(
        config_text,
        title="[bold blue]Configuration Information[/bold blue]",
        border_style="blue",
    ))

    console.print(
        "\n[dim] CLI Tips: Input /exit or /quit to exit. "
        "Input /multiline to toggle.[/dim]"
    )
    console.print("[bold]Example Queries:[/bold]")
    console.print(
        "  • Search Google OpenAI and Anthropic's latest products, LLM "
        "models, technologies, papers, search & analyze then summarize it."
    )


def handle_slash_command(
    command: str,
    multiline: bool,
    console: Console
) -> tuple[int | None, bool]:
    """ Handle slash commands """
    if command in ('/exit', '/quit'):
        console.print("[dim]Exiting...[/dim]")
        return 0, multiline
    elif command == '/multiline':
        multiline = not multiline
        if multiline:
            console.print(
                '[cyan]Multiline mode enabled.[/cyan] [dim]Press Esc+Enter or '
                'Ctrl+D (Unix) / Ctrl+Z+Enter (Win) to submit.'
            )
        else:
            console.print('[cyan]Multiline mode disabled.[/cyan]')
        return None, multiline
    # Add other commands like /markdown if needed
    # elif command == '/markdown':
    #     # ... (implementation to show last response markdown)
    #     pass
    else:
        console.print(f'[red]Unknown command:[/red] {command}')
        return None, multiline


# --- Load CodeAct specific config for streaming ---
# Note: This assumes cli.py runs independently and needs to load config.
# If cli is always run via main.py, this might be redundant.
CODACT_ENABLE_STREAMING = get_config_value(
    APP_CONFIG, 'agents.codact.enable_streaming', True  # Default to True
)


def render_json_as_markdown(final_result_str, console):
    """
    Check if the output is JSON format, if so, extract and render its content as Markdown
    Return a flag indicating whether rendering was successful
    """
    if not final_result_str:
        return False

    # Handle dictionary input directly
    json_data = None

    if isinstance(final_result_str, dict):
        json_data = final_result_str
    elif isinstance(final_result_str, str) and final_result_str.strip().startswith('{') and final_result_str.strip().endswith('}'):
        try:
            json_data = json.loads(final_result_str)
        except json.JSONDecodeError:
            return False
    else:
        return False

    # Process JSON data if we have it
    if isinstance(json_data, dict) and 'content' in json_data:
        # Extract Markdown content
        markdown_content = json_data.get('content', '')

        # Get sources for rendering
        sources = []
        if 'sources' in json_data and json_data['sources']:
            sources = json_data['sources']

        # If markdown_content doesn't already contain a Sources section, add one
        has_sources_section = '## Sources' in markdown_content

        # If there are sources and no Sources section, append one
        if sources and not has_sources_section:
            # Add newlines to ensure proper spacing
            if not markdown_content.endswith('\n\n'):
                if markdown_content.endswith('\n'):
                    markdown_content += '\n'
                else:
                    markdown_content += '\n\n'

            # Add Sources section header
            markdown_content += "## Sources\n\n"

            # Add each source as a numbered reference
            for i, url in enumerate(sources):
                # Extract a title from the URL or use a generic one
                url_parts = url.split("/")
                title = ""
                # Try to get a meaningful title from the URL
                if len(url_parts) > 2:
                    # Use last part of URL path, cleaned up
                    raw_title = url_parts[-1] if url_parts[-1] else url_parts[-2]
                    # Remove file extensions and clean up
                    title = raw_title.split('.')[0].replace('-', ' ').replace('_', ' ').capitalize()

                # If we couldn't extract a meaningful title, use a generic one
                if not title:
                    title = f"Source {i+1}"

                # Add the numbered reference
                markdown_content += f"{i+1}. [{title}]({url})\n"

        # Prepare title
        title = "[bold green]Final Markdown Output[/bold green]"
        if 'title' in json_data and json_data['title']:
            title = f"[bold green]{json_data['title']}[/bold green]"

        # Display Markdown rendering content
        console.print("\n[bold cyan]Final Answer Report:[/bold cyan]")
        console.print(Panel(
            Markdown(markdown_content),
            title=title,
            border_style="green"
        ))

        return True

    return False


async def process_query_async(
    query: str,
    agent_instance,
    verbose_mode: bool,
    console: Console,
    last_response_md: List[str]  # Use list to pass by reference
):
    """
    Asynchronously process the query and display the result, supporting
    streaming.
    """
    # Create status display
    spinner = SpinnerColumn()
    task_description = TextColumn("[bold blue]{task.description}")
    bar_column = BarColumn(bar_width=None)
    status_column = TextColumn("[cyan]{task.fields[status]}")
    time_column = TimeElapsedColumn()

    last_response_md.clear()  # Clear previous response
    final_result_str = None  # Initialize final result string

    # Collect streaming output statistics
    token_count = 0
    start_time = None
    actual_input_tokens = None # Variable for API input tokens
    actual_output_tokens = None # Variable for API output tokens

    # Track planning steps and state variables
    planning_counter = 0

    # State variable tracking data
    state_summary = {
        "visited_urls": 0,
        "search_queries": 0,
        "search_depth": 0
    }

    # Check if the agent is a streaming type
    agent_class_name = ""
    if hasattr(agent_instance, '__class__'):
        agent_class_name = agent_instance.__class__.__name__

    is_streaming_agent = (
        agent_class_name == 'StreamingCodeAgent' or
        agent_class_name == 'StreamingReactAgent' or
        agent_class_name == 'StreamingFinalAnswerWrapper'
    )

    # Only enable streaming mode if the agent is a streaming type
    use_stream = is_streaming_agent and CODACT_ENABLE_STREAMING

    # Process task_displayed logic - set the flag early to prevent duplicate task display
    # If the agent object has the task_displayed attribute, set it to True (this applies to StreamingReactAgent and StreamingCodeAgent)
    if hasattr(agent_instance, 'task_displayed'):
        agent_instance.task_displayed = True

    # Also maintain a flag in the function to ensure local display control has the same setting
    task_displayed = True

    try:
        # Use Progress to display thinking and processing stages
        with Progress(
            spinner, task_description, bar_column,
            status_column, time_column,
            console=console, transient=True,
            expand=True
        ) as progress:
            # Display thinking status
            thinking_task_id = progress.add_task(
                "[bold cyan]🤔 Thinking...",
                total=None,
                status="Processing your query"
            )

            # Use run_in_executor for the potentially blocking agent.run call
            loop = asyncio.get_running_loop()

            if use_stream:
                # Update status text
                progress.update(
                    thinking_task_id,
                    description="[bold cyan]⚙️ Processing...",
                    status="Executing agent steps"
                )

                # Get the synchronous generator from the executor
                try:
                    sync_generator = await loop.run_in_executor(
                        None, agent_instance.run, query, True
                    )

                    # Reached here means the thinking stage is complete,
                    # stop the Progress display, and prepare to show streaming results
                    progress.stop()

                    # Check if the return type is a synchronous or asynchronous iterator
                    # or a normal string
                    continue_processing = True  # Control whether to continue processing streaming output
                    if isinstance(sync_generator, str):
                        # If it's a string, use it directly as the final result
                        final_result_str = sync_generator
                    elif isinstance(sync_generator, dict):
                        # Special handling: If the return type is a dictionary,
                        # directly convert it to a JSON string for processing
                        console.print("\n[bold green]Processing returned data...[/bold green]")
                        import json
                        try:
                            final_result_str = json.dumps(sync_generator, ensure_ascii=False)
                            render_success = render_json_as_markdown(final_result_str, console)
                            if not render_success:
                                console.print("\n[bold green]Final Answer Report:[/bold green]")
                                console.print(Panel(
                                    Text(str(sync_generator)),
                                    title="[bold green]Structured Output[/bold green]",
                                    border_style="green"
                                ))
                            continue_processing = False
                        except Exception as e:
                            console.print(f"[yellow]Error processing dict result: {e}[/yellow]")
                            final_result_str = str(sync_generator)
                    # Only enter the streaming processing branch if there is a need to continue processing
                    elif continue_processing and (hasattr(sync_generator, '__iter__') and
                          not hasattr(sync_generator, '__aiter__')):
                        # Streaming processing
                        console.print("\n[bold green]Generating Final Answer...[/bold green]")

                        # Use Live component for real-time streaming updates
                        with Live(
                            console=console,
                            refresh_per_second=15,
                            vertical_overflow="visible",
                            auto_refresh=True
                        ) as live_display:
                            chunks = []
                            collected_text = ""
                            markdown_panel = None
                            start_time = time.time()

                            # Define a safe function to get the next value of the generator
                            async def get_next_safely():
                                try:
                                    def safe_next(gen):
                                        try:
                                            return next(gen), True
                                        except StopIteration:
                                            return None, False
                                        except Exception as e:
                                            console.print(f"[yellow]Iteration error: {e}[/yellow]")
                                            return None, False

                                    result, has_next = await loop.run_in_executor(
                                        None, safe_next, sync_generator
                                    )
                                    return result, has_next
                                except Exception as e:
                                    console.print(f"[yellow]Error getting value: {e}[/yellow]")
                                    return None, False

                            # Use a while loop and a safe function to process the generator
                            while True:
                                # Safe iteration with custom error handling
                                try:
                                    chunk, has_next = await get_next_safely()
                                    if not has_next:
                                        break
                                except Exception as e:
                                    # Special handling for dict type errors
                                    if "'dict' object is not an iterator" in str(e):
                                        console.print("[yellow]Detected dictionary object cannot be iterated, trying to process final result directly...[/yellow]")
                                        # If the error is due to dict type, try to access sync_generator directly
                                        if isinstance(sync_generator, dict):
                                            # Directly convert dict to JSON string
                                            import json
                                            try:
                                                json_str = json.dumps(sync_generator, ensure_ascii=False)
                                                collected_text = json_str
                                                # Break the loop, directly process the final result
                                                break
                                            except Exception as json_err:
                                                console.print(f"[yellow]JSON conversion error: {json_err}[/yellow]")
                                                collected_text = str(sync_generator)
                                                break
                                    console.print(f"[yellow]Safe iteration error: {e}[/yellow]")
                                    # Try to continue with next chunk if possible
                                    continue

                                chunks.append(chunk)

                                # Check if it's a planning step
                                if hasattr(chunk, 'plan') and chunk.plan:
                                    planning_counter += 1
                                    # Display planning step
                                    planning_panel = Panel(
                                        Markdown(chunk.plan),
                                        title=f"[bold orange]Planning Step #{planning_counter}[/bold orange]",
                                        border_style="orange",
                                        expand=True
                                    )
                                    live_display.update(planning_panel)
                                    # Brief pause to allow user to notice the planning step
                                    await asyncio.sleep(0.5)
                                    continue

                                # Try to update state variables
                                if hasattr(agent_instance, 'state'):
                                    state = agent_instance.state
                                    if isinstance(state, dict):
                                        if 'visited_urls' in state and isinstance(state['visited_urls'], set):
                                            state_summary['visited_urls'] = len(state['visited_urls'])
                                        if 'search_queries' in state and isinstance(state['search_queries'], list):
                                            state_summary['search_queries'] = len(state['search_queries'])
                                        if 'search_depth' in state:
                                            state_summary['search_depth'] = state['search_depth']

                                # Check if there is a special format block (Final Answer in React mode)
                                if (isinstance(chunk, str) and 
                                    chunk.startswith("\n<Final Answer>\n") and
                                    "</Final Answer>" in chunk):
                                    # This is the Final Answer block in React mode, need to extract content
                                    final_answer_content = (
                                        chunk.split("\n<Final Answer>\n")[1]
                                        .split("\n</Final Answer>")[0]
                                    )
                                    # Update collected text
                                    collected_text = final_answer_content
                                    content = final_answer_content
                                elif (isinstance(chunk, str) and
                                     chunk.startswith("<Final Answer>") and
                                     "</Final Answer>" in chunk):
                                    # Another possible format
                                    final_answer_content = (
                                        chunk.split("<Final Answer>")[1]
                                        .split("</Final Answer>")[0]
                                    )
                                    collected_text = final_answer_content
                                    content = final_answer_content
                                else:
                                    # Try to extract content from chunk
                                    try:
                                        # Extract content - litellm's format
                                        content = None
                                        # Try multiple ways to get content
                                        if (hasattr(chunk, 'choices') and
                                            chunk.choices):
                                            delta = chunk.choices[0].delta
                                            if (hasattr(delta, 'content') and
                                                delta.content is not None):
                                                content = delta.content
                                        # Process other possible formats
                                        elif hasattr(chunk, 'text'):
                                            content = chunk.text
                                        # StreamingAgentMixin output data format
                                        elif hasattr(chunk, 'text_chunk'):
                                            content = chunk.text_chunk
                                        elif (hasattr(chunk, 'delta') and
                                              hasattr(chunk.delta, 'content')):
                                            content = chunk.delta.content
                                        elif hasattr(chunk, 'get_chunk_text'):
                                            # CustomStreamWrapper method
                                            try:
                                                # Correct call: do not pass the object itself as an argument
                                                # to its own method
                                                content = chunk.get_chunk_text()
                                            except TypeError:
                                                # If the method requires parameters, try different cases
                                                try:
                                                    # Some cases may require passing the current block
                                                    content = (
                                                        chunk
                                                        .get_chunk_text(chunk)
                                                    )
                                                except Exception:
                                                    content = ""

                                        # If all methods fail, try string representation
                                        if content is None:
                                            content = str(chunk)
                                            if (content == "None" or
                                                "<object" in content):
                                                content = ""

                                        if content:
                                            token_count += 1
                                            collected_text += content
                                    except (AttributeError, KeyError, IndexError):
                                        # Non-standard format, try other ways to extract content
                                        pass

                                # Check if there is a specific format for Markdown report
                                is_markdown_report = False
                                if collected_text and (
                                    "# " in collected_text or
                                    "## " in collected_text or
                                    "```" in collected_text
                                ):
                                    is_markdown_report = True

                                # Try to parse JSON structured output
                                try:
                                    # Check if it's a JSON structure
                                    if (collected_text.strip().startswith('{') and 
                                        collected_text.strip().endswith('}')):
                                        try:
                                            json_data = json.loads(collected_text)
                                            # If successful JSON parsing
                                            if (isinstance(json_data, dict) and
                                                'title' in json_data and
                                                'content' in json_data):
                                                from rich.table import Table

                                                # Create a panel with table and markdown
                                                markdown_content = (
                                                    json_data.get('content', '')
                                                )

                                                table = Table(
                                                    show_header=True,
                                                    header_style="bold green"
                                                )
                                                table.add_column(
                                                    "Field",
                                                    style="cyan",
                                                    no_wrap=True
                                                )
                                                table.add_column(
                                                    "Content",
                                                    style="green"
                                                )

                                                # Add title row
                                                table.add_row(
                                                    "Title",
                                                    json_data.get('title', '')
                                                )

                                                # Add content preview row (shortened)
                                                preview_length = 200
                                                content_len = len(markdown_content)
                                                is_truncated = content_len > preview_length
                                                # Create preview text, determine if it is truncated
                                                if is_truncated:
                                                    preview_text = (
                                                        markdown_content[:preview_length]
                                                        + "..."
                                                    )
                                                else:
                                                    preview_text = markdown_content

                                                table.add_row(
                                                    "Content",
                                                    Text(preview_text)
                                                )

                                                # Add sources row
                                                if ('sources' in json_data and
                                                    json_data['sources']):
                                                    sources = json_data['sources']
                                                    max_sources = 3
                                                    # Generate source data preview
                                                    sources_preview = "\n".join(
                                                        sources[:max_sources]
                                                    )
                                                    # Check if there are more sources to omit
                                                    if len(sources) > max_sources:
                                                        sources_preview += "..."

                                                    table.add_row(
                                                        "Sources",
                                                        sources_preview
                                                    )

                                                # Add confidence row
                                                if 'confidence' in json_data:
                                                    confidence_text = (
                                                        f"{json_data['confidence']:.2f}"
                                                    )
                                                    table.add_row(
                                                        "Confidence", 
                                                        confidence_text
                                                    )

                                                # Create grouped display
                                                # Create component list
                                                group_components = []

                                                # Add table
                                                group_components.append(table)

                                                # Add Markdown content title
                                                group_components.append(
                                                    Text(
                                                        "\n[Markdown Content]",
                                                        style="bold cyan"
                                                    )
                                                )

                                                # Add Markdown content
                                                group_components.append(
                                                    Markdown(markdown_content)
                                                )

                                                # Add original JSON title
                                                group_components.append(
                                                    Text(
                                                        "\n[Raw JSON]",
                                                        style="dim"
                                                    )
                                                )

                                                # JSON formatting parameters
                                                json_format_args = {
                                                    "indent": 2,
                                                    "ensure_ascii": False
                                                }

                                                # Generate formatted JSON string
                                                json_str = json.dumps(
                                                    json_data,
                                                    **json_format_args
                                                )

                                                # Create formatted JSON display
                                                json_formatted = (
                                                    "```json\n" +
                                                    json_str +
                                                    "\n```"
                                                )

                                                # Add JSON formatting component
                                                group_components.append(
                                                    Markdown(json_formatted)
                                                )

                                                # Create panel title
                                                panel_title = (
                                                    "[bold green]Structured Output"
                                                    "[/bold green]"
                                                )

                                                # Create final panel
                                                structured_panel = Panel(
                                                    Group(*group_components),
                                                    title=panel_title,
                                                    border_style="green",
                                                    expand=True
                                                )
                                                live_display.update(structured_panel)
                                                # JSON content is marked as processed
                                                is_markdown_report = True
                                        except json.JSONDecodeError:
                                            # Not a complete JSON, continue with regular display
                                            pass
                                except Exception:
                                    # JSON processing error, ignore and continue with regular display
                                    pass

                                # Only update streaming display if not processed
                                if not is_markdown_report:
                                    try:
                                        # Add status overview
                                        status_text = Text()
                                        if any(state_summary.values()):
                                            status_text.append("\n\nStatus Overview: ", style="bold cyan")
                                            if state_summary["visited_urls"] > 0:
                                                status_text.append(f"Visited URLs: {state_summary['visited_urls']} | ", style="cyan")
                                            if state_summary["search_queries"] > 0:
                                                status_text.append(f"Search Queries: {state_summary['search_queries']} | ", style="cyan")
                                            if state_summary["search_depth"] > 0:
                                                status_text.append(f"Search Depth: {state_summary['search_depth']}", style="cyan")

                                        if not task_displayed and collected_text:
                                            task_displayed = True

                                            # Display task request
                                            task_panel = Panel(
                                                Text(query),
                                                title="[bold blue]Task Request[/bold blue]",
                                                border_style="blue",
                                                expand=True
                                            )
                                            live_display.update(task_panel)
                                            # Pause briefly to allow user to see the task
                                            await asyncio.sleep(0.5)

                                        # Use Markdown component to render
                                        markdown_panel = Panel(
                                            Group(
                                                Markdown(collected_text),
                                                status_text
                                            ),
                                            title="[bold green]Final Answer (Streaming...)[/bold green]",
                                            border_style="green",
                                            expand=True
                                        )
                                        live_display.update(markdown_panel)
                                    except Exception:
                                        # If rendering fails, use plain text display
                                        text_panel = Panel(
                                            collected_text,
                                            title="[bold green]Final Answer (Streaming...)[/bold green]",
                                            border_style="green",
                                            expand=True
                                        )
                                        live_display.update(text_panel)

                            # After processing, set the final result
                            final_result_str = collected_text

                            # Try to render JSON content
                            render_success = render_json_as_markdown(
                                final_result_str,
                                console
                            )

                            # If JSON rendering fails, but the content is Markdown, try rendering Markdown
                            if not render_success:
                                try:
                                    # Check if it contains common Markdown features
                                    is_likely_markdown = any([
                                        '##' in final_result_str,  # Title
                                        '*' in final_result_str,   # List or emphasis
                                        '```' in final_result_str, # Code block
                                        '>' in final_result_str,   # Quote
                                        # Table
                                        '|' in final_result_str and
                                        '-|-' in final_result_str 
                                    ])

                                    if is_likely_markdown:
                                        console.print(
                                            "\n[bold cyan]Final Answer Report:[/bold cyan]"
                                        )
                                        console.print(Panel(
                                            Markdown(final_result_str),
                                            title="[bold green]Markdown Content[/bold green]",
                                            border_style="green"
                                        ))
                                except Exception as e:
                                    console.print(f"[yellow]Error rendering Markdown: {e}[/yellow]")
                    else:
                        # Other cases (possibly FinalAnswerStep or other types)
                        type_name = type(sync_generator)
                        warn_msg = (
                            f"Warning: Unexpected return type from agent.run: "
                            f"{type_name}"
                        )
                        console.print(Text(warn_msg, style="yellow"))
                        # Try to convert to string
                        final_result_str = str(sync_generator)

                except Exception as run_error:
                    console.print(f"[bold red]Error during run: {run_error}[/bold red]")
                    console.print(traceback.format_exc())
            else:
                # Non-streaming mode progress display
                progress.update(
                    thinking_task_id,
                    description="[bold cyan]🤔 Thinking...", 
                    status="Processing your query"
                )
                final_result_str = await loop.run_in_executor(
                    None, agent_instance.run, query, False
                )
                progress.stop()

    except Exception as e:
        console.print(
            Text(f"Error processing query '{query[:50]}...'", style="bold red")
        )
        console.print(Text(f"Error details: {e}", style="red"))
        console.print(traceback.format_exc())  # More detailed stack trace
        return

    # --- Get Actual Token Counts After Run ---
    token_counts = {}
    if hasattr(agent_instance, 'model') and hasattr(agent_instance.model, 'get_token_counts'):
        try:
            token_counts = agent_instance.model.get_token_counts()
            actual_input_tokens = token_counts.get("input_token_count")
            actual_output_tokens = token_counts.get("output_token_count")
        except Exception as token_error:
             console.print(
                 Text(f"Warning: Could not retrieve token counts from model: {token_error}", style="yellow")
             )


    # Final output display
    if final_result_str:
        last_response_md.append(final_result_str)

        # Try to render JSON formatted results
        rendered = render_json_as_markdown(final_result_str, console)

        # If JSON rendering fails, but the content is Markdown, try rendering Markdown
        if not rendered:
            try:
                # Check if it contains common Markdown features
                is_likely_markdown = any([
                    '##' in final_result_str,  # Title
                    '*' in final_result_str,   # List or emphasis
                    '```' in final_result_str, # Code block
                    '>' in final_result_str,   # Quote
                    # Table
                    '|' in final_result_str and
                    '-|-' in final_result_str
                ])

                if is_likely_markdown:
                    console.print(
                        "\n[bold cyan]Final Answer Report:[/bold cyan]"
                    )
                    console.print(Panel(
                        Markdown(final_result_str),
                        title="[bold green]Markdown Content[/bold green]",
                        border_style="green"
                    ))
                    rendered = True
            except Exception as e:
                console.print(f"[yellow]Error rendering Markdown: {e}[/yellow]")

        # Display generation statistics if streaming mode is used
        # Now also display API token counts if available
        stats_text = Text()
        if use_stream and start_time and token_count > 0:
             # Display streamed token count (if different logic is desired)
            total_time = time.time() - start_time
            tokens_per_second = token_count / total_time if total_time > 0 else 0

            stats_text.append("\n[Streaming Stats] ", style="dim")
            stats_text.append(f"{token_count} streamed tokens", style="cyan")
            stats_text.append(" in ", style="dim")
            stats_text.append(f"{total_time:.2f}s", style="yellow")
            tokens_per_sec_text = f" ({tokens_per_second:.1f} tokens/sec)"
            stats_text.append(tokens_per_sec_text, style="green")

        # Display API token counts if available
        if actual_input_tokens is not None or actual_output_tokens is not None:
            stats_text.append("\n[API Token Usage] ", style="dim")
            if actual_input_tokens is not None:
                 stats_text.append(f"Input: {actual_input_tokens}", style="cyan")
            if actual_output_tokens is not None:
                 if actual_input_tokens is not None:
                      stats_text.append(" | ", style="dim")
                 stats_text.append(f"Output: {actual_output_tokens}", style="cyan")


            # If there are planning steps, display
            if planning_counter > 0:
                 # Add separator if previous stats were printed
                 if stats_text:
                      stats_text.append(" | ", style="dim")
                 else:
                      stats_text.append("\n", style="dim") # Start new line if no stats yet
                 stats_text.append(f"{planning_counter} planning steps", style="orange")

            # Print stats if any were added
            if stats_text:
                 console.print(stats_text)


            # Display status overview (if any)
            if any(state_summary.values()):
                status_text = Text("\n[State Summary] ", style="cyan")
                if state_summary["visited_urls"] > 0:
                    status_text.append(f"URLs visited: {state_summary['visited_urls']} | ", style="cyan")
                if state_summary["search_queries"] > 0:
                    status_text.append(f"Search queries: {state_summary['search_queries']} | ", style="cyan")
                if state_summary["search_depth"] > 0:
                    status_text.append(f"Search depth: {state_summary['search_depth']}", style="cyan")
                console.print(status_text)

        # If not streaming mode or streaming mode not displayed correctly, display final answer
        if not use_stream and not rendered:
            console.print("\n[bold green]Answer:[/bold green]")

            # Handle dictionary results (from EnhancedFinalAnswerTool)
            if isinstance(final_result_str, dict):
                # Extract content field if it exists
                if "content" in final_result_str:
                    markdown_content = final_result_str["content"]
                else:
                    # Fall back to JSON string representation
                    markdown_content = json.dumps(final_result_str, ensure_ascii=False, indent=2)

                # Try to display with standard Markdown
                console.print(Panel(
                    Markdown(markdown_content),
                    title="Final Answer",
                    border_style="green"
                ))
            else:
                # Original behavior for string content
                console.print(Panel(
                    Markdown(final_result_str),
                    title="Final Answer",
                    border_style="green"
                ))
    elif not use_stream:
        # Only display this error in non-streaming mode
        console.print(
            Text("Error: No final answer generated.", style="bold red")
        )


async def run_interactive_cli(
    agent_instance,
    args: argparse.Namespace,
    console: Console
):
    """
    Run the interactive CLI loop
    """
    history_path = Path.home() / ".deepsearch-agent-history.txt"
    session = PromptSession(history=FileHistory(str(history_path)))
    multiline = False
    last_response_md: List[str] = []  # To store the last response

    while True:
        try:
            # auto_suggest = AutoSuggestFromHistory() # Add suggestions
            prompt_text = "DeepSearchAgent ➤ "
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
                break  # Exit loop if exit code is returned
        else:
            await process_query_async(
                text, agent_instance, args.verbose, console, last_response_md
            )
    return 0  # Indicate normal exit


def select_agent_type(console: Console) -> str:
    """Interactively select the agent type"""
    console.print(Panel(
        "Please select the agent type:\n\n" +
        "[1] [cyan]React[/cyan] - Standard agent (JSON tool call mode)\n" +
        "    Suitable for simple queries, will think about next steps "
        "after each tool call\n\n" +
        "[2] [cyan]CodeAct[/cyan] - Deep search agent "
        "(Python code execution mode)\n" +
        "    Suitable for complex queries, can write Python code "
        "to implement more flexible search strategies",
        title="[bold blue]Agent Type Selection[/bold blue]",
        border_style="blue",
    ))

    while True:
        choice = input("Please input the option number [1/2]: ").strip()
        if choice == "1":
            return "react"
        elif choice == "2":
            return "codact"
        else:
            console.print("[red]Invalid choice, please input 1 or 2[/red]")


# --- Main Interface --- #

def main():
    """
    CLI main entry point
    """
    console = Console()

    parser = argparse.ArgumentParser(
        description=(
            'Run DeepSearch-AgentTeam ReAct-CodeAct deep search agent '
            '(iterative search mode) CLI'
        )
    )
    parser.add_argument(
        '--orchestrator-model',
        default=os.getenv(
            "LITELLM_ORCHESTRATOR_MODEL_ID",
            get_config_value(
                APP_CONFIG,
                'models.orchestrator_id',
                get_config_value(APP_CONFIG, 'models.orchestrator_id')
            )
        ),
        dest='orchestrator_id',
        help='Orchestrator language model name (LiteLLM variable)'
    )
    parser.add_argument(
        '--search-model',
        default=os.getenv(
            "LITELLM_SEARCH_MODEL_ID",
            get_config_value(
                APP_CONFIG,
                'models.search_id',
                get_config_value(APP_CONFIG, 'models.search_id')
            )
        ),
        dest='search_id',
        help='Search model name (LiteLLM variable)'
    )
    parser.add_argument(
        '--reranker',
        default=os.getenv(
            "RERANKER_TYPE",  # Allow environment variable override
            get_config_value(
                APP_CONFIG,
                'models.reranker_type',
                "jina-reranker-m0"
            )
        ),
        dest='reranker_type',  # Match config key
        help="Reranking model type (e.g. 'jina-reranker-m0')"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        # default load from config, allow CLI override
        default=get_config_value(
            APP_CONFIG, 'agents.common.verbose_tool_callbacks', False
        ),
        help='Display detailed processing (including tool call logs)'
    )
    parser.add_argument(
        '--enable-streaming',
        action='store_true',
        # Read default from config
        default=get_config_value(
            APP_CONFIG, 'agents.codact.enable_streaming', False
        ),
        help='Enable streaming mode for final answer generation'
    )
    parser.add_argument(
        '--react-planning-interval',
        type=int,
        default=os.getenv(
            "REACT_PLANNING_INTERVAL", 
            get_config_value(
                APP_CONFIG, 'agents.react.planning_interval', 7
            )
        ),
        help='Interval for React agent planning steps'
    )
    parser.add_argument(
        '--planning-interval',
        type=int,
        default=os.getenv(
            "PLANNING_INTERVAL", 
            get_config_value(
                APP_CONFIG, 'agents.codact.planning_interval', 5
            )
        ),
        help='Interval for CodeAct agent planning steps'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Run a single query directly without starting the interactive CLI'
    )
    parser.add_argument(
        '--agent-type',
        choices=['react', 'codact'],
        default=os.getenv(
            "DEEPSEARCH_AGENT_MODE",  # Allow environment variable override
            get_config_value(
                APP_CONFIG, 'service.deepsearch_agent_mode', 'codact'
            )
        ).lower(),
        help=(
            'Select the agent type: react (JSON tool call) or '
            'codact (Python code execution)'
        )
    )
    parser.add_argument(
        '--executor-type',
        choices=['local', 'docker', 'e2b'],
        default=os.getenv(
            "CODE_EXECUTOR_TYPE",  # Allow environment variable override
            get_config_value(
                APP_CONFIG, 'agents.codact.executor_type', 'local'
            )
        ),
        help='CodeAct agent code executor type'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=os.getenv(
            "MAX_STEPS",  # Allow environment variable override
            get_config_value(
                APP_CONFIG, 'agents.codact.max_steps', 25
            )
        ),
        help=(
            'Maximum number of steps for agent execution '
            '(CodeAct recommends higher values)'
        )
    )
    parser.add_argument(
        '--verbosity-level',
        type=int,
        default=os.getenv(
            "VERBOSITY_LEVEL",  # Allow environment variable override
            get_config_value(
                APP_CONFIG, 'agents.codact.verbosity_level', 1
            )
        ),
        help='CodeAct agent log level (0=DEBUG, 1=INFO)'
    )
    parser.add_argument(
        '--no-interactive',
        action='store_true',
        help='Disable interactive agent type selection, use --agent-type'
    )

    args = parser.parse_args()

    # --- Load API Keys ---
    litellm_master_key = get_api_key("LITELLM_MASTER_KEY")
    serper_api_key = get_api_key("SERPER_API_KEY")
    jina_api_key = get_api_key("JINA_API_KEY")
    wolfram_app_id = get_api_key("WOLFRAM_ALPHA_APP_ID")
    litellm_base_url = get_api_key("LITELLM_BASE_URL")

    # Ensure configuration value matches global setting
    global CODACT_ENABLE_STREAMING
    CODACT_ENABLE_STREAMING = args.enable_streaming

    # Update planning interval global variables
    global REACT_PLANNING_INTERVAL, CODACT_PLANNING_INTERVAL
    REACT_PLANNING_INTERVAL = args.react_planning_interval
    CODACT_PLANNING_INTERVAL = args.planning_interval

    # If not using --no-interactive and no single query specified, provide interactive selection
    if not args.no_interactive and not args.query:
        # If command line does not explicitly specify agent type, execute interactive selection
        if args.agent_type == parser.get_default('agent_type'):
            args.agent_type = select_agent_type(console)
            # Update display to inform user that selection has taken effect
            console.print(
                f"[green]Selected:[/green] "
                f"[cyan]{args.agent_type.upper()}[/cyan] agent mode"
            )

    try:
        args.max_steps = int(args.max_steps)
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid max_steps value "
            f"'{args.max_steps}'. Using default value 25."
        )
        args.max_steps = 25
    try:
        args.verbosity_level = int(args.verbosity_level)
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid verbosity_level value "
            f"'{args.verbosity_level}'. Using default value 1."
        )
        args.verbosity_level = 1

    # --- Create Agent --- #
    try:
        # Only pass cli_console when verbose mode is enabled
        cli_console_for_agent = console if args.verbose else None

        if args.agent_type == 'react':
            agent_instance = create_react_agent(
                orchestrator_model_id=args.orchestrator_id,
                search_model_name=args.search_id,
                reranker_type=args.reranker_type,
                verbose_tool_callbacks=args.verbose,
                cli_console=cli_console_for_agent,
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
                enable_streaming=args.enable_streaming,
                planning_interval=args.react_planning_interval
            )
            if agent_instance is None:
                console.print(
                    "[bold red]Error:[/bold red] "
                    "Unable to initialize React Agent, "
                    "missing necessary API keys."
                )
                exit(1)
        else:  # codact
            agent_instance = create_codact_agent(
                orchestrator_model_id=args.orchestrator_id,
                search_model_name=args.search_id,
                reranker_type=args.reranker_type,
                verbose_tool_callbacks=args.verbose,
                cli_console=cli_console_for_agent,
                executor_type=args.executor_type,
                max_steps=args.max_steps,
                verbosity_level=args.verbosity_level,
                # Pass executor_kwargs and imports (if needed)
                executor_kwargs=CODACT_EXECUTOR_KWARGS,
                additional_authorized_imports=CODACT_ADDITIONAL_IMPORTS,
                # Pass API Keys
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
                enable_streaming=args.enable_streaming,
                planning_interval=args.planning_interval
            )
            if agent_instance is None:
                console.print(
                    "[bold red]Error:[/bold red] "
                    "Unable to initialize CodeAct Agent, "
                    "missing necessary API keys."
                )
                exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        exit(1)
    except Exception:
        console.print(
            "[bold red]Error:[/bold red] Unknown error occurred "
            "while creating Agent"
        )
        console.print(traceback.format_exc())
        exit(1)

    display_welcome(args, console)

    # --- Run Mode --- #
    if args.query:
        console.print(f"[yellow]Running single query:[/yellow] {args.query}")
        # Store list of last responses for single query mode
        last_response_md_single: List[str] = []
        # Run single query processing in event loop
        try:
            # Use asyncio.run() to manage event loop
            asyncio.run(process_query_async(
                args.query, agent_instance, args.verbose,
                console, last_response_md_single
            ))
            exit_code = 0
        except KeyboardInterrupt:
            console.print("[dim]Received interrupt signal.[/dim]")
            exit_code = 1
        except Exception:
            console.print(
                "[bold red]Error:[/bold red] Unexpected error occurred "
                "while processing single query"
            )
            exit_code = 1
        exit(exit_code)

    else:
        # Start interactive loop
        try:
            exit_code = asyncio.run(
                run_interactive_cli(agent_instance, args, console)
            )
            exit(exit_code)
        except KeyboardInterrupt:
            console.print("[dim]Interactive session interrupted.[/dim]")
            exit(1)
        except Exception:
            console.print(
                "[bold red]Error:[/bold red] Unexpected error occurred "
                "while running interactive CLI"
            )
            console.print(traceback.format_exc())
            exit(1)


if __name__ == "__main__":
    main()

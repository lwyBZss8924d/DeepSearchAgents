import os
import argparse
import traceback
import asyncio
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from .agent import create_react_agent
from .codact_agent import create_codact_agent
from .config_loader import APP_CONFIG, get_config_value, get_api_key

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.status import Status
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

load_dotenv()


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
            description = description_content if description_content else ""
        else:
            description_section = readme_content.split("## Description")
            if len(description_section) > 1:
                description_content = description_section[1].split(
                    "##"
                )[0].strip()
                description = description_content if description_content else ""

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
        config_text += (
            f"\nExecutor Type: [cyan]{args.executor_type}[/cyan]\n" 
            f"Max Steps: [cyan]{args.max_steps}[/cyan]\n"
            f"Verbosity Level: [cyan]{args.verbosity_level}[/cyan]"
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
        "  • Search Google OpenAI and Anthropic's latest products, LLM models, "
        "technologies, papers, search & analyze then summarize it."
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


async def process_query_async(
    query: str,
    agent_instance,
    verbose_mode: bool,
    console: Console,
    last_response_md: List[str]  # Use list to pass by reference
):
    """
    Asynchronously process the query and display the result
    """
    status = Status("[cyan]Thinking...[/cyan]", console=console)
    live_params = {
        "console": console,
        "refresh_per_second": 10,
        "vertical_overflow": "visible"
    }
    live = Live(status, **live_params)
    last_response_md.clear()  # Clear previous response

    try:
        with live:
            # Use run_in_executor for the blocking agent.run call
            loop = asyncio.get_running_loop()
            result_str = await loop.run_in_executor(
                None, agent_instance.run, query
            )

        last_response_md.append(result_str)

        console.print("\n[bold green]Answer:[/bold green]")
        console.print(Panel(
            Markdown(result_str),
            title="Final Answer",
            border_style="green"
        ))

    except Exception:
        # Ensure live display stops before printing error
        live.stop()
        console.print(
            f"[bold red]Error processing query ' {query[:50]}...'[/bold red]"
        )
        console.print(traceback.format_exc())  # More detailed traceback
    finally:
        if live.is_started:
            live.stop()


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
            "LITELLM_ORCHESTRATOR_MODEL_ID",  # Allow environment variable override
            get_config_value(
                APP_CONFIG,
                'models.orchestrator_id',
                "openrouter/openai/gpt-4.1"
            )
        ),
        dest='orchestrator_id',  # Match config key
        help='Orchestrator language model name (e.g. LiteLLM compatible ID)'
    )
    parser.add_argument(
        '--model-name',
        default=os.getenv(
            "LITELLM_SEARCH_MODEL_ID",  # Allow environment variable override
            get_config_value(
                APP_CONFIG,
                'models.search_id',
                get_config_value(APP_CONFIG, 'models.orchestrator_id')
            )
        ),
        dest='search_id',  # Match config key
        help=(
            'Search model name (mainly determined by Agent internal tools, '
            'may only be used for display)'
        )
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
        # default load from config, allow CLI override (bool doesn't need env var)
        default=get_config_value(
            APP_CONFIG, 'agents.common.verbose_tool_callbacks', False
        ),
        help='Display detailed processing (including tool call logs)'
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
        help='Disable interactive agent type selection, use --agent-type directly'
    )

    args = parser.parse_args()

    # --- Load API Keys --- 
    litellm_master_key = get_api_key("LITELLM_MASTER_KEY")
    serper_api_key = get_api_key("SERPER_API_KEY")
    jina_api_key = get_api_key("JINA_API_KEY")
    wolfram_app_id = get_api_key("WOLFRAM_ALPHA_APP_ID")
    litellm_base_url = get_api_key("LITELLM_BASE_URL")

    # If not using --no-interactive and no single query specified, provide interactive selection
    if not args.no_interactive and not args.query:
        # If command line doesn't explicitly specify agent type, perform interactive selection
        if args.agent_type == parser.get_default('agent_type'):
            args.agent_type = select_agent_type(console)
            # Update display to let user know selection has taken effect
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
        # Pass cli_console only if verbose is enabled
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
            )
            if agent_instance is None:
                console.print(
                    "[bold red]Error:[/bold red] "
                    "Unable to initialize React Agent, missing necessary API keys."
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
                # Pass executor_kwargs and imports (if needed from CLI config)
                # executor_kwargs=...,
                # additional_authorized_imports=...,
                # Pass API Keys
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
            )
            if agent_instance is None:
                console.print(
                    "[bold red]Error:[/bold red] "
                    "Unable to initialize CodeAct Agent, missing necessary API keys."
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
        # Need a way to store the last response for single query mode
        last_response_md_single: List[str] = []
        # Run the single query processing within an event loop
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

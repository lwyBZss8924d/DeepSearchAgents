import os
import argparse
import traceback
import asyncio
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
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
    # 创建状态显示
    spinner = SpinnerColumn()
    task_description = TextColumn("[bold blue]{task.description}")
    bar_column = BarColumn(bar_width=None)
    status_column = TextColumn("[cyan]{task.fields[status]}")
    time_column = TimeElapsedColumn()
    
    last_response_md.clear()  # Clear previous response
    final_result_str = None  # Initialize final result string
    
    # 收集流式输出的统计数据
    token_count = 0
    start_time = None
    
    # 跟踪规划阶段和状态变量
    planning_counter = 0
    last_planning_step = None
    
    # 状态变量跟踪数据
    state_summary = {
        "visited_urls": 0,
        "search_queries": 0,
        "search_depth": 0
    }

    # 检查代理是否是流式类型
    is_streaming_agent = (
        hasattr(agent_instance, '__class__') and
        (agent_instance.__class__.__name__ == 'StreamingCodeAgent' or
         agent_instance.__class__.__name__ == 'StreamingReactAgent' or
         agent_instance.__class__.__name__ == 'StreamingFinalAnswerWrapper')
    )
    
    # 只有是流式代理类型的情况下才启用流式模式
    use_stream = is_streaming_agent and CODACT_ENABLE_STREAMING

    try:
        # 使用Progress显示思考和处理阶段
        with Progress(
            spinner, task_description, bar_column, 
            status_column, time_column,
            console=console, transient=True,
            expand=True
        ) as progress:
            # 显示思考状态
            thinking_task_id = progress.add_task(
                "[bold cyan]Thinking...", 
                total=None, 
                status="Processing your query"
            )
            
            # Use run_in_executor for the potentially blocking agent.run call
            loop = asyncio.get_running_loop()

            if use_stream:
                # 更新状态文本
                progress.update(
                    thinking_task_id, 
                    description="[bold cyan]Processing...", 
                    status="Executing agent steps"
                )
                
                # Get the synchronous generator from the executor
                try:
                    sync_generator = await loop.run_in_executor(
                        None, agent_instance.run, query, True
                    )
                    
                    # 走到这里说明思考阶段已经完成，关闭Progress显示，准备显示流式结果
                    progress.stop()
                    
                    # 检查返回类型是同步或异步迭代器还是普通字符串
                    if isinstance(sync_generator, str):
                        # 如果是字符串，直接作为最终结果
                        final_result_str = sync_generator
                    elif (hasattr(sync_generator, '__iter__') and
                          not hasattr(sync_generator, '__aiter__')):
                        # 流式处理
                        console.print("\n[bold green]Generating Final Answer...[/bold green]")
                        
                        # 使用Live组件进行实时流式更新
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
                            
                            # 定义一个安全的获取生成器下一个值的函数
                            async def get_next_safely():
                                try:
                                    def safe_next(gen):
                                        try:
                                            return next(gen), True
                                        except StopIteration:
                                            return None, False
                                    
                                    result, has_next = await loop.run_in_executor(
                                        None, safe_next, sync_generator
                                    )
                                    return result, has_next
                                except Exception as e:
                                    console.print(f"[yellow]获取值时出错: {e}[/yellow]")
                                    return None, False
                            
                            # 使用while循环和安全函数处理生成器
                            while True:
                                chunk, has_next = await get_next_safely()
                                if not has_next:
                                    break
                                
                                chunks.append(chunk)
                                
                                # 检查是否是规划步骤
                                if hasattr(chunk, 'plan') and chunk.plan:
                                    planning_counter += 1
                                    last_planning_step = chunk
                                    # 显示规划阶段
                                    planning_panel = Panel(
                                        Markdown(chunk.plan),
                                        title=f"[bold orange]规划阶段 #{planning_counter}[/bold orange]",
                                        border_style="orange",
                                        expand=True
                                    )
                                    live_display.update(planning_panel)
                                    # 短暂暂停，让用户注意到规划阶段
                                    await asyncio.sleep(0.5)
                                    continue
                                
                                # 尝试更新状态变量
                                if hasattr(agent_instance, 'state'):
                                    state = agent_instance.state
                                    if isinstance(state, dict):
                                        if 'visited_urls' in state and isinstance(state['visited_urls'], set):
                                            state_summary['visited_urls'] = len(state['visited_urls'])
                                        if 'search_queries' in state and isinstance(state['search_queries'], list):
                                            state_summary['search_queries'] = len(state['search_queries'])
                                        if 'search_depth' in state:
                                            state_summary['search_depth'] = state['search_depth']
                                            
                                # 尝试从chunk中提取内容
                                try:
                                    # 提取内容 - litellm的stream chunk格式
                                    content = chunk.choices[0].delta.content
                                    if content:
                                        token_count += 1
                                        collected_text += content
                                        
                                        # 尝试解析JSON结构化输出
                                        try:
                                            # 检查是否是JSON结构
                                            if collected_text.strip().startswith('{') and collected_text.strip().endswith('}'):
                                                try:
                                                    json_data = json.loads(collected_text)
                                                    # 如果成功解析JSON，创建表格显示
                                                    if isinstance(json_data, dict) and 'title' in json_data and 'content' in json_data:
                                                        from rich.table import Table
                                                        
                                                        table = Table(show_header=True, header_style="bold green")
                                                        table.add_column("字段", style="cyan", no_wrap=True)
                                                        table.add_column("内容", style="green")
                                                        
                                                        # 添加标题和内容行
                                                        table.add_row("标题", json_data.get('title', ''))
                                                        table.add_row("内容", Text(json_data.get('content', '')[:200] + 
                                                                                "..." if len(json_data.get('content', '')) > 200 else ''))
                                                        
                                                        # 添加来源行
                                                        if 'sources' in json_data and json_data['sources']:
                                                            table.add_row("来源", "\n".join(json_data['sources'][:3]) + 
                                                                        ("..." if len(json_data['sources']) > 3 else ''))
                                                        
                                                        # 添加置信度行
                                                        if 'confidence' in json_data:
                                                            confidence_text = f"{json_data['confidence']:.2f}"
                                                            table.add_row("置信度", confidence_text)
                                                        
                                                        # 创建包含表格的面板
                                                        structured_panel = Panel(
                                                            Group(
                                                                table,
                                                                Text("\n原始JSON输出:", style="dim"),
                                                                Markdown("```json\n" + json.dumps(json_data, indent=2, ensure_ascii=False) + "\n```")
                                                            ),
                                                            title="[bold green]结构化输出[/bold green]",
                                                            border_style="green",
                                                            expand=True
                                                        )
                                                        live_display.update(structured_panel)
                                                        continue
                                                except json.JSONDecodeError:
                                                    # 不是完整的JSON，继续常规显示
                                                    pass
                                        except Exception:
                                            # JSON处理出错，忽略并继续常规显示
                                            pass
                                        
                                        # 更新流式显示
                                        try:
                                            # 添加状态概览
                                            status_text = Text()
                                            if any(state_summary.values()):
                                                status_text.append("\n\n状态概览: ", style="bold cyan")
                                                if state_summary["visited_urls"] > 0:
                                                    status_text.append(f"已访问URL: {state_summary['visited_urls']} | ", style="cyan")
                                                if state_summary["search_queries"] > 0:
                                                    status_text.append(f"搜索查询: {state_summary['search_queries']} | ", style="cyan")
                                                if state_summary["search_depth"] > 0:
                                                    status_text.append(f"搜索深度: {state_summary['search_depth']}", style="cyan")
                                                                                                    
                                            # 使用Markdown组件渲染
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
                                            # 如果渲染失败，使用纯文本显示
                                            text_panel = Panel(
                                                collected_text,
                                                title="[bold green]Final Answer (Streaming...)[/bold green]",
                                                border_style="green",
                                                expand=True
                                            )
                                            live_display.update(text_panel)
                                except (AttributeError, KeyError, IndexError):
                                    # 如果不是标准格式，尝试其他方式提取内容
                                    pass
                            
                            # 处理完成后设置最终结果
                            final_result_str = collected_text
                    else:
                        # 其他情况（可能是FinalAnswerStep或其他类型）
                        type_name = type(sync_generator)
                        warn_msg = (
                            f"Warning: Unexpected return type from agent.run: "
                            f"{type_name}"
                        )
                        console.print(Text(warn_msg, style="yellow"))
                        # 尝试转换为字符串
                        final_result_str = str(sync_generator)
                        
                except Exception as run_error:
                    console.print(f"[bold red]Error during run: {run_error}[/bold red]")
                    console.print(traceback.format_exc())
            else:
                # 非流式模式下的进度显示
                progress.update(
                    thinking_task_id, 
                    description="[bold cyan]Thinking...", 
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
        console.print(traceback.format_exc())  # 更详细的堆栈跟踪
        return
   
    # 最终输出显示
    if final_result_str:
        last_response_md.append(final_result_str)
        
        # 显示生成统计如果使用了流式模式
        if use_stream and start_time and token_count > 0:
            total_time = time.time() - start_time
            tokens_per_second = token_count / total_time if total_time > 0 else 0
            
            stats_text = Text()
            stats_text.append("\n[Statistics] ", style="dim")
            stats_text.append(f"{token_count} tokens", style="cyan")
            stats_text.append(" generated in ", style="dim")
            stats_text.append(f"{total_time:.2f}s", style="yellow")
            
            tokens_per_sec_text = f" ({tokens_per_second:.1f} tokens/sec)"
            stats_text.append(tokens_per_sec_text, style="green")
            
            # 如果有规划阶段，显示
            if planning_counter > 0:
                stats_text.append(f" | {planning_counter} planning steps", style="orange")
            
            console.print(stats_text)
            
            # 显示状态概览（如果有）
            if any(state_summary.values()):
                status_text = Text("\n[State Summary] ", style="cyan")
                if state_summary["visited_urls"] > 0:
                    status_text.append(f"URLs visited: {state_summary['visited_urls']} | ", style="cyan")
                if state_summary["search_queries"] > 0:
                    status_text.append(f"Search queries: {state_summary['search_queries']} | ", style="cyan")
                if state_summary["search_depth"] > 0:
                    status_text.append(f"Search depth: {state_summary['search_depth']}", style="cyan")
                console.print(status_text)
        
        # 如果不是流式模式或者流式模式没有正确显示，则显示最终答案
        if not use_stream:
            console.print("\n[bold green]Answer:[/bold green]")
            
            # 尝试解析结构化JSON输出
            try:
                # 检查是否是JSON结构
                if final_result_str.strip().startswith('{') and final_result_str.strip().endswith('}'):
                    try:
                        json_data = json.loads(final_result_str)
                        # 如果成功解析JSON，创建表格显示
                        if isinstance(json_data, dict) and 'title' in json_data and 'content' in json_data:
                            from rich.table import Table
                            
                            table = Table(show_header=True, header_style="bold green")
                            table.add_column("Field", style="cyan", no_wrap=True)
                            table.add_column("Content", style="green")
                            
                            # 添加标题和内容行
                            table.add_row("Title", json_data.get('title', ''))
                            table.add_row("Content", Text(json_data.get('content', '')[:200] + 
                                                        "..." if len(json_data.get('content', '')) > 200 else ''))
                            
                            # 添加来源行
                            if 'sources' in json_data and json_data['sources']:
                                table.add_row("Sources", "\n".join(json_data['sources'][:3]) + 
                                            ("..." if len(json_data['sources']) > 3 else ''))
                            
                            # 添加置信度行
                            if 'confidence' in json_data:
                                confidence_text = f"{json_data['confidence']:.2f}"
                                table.add_row("Confidence", confidence_text)
                            
                            # 创建包含表格的面板
                            console.print(Panel(
                                Group(
                                    table,
                                    Text("\nRaw JSON output:", style="dim"),
                                    Markdown("```json\n" + json.dumps(json_data, indent=2, ensure_ascii=False) + "\n```")
                                ),
                                title="[bold green]Structured Output[/bold green]",
                                border_style="green"
                            ))
                            return
                    except json.JSONDecodeError:
                        # 不是完整的JSON，继续常规显示
                        pass
            except Exception:
                # JSON处理出错，忽略并继续常规显示
                pass
            
            # 标准Markdown显示
            console.print(Panel(
                Markdown(final_result_str),
                title="Final Answer",
                border_style="green"
            ))
    elif not use_stream:
        # 仅在非流式模式下显示此错误
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

    # 确保配置值与全局设置一致
    global CODACT_ENABLE_STREAMING
    CODACT_ENABLE_STREAMING = args.enable_streaming

    # 如果在命令行中没有使用 --no-interactive，并且没有指定单个查询，则提供交互式选择
    if not args.no_interactive and not args.query:
        # 如果命令行未明确指定代理类型，则执行交互式选择
        if args.agent_type == parser.get_default('agent_type'):
            args.agent_type = select_agent_type(console)
            # 更新显示，让用户知道选择已生效
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
        # 仅在启用详细模式时传递 cli_console
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
                enable_streaming=args.enable_streaming,  # 传递流式参数
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
                # 传递 executor_kwargs 和 imports（如果需要）
                # executor_kwargs=...,
                # additional_authorized_imports=...,
                # 传递 API Keys
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
                enable_streaming=args.enable_streaming,  # 传递流式参数
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
        # 存储单个查询模式的最后响应的列表
        last_response_md_single: List[str] = []
        # 在事件循环中运行单个查询处理
        try:
            # 使用 asyncio.run() 管理事件循环
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
        # 启动交互式循环
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

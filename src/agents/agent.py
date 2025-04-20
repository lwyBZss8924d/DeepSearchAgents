from typing import List, Optional
from smolagents import (
    LiteLLMModel, ToolCallingAgent, Tool
)
from .tools import (
    SearchLinksTool, ReadURLTool, ChunkTextTool,
    EmbedTextsTool, RerankTextsTool,
    EnhancedWolframAlphaTool, FinalAnswerTool
)
from .prompts import REACT_PROMPT
from .streaming_models import StreamingLiteLLMModel
from .streaming_agents import StreamingReactAgent


def create_react_agent(
    orchestrator_model_id: str,
    search_model_name: str,
    reranker_type: str,
    verbose_tool_callbacks: bool = True,
    litellm_master_key: Optional[str] = None,
    litellm_base_url: Optional[str] = None,
    serper_api_key: Optional[str] = None,
    jina_api_key: Optional[str] = None,
    wolfram_app_id: Optional[str] = None,
    cli_console=None,
    enable_streaming: bool = False,  # 添加流式输出支持的参数
    # Removed unused default parameters
):
    """
    creates and configures a React agent with fine-grained search
    and processing tools.

    Args:
        # Configuration Parameters
        orchestrator_model_id (str):
            The ID of the LLM model used for orchestration.
        search_model_name (str):
            The name of the search model to use.
        reranker_type (str):
            The type of reranker to use.
        verbose_tool_callbacks (bool):
            Whether to enable verbose tool callbacks.
        # API Keys
        litellm_master_key (Optional[str]):
            The LiteLLM Master Key.
        litellm_base_url (Optional[str]):
            The LiteLLM Base URL.
        serper_api_key (Optional[str]):
            The Serper API Key.
        jina_api_key (Optional[str]):
            The Jina API Key.
        wolfram_app_id (Optional[str]):
            The WolframAlpha App ID.
        # Other
        cli_console:
            Optional rich.console.Console for verbose CLI output.
        enable_streaming (bool): 
            Whether to enable streaming for agent responses.
            If True, all agent steps (including final answer) will be streamed.

    Returns:
        ToolCallingAgent:
            The configured React agent instance.
            Returns None if essential keys missing.
    """
    
    # --- API Key Checks (using passed keys) ---

    essential_keys_missing = False
    if not serper_api_key:
        print(
            "ERROR: SERPER_API_KEY is missing. "
            "SearchLinksTool will not work."
        )
        essential_keys_missing = True
    if not jina_api_key:
        print(
            "ERROR: JINA_API_KEY is missing. "
            "ReadURLTool, EmbedTextsTool, RerankTextsTool will not work."
        )
        essential_keys_missing = True
    # WolframAlpha is optional, don't treat as essential
    if not wolfram_app_id:
        print(
            "WARNING: WOLFRAM_ALPHA_APP_ID is missing. "
            "WolframAlphaTool will not work."
        )

    if essential_keys_missing:
        return None

    print(
        f"  (Agent Creation) Received search_model_name: {search_model_name}"
    )

    # --- Tool Initialization (using passed keys) ---

    agent_tools: List[Tool] = []

    # Serper key checked above
    search_tool = SearchLinksTool(
        serper_api_key=serper_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks,
        # max_results=default_max_sources
        # Pass max_sources if needed
    )
    agent_tools.append(search_tool)

    # Jina key checked above
    read_tool = ReadURLTool(
        jina_api_key=jina_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks,
    )
    chunk_tool = ChunkTextTool(
        cli_console=cli_console,
        verbose=verbose_tool_callbacks,
    )
    embed_tool = EmbedTextsTool(
        jina_api_key=jina_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks,
    )
    rerank_tool = RerankTextsTool(
        jina_api_key=jina_api_key,
        default_model=reranker_type,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks,
    )
    agent_tools.extend([read_tool, chunk_tool, embed_tool, rerank_tool])

    # Wolfram key checked above (optional)
    if wolfram_app_id:
        wolfram_tool = EnhancedWolframAlphaTool(
            app_id=wolfram_app_id,
            cli_console=cli_console,
            verbose=verbose_tool_callbacks
        )
        agent_tools.append(wolfram_tool)

    agent_tools.append(FinalAnswerTool())
    
    # --- 设置规划间隔 ---
    # ReAct代理也应定期重新评估搜索策略
    react_planning_interval = 7  # ReAct代理的规划间隔略大一些
    
    # --- 初始化状态管理 ---
    # 为代理提供结构化的状态跟踪，与CodeAct保持一致
    initial_state = {
        "visited_urls": set(),        # 已访问的URL
        "search_queries": [],         # 已执行的搜索查询
        "key_findings": {},           # 关键发现，按主题索引
        "search_depth": 0,            # 当前搜索深度
        "reranking_history": [],      # 重排序历史
        "content_quality": {}         # URL内容质量评分
    }

    # --- Initialize Model ---
    # 根据是否启用流式模式选择使用哪个模型类
    model_cls = StreamingLiteLLMModel if enable_streaming else LiteLLMModel
    
    model = model_cls(
        model_id=orchestrator_model_id,
        temperature=0.2,
        api_key=litellm_master_key,
        api_base=litellm_base_url
    )

    # --- Initialize React agent ---
    # 根据是否启用流式模式选择使用哪个代理类
    if enable_streaming:
        # 使用流式代理类，确保传递所有必要的提示模板
        react_agent = StreamingReactAgent(
            tools=agent_tools,
            model=model,
            prompt_templates=REACT_PROMPT,  # 包含所有必需的模板
            max_steps=25,  # 可以从配置加载
            verbosity_level=1,  # 可以从配置加载
            planning_interval=react_planning_interval  # 添加规划间隔
        )
        print("Streaming mode: ENABLED - All agent steps will be streamed")
    else:
        # 使用标准代理类
        react_agent = ToolCallingAgent(
            tools=agent_tools,
            model=model,
            prompt_templates=REACT_PROMPT,
            max_steps=25,  # 可以从配置加载
            verbosity_level=1,  # 可以从配置加载
            planning_interval=react_planning_interval  # 添加规划间隔
        )
    
    # 初始化代理状态
    react_agent.state.update(initial_state)

    # 输出日志信息
    agent_type = "StreamingReactAgent" if enable_streaming else "ReactAgent"
    print(
        f"DeepSearch {agent_type} ({orchestrator_model_id}) "
        f"created successfully."
    )
    print(
        f"Configured tools: "
        f"{[tool.name for tool in react_agent.tools.values()]}"
    )
    if react_planning_interval:
        print(f"Planning interval: Every {react_planning_interval} steps")

    return react_agent

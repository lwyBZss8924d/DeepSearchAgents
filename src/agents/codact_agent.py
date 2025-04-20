from typing import List, Optional, Dict, Any
from smolagents import (
    CodeAgent, LiteLLMModel, Tool
)
from .tools import (
    SearchLinksTool,
    ReadURLTool,
    ChunkTextTool,
    EmbedTextsTool,
    RerankTextsTool,
    EnhancedWolframAlphaTool,
    FinalAnswerTool
)
from .prompts import CODE_ACTION_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)


def create_codact_agent(
    orchestrator_model_id: str,
    search_model_name: Optional[str] = None,
    reranker_type: str = "jina-reranker-m0",
    verbose_tool_callbacks: bool = False,
    executor_type: str = "local",
    executor_kwargs: Optional[Dict[str, Any]] = None,
    max_steps: int = 25,
    verbosity_level: int = 1,
    additional_authorized_imports: Optional[List[str]] = None,
    litellm_master_key: Optional[str] = None,
    litellm_base_url: Optional[str] = None,
    serper_api_key: Optional[str] = None,
    jina_api_key: Optional[str] = None,
    wolfram_app_id: Optional[str] = None,
    cli_console=None,
    enable_streaming: bool = False,
):
    """
    Create and configure a CodeAgent with deep search capabilities.

    This agent uses Python code execution mode, not JSON tool calling mode,
    allowing more flexible logic flow and state management. The agent can
    generate Python code to implement complex search strategies, including
    query planning, multi-URL access, content chunking and reranking.

    Args:
        orchestrator_model_id (str): The LLM model ID for orchestration.
        search_model_name (str, optional):
            The search model name (for compatibility).
        reranker_type (str):
            The reranking model type.
        verbose_tool_callbacks (bool):
            Whether tools should output detailed logs.
        executor_type (str):
            The code executor type ("local", "docker" or "e2b").
        executor_kwargs (Dict[str, Any], optional):
            Additional executor parameters.
        max_steps (int):
            The maximum number of steps the agent can execute.
        verbosity_level (int): The agent's log level.
        additional_authorized_imports (List[str], optional):
            Additional authorized imports.
        litellm_master_key (Optional[str]): LiteLLM Master Key.
        litellm_base_url (Optional[str]): LiteLLM Base URL.
        serper_api_key (Optional[str]): Serper API Key.
        jina_api_key (Optional[str]): Jina API Key.
        wolfram_app_id (Optional[str]): WolframAlpha App ID.
        cli_console: Optional rich.console.Console for verbose CLI output.
        enable_streaming (bool): Whether to enable streaming for final answer 
            generation. If True, agent steps will run normally, but the final 
            answer will be streamed token-by-token.

    Returns:
        CodeAgent: The configured DeepSearch agent instance,
        or None if missing required API keys.
    """

    # --- API Key Checks (using passed keys) ---

    essential_keys_missing = False
    if not serper_api_key:
        print("ERROR: "
              "SERPER_API_KEY is missing. "
              "SearchLinksTool will not work.")
        essential_keys_missing = True
    if not jina_api_key:
        print("ERROR: "
              "JINA_API_KEY is missing. "
              "ReadURLTool, EmbedTextsTool, RerankTextsTool will not work.")
        essential_keys_missing = True

    if not wolfram_app_id:
        print("WARNING: "
              "WOLFRAM_ALPHA_APP_ID is missing. "
              "WolframAlphaTool will not work.")

    if essential_keys_missing:
        print("ERROR: "
              "CodeAgent creation failed due to missing required API keys.")
        return None

    # --- Tool Initialization (using passed keys) ---

    # Note: CodeAgent directly calls tools, so we pass instances.
    agent_tools: List[Tool] = []

    search_tool = SearchLinksTool(
        serper_api_key=serper_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks
    )

    read_tool = ReadURLTool(
        jina_api_key=jina_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks
    )

    chunk_tool = ChunkTextTool(
        cli_console=cli_console,
        verbose=verbose_tool_callbacks
    )

    embed_tool = EmbedTextsTool(
        jina_api_key=jina_api_key,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks
    )

    rerank_tool = RerankTextsTool(
        jina_api_key=jina_api_key,
        default_model=reranker_type,
        cli_console=cli_console,
        verbose=verbose_tool_callbacks
    )

    wolfram_tool = None
    if wolfram_app_id:
        wolfram_tool = EnhancedWolframAlphaTool(
            app_id=wolfram_app_id,
            cli_console=cli_console,
            verbose=verbose_tool_callbacks
        )

    final_answer_tool = FinalAnswerTool()

    agent_tools.append(search_tool)
    agent_tools.append(read_tool)
    agent_tools.append(chunk_tool)
    agent_tools.append(embed_tool)
    agent_tools.append(rerank_tool)
    if wolfram_tool:
        agent_tools.append(wolfram_tool)
    agent_tools.append(final_answer_tool)

    # --- Create prompt template dictionary ---
    # Prepare prompt templates for CodeAgent
    # The system prompt is the most critical part,
    # the other templates (planning, managed_agent, final_answer)
    # are less used but provide structure.

    # Create a dictionary of prompt templates with key system_prompt
    prompt_templates_dict = {
        'system_prompt': CODE_ACTION_SYSTEM_PROMPT,
        'planning': {
            'initial_plan': (
                'Based on the task, create a plan to search and gather '
                'information using the available tools. Think about what '
                'steps you need to take and in what order.\n\n{{task}}\n\n'
                '<end_plan>'
            ),
            'update_plan_pre_messages': (
                'Review your progress and update your plan based on what '
                'you have learned so far. Consider what new information you '
                'need and how to obtain it.'
            ),
            'update_plan_post_messages': (
                'Update your plan based on the task and new information. '
                'Decide what steps to take next to complete the task.\n\n'
                '{{task}}\n\n<end_plan>'
            )
        },
        'managed_agent': {
            'task': '{{name}}: {{task}}',
            'report': '{{name}} final report: {{final_answer}}'
        },
        'final_answer': {
            'pre_messages': (
                'You have been working on the following task. Review all '
                'the information you have gathered and provide a '
                'comprehensive final answer.'
            ),
            'post_messages': (
                'Based on all the information you have gathered, provide a '
                'final comprehensive answer to the task: {{task}}'
            )
        }
    }

    # Set default allowed imports, including 'json' for tool output handling
    default_authorized_imports = [
        "json", "re", "collections", "datetime",
        "time", "math", "itertools", "copy"
    ]
    if additional_authorized_imports:
        # Merge and deduplicate allowed imports list
        combined_authorized_imports = list(set(
            default_authorized_imports + additional_authorized_imports
        ))
    else:
        combined_authorized_imports = default_authorized_imports

    # --- 添加grammar支持 ---
    # 为搜索结果和最终答案提供JSON格式的结构化输出
    json_grammar = None
    if reranker_type:  # 如果使用了重排序，添加结构化输出支持
        json_grammar = {
            "json_object": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"}
                }
            }
        }

    # --- 设置规划间隔 ---
    # 深度搜索需要定期重新评估搜索策略
    search_planning_interval = 5  # 每执行5步重新规划一次
    
    # --- 初始化状态管理 ---
    # 为代理提供结构化的状态跟踪
    initial_state = {
        "visited_urls": set(),        # 已访问的URL
        "search_queries": [],         # 已执行的搜索查询
        "key_findings": {},           # 关键发现，按主题索引
        "search_depth": 0,            # 当前搜索深度
        "reranking_history": [],      # 重排序历史
        "content_quality": {}         # URL内容质量评分
    }
    
    # --- Initialize LiteLLM Model ---
    # 创建标准模型用于CodeAgent
    standard_model = LiteLLMModel(
        model_id=orchestrator_model_id,
        temperature=0.2,
        api_key=litellm_master_key,
        api_base=litellm_base_url
    )
    
    # --- Initialize CodeAgent ---
    # 我们始终使用标准的CodeAgent运行代码
    code_agent = CodeAgent(
        tools=agent_tools,
        model=standard_model,
        prompt_templates=prompt_templates_dict,
        additional_authorized_imports=combined_authorized_imports,
        executor_type=executor_type,
        executor_kwargs=executor_kwargs or {},
        max_steps=max_steps,
        verbosity_level=verbosity_level,
        grammar=json_grammar,                   # 添加grammar支持
        planning_interval=search_planning_interval,  # 设置规划间隔
    )
    
    # 初始化代理状态
    code_agent.state.update(initial_state)
    
    # 如果启用流式模式，创建一个包装类来提供流式最终答案功能
    if enable_streaming:
        # 导入需要的模块
        from .streaming_models import StreamingLiteLLMModel
        
        # 创建流式模型用于最终答案
        streaming_model = StreamingLiteLLMModel(
            model_id=orchestrator_model_id,
            temperature=0.2,
            api_key=litellm_master_key,
            api_base=litellm_base_url
        )
        
        # 创建一个包装类，保留原始的代理实例，但重写run方法
        class StreamingFinalAnswerWrapper:
            """包装CodeAct代理，使其在最终答案生成时提供流式输出。

            其他步骤正常执行，只有最终答案会以流式方式输出。
            """

            def __init__(self, agent, model, verbosity_level=None):
                """初始化包装器。

                Args:
                    agent: 包装的CodeAct代理
                    model: 流式输出模型，用于生成最终答案
                    verbosity_level: 日志详细级别
                """
                self.agent = agent
                self.model = model
                
                # 如果代理有verbosity_level属性，保存它
                if hasattr(agent, 'verbosity_level'):
                    self.verbosity_level = agent.verbosity_level
                elif verbosity_level is not None:
                    self.verbosity_level = verbosity_level
                else:
                    self.verbosity_level = 1  # 默认值

            def _convert_stream_to_iterator(self, stream_obj):
                """将LiteLLM的流对象转换为标准的字符串迭代器。
                
                Args:
                    stream_obj: LiteLLM返回的流对象，可能是CustomStreamWrapper
                    
                Returns:
                    Iterator[str]: 产生字符串标记的迭代器
                """
                try:
                    # 尝试直接迭代流对象
                    for token in stream_obj:
                        yield token
                except (TypeError, AttributeError) as e:
                    # 如果对象不支持迭代，尝试获取其内容
                    logger.warning(f"流对象不支持迭代: {e}")
                    try:
                        if hasattr(stream_obj, 'content'):
                            yield stream_obj.content
                        elif hasattr(stream_obj, 'get_content'):
                            yield stream_obj.get_content()
                        elif hasattr(stream_obj, '__str__'):
                            yield str(stream_obj)
                        else:
                            yield "无法从流对象获取内容"
                    except Exception as e:
                        logger.exception(f"处理流对象出错: {e}")
                        yield f"处理流对象时发生错误: {str(e)}"

            def run(self, task, stream=False, **kwargs):
                """运行代理，如果stream=True，则最终答案以流式方式输出。

                Args:
                    task: 要执行的任务
                    stream: 是否启用流式输出
                    **kwargs: 传递给代理的额外参数

                Returns:
                    如果stream=True，返回最终答案的流式输出；否则返回最终答案字符串
                """
                # 如果不需要流式输出，直接调用原始代理的run方法
                if not stream:
                    return self.agent.run(task, stream=False, **kwargs)
                    
                # 执行原始代理的run方法获取最终答案
                try:
                    result = self.agent.run(task, stream=False, **kwargs)
                    
                    # 如果结果已经是字符串或迭代器，直接返回
                    if isinstance(result, str) or (
                        hasattr(result, '__iter__') and not hasattr(result, 'content')
                    ):
                        return result
                        
                    # 使用 FinalAnswerTool 处理最终答案
                    final_prompt = f"请将以下内容格式化为Markdown报告：\n\n{result}"
                    
                    # 创建简单的消息列表用于模型
                    messages = [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "你是一个专业文档格式化助手，"
                                           "擅长将研究结果转换为结构化的Markdown报告。"
                                }
                            ]
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": final_prompt
                                }
                            ]
                        }
                    ]
                    
                    # 调用模型获取流式输出
                    stream_result = self.model(messages, stream=True)
                    
                    # 将流对象转换为标准迭代器
                    return self._convert_stream_to_iterator(stream_result)
                    
                except Exception as e:
                    logger.exception("生成流式最终答案时出错: %s", str(e))
                    return f"生成流式最终答案时出错: {str(e)}"
                
            # 确保包装器实现与原代理相同的public方法
            def initialize_system_prompt(self):
                """委托给基础代理"""
                return self.agent.initialize_system_prompt()
                
            def step(self, memory_step):
                """委托给基础代理"""
                return self.agent.step(memory_step)
                
            def write_memory_to_messages(self, summary_mode=False):
                """委托给基础代理"""
                return self.agent.write_memory_to_messages(summary_mode)
                
            def provide_final_answer(self, task, images=None):
                """委托给基础代理"""
                return self.agent.provide_final_answer(task, images)
                
            def interrupt(self):
                """中断代理执行"""
                self.agent.interrupt_switch = True
                    
        # 将原始代理包装在流式包装器中
        wrapped_agent = StreamingFinalAnswerWrapper(code_agent, streaming_model, verbosity_level)
        
        # 设置日志输出
        print("DeepSearch CodeAgent with StreamingFinalAnswer " 
              f"({orchestrator_model_id}) created successfully, "
              f"using executor: {executor_type}")
        print(f"Allowed import modules: {combined_authorized_imports}")
        print(f"Configured tools: "
              f"{[tool.name for tool in code_agent.tools.values()]}")
        print("Streaming mode: ENABLED - Only Final Answer will be streamed")
        if search_planning_interval:
            print(f"Planning interval: Every {search_planning_interval} steps")
        
        return wrapped_agent
    else:
        # 非流式模式：使用标准的CodeAgent
        print(f"DeepSearch CodeAgent ({orchestrator_model_id}) "
              f"created successfully, using executor: {executor_type}")
        print(f"Allowed import modules: {combined_authorized_imports}")
        print(f"Configured tools: "
              f"{[tool.name for tool in code_agent.tools.values()]}")
        if search_planning_interval:
            print(f"Planning interval: Every {search_planning_interval} steps")
              
        return code_agent

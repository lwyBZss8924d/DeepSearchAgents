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

    Returns:
        CodeAgent: The configured DeepSearch agent instance,
        or None if missing required API keys.
    """

    # --- LiteLLM Model Initialization (using passed keys/url) ---

    model = LiteLLMModel(
        model_id=orchestrator_model_id,
        temperature=0.2,
        api_key=litellm_master_key,
        api_base=litellm_base_url
    )

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

    # --- Initialize CodeAgent ---
    code_agent = CodeAgent(
        tools=agent_tools,
        model=model,
        prompt_templates=prompt_templates_dict,
        additional_authorized_imports=combined_authorized_imports,
        executor_type=executor_type,
        executor_kwargs=executor_kwargs,
        max_steps=max_steps,  # Depth search may require more steps parameter
        verbosity_level=verbosity_level
    )

    print(
        f"DeepSearch CodeAgent ({orchestrator_model_id}) created successfully,"
        f"using executor: {executor_type}"
    )
    print(f"Allowed import modules: {combined_authorized_imports}")
    print(
        f"Configured tools: "
        f"{[tool.name for tool in code_agent.tools.values()]}"
    )

    return code_agent

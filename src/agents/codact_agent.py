from typing import List, Optional, Dict, Any
import importlib
import yaml
from smolagents import (
    LiteLLMModel, CodeAgent, Tool
)
from .tools import (
    SearchLinksTool, ReadURLTool, ChunkTextTool,
    EmbedTextsTool, RerankTextsTool,
    EnhancedWolframAlphaTool, FinalAnswerTool
)
from .prompt_templates.codact_prompts import (
    CODACT_SYSTEM_EXTENSION, PLANNING_TEMPLATES,
    FINAL_ANSWER_EXTENSION, MANAGED_AGENT_TEMPLATES,
    merge_prompt_templates
)
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
    enable_streaming: bool = True,
    planning_interval: int = 5,
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
        planning_interval (int): Interval for agent planning steps
            (default: 5). Agent will reassess strategy every this many steps.

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

    # --- Load base prompt templates ---
    # Load base CodeAgent prompt templates from smolagents framework
    base_prompts = yaml.safe_load(
        importlib.resources.files(
            "smolagents.prompts"
        ).joinpath("code_agent.yaml").read_text()
    )

    # --- Create extended prompt templates ---
    extension_content = {
        "system_extension": CODACT_SYSTEM_EXTENSION,
        "planning": PLANNING_TEMPLATES,
        "final_answer": FINAL_ANSWER_EXTENSION,
        "managed_agent": MANAGED_AGENT_TEMPLATES
    }

    # Merge base templates with extension content
    extended_prompt_templates = merge_prompt_templates(
        base_templates=base_prompts,
        extensions=extension_content
    )

    # --- Set default allowed imports ---
    # Including 'json' for tool output handling
    default_authorized_imports = [
        "json", "re", "collections", "datetime",
        "time", "math", "itertools", "copy",
        "requests", "bs4", "urllib", "html",
        "io", "os", "aiohttp", "asyncio", "dotenv",
    ]
    if additional_authorized_imports:
        # Merge and deduplicate allowed imports list
        combined_authorized_imports = list(set(
            default_authorized_imports + additional_authorized_imports
        ))
    else:
        combined_authorized_imports = default_authorized_imports

    # --- Structured Output JSON Schema ---
    # Provide JSON-formatted structured output
    # for search results and final answer
    json_grammar = None
    if reranker_type:  # If reranking is used, add structured output support
        json_grammar = {
            "json_object": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"}
                },
                "required": ["title", "content"]
            }
        }

    # --- Set Planning Interval ---
    # Deep search requires periodic reassessment of search strategy
    search_planning_interval = planning_interval

    # --- Initialize State Management ---
    # Provide structured state tracking for the agent
    initial_state = {
        "visited_urls": set(),        # Visited URLs
        "search_queries": [],         # Executed search queries
        "key_findings": {},           # Key findings, indexed by topic
        "search_depth": 0,            # Current search depth
        "reranking_history": [],      # Reranking history
        "content_quality": {}         # URL content quality scores
    }

    # --- Initialize LiteLLM Model ---
    # Create a standard model for CodeAgent
    standard_model = LiteLLMModel(
        model_id=orchestrator_model_id,
        temperature=0.2,
        api_key=litellm_master_key,
        api_base=litellm_base_url
    )

    # --- Initialize CodeAgent with extended templates ---
    code_agent = CodeAgent(
        tools=agent_tools,
        model=standard_model,
        # base smolagents.prompts.code_agent.yaml + codact_prompts.py
        prompt_templates=extended_prompt_templates,
        additional_authorized_imports=combined_authorized_imports,
        executor_type=executor_type,
        executor_kwargs=executor_kwargs or {},
        max_steps=max_steps,
        verbosity_level=verbosity_level,
        grammar=json_grammar,
        planning_interval=search_planning_interval,
    )

    # Initialize agent state
    code_agent.state.update(initial_state)

    # Stream mode: If streaming mode is enabled, use StreamingCodeAgent
    if enable_streaming:
        # Import needed modules
        from .streaming_models import StreamingLiteLLMModel
        from .streaming_agents import StreamingCodeAgent

        # Create a streaming model for final answer
        streaming_model = StreamingLiteLLMModel(
            model_id=orchestrator_model_id,
            temperature=0.2,
            api_key=litellm_master_key,
            api_base=litellm_base_url
        )

        # Create a StreamingCodeAgent with the same configuration
        streaming_agent = StreamingCodeAgent(
            tools=agent_tools,
            model=streaming_model,
            # base smolagents.prompts.code_agent.yaml + codact_prompts.py
            prompt_templates=extended_prompt_templates,
            additional_authorized_imports=combined_authorized_imports,
            executor_type=executor_type,
            executor_kwargs=executor_kwargs or {},
            max_steps=max_steps,
            verbosity_level=verbosity_level,
            grammar=json_grammar,
            planning_interval=search_planning_interval,
        )

        # Initialize agent state
        streaming_agent.state.update(initial_state)

        # Ensure execution environment is correctly set up
        streaming_agent._setup_executor_environment()

        # Set logging output
        print("DeepSearch CodeAgent with streaming support "
              f"({orchestrator_model_id}) created successfully, "
              f"using executor: {executor_type}")
        print(f"Allowed import modules: {combined_authorized_imports}")
        print(f"Configured tools: "
              f"{[tool.name for tool in streaming_agent.tools.values()]}")
        print("Streaming mode: ENABLED - Only Final Answer will be streamed")
        if search_planning_interval:
            print(f"Planning interval: Every {search_planning_interval} steps")

        return streaming_agent
    else:
        # Non-streaming mode: Use the standard CodeAgent
        print(f"DeepSearch CodeAgent ({orchestrator_model_id}) "
              f"created successfully, using executor: {executor_type}")
        print(f"Allowed import modules: {combined_authorized_imports}")
        print(f"Configured tools: "
              f"{[tool.name for tool in code_agent.tools.values()]}")
        if search_planning_interval:
            print(f"Planning interval: Every {search_planning_interval} steps")

        return code_agent

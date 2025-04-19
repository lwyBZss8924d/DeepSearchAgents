#!/usr/bin/env python
import os
import uvicorn
import traceback
import asyncio
import time
import logging
from typing import Optional, Dict, Any
from .config_loader import APP_CONFIG, get_config_value, get_api_key
from .agent import create_react_agent
from .codact_agent import create_codact_agent
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger("deepsearch-api")

# --- Load values from the loaded config ---
SERVICE_HOST = get_config_value(APP_CONFIG, 'service.host', "0.0.0.0")
SERVICE_PORT = get_config_value(APP_CONFIG, 'service.port', 8000)
# Allow environment variable to override YAML mode
DEEPSEARCH_AGENT_MODE = os.getenv(
    "DEEPSEARCH_AGENT_MODE",
    get_config_value(APP_CONFIG, 'service.deepsearch_agent_mode', "codact")
).lower()
ORCHESTRATOR_MODEL_ID = get_config_value(
    APP_CONFIG, 'models.orchestrator_id', "openrouter/openai/gpt-4.1"
)
# Default search model to orchestrator
SEARCH_MODEL_NAME = get_config_value(
    APP_CONFIG, 'models.search_id', ORCHESTRATOR_MODEL_ID
)
RERANKER_TYPE = get_config_value(
    APP_CONFIG, 'models.reranker_type', "jina-reranker-m0"
)
VERBOSE_TOOL_CALLBACKS = get_config_value(
    APP_CONFIG, 'agents.common.verbose_tool_callbacks', True
)
CODACT_EXECUTOR_TYPE = get_config_value(
    APP_CONFIG, 'agents.codact.executor_type', "local"
)
CODACT_MAX_STEPS = get_config_value(
    APP_CONFIG, 'agents.codact.max_steps', 25
)
CODACT_VERBOSITY_LEVEL = get_config_value(
    APP_CONFIG, 'agents.codact.verbosity_level', 1
)
CODACT_EXECUTOR_KWARGS = get_config_value(
    APP_CONFIG, 'agents.codact.executor_kwargs', {}
)
CODACT_ADDITIONAL_IMPORTS = get_config_value(
    APP_CONFIG, 'agents.codact.additional_authorized_imports', []
)

# Output configuration information only in non-standalone mode
if True:
    print(f"Service configuration: Host={SERVICE_HOST}, Port={SERVICE_PORT}")
    print(
        f"Model configuration: Orchestrator={ORCHESTRATOR_MODEL_ID}, "
        f"Search={SEARCH_MODEL_NAME}, Reranker={RERANKER_TYPE}"
    )
    print(
        f"Agent configuration: Mode={DEEPSEARCH_AGENT_MODE}, "
        f"VerboseTools={VERBOSE_TOOL_CALLBACKS}"
    )
    print(
        f"CodeAct configuration: Executor={CODACT_EXECUTOR_TYPE}, "
        f"MaxSteps={CODACT_MAX_STEPS}, Verbosity={CODACT_VERBOSITY_LEVEL}"
    )


class SmolReactAgentRunner:
    """ Wrapper for smolagents.ToolCallingAgent instance and execution logic.
    """

    def __init__(self):
        """Initialize and create internal smolagents instance."""
        litellm_master_key = get_api_key("LITELLM_MASTER_KEY")
        serper_api_key = get_api_key("SERPER_API_KEY")
        jina_api_key = get_api_key("JINA_API_KEY")
        wolfram_app_id = get_api_key("WOLFRAM_ALPHA_APP_ID")
        # Optional LiteLLM Base URL
        litellm_base_url = get_api_key("LITELLM_BASE_URL")

        try:
            self.react_agent = create_react_agent(
                orchestrator_model_id=ORCHESTRATOR_MODEL_ID,
                search_model_name=SEARCH_MODEL_NAME,
                reranker_type=RERANKER_TYPE,
                verbose_tool_callbacks=VERBOSE_TOOL_CALLBACKS,
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
                # cli_console is None in service mode
                cli_console=None
            )

            if self.react_agent is None:
                raise RuntimeError(
                    "Failed to initialize React Agent, "
                    "missing required API keys."
                )

        except (ValueError, RuntimeError) as e:
            print(f"[Error] Failed to initialize SmolReactAgentRunner: {e}")
            self.react_agent = None
            raise RuntimeError(f"Agent initialization failed: {e}") from e
        except Exception as e:
            print(f"[Error] Failed to initialize SmolReactAgentRunner: {e}")
            traceback.print_exc()
            raise RuntimeError(
                f"Unexpected error during agent initialization: {e}"
            ) from e

    async def run(self, user_input: str) -> str:
        """Async wrapper for agent execution."""
        if self.react_agent is None:
            return "Error: React Agent failed to initialize."

        print(f"(Async) Received input: {user_input}")
        try:
            loop = asyncio.get_running_loop()
            result_str = await loop.run_in_executor(
                None, self.react_agent.run, user_input
            )
            print(f"(Async) Generated result: {result_str[:200]}...")
            return result_str
        except Exception as e:
            error_message = f"Error processing request: {str(e)}"
            print(f"(Async) Error executing agent: {e}")
            traceback.print_exc()
            return error_message


class CodeAgentRunner:
    """Wrapper for smolagents.CodeAgent instance and execution logic,
    for deep search."""

    def __init__(self):
        """Initialize and create internal smolagents CodeAgent instance."""
        litellm_master_key = get_api_key("LITELLM_MASTER_KEY")
        serper_api_key = get_api_key("SERPER_API_KEY")
        jina_api_key = get_api_key("JINA_API_KEY")
        wolfram_app_id = get_api_key("WOLFRAM_ALPHA_APP_ID")
        litellm_base_url = get_api_key("LITELLM_BASE_URL")

        try:
            self.code_agent = create_codact_agent(
                orchestrator_model_id=ORCHESTRATOR_MODEL_ID,
                search_model_name=SEARCH_MODEL_NAME,
                reranker_type=RERANKER_TYPE,
                verbose_tool_callbacks=VERBOSE_TOOL_CALLBACKS,
                executor_type=CODACT_EXECUTOR_TYPE,
                max_steps=CODACT_MAX_STEPS,
                verbosity_level=CODACT_VERBOSITY_LEVEL,
                executor_kwargs=CODACT_EXECUTOR_KWARGS,
                additional_authorized_imports=CODACT_ADDITIONAL_IMPORTS,
                litellm_master_key=litellm_master_key,
                litellm_base_url=litellm_base_url,
                serper_api_key=serper_api_key,
                jina_api_key=jina_api_key,
                wolfram_app_id=wolfram_app_id,
                # cli_console is None in service mode
                cli_console=None
            )

            if self.code_agent is None:
                raise RuntimeError(
                    "Failed to initialize DeepSearch CodeAgent, "
                    "missing required API keys."
                )

        except (ValueError, RuntimeError) as e:
            print(f"[Error] Failed to initialize CodeAgentRunner: {e}")
            self.code_agent = None
            raise RuntimeError(f"CodeAgent initialization failed: {e}") from e
        except Exception as e:
            print(f"[Error] Failed to initialize CodeAgentRunner: {e}")
            traceback.print_exc()
            raise RuntimeError(
                f"Unexpected error during CodeAgent initialization: {e}"
            ) from e

    async def run(self, user_input: str) -> str:
        """Async wrapper for agent execution."""
        if self.code_agent is None:
            return "Error: DeepSearch CodeAgent failed to initialize."

        print(f"(Async) Received input: {user_input}")
        try:
            loop = asyncio.get_running_loop()
            start_time = time.time()
            result_str = await loop.run_in_executor(
                None, self.code_agent.run, user_input
            )
            execution_time = time.time() - start_time
            print(
                f"(Async) CodeAgent execution completed, "
                f"time taken: {execution_time:.2f} seconds"
            )
            preview_length = 500
            msg = f"(Async) Generated result: {result_str[:preview_length]}..."
            print(msg)
            return result_str
        except Exception as e:
            error_message = f"Error processing request: {str(e)}"
            print(f"(Async) Error executing agent: {e}")
            traceback.print_exc()
            return error_message


# --- FastAPI application setup ---
app = FastAPI(
    title="DeepSearch Agents API",
    description=(
        "provides a Search Agent API with Normal React mode "
        "or CodeAct-ReAct Agent deep search mode."
    ),
    version="0.2.3",
)

# 添加CORS中间件，允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create agent runners
try:
    agent_runner = SmolReactAgentRunner()
    code_agent_runner = CodeAgentRunner()
except RuntimeError as e:
    print(f"[Fatal Error] "
          f"Failed to create Agent Runner: {e}. "
          f"API will not work.")
    agent_runner = None
    code_agent_runner = None


# Define request body model
class UserInput(BaseModel):
    user_input: str


class DeepSearchRequest(BaseModel):
    user_input: str = Field(..., description="User's query content")
    agent_type: Optional[str] = Field(
        "codact",
        description="Agent type to use (codact or react)"
    )
    model_args: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional arguments to pass to the model"
    )


# --- Manual Agent Endpoint ---
@app.post("/run_react_agent", response_class=PlainTextResponse)
async def run_agent_endpoint(input_data: UserInput) -> PlainTextResponse:
    """Receive user input and execute React agent."""
    if agent_runner is None or agent_runner.react_agent is None:
        return PlainTextResponse(
            content="Error: Agent service failed to initialize, "
                    "unable to process request.",
            status_code=503  # Service Unavailable
        )

    result = await agent_runner.run(input_data.user_input)
    # Check if result indicates an internal error
    if result.startswith("Error processing request:") or (
        result.startswith("Error:")
    ):
        # Consider logging more detailed logs
        print(f"Agent run returned an error state: {result}")
        return PlainTextResponse(content=result, status_code=500)
    else:
        return PlainTextResponse(content=result)


@app.post(
    "/run_deepsearch_agent",
    response_class=PlainTextResponse,
    operation_id="deep_search",
    tags=["agents"],
    summary="Execute deep web search and analysis",
    description=(
        "Performs comprehensive web search and analysis on a given query, "
        "returning detailed results"
    )
)
async def run_deepsearch_agent(input_data: UserInput) -> PlainTextResponse:
    """
    Run DeepSearch agent to process complex queries and analysis requests

    This endpoint accepts a user query and uses the DeepSearch agent
    to process it, returning the deep search results.
    Based on server configuration, it can use CodeAct or ReAct agent mode.

    Parameters:
        input_data: Input data object containing user query

    Returns:
        Generated comprehensive answer with deep analysis results.
    """

    # Select the appropriate Agent Runner based on configuration
    selected_runner = None
    if DEEPSEARCH_AGENT_MODE == "codact":
        selected_runner = code_agent_runner
        runner_name = "CodeAgent"
    elif DEEPSEARCH_AGENT_MODE == "react":
        selected_runner = agent_runner  # Use SmolReactAgentRunner
        runner_name = "ReactAgent"
    else:
        print(f"[Error] Invalid DEEPSEARCH_AGENT_MODE configuration: "
              f"{DEEPSEARCH_AGENT_MODE}")
        logger.error(f"Invalid agent mode configuration: "
                     f"{DEEPSEARCH_AGENT_MODE}")
        return PlainTextResponse(
            content=f"Error: Server configured with invalid agent mode "
                    f"'{DEEPSEARCH_AGENT_MODE}'.",
            status_code=500
        )

    agent_attribute = (
        'react_agent' if (
            DEEPSEARCH_AGENT_MODE == 'react'
        ) else 'code_agent'
    )
    if selected_runner is None or getattr(
        selected_runner, agent_attribute, None
    ) is None:
        logger.error(f"DeepSearch {runner_name} service initialization "
                     f"failed, unable to process request")
        return PlainTextResponse(
            content=(f"Error: DeepSearch {runner_name} service failed to "
                     f"initialize, unable to process request."),
            status_code=503  # Service Unavailable
        )

    logger.info(f"Received user query: {input_data.user_input[:100]}...")
    try:
        result = await selected_runner.run(input_data.user_input)
        # Check if result indicates an internal error
        if result.startswith("Error processing request:") or (
            result.startswith("Error:")
        ):
            # Consider logging more detailed logs
            logger.error(
                f"DeepSearch {runner_name} execution returned an error: "
                f"{result[:200]}..."
            )
            return PlainTextResponse(content=result, status_code=500)
        else:
            logger.info(f"Successfully generated result, "
                        f"length: {len(result)}")
            return PlainTextResponse(content=result)
    except Exception as e:
        error_msg = f"An error occurred while processing the query: {str(e)}"
        logger.error(error_msg)
        traceback.print_exc()
        return PlainTextResponse(
            content=f"Error processing request: {str(e)}",
            status_code=500
        )


# Keep startup event but remove MCP related code
@app.on_event("startup")
async def startup_event():
    """Print all registered routes when the application starts."""
    print("\n--- Registered Routes ---")
    for route in app.routes:
        if hasattr(route, "path"):
            methods_str = str(getattr(route, 'methods', 'N/A'))
            operation_id = getattr(route, 'operation_id', 'N/A')
            print(
                f"Path: {route.path}, Name: {route.name}, "
                f"Methods: {methods_str}, Operation ID: {operation_id}"
            )
        elif hasattr(route, "mount_path"):
            print(f"Mounted App: {route.mount_path}")
            if hasattr(route, "app") and hasattr(route.app, "routes"):
                print(f"  Routes within {route.mount_path}:")
                for sub_route in route.app.routes:
                    if hasattr(sub_route, "path"):
                        sub_methods_str = str(
                            getattr(sub_route, 'methods', 'N/A')
                        )
                        print(
                            f"  - Path: {sub_route.path}, "
                            f"Name: {sub_route.name}, "
                            f"Methods: {sub_methods_str}"
                        )
    print("--- End Routes ---\n")

    if agent_runner is None:
        logger.warning("React Agent Runner failed to initialize, "
                       "related APIs may not work.")
    else:
        logger.info("React Agent Runner initialized successfully.")

    if code_agent_runner is None:
        logger.warning("DeepSearch CodeAgent Runner failed to initialize, "
                       "related APIs may not work.")
    else:
        logger.info("DeepSearch CodeAgent Runner initialized successfully.")


# Root path for health check
@app.get("/")
async def read_root():
    agent_status = "ok" if (
        agent_runner and agent_runner.react_agent
    ) else "error"
    code_agent_status = "ok" if (
        code_agent_runner and code_agent_runner.code_agent
    ) else "error"

    agents_info = {
        "react_agent": {
            "status": agent_status,
            "endpoint": "/run_react_agent",
            "model": ORCHESTRATOR_MODEL_ID if agent_status == "ok" else None
        },
        "deepsearch_agent": {
            "status": code_agent_status,
            "endpoint": "/run_deepsearch_agent",
            "model": (
                ORCHESTRATOR_MODEL_ID if code_agent_status == "ok" else None
            ),
            "executor_type": CODACT_EXECUTOR_TYPE,
            "max_steps": CODACT_MAX_STEPS
        }
    }

    return {
        "message": "DeepSearch-AgentTeam API service is running",
        "agents": agents_info,
        "version": "0.2.3"
    }


if __name__ == "__main__":
    log_level_name = os.getenv("LOG_LEVEL", "info").upper()
    log_level = getattr(logging, log_level_name)
    logging.basicConfig(level=log_level)

    print(f"Starting FastAPI server at http://{SERVICE_HOST}:{SERVICE_PORT}")

    if agent_runner is None or code_agent_runner is None:
        logger.error(
            "Due to Agent Runner initialization failure, "
            "the server cannot start. "
            "Please check API keys and configuration."
        )
    else:
        uvicorn.run(
            app,
            host=SERVICE_HOST,
            port=SERVICE_PORT,
            log_level=os.getenv("LOG_LEVEL", "info")
        )

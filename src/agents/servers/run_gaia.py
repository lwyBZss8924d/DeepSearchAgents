#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/servers/run_gaia.py
# code style: PEP 8

"""
Run DeepSearch Agent with Gradio UI Application Interface Server
"""

import argparse
import logging
import os
from pathlib import Path

from smolagents.gradio_ui import GradioUI

from src.agents.runtime import agent_runtime
from src.core.config.settings import settings
from src.agents.ui_common.gradio_adapter import create_gradio_compatible_agent
from src.agents.ui_common.agent_step_callback import AgentStepCallback
from .gradio_patch import apply_gradio_patches

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments for the Gradio UI server"""
    parser = argparse.ArgumentParser(
        description="Run DeepSearch Agent with Gradio UI"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["react", "codact"],
        default=None,
        help="Agent mode (react or codact)"
    )

    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public shareable link (for macOS configurations)"
    )

    parser.add_argument(
        "--server-name",
        type=str,
        default="0.0.0.0",
        help="Hostname to bind server to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--server-port",
        type=int,
        default=7860,
        help="Port to bind server to (default: 7860)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional logging"
    )

    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Temporarily disable proxy settings to start local server"
    )

    return parser.parse_args()


def create_step_callback(debug_mode=False):
    """Create a step callback for token counting and step tracking

    Args:
        debug_mode: Whether to enable debug mode

    Returns:
        AgentStepCallback: Configured callback
    """
    return AgentStepCallback(debug_mode=debug_mode)


def run_gradio_ui(
    mode=None,
    share=False,
    server_name="0.0.0.0",
    server_port=7860,
    debug_mode=False,
    no_proxy=False,
    use_fastapi=True
):
    """
    Run DeepSearch Agent with Gradio UI Application Interface Server

    Args:
        mode: Which agent mode to use ("react" or "codact")
        share: Whether to create a public sharable link
        server_name: Hostname to bind server to
        server_port: Port to bind server to
        debug_mode: Whether to enable debug mode
        no_proxy: Whether to temporarily disable proxy settings
        use_fastapi: Whether to use FastAPI to start Gradio
    """
    original_http_proxy = None
    original_https_proxy = None
    # Disable proxy first, then execute other initialization steps
    if no_proxy:
        # Save and disable all proxy settings correctly
        original_http_proxy = os.environ.get('HTTP_PROXY')
        original_https_proxy = os.environ.get('HTTPS_PROXY')

        # Clear all proxy environment variables
        for proxy_var in [
            'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'
        ]:
            if proxy_var in os.environ:
                os.environ.pop(proxy_var)

        # Explicitly set NO_PROXY environment variable
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1,0.0.0.0'
        print(
            "All proxy settings disabled, explicitly allowed local connection"
        )

    # Apply patches for Gradio compatibility
    apply_gradio_patches()

    # Set environment variables for Gradio
    os.environ["GRADIO_SERVER_NAME"] = server_name
    os.environ["GRADIO_ALLOW_ORIGINS"] = "*"
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

    # If on MacOS, try adding this environment variable
    if os.name == 'posix' and os.uname().sysname == 'Darwin':
        os.environ["GRADIO_TEMP_DIR"] = "./tmp_gradio"
        # Ensure temporary directory exists
        Path("./tmp_gradio").mkdir(exist_ok=True)

    # Determine agent mode
    agent_mode = mode or settings.DEEPSEARCH_AGENT_MODE
    logger.info(f"Starting DeepSearch Agent in {agent_mode} mode")

    # Create step callback for tracking
    step_callback = create_step_callback(debug_mode=debug_mode)

    # Create appropriate agent
    if agent_mode.lower() == "react":
        agent = agent_runtime.create_react_agent(
            step_callback=step_callback,
            debug_mode=debug_mode
        )
        agent_name = "DeepSearch ReAct Agent"
        agent_description = (
            "An intelligent agent using the ReAct (Reasoning + Acting) "
            "paradigm for deep web research."
        )
    else:
        agent = agent_runtime.create_codact_agent(
            step_callback=step_callback,
            debug_mode=debug_mode
        )
        agent_name = "DeepSearch CodeAct Agent"
        agent_description = (
            "An intelligent agent using the CodeAct paradigm for "
            "deep web research through code execution."
        )

    # Create Gradio-compatible version of the agent
    compatible_agent = create_gradio_compatible_agent(
        agent,
        name=agent_name,
        description=agent_description
    )

    # Create upload folder if it doesn't exist
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # Initialize GradioUI with the compatible agent
    ui = GradioUI(
        agent=compatible_agent,
        file_upload_folder=str(uploads_dir)
    )

    # Configure UI launch parameters
    ui_launch_kwargs = {
        "share": share,
        "server_name": "localhost",
        "server_port": server_port,
        "inbrowser": False,
        "prevent_thread_lock": True,
        "show_api": False,
        "quiet": not debug_mode,
        "favicon_path": None,
    }

    # Print startup message
    print(f"Starting DeepSearch {agent_mode} Agent with Gradio UI")
    server_addr = ui_launch_kwargs['server_name']
    print(
        f"Server running at: http://{server_addr}:{server_port}"
    )
    if share:
        print("Creating public share link...")

    try:
        # If use_fastapi is True, try to run with FastAPI
        if use_fastapi:
            return run_with_fastapi(
                compatible_agent,
                server_name=server_name,
                server_port=server_port,
                debug_mode=debug_mode
            )

        # Launch the UI
        ui.launch(**ui_launch_kwargs)
        return ui
    finally:
        # If proxy was disabled, restore original settings
        if no_proxy and original_http_proxy:
            os.environ['HTTP_PROXY'] = original_http_proxy
        if no_proxy and original_https_proxy:
            os.environ['HTTPS_PROXY'] = original_https_proxy


def run_with_fastapi(
    compatible_agent,
    server_name="0.0.0.0",
    server_port=7860,
    debug_mode=False
):
    """
    Use FastAPI to start Gradio interface, showing agent execution process
    """
    import gradio as gr
    from fastapi import FastAPI
    import uvicorn
    from fastapi.middleware.cors import CORSMiddleware

    # Create FastAPI app
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create Gradio interface
    with gr.Blocks(theme="ocean") as demo:
        gr.Markdown(f"# {compatible_agent.name}")
        gr.Markdown("## Multi-step Reasoning and Code Action "
                    "with ToolBox Agent ")

        # Session state
        session_state = gr.State({})

        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    type="messages",
                    height=900,
                    show_label=False,
                    render_markdown=True,
                    latex_delimiters=[
                        {"left": "$$", "right": "$$", "display": True},
                        {"left": "$", "right": "$", "display": False},
                    ],
                    avatar_images=(
                        None,
                        "https://huggingface.co/datasets/huggingface/"
                        "documentation-images/resolve/main/smolagents/"
                        "mascot_smol.png"
                    ),
                )

                # User input area
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Enter your deep search question...",
                        show_label=False,
                        scale=8
                    )
                    submit_btn = gr.Button("Send", variant="primary", scale=1)
                    clear_btn = gr.Button("Clear", scale=1)

            # Right side display execution statistics
            with gr.Column(scale=2, visible=debug_mode):
                gr.Markdown("### Execution Statistics")
                stats = gr.JSON(label="Statistics")
                steps_count = gr.Number(label="Steps Count", value=0)
                tools_used = gr.JSON(label="Used Tools")

        # Process interaction functions - use stream_to_gradio
        def chat(message, history, session):
            """Process user message and stream agent execution process"""
            # Ensure agent instance exists
            if "agent" not in session:
                session["agent"] = compatible_agent
                session["stats"] = {"steps": 0, "tools": []}

            # Add user message as gr.ChatMessage for proper rendering
            history = history or []
            user_msg = gr.ChatMessage(
                role="user", content=message, metadata={"status": "done"}
            )
            history.append(user_msg)
            yield history, session

            try:
                # Use agent instance
                agent_instance = session["agent"]

                # Get streaming configuration and agent type
                agent_type = agent_instance.__class__.__name__.lower()
                if "react" in agent_type:
                    agent_type = "react"
                elif "codact" in agent_type or "code" in agent_type:
                    agent_type = "codact"

                # Streaming is currently not recommended, set to True
                # But stream_to_gradio internally already sets stream=True
                # so we don't need to pass it

                # Find model in different possible locations
                model = None
                if hasattr(agent_instance, 'model'):
                    model = agent_instance.model
                elif (hasattr(agent_instance, 'agent') and
                      hasattr(agent_instance.agent, 'model')):
                    model = agent_instance.agent.model

                if not model:
                    error_msg = (
                        "Model not found in agent. Cannot check if streaming "
                        "is supported."
                    )
                    history.append(
                        {
                            "role": "assistant",
                            "content": f"Error: {error_msg}",
                        }
                    )
                    yield history, session
                    return

                # Check if API key is configured correctly
                if model and hasattr(model, 'api_key'):
                    if not model.api_key:
                        error_msg = (
                            "API key not configured. Please check the"
                            " LITELLM_MASTER_KEY in the .env file."
                        )
                        history.append(
                            {
                                "role": "assistant",
                                "content": f"Error: {error_msg}",
                            }
                        )
                        yield history, session
                        return

                # Check if streaming is supported by the model
                if not hasattr(model, 'generate_stream'):
                    error_msg = (
                        "Current model does not support streaming output. "
                        "Please use a model that supports streaming."
                    )
                    history.append(
                        {
                            "role": "assistant",
                            "content": f"Error: {error_msg}",
                        }
                    )
                    yield history, session
                    return

                # Run agent with streaming using stream_to_gradio
                try:
                    # Check if our agent.run supports 'images' parameter
                    import inspect
                    run_params = inspect.signature(
                        agent_instance.run
                    ).parameters
                    stream_to_gradio_kwargs = {
                        'task': message,
                        'reset_agent_memory': False
                    }

                    # Only add images parameter if agent.run supports it
                    if 'images' in run_params:
                        stream_to_gradio_kwargs['task_images'] = None

                    # Fix for CodeActAgent: Add model attribute if missing
                    # This is needed for token counting in stream_to_gradio
                    original_model = None
                    if not hasattr(agent_instance, 'model'):
                        # Try to find model in different locations
                        if hasattr(agent_instance, 'agent') and hasattr(
                            agent_instance.agent, 'model'
                        ):
                            # Remember we didn't have model attribute
                            # originally
                            original_model = True
                            agent_instance.model = agent_instance.agent.model
                            logger.debug(
                                "Added model attribute to agent_instance "
                                "for stream_to_gradio"
                            )

                    # Create a wrapper generator that will clean up after
                    # iteration
                    def wrapper_generator():
                        import gradio as gr
                        try:
                            # agent_instance is GradioUIAdapter.
                            # Its .run(stream=True) already yields
                            # gr.ChatMessage or str.
                            run_kwargs_for_adapter = {
                                'task': message,
                                'stream': True,
                                'reset': stream_to_gradio_kwargs.get(
                                    'reset_agent_memory', False
                                ),
                                'images': stream_to_gradio_kwargs.get(
                                    'task_images', None
                                )
                                # additional_args and max_steps could be added
                                # if needed
                            }
                            generator = (
                                agent_instance.run(**run_kwargs_for_adapter)
                            )

                            for response in generator:
                                # DEBUG: Inspect items from stream_to_gradio
                                print(
                                    f"DBG: type={type(response)}, cont='"
                                    f"{str(response)[:150]}'..."
                                )
                                # response can be either gr.ChatMessage or
                                # a plain string (delta content)
                                if isinstance(response, gr.ChatMessage):
                                    # Append complete ChatMessage directly so
                                    # Chatbot (type="messages") can render it
                                    history.append(response)
                                    # Update statistics if available
                                    session["stats"]["steps"] += 1
                                elif isinstance(response, str):
                                    # Handle streaming delta strings
                                    if (
                                        history
                                        and isinstance(
                                            history[-1], gr.ChatMessage
                                        )
                                        and history[-1].metadata.get(
                                            "status"
                                        )
                                        == "pending"
                                    ):
                                        # Update the pending assistant message
                                        history[-1].content = response
                                    else:
                                        # Create a new pending message
                                        history.append(
                                            gr.ChatMessage(
                                                role="assistant",
                                                content=response,
                                                metadata={
                                                    "status": "pending"
                                                },
                                            )
                                        )
                                    # No step increment for partial delta
                                    # Yield outside the string check, but
                                    # inside the loop
                                yield history, session
                        finally:
                            # Clean up temporary model attribute if we added it
                            if (
                                original_model
                                and hasattr(agent_instance, 'model')
                            ):
                                delattr(agent_instance, 'model')
                                logger.debug(
                                    "Removed temporary model attribute "
                                    "from agent_instance"
                                )

                    # Return the wrapper generator
                    yield from wrapper_generator()

                except Exception as stream_error:
                    error_msg = f"Streaming error: {str(stream_error)}"
                    logger.error("%s", error_msg, exc_info=True)
                    history.append(
                        {
                            "role": "assistant",
                            "content": f"Error: {error_msg}",
                        }
                    )
                    yield history, session

            except Exception as e:
                import traceback
                error_msg = f"Execution error: {str(e)}"
                logger.error(
                    "%s\n%s", error_msg, traceback.format_exc()
                )
                history.append(
                    {
                        "role": "assistant",
                        "content": f"Error: {str(e)}",
                    }
                )
                yield history, session

        # Get latest statistics
        def update_stats(session):
            """Update statistics display"""
            if "stats" in session:
                return (
                    session["stats"],
                    session["stats"].get("steps", 0),
                    session["stats"].get("tools", [])
                )
            return {}, 0, []

        # Clear chat history
        def clear_history():
            return [], {
                "agent": compatible_agent,
                "stats": {"steps": 0, "tools": []}
            }

        # Set event handling
        submit_btn.click(
            chat,
            [msg, chatbot, session_state],
            [chatbot, session_state]
        ).then(
            update_stats,
            [session_state],
            [stats, steps_count, tools_used]
        ).then(
            lambda: gr.Textbox(value="", interactive=True),
            None,
            [msg]
        )

        msg.submit(
            chat,
            [msg, chatbot, session_state],
            [chatbot, session_state]
        ).then(
            update_stats,
            [session_state],
            [stats, steps_count, tools_used]
        ).then(
            lambda: gr.Textbox(value="", interactive=True),
            None,
            [msg]
        )

        clear_btn.click(
            clear_history,
            None,
            [chatbot, session_state]
        ).then(
            lambda: ({}, 0, []),
            None,
            [stats, steps_count, tools_used]
        )

    # Mount Gradio app to FastAPI
    app = gr.mount_gradio_app(app, demo, path="/")

    # Start service
    print(
        f"Starting Gradio UI (via FastAPI): "
        f"http://{server_name}:{server_port}"
    )
    uvicorn.run(app, host=server_name, port=server_port)


if __name__ == "__main__":
    args = parse_args()
    ui = run_gradio_ui(
        mode=args.mode,
        share=args.share,
        server_name=args.server_name,
        server_port=args.server_port,
        debug_mode=args.debug,
        no_proxy=args.no_proxy
    )

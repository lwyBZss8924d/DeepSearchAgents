#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/api.py
# code style: PEP 8

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional

from ..core.config.settings import settings
from .v1.router import api_router

logger = logging.getLogger(__name__)

# Import v2 router if available
try:
    from .v2.endpoints import router as v2_router
    V2_API_AVAILABLE = True
except ImportError:
    V2_API_AVAILABLE = False
    logger.info("Web API v2 not available")

try:
    from src.agents.servers.run_fastmcp import create_fastmcp_server
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False


@asynccontextmanager
async def default_lifespan(app):
    """Default lifespan context manager"""
    # Startup
    print("\n--- Registered routes ---")
    for route in app.routes:
        if hasattr(route, "path"):
            methods_str = str(getattr(route, 'methods', 'N/A'))
            print(f"Path: {route.path}, Methods: {methods_str}")
    print("--- Route list end ---\n")

    yield

    # Shutdown
    pass


def create_app(
    lifespan=default_lifespan,
    enable_fastmcp: bool = False,
    fastmcp_path: Optional[str] = "/mcp",
    agent_type: str = "codact"
) -> FastAPI:
    """Create and configure the FastAPI application

    Args:
        lifespan: Optional lifespan context manager
        enable_fastmcp: Whether to enable FastMCP integration
        fastmcp_path: Path to mount the FastMCP server at
        agent_type: Type of agent to use for FastMCP server (default: "codact")

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Store original lifespan
    original_lifespan = lifespan
    mcp_lifespan = None

    # Integrate FastMCP if enabled - create the server first for lifespan setup
    if enable_fastmcp and FASTMCP_AVAILABLE:
        try:
            # Create FastMCP server
            mcp_server = create_fastmcp_server(agent_type)

            # Get the ASGI app for the MCP server with explicit
            # Streamable HTTP transport
            mcp_app = mcp_server.http_app(
                path='/mcp',
                transport="streamable-http"
            )

            # Get the MCP app's lifespan
            mcp_lifespan = mcp_app.lifespan

            # Create a combined lifespan context manager that runs both
            @asynccontextmanager
            async def combined_lifespan(app):
                # Enter the MCP lifespan first to initialize task groups
                async with mcp_lifespan(app):
                    # Then enter the original app lifespan
                    async with original_lifespan(app):
                        yield

            # Use the combined lifespan
            lifespan = combined_lifespan

        except Exception as e:
            logger.exception(f"Failed to initialize FastMCP server: {e}")
            # Continue with original lifespan if FastMCP setup fails

    # Create the app with the appropriate lifespan
    app = FastAPI(
        title="DeepSearch Agents API",
        description=(
            "Provide Search Agent API, supporting React mode "
            "or CodeAct-ReAct Agent deep search mode"
        ),
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # CORS middleware with Streamable HTTP compatible settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Type", "Cache-Control", "X-Accel-Buffering",
            "Mcp-Session-Id", "Connection"
        ],
    )

    # Register routes
    app.include_router(api_router)

    # Register v2 routes if available
    if V2_API_AVAILABLE:
        app.include_router(v2_router)
        logger.info("Web API v2 endpoints registered")

    # Mount the MCP server if it was successfully created
    if enable_fastmcp and FASTMCP_AVAILABLE and mcp_lifespan is not None:
        try:
            # Create FastMCP server (already created above)
            mcp_server = create_fastmcp_server(agent_type)

            # Get the ASGI app for the MCP server
            # (same as above but keep for clarity)
            mcp_app = mcp_server.http_app(
                path='/mcp',
                transport="streamable-http"
            )

            # Mount the MCP server app to the FastAPI app
            app.mount(fastmcp_path, mcp_app)

            mount_path = f"{fastmcp_path}/mcp"
            logger.info(
                f"FastMCP server mounted at {mount_path} "
                f"(agent_type={agent_type})"
            )
        except Exception as e:
            logger.exception(f"Failed to mount FastMCP server: {e}")

    return app

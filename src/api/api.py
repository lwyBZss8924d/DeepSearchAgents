#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/api.py
# code style: PEP 8

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from ..core.config.settings import settings
from .v1.router import api_router


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


def create_app(lifespan=default_lifespan) -> FastAPI:
    """Create and configure the FastAPI application

    Args:
        lifespan: Optional lifespan context manager

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="DeepSearch Agents API",
        description="Provide Search Agent API, supporting React mode "
                    "or CodeAct-ReAct Agent deep search mode",
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

    return app

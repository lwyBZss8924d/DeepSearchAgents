#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/main.py
# code style: PEP 8

"""
Main entry point for DeepSearchAgents Web API v2.
"""

import os
import sys
import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v2.endpoints import router
from src.api.v2.session import session_manager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting DeepSearchAgents Web API v2...")
    await session_manager.start()
    yield
    # Shutdown
    logger.info("Shutting down DeepSearchAgents Web API v2...")
    await session_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title="DeepSearchAgents Web API v2",
    description="Simplified API using Gradio message pass-through",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DeepSearchAgents Web API v2",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v2/health"
    }


if __name__ == "__main__":
    # Run with uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "src.api.v2.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v1/endpoints/health.py
# code style: PEP 8

from fastapi import APIRouter
from ....agents.runtime import agent_runtime
from ....core.config.settings import settings

router = APIRouter()


@router.get("/")
async def read_root():
    """Health check endpoint"""
    react_status = "ok" if agent_runtime.react_agent else "error"
    code_status = "ok" if agent_runtime.code_agent else "error"

    agents_info = {
        "react_agent": {
            "status": react_status,
            "endpoint": "/api/v1/agents/run_react_agent",
            "models": {
                "orchestrator": (
                    settings.ORCHESTRATOR_MODEL_ID if react_status == "ok"
                    else None
                ),
                "search": (
                    settings.SEARCH_MODEL_NAME if react_status == "ok"
                    else None
                )
            }
        },
        "deepsearch_agent": {
            "status": code_status,
            "endpoint": "/api/v1/agents/run_deepsearch_agent",
            "models": {
                "orchestrator": (
                    settings.ORCHESTRATOR_MODEL_ID if code_status == "ok"
                    else None
                ),
                "search": (
                    settings.SEARCH_MODEL_NAME if code_status == "ok"
                    else None
                )
            },
            "executor_type": settings.CODACT_EXECUTOR_TYPE,
            "max_steps": settings.CODACT_MAX_STEPS
        }
    }

    return {
        "message": "DeepSearch-Agent Team API is running",
        "agents": agents_info,
        "version": settings.VERSION
    }

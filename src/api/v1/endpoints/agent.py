#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v1/endpoints/agent.py
# code style: PEP 8

"""
DeepSearchAgents - Core Agent API Routes

This module contains only the basic DeepSearchAgents Agent Run endpoints.
All real-time streaming (Streamable HTTP & SSE) functionality has been removed.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import json

from ....agents.runtime import agent_runtime

logger = logging.getLogger(__name__)

router = APIRouter()


class UserInput(BaseModel):
    """User input request model"""
    user_input: str = Field(..., description="User query content")


class DeepSearchRequest(BaseModel):
    """Deep search request model"""
    user_input: str = Field(..., description="User query content")
    agent_type: Optional[str] = Field(
        "codact", description="Agent type used (codact or react)"
    )
    model_args: Optional[Dict[str, Any]] = Field(
        None, description="Model additional parameters"
    )


# Basic Agent Endpoints

@router.post(
    "/run_react_agent",
    response_class=PlainTextResponse,
    operation_id="run_react",
    tags=["agents"],
    summary="Execute React agent search",
    description="Execute network search and analysis using ReAct "
                "chain of thought agent, return detailed results"
)
async def run_agent_endpoint(input_data: UserInput) -> PlainTextResponse:
    """Execute React agent

    Args:
        input_data: Request containing user query

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing React agent with query: {input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(input_data.user_input, "react")

    if result.startswith("Error:") or result.startswith(
        "Error processing request:"
    ):
        logger.error(f"Error executing React agent: {result[:100]}...")
        return PlainTextResponse(content=result, status_code=500)
    else:
        return PlainTextResponse(content=result)


@router.post(
    "/run_deepsearch_agent",
    response_class=PlainTextResponse,
    operation_id="deep_search",
    tags=["agents"],
    summary="Execute deep network search and analysis",
    description="Execute comprehensive network search and analysis "
                "for the given query, using ReAct-CodeAct agent, "
                "return detailed results"
)
async def run_deepsearch_agent(input_data: UserInput) -> PlainTextResponse:
    """Execute DeepSearch agent

    Args:
        input_data: Request containing user query

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing DeepSearch agent with query: "
        f"{input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(input_data.user_input)

    # Handle different result types
    if isinstance(result, dict):
        # If result is dict, convert to JSON string
        result_text = json.dumps(result)
    elif isinstance(result, str):
        result_text = result
    else:
        result_text = json.dumps({"content": str(result)})

    # Check for error
    if (isinstance(result_text, str) and
            (result_text.startswith("Error:") or
             result_text.startswith("Error processing request:"))):
        logger.error(f"Error executing DeepSearch agent: "
                     f"{result_text[:100]}...")
        return PlainTextResponse(content=result_text, status_code=500)
    else:
        return PlainTextResponse(content=result_text)


@router.post(
    "/run_agent",
    response_class=PlainTextResponse,
    operation_id="run_agent",
    tags=["agents"],
    summary="Execute any type of agent",
    description="Select CodeAct-ReAct or normal ReAct agent type "
                "based on agent_type (codact or react) parameter "
                "in request"
)
async def run_selected_agent(
    input_data: DeepSearchRequest
) -> PlainTextResponse:
    """Execute any type of agent

    Args:
        input_data: Request containing user query and agent type

    Returns:
        PlainTextResponse: Response containing agent results
    """
    logger.info(
        f"Executing {input_data.agent_type} agent with query: "
        f"{input_data.user_input[:50]}..."
    )
    result = await agent_runtime.run(
        input_data.user_input,
        input_data.agent_type
    )

    if result.startswith("Error:") or result.startswith(
        "Error processing request:"
    ):
        logger.error(
            f"Error executing {input_data.agent_type} agent: "
            f"{result[:100]}..."
        )
        return PlainTextResponse(content=result, status_code=500)
    else:
        return PlainTextResponse(content=result)

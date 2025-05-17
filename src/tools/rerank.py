#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/rerank.py
# code style: PEP 8

"""
Rerank Texts Agent Tool for DeepSearchAgents.
"""

import os
import json
import asyncio
from typing import List, Optional, Dict, Union, Any
from smolagents import Tool
from src.core.ranking.jina_reranker import JinaAIReranker


class RerankTextsTool(Tool):
    """
    Uses Jina AI Reranker to rerank a list of texts/documents based on their
    relevance to a query.
    """
    name = "rerank_texts"
    description = (
        "Reranks a list of texts/documents based on their relevance to"
        "a query using Jina AI Reranker."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "The query string to use for reranking.",
        },
        "texts": {
            "type": "string",
            "description": (
                "A JSON string representing a list of texts or documents "
                "(dictionaries with 'text' and optional 'image_url') "
                "to be reranked."
            ),
        },
        "model": {
            "type": "string",
            "description": (
                "The reranker model to use (e.g., 'jina-reranker-m0', "
                "'jina-reranker-v2-base-multilingual')."
            ),
            "default": "jina-reranker-m0",
            "nullable": True,
        },
        "top_n": {
            "type": "integer",
            "description": (
                "Number of top results to return. Returns all if None."
            ),
            "default": None,
            "nullable": True,
        },
        "query_image_url": {
            "type": "string",
            "description": (
                "URL of an image related to the query (only for multimodal "
                "models like jina-reranker-m0)."
            ),
            "default": None,
            "nullable": True,
        }
    }

    output_type = "string"

    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        default_model: str = "jina-reranker-m0",
        cli_console=None,
        verbose: bool = False
    ):
        """
        Initialize RerankTextsTool.

        Args:
            jina_api_key (str, optional): Jina AI API key.
            default_model (str): Default reranking model to use.
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        if not self.jina_api_key:
            raise ValueError(
                "JINA_API_KEY is required but not provided "
                "or found in environment."
            )
        self.default_model = default_model
        # Reranker instances will be created when needed
        self._rerankers: Dict[str, JinaAIReranker] = {}
        self.cli_console = cli_console
        self.verbose = verbose

    def _get_reranker(self, model_name: str) -> JinaAIReranker:
        """Get or create Reranker instance based on model name."""
        if model_name not in self._rerankers:
            self._rerankers[model_name] = JinaAIReranker(
                api_key=self.jina_api_key,
                model=model_name
                # Add concurrency and timeout configuration
            )
        return self._rerankers[model_name]

    def forward(
        self,
        query: str,
        texts: str,
        model: Optional[str] = None,
        top_n: Optional[int] = None,
        query_image_url: Optional[str] = None  # Support multimodal queries
    ) -> str:
        """
        Execute text reranking and return a JSON string
        of the sorted list of texts.

        Args:
            query (str): The query to use for reranking.
            texts (str):
                A JSON string representing a list of texts or documents
                (dictionaries with 'text' and optional 'image_url').
            model (str, optional): The model to use.
            top_n (int, optional): Return top N results.
            query_image_url (str, optional):
                URL of an image related to the query
                (only for multimodal models).

        Returns:
            str: A JSON string containing the reranked list of texts.
            If an error occurs, return an error message string.
        """
        effective_model = model if model is not None else self.default_model

        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)
        log_func(f"[bold blue]Executing text reranking "
                 f"(model: {effective_model})[/bold blue]")
        log_func(f"[dim]Query: {query[:100]}...[/dim]")
        if query_image_url:
            log_func(f"[dim]Query image URL: {query_image_url}[/dim]")

        try:
            # Parse the input JSON string
            try:
                input_list: List[Union[str, Dict[str, Any]]] = (
                    json.loads(texts)
                )
                if not isinstance(input_list, list):
                    raise ValueError(
                        "Input 'texts' must be a JSON string of a list "
                        "(of strings or dicts)."
                    )
                if not input_list:
                    log_func("[yellow]Input texts/documents list is empty, "
                             "returning empty list.[/yellow]")
                    return "[]"
                log_func(f"[dim]Number of texts/documents to rerank: "
                         f"{len(input_list)}[/dim]")
            except json.JSONDecodeError:
                return "Error: Input 'texts' is not a valid JSON string."
            except ValueError as e:
                return f"Error: {e}"

            reranker = self._get_reranker(effective_model)

            # Get event loop and run async reranking task
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def run_rerank():
                async with reranker:
                    # get_reranked_documents_async returns List[str]
                    return await reranker.get_reranked_documents_async(
                        query=query,
                        documents=input_list,
                        top_n=top_n,
                        query_image_url=query_image_url
                    )

            reranked_list: List[str] = loop.run_until_complete(run_rerank())

            log_func(f"[bold green]Text reranking completed, returning "
                     f"{len(reranked_list)} results.[/bold green]")

            # Convert reranked list to JSON string
            return json.dumps(reranked_list, ensure_ascii=False)

        except Exception as e:
            log_func(f"[bold red]Error during text reranking: {e}")
            # import traceback
            # traceback.print_exc()
            return f"Error during text reranking: {str(e)}"

    def setup(self):
        """Tool setup (if needed)."""
        pass

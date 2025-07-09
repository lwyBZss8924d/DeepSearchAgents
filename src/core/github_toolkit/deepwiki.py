#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/github_toolkit/deepwiki.py
# code style: PEP 8

"""
[`GitHubRepoQATool(Tool)`] using MCP Client Call DeepWiki Remote MCP Server.
Provides access to DeepWiki's repository documentation and Q&A capabilities.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from smolagents import MCPClient, Tool

logger = logging.getLogger(__name__)


class DeepWikiClient:
    """
    Implementation of a GitHub repository Q&A tool using DeepWiki Remote MCP Server.

    DeepWiki provides AI-powered documentation reading and Q&A for GitHub repos.
    This wrapper wraps the MCP tools for easy integration with DeepSearchAgents.
    """

    def __init__(
        self,
        server_url: str = "https://mcp.deepwiki.com/mcp",
        transport: str = "streamable-http",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize DeepWikiClient to connect DeepWiki Remote MCP Server.

        Args:
            server_url: URL of the DeepWiki Remote MCP server
            transport: Transport protocol (Default: "streamable-http", or "sse")
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.server_url = server_url
        self.transport = transport
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._mcp_client: Optional[MCPClient] = None
        self._tools: Optional[List[Tool]] = None
        self._tools_by_name: Dict[str, Tool] = {}

    def _ensure_connection(self):
        """Ensure MCP client is connected and tools are loaded."""
        if self._mcp_client is None:
            # Configure server parameters based on transport
            if self.transport == "streamable-http":
                server_params = {
                    "url": "https://mcp.deepwiki.com/mcp",
                    "transport": "streamable-http",
                }
            else:
                # or "sse"
                server_params = {"url": self.server_url, "transport": "sse"}

            try:
                self._mcp_client = MCPClient(server_parameters=server_params)
                self._tools = self._mcp_client.get_tools()

                # Build MCP tools lookup by name
                for tool in self._tools:
                    self._tools_by_name[tool.name] = tool

                logger.info(
                    f"Connected to DeepWiki MCP server. "
                    f"Available tools: {list(self._tools_by_name.keys())}"
                )
            except Exception as e:
                logger.error(f"Failed to connect to DeepWiki MCP server: {e}")
                raise

    def _get_tool(self, tool_name: str) -> Tool:
        """Get a specific MCP tool by name."""
        self._ensure_connection()

        if tool_name not in self._tools_by_name:
            available = list(self._tools_by_name.keys())
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available tools: {available}"
            )

        return self._tools_by_name[tool_name]

    async def read_wiki_structure_async(
        self, repo_name: str
    ) -> Dict[str, Any]:
        """
        Get a list of documentation topics for a GitHub repository.

        Args:
            repo_name: GitHub repository in format "owner/repo"

        Returns:
            Dictionary containing documentation structure
        """
        tool = self._get_tool("read_wiki_structure")

        for attempt in range(self.max_retries):
            try:
                result = await tool.aforward(repoName=repo_name)
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for read_wiki_structure: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    async def read_wiki_contents_async(self, repo_name: str) -> Dict[str, Any]:
        """
        View documentation about a GitHub repository.

        Args:
            repo_name: GitHub repository in format "owner/repo"

        Returns:
            Dictionary containing documentation contents
        """
        tool = self._get_tool("read_wiki_contents")

        for attempt in range(self.max_retries):
            try:
                result = await tool.aforward(repoName=repo_name)
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for read_wiki_contents: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    async def ask_question_async(
        self, repo_name: str, question: str
    ) -> Dict[str, Any]:
        """
        Ask any question about a GitHub repository.

        Args:
            repo_name: GitHub repository in format "owner/repo"
            question: Question to ask about the repository

        Returns:
            Dictionary containing the AI-powered answer
        """
        tool = self._get_tool("ask_question")

        for attempt in range(self.max_retries):
            try:
                result = await tool.aforward(
                    repoName=repo_name, question=question
                )
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for ask_question: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    def read_wiki_structure(self, repo_name: str) -> Dict[str, Any]:
        """Synchronous wrapper for read_wiki_structure_async."""
        tool = self._get_tool("read_wiki_structure")

        for attempt in range(self.max_retries):
            try:
                result = tool.forward(repoName=repo_name)
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for read_wiki_structure: {e}"
                )
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    def read_wiki_contents(self, repo_name: str) -> Dict[str, Any]:
        """Synchronous wrapper for read_wiki_contents_async."""
        tool = self._get_tool("read_wiki_contents")

        for attempt in range(self.max_retries):
            try:
                result = tool.forward(repoName=repo_name)
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for read_wiki_contents: {e}"
                )
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    def ask_question(self, repo_name: str, question: str) -> Dict[str, Any]:
        """Synchronous wrapper for ask_question_async."""
        tool = self._get_tool("ask_question")

        for attempt in range(self.max_retries):
            try:
                result = tool.forward(repoName=repo_name, question=question)
                return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for ask_question: {e}"
                )
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {e}",
                    }

    def disconnect(self):
        """Disconnect from the DeepWiki Remote MCP server."""
        if self._mcp_client:
            try:
                self._mcp_client.disconnect()
                logger.info("Disconnected from DeepWiki MCP server")
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {e}")
            finally:
                self._mcp_client = None
                self._tools = None
                self._tools_by_name = {}

    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect()

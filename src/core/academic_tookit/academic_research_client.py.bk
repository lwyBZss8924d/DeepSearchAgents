#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/academic_research_client.py
# code style: PEP 8

"""
Academic Research Client using FutureHouse FALCON API.

This module performs comprehensive research using multiple sources
to generate detailed, structured research reports.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from futurehouse_client import FutureHouseClient, JobNames
from futurehouse_client.models import TaskRequest

logger = logging.getLogger(__name__)


class AcademicResearchClient:
    """
    Deep academic search & research using FutureHouse FALCON API.

    This client performs comprehensive research using multiple sources
    to generate detailed, structured research reports.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 1200,  # 20 minutes default
        max_concurrent_tasks: int = 1,
    ):
        """
        Initialize the academic research client.

        Args:
            api_key: FutureHouse API key. If not provided,
                    uses FUTUREHOUSE_API_KEY env var
            timeout: Timeout in seconds for research tasks
            max_concurrent_tasks: Maximum concurrent research tasks
        """
        if not api_key:
            api_key = os.environ.get("FUTUREHOUSE_API_KEY")
        if not api_key:
            raise ValueError(
                "FutureHouse API key required. "
                "Set FUTUREHOUSE_API_KEY env var "
                "or pass api_key parameter"
            )

        self.client = FutureHouseClient(api_key=api_key)
        self.timeout = timeout
        self.max_concurrent_tasks = max_concurrent_tasks
        self.usage_count = 0
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent_tasks
        )

    def research(
        self,
        query: str,
        initial_context: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Perform synchronous academic research (blocking).

        Args:
            query: Research question or topic
            initial_context: Optional context from previous research
            verbose: Whether to return detailed results

        Returns:
            Research report as structured dictionary
        """
        self.usage_count += 1

        try:
            # Prepare task data
            if isinstance(JobNames.FALCON, str):
                task_request = TaskRequest(
                    name=JobNames.FALCON,
                    query=query
                )
            else:
                task_request = {
                    "name": JobNames.FALCON,
                    "query": query,
                }

            # Add runtime config if we have initial context
            if initial_context:
                if hasattr(task_request, 'runtime_config'):
                    task_request.runtime_config = {
                        "agent": {
                            "agent_kwargs": {
                                "initial_context": initial_context
                            }
                        }
                    }
                else:
                    task_request["runtime_config"] = {
                        "agent": {
                            "agent_kwargs": {
                                "initial_context": initial_context
                            }
                        }
                    }

            # Create task
            task_response = self.client.create_task(task_request)

            # Get task ID
            if hasattr(task_response, 'task_id'):
                task_id = task_response.task_id
            elif isinstance(task_response, dict):
                task_id = task_response.get('task_id')
            else:
                raise ValueError("Could not get task_id from task response")

            # Poll for completion
            task_response = self._wait_for_task_completion(
                task_id,
                timeout=self.timeout,
                verbose=verbose
            )

            # Process and return result
            result = self._process_research_result(task_response, query)
            return result

        except Exception as e:
            logger.error(
                f"Error in deep research for query '{query}': {e}"
            )
            return self._create_error_result(query, str(e))

    def _wait_for_task_completion(
        self,
        task_id: str,
        timeout: int = 1200,
        verbose: bool = True,
        poll_interval: int = 10
    ):
        """
        Wait for a task to complete by polling its status.

        Args:
            task_id: The ID of the task to monitor
            timeout: Maximum time to wait in seconds
            verbose: Whether to get verbose results
            poll_interval: Time between status checks in seconds

        Returns:
            Completed task response

        Raises:
            TimeoutError: If task doesn't complete within timeout
            Exception: If task fails
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Get task status
                task_response = self.client.get_task(
                    task_id=task_id,
                    verbose=verbose
                )

                # Check status
                status = getattr(task_response, 'status', None)
                if status == 'success' or status == 'completed':
                    return task_response
                elif status in ['failed', 'error', 'cancelled']:
                    raise Exception(
                        f"Task {task_id} failed with status: {status}"
                    )

                # Still running, wait before next check
                time.sleep(poll_interval)

            except Exception as e:
                if "failed" in str(e).lower():
                    raise
                logger.warning(f"Error checking task status: {e}")
                time.sleep(poll_interval)

        raise TimeoutError(
            f"Task {task_id} did not complete within {timeout} seconds"
        )

    async def research_async(
        self,
        query: str,
        initial_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform asynchronous academic research.

        Args:
            query: Research question or topic
            initial_context: Optional context from previous research

        Returns:
            Research report as structured dictionary
        """
        self.usage_count += 1

        try:
            # Create task asynchronously
            task_id = await self.create_research_task(
                query, initial_context
            )

            # Wait for and retrieve result
            result = await self.get_research_result(task_id)

            if result:
                return result
            else:
                return self._create_error_result(
                    query, "Task failed or timed out"
                )

        except Exception as e:
            logger.error(
                f"Error in async research for query '{query}': {e}"
            )
            return self._create_error_result(query, str(e))

    async def create_research_task(
        self,
        query: str,
        initial_context: Optional[str] = None
    ) -> str:
        """
        Create an asynchronous academic research task.

        Args:
            query: Research question
            initial_context: Optional context from previous research

        Returns:
            Task ID for tracking the research progress
        """
        task_data = {
            "name": JobNames.FALCON,
            "query": query,
        }

        # Add runtime config if we have initial context
        if initial_context:
            task_data["runtime_config"] = {
                "agent": {
                    "agent_kwargs": {
                        "initial_context": initial_context
                    }
                }
            }

        # Create task using asyncio
        loop = asyncio.get_event_loop()
        task_response = await loop.run_in_executor(
            self._executor,
            self.client.create_task,
            task_data
        )
        return (task_response.task_id if hasattr(task_response, 'task_id')
                else task_response.get('task_id'))

    async def get_research_result(
        self,
        task_id: str,
        poll_interval: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the result of an academic research task.

        Args:
            task_id: Task ID to check
            poll_interval: Seconds between status checks

        Returns:
            Research report data or None if not ready/failed
        """
        elapsed_time = 0

        while elapsed_time < self.timeout:
            try:
                # Get task status using asyncio
                loop = asyncio.get_event_loop()
                task_status = await loop.run_in_executor(
                    self._executor,
                    self.client.get_task,
                    task_id,
                    False,  # history
                    True   # verbose
                )

                if task_status.status == "success":
                    return self._process_research_result(
                        task_status, "Async research query"
                    )
                elif task_status.status in ["failed", "error"]:
                    logger.error(
                        f"Research task {task_id} failed"
                    )
                    return None

                # Still processing, wait before next check
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

            except Exception as e:
                logger.error(
                    f"Error checking research task {task_id}: {e}"
                )
                return None

        logger.warning(
            f"Research task {task_id} timed out after {self.timeout}s"
        )
        return None

    def _process_research_result(
        self,
        task_response,
        query: str
    ) -> Dict[str, Any]:
        """
        Process research task response into standard format.

        Args:
            task_response: Response from FutureHouse API
            query: Original research query

        Returns:
            Standardized research report dictionary
        """
        try:
            # Extract the comprehensive report
            report_content = getattr(task_response, 'answer', '')
            formatted_content = getattr(
                task_response, 'formatted_answer', report_content
            )

            # Extract sections from the report if possible
            sections = self._extract_sections(formatted_content)

            # Build the result
            result = {
                'title': 'Comprehensive Research Report',
                'query': query,
                'content': formatted_content,
                'sections': sections,
                'url': (f'futurehouse://falcon/'
                        f'{getattr(task_response, "task_id", "unknown")}'),
                'meta': {
                    'source_type': 'academic_research_report',
                    'task_id': getattr(task_response, 'task_id', ''),
                    'has_successful_answer': getattr(
                        task_response,
                        'has_successful_answer',
                        True
                    ),
                    'status': getattr(task_response, 'status', 'unknown')
                }
            }

            # If verbose, include additional metadata
            if hasattr(task_response, 'environment_frame'):
                env_data = task_response.environment_frame
                if isinstance(env_data, dict):
                    # Extract sources/references if available
                    if 'sources' in env_data:
                        result['sources'] = env_data['sources']
                    if 'references' in env_data:
                        result['references'] = env_data['references']
                    # Store full environment data in meta
                    result['meta']['environment_data'] = env_data

            return result

        except Exception as e:
            logger.error(f"Error processing research result: {e}")
            return self._create_error_result(
                query, f"Result processing error: {e}"
            )

    def _extract_sections(self, content: str) -> List[str]:
        """
        Extract section titles from markdown content.

        Args:
            content: Markdown formatted content

        Returns:
            List of section titles
        """
        sections = []
        lines = content.split('\n')

        for line in lines:
            # Look for markdown headers
            if line.strip().startswith('#'):
                # Remove # symbols and whitespace
                section = line.strip().lstrip('#').strip()
                if section:
                    sections.append(section)

        return sections

    def _create_error_result(
        self,
        query: str,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Create a standardized error result.

        Args:
            query: Original query
            error_message: Error description

        Returns:
            Error result dictionary
        """
        return {
            'title': 'Research Error',
            'query': query,
            'content': f"Error: {error_message}",
            'sections': [],
            'url': 'error://research_failed',
            'meta': {
                'source_type': 'error',
                'error': error_message,
                'has_successful_answer': False
            }
        }

    def close(self):
        """Clean up resources."""
        self._executor.shutdown(wait=True)

    def get_usage_stats(self) -> Dict[str, int]:
        """
        Get usage statistics.

        Returns:
            Dictionary with usage counts
        """
        return {
            "research_count": self.usage_count
        }

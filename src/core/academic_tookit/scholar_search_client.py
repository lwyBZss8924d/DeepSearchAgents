#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/scholar_search_client.py
# code style: PEP 8

"""
Scholar Search Client using FutureHouse CROW API for academic retrieval.

This module provides high-accuracy, cited responses from scientific data
sources for academic queries using FutureHouse Platform's CROW API.
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional

from futurehouse_client import FutureHouseClient, JobNames
from futurehouse_client.models import TaskRequest

logger = logging.getLogger(__name__)


class ScholarSearchClient:
    """
    Scholar search client using FutureHouse CROW API for academic retrieval.

    This client provides high-accuracy, cited responses from
    scientific data sources for academic queries.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 600,
        verbose: bool = False,
    ):
        """
        Initialize the academic search client.

        Args:
            api_key: FutureHouse API key. If not provided,
                    uses FUTUREHOUSE_API_KEY env var
            timeout: Timeout in seconds for API calls
            verbose: Whether to retrieve verbose task responses
                    with full metadata
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
        self.verbose = verbose
        self.usage_count = 0

    def search(
        self,
        query: str,
        num_results: int = 20,
        verbose: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Search academic literature for a query.

        Args:
            query: The research question or search query
            num_results: Maximum number of results to return
            verbose: Override instance verbose setting

        Returns:
            List of search results with standardized format
        """
        use_verbose = verbose if verbose is not None else self.verbose
        self.usage_count += 1

        try:
            # Create task request for CROW (fast academic search)
            if isinstance(JobNames.CROW, str):
                task_request = TaskRequest(
                    name=JobNames.CROW,
                    query=query
                )
            else:
                # Handle if JobNames.CROW is not a string
                task_request = {
                    "name": JobNames.CROW,
                    "query": query
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
                verbose=use_verbose
            )

            # Extract and format results
            results = self._extract_search_results(
                task_response,
                query,
                num_results
            )

            return results

        except Exception as e:
            logger.error(
                f"Error in academic search for query '{query}': {e}"
            )
            return []

    def _wait_for_task_completion(
        self,
        task_id: str,
        timeout: int = 600,
        verbose: bool = False,
        poll_interval: int = 5
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

    def _extract_search_results(
        self,
        task_response,
        query: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Extract structured results from FutureHouse task response.

        Args:
            task_response: Response from FutureHouse API
            query: Original search query
            num_results: Maximum number of results

        Returns:
            List of standardized result dictionaries
        """
        results = []

        # If verbose mode, extract from environment_frame
        if self.verbose and hasattr(task_response, 'environment_frame'):
            env_data = task_response.environment_frame

            # Extract paper contexts if available
            if isinstance(env_data, dict) and 'contexts' in env_data:
                for i, context in enumerate(
                    env_data['contexts'][:num_results]
                ):
                    result = {
                        'title': context.get('title', 'Academic Paper'),
                        'url': context.get(
                            'url',
                            f'paper://{context.get("doc_id", "unknown")}'
                        ),
                        'description': context.get('summary', ''),
                        'snippets': [context.get('text', '')],
                        'meta': {
                            'query': query,
                            'score': context.get('score', 0.0),
                            'doc_id': context.get('doc_id', ''),
                            'source_type': 'academic_paper',
                            'position': i + 1,
                            'authors': context.get('authors', []),
                            'year': context.get('year'),
                            'journal': context.get('journal', ''),
                            'doi': context.get('doi', '')
                        }
                    }
                    results.append(result)

        # If no verbose results or not enough, create from answer
        if not results and hasattr(task_response, 'answer'):
            answer_text = task_response.answer
            formatted_answer = getattr(
                task_response,
                'formatted_answer',
                answer_text
            )

            # Create a synthetic result from the answer
            result = {
                'title': f'Academic Search: {query[:50]}...',
                'url': (f'futurehouse://crow/'
                        f'{getattr(task_response, "task_id", "unknown")}'),
                'description': 'Synthesized academic search result',
                'snippets': [formatted_answer],
                'meta': {
                    'query': query,
                    'source_type': 'academic_synthesis',
                    'has_successful_answer': getattr(
                        task_response,
                        'has_successful_answer',
                        True
                    ),
                    'task_id': getattr(task_response, 'task_id', '')
                }
            }
            results.append(result)

        return results[:num_results]

    def get_usage_stats(self) -> Dict[str, int]:
        """
        Get usage statistics.

        Returns:
            Dictionary with usage counts
        """
        return {
            "search_count": self.usage_count
        }

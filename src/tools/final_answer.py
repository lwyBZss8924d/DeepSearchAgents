#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/tools/final_answer.py
# code style: PEP 8

"""
Enhanced FinalAnswerTool implementation to standardize output format across
DeepSearchAgents, ReAct and CodeAct agents.
"""

import json
import logging
from typing import Any, Dict, List

from smolagents.default_tools import FinalAnswerTool as BaseFinaAnswerTool

logger = logging.getLogger(__name__)


class EnhancedFinalAnswerTool(BaseFinaAnswerTool):
    """
    Enhanced version of FinalAnswerTool to standardize output formats
    across ReAct and CodeAct agents.

    This tool ensures that:
    1. Final answers are consistently formatted with the same Markdown
       rendering
    2. Source URL lists are consistently formatted and positioned in the output
    3. JSON schema is standardized for both agent types
    """

    name = "final_answer"
    description = "Provides a standardized final answer to the given problem."
    inputs = {
        "answer": {
            "type": "object",
            "description": (
                "The final answer to the problem. Can be a string or "
                "a JSON object with content, title, and sources fields"
            )
        }
    }
    output_type = "object"

    def forward(self, answer: Any) -> Any:
        """
        Process the answer to ensure consistent formatting.

        Args:
            answer: The final answer, which can be a string or a structured
            object

        Returns:
            A standardized JSON object with consistent formatting
        """
        try:
            # If answer is a string that contains valid JSON, parse it
            if (isinstance(answer, str) and answer.strip().startswith('{')
                    and answer.strip().endswith('}')):
                try:
                    answer = json.loads(answer)
                except json.JSONDecodeError:
                    # Not valid JSON, continue with string processing
                    pass

            # Process based on input type
            if isinstance(answer, dict):
                # Already structured, ensure it has all required fields
                return self._standardize_json_object(answer)
            elif isinstance(answer, str):
                # Convert string to standardized object
                return self._standardize_string_answer(answer)
            else:
                # Handle other types by converting to string
                return self._standardize_string_answer(str(answer))

        except Exception as e:
            logger.error(f"Error processing final answer: {e}")
            # In case of error, return a simple object with the raw answer
            return {
                "title": "Final Answer",
                "content": str(answer),
                "sources": [],
                "type": "final_answer",
                "format": "markdown"
            }

    def _standardize_json_object(self, answer_dict: Dict) -> Dict:
        """
        Ensure JSON object has standard format.
        """
        # Basic fields
        standardized = {
            "title": answer_dict.get("title", "Final Answer"),
            "content": "",
            "sources": [],
            "type": "final_answer",
            "format": "markdown"
        }

        # Process content field
        if "content" in answer_dict:
            standardized["content"] = answer_dict["content"]
        elif "answer" in answer_dict:
            standardized["content"] = answer_dict["answer"]
        elif "markdown" in answer_dict:
            standardized["content"] = answer_dict["markdown"]
        elif "text" in answer_dict:
            standardized["content"] = answer_dict["text"]

        # Process sources field
        if (
            "sources" in answer_dict and
            isinstance(answer_dict["sources"], list)
        ):
            standardized["sources"] = answer_dict["sources"]

        # Ensure content contains sources
        if (standardized["sources"] and
                "## Sources" not in standardized["content"]):
            sources_text = "\n\n## Sources\n\n"
            for i, url in enumerate(standardized["sources"]):
                sources_text += f"{i+1}. [{url}]({url})\n"
            standardized["content"] += sources_text

        return standardized

    def _standardize_string_answer(self, answer_str: str) -> Dict:
        """
        Convert a string answer to the standardized JSON object format.

        Args:
            answer_str: String containing the answer

        Returns:
            Standardized dictionary with all required fields
        """
        # Extract potential URLs from the string
        import re
        urls = []

        # Look for URL patterns in the text
        url_pattern = r'https?://[^\s)>]+'
        found_urls = re.findall(url_pattern, answer_str)

        # Remove URLs from content but save them for sources
        if found_urls:
            urls = found_urls

        return {
            "title": "Final Answer",
            "content": answer_str,
            "sources": urls
        }

    def _append_sources_to_content(
        self,
        content: str,
        sources: List[str]
    ) -> str:
        """
        Append sources in Markdown format to the content
        if they don't already exist.

        Args:
            content: The main content text
            sources: List of source URLs

        Returns:
            Content with sources appended in Markdown format
        """
        if not sources:
            return content

        # Check if content already ends with sources section
        has_sources_section = "## Sources" in content and any(
            url in content for url in sources
        )
        if has_sources_section:
            return content

        # Add newlines to ensure proper spacing
        if not content.endswith('\n\n'):
            if content.endswith('\n'):
                content += '\n'
            else:
                content += '\n\n'

        # Format sources in Markdown
        content += "## Sources\n\n"
        for i, url in enumerate(sources):
            # Extract a title from the URL or use a generic one
            url_parts = url.split("/")
            title = ""
            # Try to get a meaningful title from the URL
            if len(url_parts) > 2:
                # Use last part of URL path, cleaned up
                raw_title = url_parts[-1] if url_parts[-1] else url_parts[-2]
                # Remove file extensions and clean up
                title = (raw_title.split('.')[0]
                         .replace('-', ' ')
                         .replace('_', ' ')
                         .capitalize())

            # If we couldn't extract a meaningful title, use a generic one
            if not title:
                title = f"Source {i+1}"

            # Add the numbered reference with consistent format
            content += f"{i+1}. [{title}]({url})\n"

        return content

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/utils/search_token_counter.py
# code style: PEP 8

"""
Unified token counting system for search providers.

This module provides a consistent interface for counting tokens across different
search providers, supporting native API token counts and approximate counting.

Token Counting Strategy:
1. Native API counts (when available): Most accurate for billing purposes
   - Jina AI: Returns token usage in API response
   - XAI (Grok): Returns token usage in API response

2. Approximate counting (default): Conservative estimate for providers without documentation
   - Serper: No documented token counting method
   - Exa: No documented token counting method
   - Uses 4 characters per token (industry standard approximation)
   - Sufficient for result size control and splitting in agent tools
"""

import json
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class SearchUsage:
    """Enhanced token usage statistics with source tracking."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    counting_method: str = "unknown"  # "native", "approximate"


# Token counter configuration
TOKENIZER_CONFIG = {
    "default_model": "approximate",  # Default to approximate counting
    "chars_per_token": 4.0,  # Conservative estimate for general text
    "extra_tokens_per_message": 3.0,
    "json_overhead_factor": 1.1,  # Account for JSON structure overhead
    "provider_models": {
        "jina": "native",  # Jina provides native token usage
        "xai": "native",  # XAI provides native token usage
        "serper": "approximate",  # No documented token counting, use approximate
        "exa": "approximate",  # No documented token counting, use approximate
    },
}


class TokenCounter(ABC):
    """Abstract base class for token counting strategies."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        pass

    @abstractmethod
    def count_search_usage(self, query: str, response: Union[str, Dict, List]) -> SearchUsage:
        """Count tokens for a search query and response."""
        pass

    def _serialize_response(self, response: Union[str, Dict, List]) -> str:
        """Convert response to string for token counting."""
        if isinstance(response, str):
            return response
        try:
            return json.dumps(response, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(response)


class NativeTokenCounter(TokenCounter):
    """Token counter that extracts usage from API response."""

    def count_tokens(self, text: str) -> int:
        """Not applicable for native counting."""
        raise NotImplementedError("Native counter uses API response data")

    def count_search_usage(self, query: str, response: Union[str, Dict, List]) -> SearchUsage:
        """Extract token usage from API response."""
        if not isinstance(response, dict):
            logger.warning("Native token counter expects dict response")
            return SearchUsage(counting_method="native_failed")

        # Try to extract usage information from response
        usage = response.get("usage", {})
        if isinstance(usage, dict):
            return SearchUsage(
                total_tokens=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                counting_method="native",
            )

        # Try SearchUsage object (for providers that return our dataclass)
        if hasattr(usage, "total_tokens"):
            return SearchUsage(
                total_tokens=getattr(usage, "total_tokens", 0),
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
                counting_method="native",
            )

        logger.warning("No usage data found in API response")
        return SearchUsage(counting_method="native_failed")


class ApproximateTokenCounter(TokenCounter):
    """Token counter using character-based approximation."""

    def __init__(self, chars_per_token: Optional[float] = None, extra_tokens_per_message: Optional[float] = None):
        """
        Initialize approximate counter with custom parameters.

        Args:
            chars_per_token: Average characters per token
            extra_tokens_per_message: Extra tokens to add per message
        """
        self.chars_per_token = chars_per_token if chars_per_token is not None else TOKENIZER_CONFIG["chars_per_token"]
        self.extra_tokens_per_message = (
            extra_tokens_per_message
            if extra_tokens_per_message is not None
            else TOKENIZER_CONFIG["extra_tokens_per_message"]
        )

    def count_tokens(self, text: str) -> int:
        """Approximate token count based on character length."""
        if not text:
            return 0

        # Basic character-based approximation
        char_count = len(text)
        token_count = char_count / self.chars_per_token

        # Add extra tokens for message structure
        token_count += self.extra_tokens_per_message

        return math.ceil(token_count)

    def count_search_usage(self, query: str, response: Union[str, Dict, List]) -> SearchUsage:
        """Count tokens for search query and response."""
        prompt_tokens = self.count_tokens(query)

        # Serialize response and count
        response_str = self._serialize_response(response)
        completion_tokens = self.count_tokens(response_str)

        # Apply JSON overhead factor
        if not isinstance(response, str):
            completion_tokens = int(completion_tokens * TOKENIZER_CONFIG["json_overhead_factor"])

        total_tokens = prompt_tokens + completion_tokens

        return SearchUsage(
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            counting_method="approximate",
        )


# Cache for token counter instances
_token_counter_cache = {}


def get_token_counter(provider: str, model: Optional[str] = None) -> TokenCounter:
    """
    Get appropriate token counter for a provider.

    Args:
        provider: Name of the search provider
        model: Optional model name for tokenizer (not used anymore)

    Returns:
        TokenCounter instance
    """
    cache_key = f"{provider}:{model or 'default'}"

    if cache_key in _token_counter_cache:
        return _token_counter_cache[cache_key]

    # Determine counting method
    provider_config = TOKENIZER_CONFIG["provider_models"].get(provider.lower(), TOKENIZER_CONFIG["default_model"])

    if provider_config == "native":
        counter = NativeTokenCounter()
    else:
        # Default to approximate counting for all non-native providers
        counter = ApproximateTokenCounter()

    _token_counter_cache[cache_key] = counter
    return counter


def count_search_tokens(
    query: str,
    response: Union[str, Dict, List],
    provider: str,
    native_usage: Optional[Dict[str, int]] = None,
    tokenizer_model: Optional[str] = None,
) -> SearchUsage:
    """
    Unified function to count tokens for search operations.

    Args:
        query: Search query string
        response: API response (string, dict, or list)
        provider: Name of the search provider
        native_usage: Optional native usage data from API
        tokenizer_model: Optional specific tokenizer model (not used anymore)

    Returns:
        SearchUsage object with token counts
    """
    # If native usage is provided, use it
    if native_usage:
        return SearchUsage(
            total_tokens=native_usage.get("total_tokens", 0),
            prompt_tokens=native_usage.get("prompt_tokens", 0),
            completion_tokens=native_usage.get("completion_tokens", 0),
            counting_method="native",
        )

    # Get appropriate counter
    counter = get_token_counter(provider, tokenizer_model)

    # Count tokens
    return counter.count_search_usage(query, response)


# Example usage
if __name__ == "__main__":
    # Test approximate counting
    approx_counter = ApproximateTokenCounter()
    usage = approx_counter.count_search_usage(
        "What is artificial intelligence?", {"results": ["AI is...", "Machine learning..."]}
    )
    print(f"Approximate usage: {usage}")

    # Approximate counting is sufficient for all use cases

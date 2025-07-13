#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/search_engines/search_hybrid.py
# code style: PEP 8

"""
Hybrid Search Engine that aggregates results from multiple providers for
any LLM Agent functionCall ToolCalling Wrapping Standardized
(e.g., OpenAI functionCall, JSON Mode, MCP Wrapping, Gemini ToolCalling,
Anthropic ToolCalling, etc.)

This module provides a unified interface for searching across multiple
search engines (Serper, XAI, Jina, Exa) with intelligent deduplication,
parallel execution, and standardized result formatting.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Literal, Set
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from concurrent.futures import ThreadPoolExecutor

from .base import BaseSearchClient
from .search_serper import GoogleSerperClient
from .search_xcom import XAISearchClient
from .search_jina import JinaSearchClient
from .search_exa import ExaSearchClient
from .utils.search_token_counter import SearchUsage


logger = logging.getLogger(__name__)


class HybridSearchEngine(BaseSearchClient):
    """
    Hybrid search engine that aggregates results from multiple providers.

    Features:
    - Parallel search execution across providers
    - Intelligent URL deduplication
    - Unified result format with provider tracking
    - Configurable aggregation strategies
    - Automatic failover when providers fail
    - Aggregate token usage tracking
    """

    # Supported providers
    SUPPORTED_PROVIDERS = ["serper", "xai", "jina", "exa"]

    # Default provider priorities (higher = better)
    PROVIDER_PRIORITIES = {
        "serper": 4,  # Google search, best for general web
        "xai": 3,     # Good for X.com and AI content
        "jina": 2,    # Good for LLM-optimized content
        "exa": 1,     # Neural search, good for semantic queries
    }

    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        providers: Optional[List[str]] = None,
        timeout: int = 30,
        max_retries: int = 2,
        parallel: bool = True,
        deduplicate: bool = True,
    ):
        """
        Initialize HybridSearchEngine.

        Args:
            api_keys: Dict mapping provider names to API keys
            providers: List of providers to use (defaults to all available)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per provider
            parallel: Execute searches in parallel
            deduplicate: Enable URL deduplication
        """
        super().__init__(
            api_key=None,  # We manage multiple keys
            timeout=timeout,
            max_retries=max_retries,
        )

        self.api_keys = api_keys or {}
        self.parallel = parallel
        self.deduplicate = deduplicate

        # Initialize provider clients
        self.clients = {}
        self._initialize_clients(providers)

        if not self.clients:
            raise ValueError(
                "No search providers available. Please provide API keys."
            )

        logger.info(
            f"HybridSearchEngine initialized with providers: "
            f"{list(self.clients.keys())}"
        )

    def _initialize_clients(self, providers: Optional[List[str]] = None):
        """Initialize search provider clients."""
        # Determine which providers to use
        if providers:
            requested_providers = [p for p in providers
                                   if p in self.SUPPORTED_PROVIDERS]
        else:
            requested_providers = self.SUPPORTED_PROVIDERS

        # Try to initialize each provider
        for provider in requested_providers:
            try:
                client = self._create_client(provider)
                if client:
                    self.clients[provider] = client
            except Exception as e:
                logger.warning(
                    f"Failed to initialize {provider} client: {str(e)}"
                )

    def _create_client(self, provider: str) -> Optional[BaseSearchClient]:
        """Create a client for a specific provider."""
        api_key = self.api_keys.get(provider)

        if provider == "serper":
            if api_key:
                return GoogleSerperClient(
                    api_key=api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )
        elif provider == "xai":
            if api_key:
                return XAISearchClient(
                    api_key=api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )
        elif provider == "jina":
            if api_key:
                return JinaSearchClient(
                    api_key=api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )
        elif provider == "exa":
            if api_key:
                return ExaSearchClient(
                    api_key=api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )

        return None

    def search(
        self,
        query: str,
        num: int = 10,
        providers: Optional[List[str]] = None,
        aggregation_strategy: Literal["merge", "round_robin", "priority"] = "merge",
        search_type: Literal["auto", "neural", "keyword"] = "auto",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform aggregated search across multiple providers.

        Args:
            query: Search query string
            num: Number of results to return per provider
            providers: Specific providers to use (defaults to all)
            aggregation_strategy: How to combine results:
                - "merge": Combine all results, deduplicate
                - "round_robin": Alternate between providers
                - "priority": Use provider priority ordering
            search_type: Type of search (auto, neural, keyword)
            include_domains: Domains to include in search
            exclude_domains: Domains to exclude from search
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            page: Page number for pagination (default: 1)
            per_page: Results per page (default: None, returns all)
            **kwargs: Additional provider-specific parameters

        Returns:
            Aggregated search results with metadata
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Determine which providers to use
        active_providers = self._get_active_providers(providers)
        if not active_providers:
            raise ValueError("No active search providers available")

        # Execute searches
        if self.parallel:
            results_by_provider = self._search_parallel(
                query, num, active_providers, search_type,
                include_domains, exclude_domains, start_date, end_date,
                **kwargs
            )
        else:
            results_by_provider = self._search_sequential(
                query, num, active_providers, search_type,
                include_domains, exclude_domains, start_date, end_date,
                **kwargs
            )

        # Aggregate results
        aggregated_results = self._aggregate_results(
            results_by_provider, aggregation_strategy
        )

        # Apply pagination if requested
        total_results = len(aggregated_results)
        if per_page is not None and per_page > 0:
            # Calculate pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = aggregated_results[start_idx:end_idx]
            total_pages = (total_results + per_page - 1) // per_page
        else:
            # Return all results
            paginated_results = aggregated_results
            total_pages = 1

        # Calculate total usage
        total_usage = self._aggregate_usage(results_by_provider)

        return {
            "results": paginated_results,
            "query": query,
            "total_results": total_results,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "results_by_provider": {
                p: len(r.get("results", []))
                for p, r in results_by_provider.items()
            },
            "usage": total_usage,
            "providers_used": list(results_by_provider.keys()),
            "aggregation_strategy": aggregation_strategy,
        }

    def _get_active_providers(
        self,
        providers: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of active providers to use."""
        if providers:
            # Use only requested providers that are available
            return [p for p in providers if p in self.clients]
        else:
            # Use all available providers
            return list(self.clients.keys())

    def _search_parallel(
        self,
        query: str,
        num: int,
        providers: List[str],
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """Execute searches in parallel across providers."""
        results = {}

        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {}

            for provider in providers:
                future = executor.submit(
                    self._search_single_provider,
                    provider, query, num, search_type,
                    include_domains, exclude_domains,
                    start_date, end_date, **kwargs
                )
                futures[future] = provider

            for future in futures:
                provider = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    if result:
                        results[provider] = result
                except Exception as e:
                    logger.error(
                        f"Error in {provider} search: {str(e)}"
                    )

        return results

    async def _search_parallel_async(
        self,
        query: str,
        num: int,
        providers: List[str],
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """Execute searches in parallel asynchronously across providers."""
        tasks = []
        provider_mapping = {}

        for provider in providers:
            task = asyncio.create_task(
                self._search_single_provider_async(
                    provider, query, num, search_type,
                    include_domains, exclude_domains,
                    start_date, end_date, **kwargs
                )
            )
            tasks.append(task)
            provider_mapping[id(task)] = provider

        # Wait for all tasks with timeout
        results = {}
        done, pending = await asyncio.wait(
            tasks, timeout=self.timeout, return_when=asyncio.ALL_COMPLETED
        )

        # Cancel any pending tasks
        for task in pending:
            task.cancel()

        # Collect results from completed tasks
        for task in done:
            provider = provider_mapping[id(task)]
            try:
                result = await task
                if result:
                    results[provider] = result
            except Exception as e:
                logger.error(f"Error in {provider} async search: {str(e)}")

        return results

    def _search_sequential(
        self,
        query: str,
        num: int,
        providers: List[str],
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """Execute searches sequentially across providers."""
        results = {}

        for provider in providers:
            try:
                result = self._search_single_provider(
                    provider, query, num, search_type,
                    include_domains, exclude_domains,
                    start_date, end_date, **kwargs
                )
                if result:
                    results[provider] = result
            except Exception as e:
                logger.error(
                    f"Error in {provider} search: {str(e)}"
                )

        return results

    def _search_single_provider(
        self,
        provider: str,
        query: str,
        num: int,
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Execute search on a single provider."""
        client = self.clients.get(provider)
        if not client:
            return None

        try:
            # Map parameters to provider-specific format
            provider_params = self._map_provider_params(
                provider, search_type, include_domains, exclude_domains,
                start_date, end_date, **kwargs
            )

            # Execute search
            result = client.search(query=query, num=num, **provider_params)

            # Ensure consistent result format
            if result and "results" in result:
                # Add provider info to each result
                for item in result.get("results", []):
                    if isinstance(item, dict):
                        item["provider"] = provider

            return result

        except Exception as e:
            logger.error(
                f"Failed to search with {provider}: {str(e)}"
            )
            return None

    async def _search_single_provider_async(
        self,
        provider: str,
        query: str,
        num: int,
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Execute async search on a single provider."""
        client = self.clients.get(provider)
        if not client:
            return None

        try:
            # Map parameters to provider-specific format
            provider_params = self._map_provider_params(
                provider, search_type, include_domains, exclude_domains,
                start_date, end_date, **kwargs
            )

            # Execute async search based on provider
            if provider == "serper" and hasattr(client, "asearch"):
                # GoogleSerperClient uses 'asearch' method
                result = await client.asearch(query=query, num=num, **provider_params)
            elif hasattr(client, "search_async"):
                # Other providers use 'search_async' method
                result = await client.search_async(query=query, num=num, **provider_params)
            else:
                # Fallback to sync search in executor if no async method
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: client.search(query=query, num=num, **provider_params)
                )

            # Ensure consistent result format
            if result and "results" in result:
                # Add provider info to each result
                for item in result.get("results", []):
                    if isinstance(item, dict):
                        item["provider"] = provider

            return result

        except Exception as e:
            logger.error(
                f"Failed to search with {provider} (async): {str(e)}"
            )
            return None

    def _map_provider_params(
        self,
        provider: str,
        search_type: str,
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Map unified parameters to provider-specific format."""
        params = {}

        if provider == "serper":
            # Serper uses 'search_type' parameter
            if search_type != "auto":
                params["search_type"] = "search"  # Serper only has regular search

            # Domain filters
            if include_domains:
                params["include_domains"] = include_domains
            if exclude_domains:
                params["exclude_domains"] = exclude_domains

            # Date filters (Serper uses tbs parameter)
            if start_date or end_date:
                # Convert to Serper's time-based search format
                if start_date and end_date:
                    params["tbs"] = f"cdr:1,cd_min:{start_date},cd_max:{end_date}"
                elif start_date:
                    params["tbs"] = f"cdr:1,cd_min:{start_date}"
                elif end_date:
                    params["tbs"] = f"cdr:1,cd_max:{end_date}"

        elif provider == "xai":
            # XAI parameters
            params["mode"] = "auto"  # XAI uses mode instead of search_type

            # Date filters
            if start_date:
                params["from_date"] = start_date
            if end_date:
                params["to_date"] = end_date

            # XAI-specific parameters from kwargs
            if "x_handles" in kwargs:
                params["x_handles"] = kwargs["x_handles"]
            if "sources" in kwargs:
                params["sources"] = kwargs["sources"]
            else:
                # Default to web and X sources
                params["sources"] = ["web", "x"]

        elif provider == "jina":
            # Jina parameters
            if search_type == "neural":
                params["engine"] = "browser"  # Better quality
            else:
                params["engine"] = "direct"  # Faster

            # Domain filter (Jina only supports single domain)
            if include_domains and len(include_domains) == 1:
                params["domain"] = include_domains[0]

        elif provider == "exa":
            # Exa parameters
            if search_type != "auto":
                params["search_type"] = search_type

            # Domain filters
            if include_domains:
                params["include_domains"] = include_domains
            if exclude_domains:
                params["exclude_domains"] = exclude_domains

            # Date filters
            if start_date:
                params["start_published_date"] = start_date
            if end_date:
                params["end_published_date"] = end_date

            # Exa-specific
            if search_type == "neural":
                params["use_autoprompt"] = True

        # Add any provider-specific kwargs
        provider_key = f"{provider}_params"
        if provider_key in kwargs:
            params.update(kwargs[provider_key])

        return params

    def _aggregate_results(
        self,
        results_by_provider: Dict[str, Dict[str, Any]],
        strategy: str
    ) -> List[Dict[str, Any]]:
        """Aggregate results from multiple providers."""
        all_results = []

        # Collect all results
        for provider, response in results_by_provider.items():
            if response and "results" in response:
                for result in response["results"]:
                    # Normalize result format
                    normalized = self._normalize_result(result, provider)
                    if normalized:
                        all_results.append(normalized)

        # Apply deduplication if enabled
        if self.deduplicate:
            all_results = self._deduplicate_results(all_results)

        # Apply aggregation strategy
        if strategy == "merge":
            # Simple merge, already done
            pass
        elif strategy == "round_robin":
            all_results = self._round_robin_results(
                results_by_provider, self.deduplicate
            )
        elif strategy == "priority":
            all_results = self._priority_results(all_results)

        return all_results

    def _normalize_result(
        self,
        result: Any,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """Normalize result to unified format."""
        # Handle different result formats
        if hasattr(result, "__dict__"):
            # Convert dataclass to dict
            result_dict = result.__dict__
        elif isinstance(result, dict):
            result_dict = result
        else:
            return None

        # Extract common fields
        normalized = {
            "title": result_dict.get("title", ""),
            "url": result_dict.get("url", "") or result_dict.get("link", ""),
            "content": (
                result_dict.get("content", "") or
                result_dict.get("snippet", "") or
                result_dict.get("description", "") or
                result_dict.get("extract", "")
            ),
            "snippet": result_dict.get("snippet", ""),
            "provider": provider,
            "score": result_dict.get("score", 0.0),
            "published_date": result_dict.get("published_date"),
            "author": result_dict.get("author"),
            "provider_metadata": {
                k: v for k, v in result_dict.items()
                if k not in ["title", "url", "content", "snippet",
                             "score", "published_date", "author", "provider"]
            }
        }

        # Ensure URL is present
        if not normalized["url"]:
            return None

        return normalized

    def _deduplicate_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate results based on normalized URLs."""
        seen_urls: Set[str] = set()
        unique_results = []

        for result in results:
            normalized_url = self._normalize_url(result["url"])
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
            else:
                # If duplicate, merge metadata if score is higher
                for idx, existing in enumerate(unique_results):
                    if self._normalize_url(existing["url"]) == normalized_url:
                        if result.get("score", 0) > existing.get("score", 0):
                            # Keep result with higher score
                            unique_results[idx] = result
                        break

        return unique_results

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        try:
            # Parse URL
            parsed = urlparse(url.lower())

            # Remove common tracking parameters
            if parsed.query:
                params = parse_qs(parsed.query)
                # Remove tracking params
                tracking_params = {
                    "utm_source", "utm_medium", "utm_campaign",
                    "utm_term", "utm_content", "fbclid", "gclid",
                    "ref", "source"
                }
                cleaned_params = {
                    k: v for k, v in params.items()
                    if k not in tracking_params
                }
                query = urlencode(cleaned_params, doseq=True)
            else:
                query = ""

            # Remove trailing slash
            path = parsed.path.rstrip("/") or "/"

            # Remove www. prefix
            netloc = parsed.netloc
            if netloc.startswith("www."):
                netloc = netloc[4:]

            # Reconstruct normalized URL
            normalized = urlunparse((
                parsed.scheme,
                netloc,
                path,
                parsed.params,
                query,
                ""  # Remove fragment
            ))

            return normalized

        except Exception:
            # If normalization fails, return original URL
            return url.lower()

    def _round_robin_results(
        self,
        results_by_provider: Dict[str, Dict[str, Any]],
        deduplicate: bool
    ) -> List[Dict[str, Any]]:
        """Aggregate results using round-robin strategy."""
        # Create iterators for each provider's results
        iterators = {}
        for provider, response in results_by_provider.items():
            if response and "results" in response:
                results = [
                    self._normalize_result(r, provider)
                    for r in response["results"]
                ]
                iterators[provider] = iter([r for r in results if r])

        # Round-robin collection
        aggregated = []
        seen_urls: Set[str] = set() if deduplicate else set()

        while iterators:
            providers_to_remove = []

            for provider, iterator in iterators.items():
                try:
                    result = next(iterator)
                    if deduplicate:
                        normalized_url = self._normalize_url(result["url"])
                        if normalized_url not in seen_urls:
                            seen_urls.add(normalized_url)
                            aggregated.append(result)
                    else:
                        aggregated.append(result)
                except StopIteration:
                    providers_to_remove.append(provider)

            # Remove exhausted iterators
            for provider in providers_to_remove:
                del iterators[provider]

        return aggregated

    def _priority_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sort results by provider priority."""
        return sorted(
            results,
            key=lambda x: (
                self.PROVIDER_PRIORITIES.get(x["provider"], 0),
                x.get("score", 0)
            ),
            reverse=True
        )

    def _aggregate_usage(
        self,
        results_by_provider: Dict[str, Dict[str, Any]]
    ) -> SearchUsage:
        """Aggregate token usage from all providers."""
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0

        for provider, response in results_by_provider.items():
            if response and "usage" in response:
                usage = response["usage"]
                if isinstance(usage, dict):
                    total_tokens += usage.get("total_tokens", 0)
                    prompt_tokens += usage.get("prompt_tokens", 0)
                    completion_tokens += usage.get("completion_tokens", 0)
                elif hasattr(usage, "total_tokens"):
                    total_tokens += getattr(usage, "total_tokens", 0)
                    prompt_tokens += getattr(usage, "prompt_tokens", 0)
                    completion_tokens += getattr(usage, "completion_tokens", 0)

        return SearchUsage(
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            counting_method="aggregate"
        )

    async def search_async(
        self,
        query: str,
        num: int = 10,
        providers: Optional[List[str]] = None,
        aggregation_strategy: Literal["merge", "round_robin", "priority"] = "merge",
        search_type: Literal["auto", "neural", "keyword"] = "auto",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of search method with true async support.

        Args:
            query: Search query string
            num: Number of results to return per provider
            providers: Specific providers to use (defaults to all)
            aggregation_strategy: How to combine results
            search_type: Type of search (auto, neural, keyword)
            include_domains: Domains to include in search
            exclude_domains: Domains to exclude from search
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            page: Page number for pagination (default: 1)
            per_page: Results per page (default: None, returns all)
            **kwargs: Additional provider-specific parameters

        Returns:
            Aggregated search results with metadata
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Determine which providers to use
        active_providers = self._get_active_providers(providers)
        if not active_providers:
            raise ValueError("No active search providers available")

        # Execute searches asynchronously
        results_by_provider = await self._search_parallel_async(
            query, num, active_providers, search_type,
            include_domains, exclude_domains, start_date, end_date,
            **kwargs
        )

        # Aggregate results
        aggregated_results = self._aggregate_results(
            results_by_provider, aggregation_strategy
        )

        # Apply pagination if requested
        total_results = len(aggregated_results)
        if per_page is not None and per_page > 0:
            # Calculate pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = aggregated_results[start_idx:end_idx]
            total_pages = (total_results + per_page - 1) // per_page
        else:
            # Return all results
            paginated_results = aggregated_results
            total_pages = 1

        # Calculate total usage
        total_usage = self._aggregate_usage(results_by_provider)

        return {
            "results": paginated_results,
            "query": query,
            "total_results": total_results,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "results_by_provider": {
                p: len(r.get("results", []))
                for p, r in results_by_provider.items()
            },
            "usage": total_usage,
            "providers_used": list(results_by_provider.keys()),
            "aggregation_strategy": aggregation_strategy,
        }


# Convenience function
def hybrid_search(
    query: str,
    num: int = 10,
    api_keys: Optional[Dict[str, str]] = None,
    providers: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for hybrid search.

    Args:
        query: Search query
        num: Number of results per provider
        api_keys: Dict of provider API keys
        providers: List of providers to use
        **kwargs: Additional search parameters

    Returns:
        Aggregated search results
    """
    engine = HybridSearchEngine(api_keys=api_keys, providers=providers)
    return engine.search(query, num, **kwargs)

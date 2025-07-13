#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/scrape_url.py
# code style: PEP 8

"""
Unified URL scraper that wraps multiple scraping providers.

This module provides a unified interface for scraping URLs using different
backends like JinaReader, Firecrawl, and potentially other scrapers.
It automatically selects the best scraper based on configuration, URL type,
and availability.
"""

import os
import logging
from enum import Enum
from typing import Optional, Dict, List, Any, Union
from dotenv import load_dotenv

from .base import BaseScraper
from .result import ExtractionResult
from .scraper_jinareader import JinaReaderScraper
from .scraper_firecrawl import FirecrawlScraper
from .scraper_xcom import XcomScraper

logger = logging.getLogger(__name__)


class ScraperProvider(Enum):
    """Available scraper providers."""
    JINA = "jina"
    FIRECRAWL = "firecrawl"
    XCOM = "xcom"
    AUTO = "auto"


class ScraperConfig:
    """Configuration for scraper selection and behavior."""

    def __init__(
        self,
        default_provider: ScraperProvider = ScraperProvider.AUTO,
        fallback_enabled: bool = True,
        provider_priority: Optional[List[ScraperProvider]] = None,
        provider_config: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        Initialize scraper configuration.

        Args:
            default_provider: Default scraper to use
            fallback_enabled: Whether to fallback to other scrapers on failure
            provider_priority: Priority order for auto selection
            provider_config: Provider-specific configurations
        """
        self.default_provider = default_provider
        self.fallback_enabled = fallback_enabled
        self.provider_priority = provider_priority or [
            ScraperProvider.JINA,
            ScraperProvider.FIRECRAWL,
            # XCOM is excluded from auto selection
            # It will only be used for X.com URLs or when explicitly requested
        ]
        self.provider_config = provider_config or {}


class ScrapeUrl(BaseScraper):
    """
    Unified URL scraper that provides a single interface for multiple
    scraping backends.

    This class automatically selects the appropriate scraper based on:
    - Configuration preferences
    - URL type (e.g., X.com URLs use XcomScraper)
    - Feature requirements (e.g., JavaScript rendering)
    - API key availability

    Features:
    1. Automatic provider selection
    2. Fallback support
    3. URL mapping and crawling
    4. Structured data extraction
    5. Multiple output formats
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        timeout: int = 1200,
        max_retries: int = 3,
    ):
        """
        Initialize unified scraper.

        Args:
            config: Scraper configuration
            timeout: Default timeout for requests
            max_retries: Maximum retry attempts
        """
        # Load environment variables
        load_dotenv()

        # Initialize base class without API key
        super().__init__(
            api_key=None,
            timeout=timeout,
            max_retries=max_retries,
            rate_limiter=None  # Each provider has its own rate limiter
        )

        self.config = config or ScraperConfig()
        self._scrapers: Dict[ScraperProvider, Optional[BaseScraper]] = {}
        self._initialize_scrapers()

    def _initialize_scrapers(self):
        """
        Initialize available scrapers based on API keys and configuration.
        """
        # Initialize Jina scraper if API key is available
        jina_api_key = os.getenv('JINA_API_KEY')
        if jina_api_key:
            try:
                jina_config = self.config.provider_config.get('jina', {})
                self._scrapers[ScraperProvider.JINA] = JinaReaderScraper(
                    api_key=jina_api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                    **jina_config
                )
                logger.info("JinaReader scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize JinaReader: {e}")
                self._scrapers[ScraperProvider.JINA] = None
        else:
            self._scrapers[ScraperProvider.JINA] = None

        # Initialize Firecrawl scraper if API key is available
        firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        if firecrawl_api_key:
            try:
                firecrawl_config = self.config.provider_config.get(
                    'firecrawl', {}
                )
                self._scrapers[ScraperProvider.FIRECRAWL] = FirecrawlScraper(
                    api_key=firecrawl_api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                    **firecrawl_config
                )
                logger.info("Firecrawl scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Firecrawl: {e}")
                self._scrapers[ScraperProvider.FIRECRAWL] = None
        else:
            self._scrapers[ScraperProvider.FIRECRAWL] = None

        # Initialize Xcom scraper if API key is available
        xai_api_key = os.getenv('XAI_API_KEY')
        if xai_api_key:
            try:
                xcom_config = self.config.provider_config.get('xcom', {})
                self._scrapers[ScraperProvider.XCOM] = XcomScraper(
                    api_key=xai_api_key,
                    timeout=self.timeout,
                    **xcom_config
                )
                logger.info("Xcom scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Xcom scraper: {e}")
                self._scrapers[ScraperProvider.XCOM] = None
        else:
            self._scrapers[ScraperProvider.XCOM] = None

    def _select_scraper(
        self,
        url: str,
        provider: Optional[ScraperProvider] = None,
        **kwargs
    ) -> Optional[BaseScraper]:
        """
        Select appropriate scraper for the URL.

        Args:
            url: URL to scrape
            provider: Specific provider requested
            **kwargs: Additional parameters that might influence selection

        Returns:
            Selected scraper instance or None
        """
        # Use specific provider if requested
        if provider and provider != ScraperProvider.AUTO:
            scraper = self._scrapers.get(provider)
            if scraper:
                return scraper
            elif not self.config.fallback_enabled:
                return None

        # Special case: X.com URLs should use XcomScraper
        if (
            XcomScraper.is_x_url(url) and
            self._scrapers.get(ScraperProvider.XCOM)
        ):
            return self._scrapers[ScraperProvider.XCOM]

        # Check if JavaScript rendering is required
        needs_js = kwargs.get('javascript', False) or kwargs.get('actions')
        if needs_js and self._scrapers.get(ScraperProvider.FIRECRAWL):
            return self._scrapers[ScraperProvider.FIRECRAWL]

        # Follow priority order for auto selection
        for provider in self.config.provider_priority:
            scraper = self._scrapers.get(provider)
            if scraper:
                # Special check: Don't use XcomScraper for non-X.com URLs
                if provider == ScraperProvider.XCOM:
                    # Only use XcomScraper if it's an X.com URL
                    if XcomScraper.is_x_url(url):
                        return scraper
                    else:
                        # Skip XcomScraper for non-X.com URLs
                        continue
                return scraper

        return None

    def scrape(
        self,
        url: str,
        provider: Optional[Union[ScraperProvider, str]] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Scrape a single URL with automatic provider selection.

        Args:
            url: URL to scrape
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters passed to the scraper:
                - output_format: 'markdown', 'html', 'text', etc.
                - javascript: Whether JavaScript rendering is needed
                - actions: Browser actions to perform
                - screenshot: Whether to capture screenshot
                - wait_for: CSS selector to wait for
                - remove_selector: CSS selectors to remove
                - And provider-specific parameters

        Returns:
            ExtractionResult containing scraped content
        """
        # Convert string provider to enum
        if isinstance(provider, str):
            try:
                provider = ScraperProvider(provider.lower())
            except ValueError:
                provider = None

        # Use configured default if no provider specified
        if provider is None:
            provider = self.config.default_provider

        # Try primary scraper
        scraper = self._select_scraper(url, provider, **kwargs)
        if not scraper:
            return self.standardize_result(
                url=url,
                success=False,
                error="No suitable scraper available for this URL"
            )

        try:
            logger.info(f"Scraping {url} with {scraper.__class__.__name__}")
            return scraper.scrape(url, **kwargs)
        except Exception as e:
            logger.error(
                f"Scraping failed with {scraper.__class__.__name__}: {e}"
            )

            # Try fallback scrapers if enabled
            if self.config.fallback_enabled:
                for fallback_provider in self.config.provider_priority:
                    if fallback_provider == provider:
                        continue  # Skip the one that just failed

                    fallback_scraper = self._scrapers.get(fallback_provider)
                    if fallback_scraper:
                        try:
                            logger.info(
                                f"Trying fallback scraper: "
                                f"{fallback_scraper.__class__.__name__}"
                            )
                            return fallback_scraper.scrape(url, **kwargs)
                        except Exception as fallback_e:
                            logger.error(
                                f"Fallback scraper "
                                f"{fallback_scraper.__class__.__name__} "
                                f"also failed: {fallback_e}"
                            )
                            continue

            # All scrapers failed
            return self.standardize_result(
                url=url,
                success=False,
                error=f"All scrapers failed. Last error: {str(e)}"
            )

    async def scrape_async(
        self,
        url: str,
        provider: Optional[Union[ScraperProvider, str]] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Async version of scrape.

        Args:
            url: URL to scrape
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters

        Returns:
            ExtractionResult
        """
        # Convert string provider to enum
        if isinstance(provider, str):
            try:
                provider = ScraperProvider(provider.lower())
            except ValueError:
                provider = None

        # Use configured default if no provider specified
        if provider is None:
            provider = self.config.default_provider

        # Select scraper
        scraper = self._select_scraper(url, provider, **kwargs)
        if not scraper:
            return self.standardize_result(
                url=url,
                success=False,
                error="No suitable scraper available for this URL"
            )

        try:
            logger.info(
                f"Async scraping {url} with {scraper.__class__.__name__}"
            )
            return await scraper.scrape_async(url, **kwargs)
        except Exception as e:
            logger.error(f"Async scraping failed: {e}")

            # Try fallback scrapers
            if self.config.fallback_enabled:
                for fallback_provider in self.config.provider_priority:
                    if fallback_provider == provider:
                        continue

                    fallback_scraper = self._scrapers.get(fallback_provider)
                    if fallback_scraper:
                        try:
                            logger.info(
                                f"Trying async fallback: "
                                f"{fallback_scraper.__class__.__name__}"
                            )
                            return await fallback_scraper.scrape_async(
                                url, **kwargs
                            )
                        except Exception as fallback_e:
                            logger.error(
                                f"Async fallback failed: {fallback_e}"
                            )
                            continue

            return self.standardize_result(
                url=url,
                success=False,
                error=f"All scrapers failed. Last error: {str(e)}"
            )

    def map_website(
        self,
        url: str,
        provider: Optional[Union[ScraperProvider, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Map/discover all URLs from a website.

        Args:
            url: Website URL to map
            provider: Specific provider to use
            **kwargs: Additional parameters

        Returns:
            Dictionary with discovered URLs and metadata
        """
        # Only Firecrawl supports website mapping currently
        if provider and provider != ScraperProvider.FIRECRAWL:
            logger.warning(
                f"{provider} does not support website mapping. "
                "Using Firecrawl if available."
            )

        firecrawl = self._scrapers.get(ScraperProvider.FIRECRAWL)
        if firecrawl and hasattr(firecrawl, 'map_website'):
            return firecrawl.map_website(url, **kwargs)
        else:
            return {
                'success': False,
                'error': 'Website mapping requires Firecrawl API',
                'urls': []
            }

    def crawl_website(
        self,
        url: str,
        limit: int = 10,
        provider: Optional[Union[ScraperProvider, str]] = None,
        **kwargs
    ) -> List[ExtractionResult]:
        """
        Crawl multiple pages from a website.

        Args:
            url: Starting URL for crawl
            limit: Maximum pages to crawl
            provider: Specific provider to use
            **kwargs: Additional parameters

        Returns:
            List of ExtractionResult objects
        """
        # Only Firecrawl supports crawling currently
        if provider and provider != ScraperProvider.FIRECRAWL:
            logger.warning(
                f"{provider} does not support crawling. "
                "Using Firecrawl if available."
            )

        firecrawl = self._scrapers.get(ScraperProvider.FIRECRAWL)
        if firecrawl and hasattr(firecrawl, 'crawl_website'):
            return firecrawl.crawl_website(url, limit=limit, **kwargs)
        else:
            # Fallback: Just scrape the single URL
            result = self.scrape(url, provider=provider, **kwargs)
            return [result]

    def get_available_providers(self) -> List[str]:
        """
        Get list of available scraper providers.

        Returns:
            List of provider names that are initialized and ready
        """
        return [
            provider.value
            for provider, scraper in self._scrapers.items()
            if scraper is not None
        ]

    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available providers.

        Returns:
            Dictionary with provider information
        """
        info = {}
        for provider, scraper in self._scrapers.items():
            if scraper:
                provider_info = {
                    'available': True,
                    'class': scraper.__class__.__name__,
                    'features': []
                }

                # Add feature information
                if provider == ScraperProvider.JINA:
                    provider_info['features'] = [
                        'markdown', 'html', 'text', 'screenshot',
                        'remove_selectors', 'wait_for_selectors'
                    ]
                elif provider == ScraperProvider.FIRECRAWL:
                    provider_info['features'] = [
                        'javascript', 'actions', 'crawling',
                        'mapping', 'screenshot', 'structured_data'
                    ]
                elif provider == ScraperProvider.XCOM:
                    provider_info['features'] = [
                        'x.com_specialized', 'profile_extraction',
                        'post_extraction'
                    ]

                info[provider.value] = provider_info
            else:
                info[provider.value] = {
                    'available': False,
                    'reason': f'{provider.value.upper()}_API_KEY not found'
                }

        return info


# Convenience function for simple scraping
def scrape_url(
    url: str,
    provider: Optional[str] = None,
    **kwargs
) -> ExtractionResult:
    """
    Convenience function for scraping a URL with automatic provider selection.

    Args:
        url: URL to scrape
        provider: Optional provider name ('jina', 'firecrawl', 'xcom', 'auto')
        **kwargs: Additional parameters

    Returns:
        ExtractionResult
    """
    scraper = ScrapeUrl()
    return scraper.scrape(url, provider=provider, **kwargs)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_readurl_routing_integration.py
# code style: PEP 8

"""
Integration tests for ReadURLTool routing logic.

These tests verify the actual routing behavior without mocking,
ensuring that URLs are correctly routed to appropriate scrapers.
"""

import pytest
import os
from unittest.mock import patch

from src.tools.readurl import ReadURLTool
from src.core.scraping.scraper_xcom import XcomScraper


class TestReadURLRoutingIntegration:
    """Integration tests for URL routing in ReadURLTool."""

    @pytest.fixture
    def env_with_all_keys(self):
        """Set up environment with all API keys."""
        with patch.dict('os.environ', {
            'JINA_API_KEY': os.getenv('JINA_API_KEY', 'test_jina'),
            'FIRECRAWL_API_KEY': os.getenv('FIRECRAWL_API_KEY', 'test_fc'),
            'XAI_API_KEY': os.getenv('XAI_API_KEY', 'test_xai')
        }):
            yield

    @pytest.fixture
    def env_only_xai(self):
        """Set up environment with only XAI API key."""
        # Save current env vars
        saved_jina = os.environ.get('JINA_API_KEY')
        saved_firecrawl = os.environ.get('FIRECRAWL_API_KEY')

        # Remove JINA and Firecrawl keys
        if 'JINA_API_KEY' in os.environ:
            del os.environ['JINA_API_KEY']
        if 'FIRECRAWL_API_KEY' in os.environ:
            del os.environ['FIRECRAWL_API_KEY']

        # Ensure XAI key exists
        if 'XAI_API_KEY' not in os.environ:
            os.environ['XAI_API_KEY'] = 'test_xai'

        yield

        # Restore original env vars
        if saved_jina:
            os.environ['JINA_API_KEY'] = saved_jina
        if saved_firecrawl:
            os.environ['FIRECRAWL_API_KEY'] = saved_firecrawl

    def test_xcom_url_detection(self):
        """Test X.com URL detection logic."""
        # Test X.com URLs
        assert XcomScraper.is_x_url("https://x.com/user/status/123")
        assert XcomScraper.is_x_url("https://twitter.com/user/status/456")
        assert XcomScraper.is_x_url("http://x.com/user")
        assert XcomScraper.is_x_url("https://mobile.twitter.com/user")

        # Test non-X.com URLs
        assert not XcomScraper.is_x_url("https://example.com")
        assert not XcomScraper.is_x_url("https://github.com/x.com")
        assert not XcomScraper.is_x_url("https://news.ycombinator.com")
        assert not XcomScraper.is_x_url("https://xkcd.com")

    def test_scraper_availability(self, env_with_all_keys):
        """Test which scrapers are available."""
        from src.core.scraping.scrape_url import ScrapeUrl

        scraper = ScrapeUrl()
        available = scraper.get_available_providers()

        # Check what's available
        print(f"Available providers: {available}")

        # Get detailed info
        info = scraper.get_provider_info()
        for provider, details in info.items():
            print(f"{provider}: {details}")

    def test_xcom_routing_with_only_xai(self, env_only_xai):
        """Test that non-X.com URLs fail when only XAI is available."""
        from src.core.scraping.scrape_url import ScrapeUrl

        scraper = ScrapeUrl()

        # Test that X.com URLs would use XcomScraper
        x_url = "https://x.com/deedydas/status/1943190393602068801"
        selected = scraper._select_scraper(x_url)

        if selected:
            assert selected.__class__.__name__ == "XcomScraper"

        # Test that non-X.com URLs get no scraper
        non_x_urls = [
            "https://example.com",
            "https://github.com/repo",
            "https://stackoverflow.com/questions"
        ]

        for url in non_x_urls:
            selected = scraper._select_scraper(url)
            assert selected is None, (
                f"Expected no scraper for {url}, "
                f"but got {selected.__class__.__name__}"
            )

    def test_scraper_priority(self, env_with_all_keys):
        """Test that scraper priority is respected."""
        from src.core.scraping.scrape_url import (
            ScrapeUrl, ScraperConfig, ScraperProvider
        )

        config = ScraperConfig()
        scraper = ScrapeUrl(config=config)

        # Verify default priority excludes XCOM
        assert ScraperProvider.XCOM not in config.provider_priority
        assert ScraperProvider.JINA in config.provider_priority
        assert ScraperProvider.FIRECRAWL in config.provider_priority

        # Test selection for general URL
        selected = scraper._select_scraper("https://example.com")
        if selected:
            # Should be Jina or Firecrawl, not Xcom
            assert selected.__class__.__name__ in [
                "JinaReaderScraper", "FirecrawlScraper"
            ]
            assert selected.__class__.__name__ != "XcomScraper"

    def test_readurl_tool_initialization(self):
        """Test ReadURLTool can be initialized."""
        # Default initialization
        tool = ReadURLTool()
        assert tool is not None
        assert tool.name == "read_url"

        # With specific provider
        tool_jina = ReadURLTool(default_provider="jina")
        assert tool_jina.default_provider == "jina"

        # With fallback disabled
        tool_no_fallback = ReadURLTool(fallback_enabled=False)
        assert not tool_no_fallback.fallback_enabled

    @pytest.mark.skipif(
        not os.getenv('XAI_API_KEY'),
        reason="XAI_API_KEY not set"
    )
    def test_xcom_url_routing_real(self):
        """Test real X.com URL routing (requires XAI_API_KEY)."""
        tool = ReadURLTool()

        # This would make a real API call
        # Only run if you want to test with real API
        # result = tool.forward("https://x.com/elonmusk/status/123")
        # assert "X.com" in result or "Twitter" in result
        pass

    def test_url_validation_patterns(self):
        """Test various URL patterns for X.com detection."""
        test_cases = [
            # Should match
            ("https://x.com/user", True),
            ("https://x.com/user/status/123", True),
            ("https://twitter.com/user", True),
            ("https://twitter.com/user/status/123", True),
            ("http://x.com/search?q=test", True),
            ("https://mobile.twitter.com/user", True),
            ("https://www.x.com/user", True),

            # Should not match
            ("https://example.com/x.com", False),
            ("https://notx.com", False),
            ("https://x.company", False),
            ("https://twitterclone.com", False),
            ("https://github.com/twitter.com/repo", False),
            ("https://docs.x.com.fake.com", False),
        ]

        for url, expected in test_cases:
            result = XcomScraper.is_x_url(url)
            assert result == expected, (
                f"URL {url} detection failed: "
                f"expected {expected}, got {result}"
            )

    def test_scraper_config_behavior(self):
        """Test ScraperConfig configuration options."""
        from src.core.scraping.scrape_url import (
            ScraperConfig, ScraperProvider
        )

        # Default config
        default_config = ScraperConfig()
        assert default_config.default_provider == ScraperProvider.AUTO
        assert default_config.fallback_enabled is True
        assert ScraperProvider.XCOM not in default_config.provider_priority

        # Custom config
        custom_config = ScraperConfig(
            default_provider=ScraperProvider.FIRECRAWL,
            fallback_enabled=False,
            provider_priority=[ScraperProvider.FIRECRAWL]
        )
        assert custom_config.default_provider == ScraperProvider.FIRECRAWL
        assert not custom_config.fallback_enabled
        assert len(custom_config.provider_priority) == 1


class TestErrorHandling:
    """Test error handling in routing."""

    def test_no_api_keys_error(self):
        """Test behavior when no API keys are available."""
        # Temporarily remove all API keys
        saved_keys = {}
        for key in ['JINA_API_KEY', 'FIRECRAWL_API_KEY', 'XAI_API_KEY']:
            if key in os.environ:
                saved_keys[key] = os.environ[key]
                del os.environ[key]

        try:
            from src.core.scraping.scrape_url import ScrapeUrl

            scraper = ScrapeUrl()
            result = scraper.scrape("https://example.com")

            assert not result.success
            assert "No suitable scraper" in result.error
        finally:
            # Restore keys
            for key, value in saved_keys.items():
                os.environ[key] = value

    def test_scraper_initialization_logging(self, caplog):
        """Test that scraper initialization is logged."""
        import logging

        # Set logging level
        caplog.set_level(logging.INFO)

        # Force re-initialization
        from src.core.scraping.scrape_url import ScrapeUrl

        with patch.dict('os.environ', {
            'JINA_API_KEY': 'test_key'
        }):
            _ = ScrapeUrl()

            # Check logs
            assert any(
                "JinaReader scraper initialized" in record.message
                for record in caplog.records
            )

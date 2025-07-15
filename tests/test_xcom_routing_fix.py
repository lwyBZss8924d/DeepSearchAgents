#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_xcom_routing_fix.py
# code style: PEP 8

"""
Focused test to verify XcomScraper routing fix works correctly.

This test verifies that the fix to prevent non-X.com URLs from
being routed to XcomScraper is working as expected.
"""

import pytest
from src.core.scraping.scraper_xcom import XcomScraper
from src.core.scraping.scrape_url import ScrapeUrl, ScraperProvider


class TestXcomRoutingFix:
    """Test the XcomScraper routing fix."""

    def test_improved_url_detection(self):
        """Test that is_x_url() correctly identifies X.com URLs."""
        # Valid X.com URLs
        x_urls = [
            "https://x.com/user",
            "https://x.com/user/status/123",
            "https://www.x.com/user",
            "http://x.com/user",
            "https://twitter.com/user",
            "https://twitter.com/user/status/123",
            "https://www.twitter.com/user",
            "https://mobile.twitter.com/user",
        ]

        for url in x_urls:
            assert XcomScraper.is_x_url(url), f"Should match: {url}"

        # Invalid X.com URLs
        non_x_urls = [
            "https://example.com",
            "https://github.com/x.com",
            "https://example.com/x.com",
            "https://x.company",
            "https://xkcd.com",
            "https://notx.com",
            "https://twitter.clone.com",
            "https://docs.twitter.com.fake.com",
            "x.com/user",  # No protocol
            "twitter.com/user",  # No protocol
        ]

        for url in non_x_urls:
            assert not XcomScraper.is_x_url(url), f"Should NOT match: {url}"

    def test_select_scraper_logic(self):
        """Test the _select_scraper logic for X.com URLs."""
        scraper = ScrapeUrl()

        # Test X.com URL selection
        x_urls = [
            "https://x.com/deedydas/status/1943190393602068801",
            "https://twitter.com/deedydas/status/1943190393602068801"
        ]

        for url in x_urls:
            selected = scraper._select_scraper(url)
            # If XcomScraper is available, it should be selected
            if scraper._scrapers.get(ScraperProvider.XCOM):
                assert selected is scraper._scrapers[ScraperProvider.XCOM]
                assert selected.__class__.__name__ == "XcomScraper"

        # Test non-X.com URL selection
        non_x_urls = [
            "https://example.com",
            "https://github.com/repo",
            "https://stackoverflow.com/questions"
        ]

        for url in non_x_urls:
            selected = scraper._select_scraper(url)
            # Should never select XcomScraper for non-X.com URLs
            if selected:
                assert selected.__class__.__name__ != "XcomScraper"

    def test_provider_priority_excludes_xcom(self):
        """Test that XCOM is excluded from default provider priority."""
        from src.core.scraping.scrape_url import ScraperConfig

        config = ScraperConfig()
        
        # XCOM should not be in default priority
        assert ScraperProvider.XCOM not in config.provider_priority
        
        # JINA and FIRECRAWL should be in priority
        assert ScraperProvider.JINA in config.provider_priority
        assert ScraperProvider.FIRECRAWL in config.provider_priority

    def test_actual_scraping_behavior(self):
        """Test actual scraping behavior with different URLs."""
        scraper = ScrapeUrl()

        # Get available providers
        available = scraper.get_available_providers()
        print(f"Available providers: {available}")

        # Test that we can get provider info
        info = scraper.get_provider_info()
        assert 'jina' in info or 'firecrawl' in info or 'xcom' in info

        # If Xcom is available, test X.com URL routing
        if 'xcom' in available:
            # X.com URLs should potentially use XcomScraper
            selected = scraper._select_scraper("https://x.com/test")
            assert selected is not None

        # General URLs should not use XcomScraper
        general_url = "https://example.com/article"
        selected = scraper._select_scraper(general_url)
        
        if selected:
            print(f"Selected scraper for {general_url}: "
                  f"{selected.__class__.__name__}")
            # Should be Jina or Firecrawl, not Xcom
            assert selected.__class__.__name__ in [
                'JinaReaderScraper', 'FirecrawlScraper'
            ]

    def test_special_url_cases(self):
        """Test edge cases in URL detection."""
        edge_cases = [
            # Subdomain variations
            ("https://api.twitter.com/user", True),
            ("https://m.twitter.com/user", True),
            ("https://mobile.x.com/user", True),
            
            # Path variations  
            ("https://x.com", True),
            ("https://x.com/", True),
            ("https://twitter.com/i/events/123", True),
            
            # Should not match
            ("https://mytwitter.com", False),
            ("https://twitterapi.com", False),
            ("https://x.communitynotes.com", False),
            ("https://developer.x.com", True),  # Subdomain of x.com
        ]

        for url, expected in edge_cases:
            result = XcomScraper.is_x_url(url)
            assert result == expected, (
                f"URL {url}: expected {expected}, got {result}"
            )
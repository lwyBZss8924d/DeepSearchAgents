#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/test_unified_scraper.py
# code style: PEP 8

"""
Test script for unified URL scraper.

This script tests the unified scraper wrapper functionality including:
- Provider selection
- Fallback behavior
- Multiple scraper backends
"""

import asyncio
import os
from src.core.scraping import ScrapeUrl, ScraperConfig, ScraperProvider


def test_unified_scraper():
    """Test unified scraper with different providers."""
    # Create scraper with default configuration
    config = ScraperConfig(
        default_provider=ScraperProvider.AUTO,
        fallback_enabled=True
    )
    scraper = ScrapeUrl(config=config)
    
    # Print available providers
    print("Available providers:")
    providers = scraper.get_available_providers()
    print(f"  {providers}")
    
    print("\nProvider information:")
    info = scraper.get_provider_info()
    for provider, details in info.items():
        print(f"  {provider}: {details}")
    
    # Test URLs
    test_urls = [
        ("https://example.com", None),  # General URL - auto select
        ("https://x.com/elonmusk", "xcom"),  # X.com URL
        ("https://jina.ai", "jina"),  # Explicit Jina
    ]
    
    print("\n\nTesting scraping:")
    for url, provider in test_urls:
        print(f"\n{'='*60}")
        print(f"URL: {url}")
        print(f"Provider: {provider or 'auto'}")
        
        try:
            result = scraper.scrape(url, provider=provider)
            
            print(f"Success: {result.success}")
            if result.success:
                print(f"Content length: {len(result.content or '')}")
                print(f"Metadata: {result.metadata}")
            else:
                print(f"Error: {result.error}")
                
        except Exception as e:
            print(f"Exception: {str(e)}")


async def test_async_scraping():
    """Test async scraping functionality."""
    print("\n\nTesting async scraping:")
    print("="*60)
    
    scraper = ScrapeUrl()
    
    # Test async scraping
    url = "https://example.com"
    result = await scraper.scrape_async(url)
    
    print(f"Async scraping result:")
    print(f"  Success: {result.success}")
    print(f"  Content length: {len(result.content or '')}")


def test_provider_specific_features():
    """Test provider-specific features."""
    print("\n\nTesting provider-specific features:")
    print("="*60)
    
    scraper = ScrapeUrl()
    
    # Test website mapping (Firecrawl only)
    if 'firecrawl' in scraper.get_available_providers():
        print("\nTesting website mapping with Firecrawl:")
        map_result = scraper.map_website("https://example.com")
        print(f"  Mapping result: {map_result}")


def main():
    """Run all tests."""
    print("Unified Scraper Test Suite")
    print("="*60)
    
    # Check environment variables
    print("\nEnvironment check:")
    apis = {
        "JINA_API_KEY": bool(os.getenv("JINA_API_KEY")),
        "FIRECRAWL_API_KEY": bool(os.getenv("FIRECRAWL_API_KEY")),
        "XAI_API_KEY": bool(os.getenv("XAI_API_KEY"))
    }
    for key, available in apis.items():
        print(f"  {key}: {'✓' if available else '✗'}")
    
    # Run tests
    test_unified_scraper()
    
    # Run async test
    asyncio.run(test_async_scraping())
    
    # Test provider features
    test_provider_specific_features()
    
    print("\n\nTest completed!")


if __name__ == "__main__":
    main()
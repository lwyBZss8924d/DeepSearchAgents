#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_xcom_scraper_sdk.py
# Test script for the new SDK-based XcomScraper

import asyncio
import os
from dotenv import load_dotenv

from src.core.scraping.scraper_xcom import XcomScraper

# Add the project root to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_xcom_scraper():
    """Test the SDK-based XcomScraper implementation."""

    # Load environment variables
    load_dotenv()

    # Initialize scraper
    print("Initializing XcomScraper with xAI SDK...")
    try:
        scraper = XcomScraper()
        print("✓ XcomScraper initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize XcomScraper: {e}")
        return

    # Test URLs
    test_urls = [
        # elonmusk post about new Grok version Grok-4 tweet post URL
        "https://x.com/elonmusk/status/1943230468519788551",
        # Profile URL
        "https://x.com/elonmusk",
        # Invalid URL
        "https://google.com",
    ]

    print("\n" + "="*60)
    print("Testing URL validation and scraping...")
    print("="*60)

    for url in test_urls:
        print(f"\nTesting URL: {url}")
        print("-" * 40)

        # Test URL validation
        is_valid = XcomScraper.is_x_url(url)
        print(f"Is X.com URL: {is_valid}")

        if is_valid:
            # Test URL type detection
            url_type = XcomScraper.get_url_type(url)
            print(f"URL type: {url_type}")

            # Test username extraction
            username = XcomScraper.extract_username_from_url(url)
            print(f"Extracted username: {username}")

            # Test synchronous scraping
            print("\nTesting synchronous scraping...")
            try:
                result = scraper.scrape(url)
                if result.success:
                    print("✓ Scraping successful")
                    print(f"Title: {result.metadata.get('title', 'N/A')}")
                    print(f"Content length: {len(result.content)} chars")
                    print(f"Citations: {len(result.metadata.get('citations', []))}")
                    if 'usage' in result.metadata:
                        usage = result.metadata['usage']
                        print(f"Tokens used: {usage.get('total_tokens', 'N/A')}")
                else:
                    print(f"✗ Scraping failed: {result.error}")
            except Exception as e:
                print(f"✗ Error during scraping: {e}")

            # Test asynchronous scraping
            print("\nTesting asynchronous scraping...")
            try:
                result = await scraper.scrape_async(url)
                if result.success:
                    print("✓ Async scraping successful")
                else:
                    print(f"✗ Async scraping failed: {result.error}")
            except Exception as e:
                print(f"✗ Error during async scraping: {e}")

    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_xcom_scraper())

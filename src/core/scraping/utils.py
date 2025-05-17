#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/scraping/utils.py
# code style: PEP 8

"""
Wikipedia API for extracting content from Wikipedia URLs.
"""

import wikipediaapi


def get_wikipedia_content(url: str) -> str | None:
    """
    Extract content from a Wikipedia URL.

    Args:
        url: Wikipedia URL to scrape

    Returns:
        str: Page content if found, None otherwise
    """
    wiki = wikipediaapi.Wikipedia(
        user_agent="deepsearch_agents_wiki_client",
        language='en'
    )

    # Extract the page title from URL (everything after /wiki/)
    try:
        title = url.split('/wiki/')[-1]
        if not title:  # handle URLs like https://en.wikipedia.org/wiki/
            return None
        page = wiki.page(title)
        if page.exists():
            # print(f"Successfully fetched Wikipedia content for: {title}")
            return page.text
        else:
            # print(f"Wikipedia page not found: {title}")
            return None
    except Exception as e:
        print(f"Error fetching Wikipedia content for {url}: {e}")
        return None

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/conftest.py
# code style: PEP 8

"""
Pytest configuration and shared fixtures for DeepSearchAgents tests.
"""

import pytest
import asyncio
import os
import sys
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config.settings import Settings
from src.agents.runtime import AgentRuntime
from src.agents.base_agent import MultiModelRouter, BaseAgent
from src.agents.react_agent import ReactAgent
from src.agents.codact_agent import CodeActAgent
from src.agents.manager_agent import ManagerAgent

# Academic toolkit imports
from src.core.academic_tookit.models import Paper, SearchParams, PaperSource
from src.core.academic_tookit.paper_search.arxiv import ArxivClient
from src.core.academic_tookit.paper_reader import PaperReader, PaperReaderConfig
from src.core.academic_tookit.paper_retrievaler import PaperRetriever


# Configure pytest for async tests
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings with minimal configuration."""
    settings = Settings()
    
    # Set test environment
    settings.DEEPSEARCH_ENV = "test"
    settings.DEEPSEARCH_DEBUG = True
    
    # Use minimal models for testing
    settings.ORCHESTRATOR_MODEL_ID = "openai/gemini-2.5-pro"
    settings.SEARCH_MODEL_NAME = "openai/gemini-2.5-pro"
    
    # Reduce limits for faster tests
    settings.REACT_MAX_STEPS = 5
    settings.CODACT_MAX_STEPS = 5
    settings.REACT_PLANNING_INTERVAL = 2
    settings.CODACT_PLANNING_INTERVAL = 2
    settings.CODACT_USE_STRUCTURED_OUTPUTS = True
    
    # Disable streaming for tests
    settings.ENABLE_STREAMING = False
    
    return settings


@pytest.fixture
def test_api_keys():
    """Test API keys - should be set in environment for real tests."""
    return {
        "litellm_master_key": os.getenv("LITELLM_MASTER_KEY", ""),
        "serper_api_key": os.getenv("SERPER_API_KEY", ""),
        "jina_api_key": os.getenv("JINA_API_KEY", ""),
        "wolfram_app_id": os.getenv("WOLFRAM_ALPHA_APP_ID", ""),
        "xai_api_key": os.getenv("XAI_API_KEY", ""),
        "litellm_base_url": os.getenv("LITELLM_BASE_URL", "http://localhost:8000")
    }


@pytest.fixture
def test_runtime(test_settings):
    """Create test runtime with test settings."""
    runtime = AgentRuntime(settings_obj=test_settings)
    return runtime


@pytest.fixture
def initial_state():
    """Initial state for agents."""
    return {
        "visited_urls": set(),
        "search_queries": [],
        "key_findings": {},
        "search_depth": {},
        "reranking_history": [],
        "content_quality": {}
    }


@pytest.fixture
def simple_tools(test_runtime):
    """Get a minimal set of tools for testing."""
    # Get only essential tools
    essential_tool_names = ["search_links", "read_url", "final_answer"]
    all_tools = test_runtime._tools
    
    return [tool for tool in all_tools if tool.name in essential_tool_names]


@pytest.fixture
def sample_queries():
    """Sample queries for testing."""
    return {
        "simple": "What is 2 + 2?",
        "search": "What is the capital of France?",
        "complex": "Compare the GDP of USA and China in 2023",
        "code": "Write a Python function to calculate factorial",
        "multi_step": "Find the latest news about AI and summarize the key points"
    }


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Configure test environment."""
    # Set test environment
    monkeypatch.setenv("DEEPSEARCH_ENV", "test")
    monkeypatch.setenv("DEEPSEARCH_DEBUG", "true")
    
    # Reduce timeouts for tests
    monkeypatch.setenv("DEEPSEARCH_REQUEST_TIMEOUT", "10")
    
    # Use test configuration file if it exists
    test_config = os.path.join(os.path.dirname(__file__), "test_config.toml")
    if os.path.exists(test_config):
        monkeypatch.setenv("DEEPSEARCH_CONFIG_FILE", test_config)


@pytest.fixture
def cleanup_agents():
    """Cleanup helper for agent resources."""
    agents = []
    
    def register(agent):
        agents.append(agent)
        return agent
    
    yield register
    
    # Cleanup all registered agents
    for agent in agents:
        try:
            if hasattr(agent, 'reset_agent_memory'):
                agent.reset_agent_memory()
            if hasattr(agent, '__exit__'):
                agent.__exit__(None, None, None)
        except Exception:
            pass


# Markers for different test types
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_llm: test requires LLM API access"
    )
    config.addinivalue_line(
        "markers", "requires_search: test requires search API access"
    )
    config.addinivalue_line(
        "markers", "slow: test takes more than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "integration: integration test"
    )
    config.addinivalue_line(
        "markers", "unit: unit test"
    )
    config.addinivalue_line(
        "markers", "requires_mistral: test requires Mistral API access"
    )
    config.addinivalue_line(
        "markers", "requires_jina: test requires Jina API access"
    )


# Academic toolkit specific fixtures
@pytest.fixture
def skip_if_no_api_key():
    """Skip test if API keys not configured."""
    def _skip(api_name: str) -> None:
        key_name = f"{api_name.upper()}_API_KEY"
        if not os.getenv(key_name):
            pytest.skip(f"{key_name} not configured")
    return _skip


@pytest.fixture
def arxiv_test_paper_ids():
    """Common arXiv paper IDs for testing."""
    return {
        "react": "2210.03629",  # ReAct paper
        "gpt4": "2303.08774",   # GPT-4 technical report
        "attention": "1706.03762",  # Attention is all you need
        "bert": "1810.04805",   # BERT paper
        "invalid": "0000.00000"  # Invalid ID for error testing
    }


@pytest.fixture
def academic_search_queries():
    """Common search queries for academic paper testing."""
    return {
        "react": "ReAct agent methodology",
        "llm_agents": ("AI LLM Agent papers ReAct agent "
                       "methodology derived methods"),
        "transformers": "transformer models attention mechanism",
        "recent_ai": "artificial intelligence language models 2024",
        "specific_authors": "author:Yao author:Zhao ReAct"
    }


@pytest.fixture
def rate_limit_delay():
    """ArXiv API rate limit delay in seconds."""
    return 3.0  # ArXiv requires 3 seconds between requests


@pytest.fixture
def sample_paper():
    """Create a sample Paper object for testing."""
    from datetime import datetime

    return Paper(
        paper_id="2210.03629",
        title="ReAct: Synergizing Reasoning and Acting in Language Models",
        authors=["Shunyu Yao", "Jeffrey Zhao", "Dian Yu", "Nan Du",
                 "Izhak Shafran", "Karthik Narasimhan", "Yuan Cao"],
        abstract=("While large language models (LLMs) have demonstrated "
                  "impressive capabilities..."),
        source=PaperSource.ARXIV,
        url="https://arxiv.org/abs/2210.03629",
        pdf_url="https://arxiv.org/pdf/2210.03629.pdf",
        html_url="",  # this paper is not available in html format
        published_date=datetime(2022, 10, 6),
        updated_date=datetime(2023, 3, 10),
        categories=["cs.CL", "cs.AI"],
        doi="10.48550/arXiv.2210.03629",
        citations_count=100,
        venue=None,
        volume=None,
        issue=None,
        pages=None
    )


@pytest.fixture
async def paper_reader():
    """Create a PaperReader instance for testing."""
    config = PaperReaderConfig()
    return PaperReader(config)


@pytest.fixture
async def arxiv_client():
    """Create an ArxivClient instance for testing."""
    return ArxivClient()


@pytest.fixture
async def paper_retriever():
    """Create a PaperRetriever instance for testing."""
    return PaperRetriever()
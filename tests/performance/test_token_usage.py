#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/performance/test_token_usage.py
# code style: PEP 8

"""
Performance tests for token usage tracking.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from src.agents.runtime import AgentRuntime
from src.agents.base_agent import MultiModelRouter
from src.agents.run_result import RunResult


class TestTokenUsagePerformance:
    """Test token usage tracking and performance."""
    
    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        runtime = AgentRuntime(settings_obj=test_settings)
        return runtime
    
    @pytest.mark.performance
    def test_token_counting_accuracy(self):
        """Test accuracy of token counting."""
        # Create mock models with known token counts
        search_model = MagicMock()
        search_model.model_id = "test-search"
        search_model.last_input_token_count = 100
        search_model.last_output_token_count = 50
        
        orchestrator_model = MagicMock()
        orchestrator_model.model_id = "test-orchestrator"
        orchestrator_model.last_input_token_count = 200
        orchestrator_model.last_output_token_count = 100
        
        # Create router
        router = MultiModelRouter(search_model, orchestrator_model)
        
        # Simulate multiple calls
        test_cases = [
            (search_model, 100, 50),
            (orchestrator_model, 200, 100),
            (search_model, 150, 75),
            (orchestrator_model, 250, 125)
        ]
        
        for model, expected_input, expected_output in test_cases:
            router._last_used_model = model
            model.last_input_token_count = expected_input
            model.last_output_token_count = expected_output
            
            router._update_token_counts_from_model(model)
            
            counts = router.get_token_counts()
            assert counts["input"] == expected_input
            assert counts["output"] == expected_output
    
    @pytest.mark.performance
    def test_token_tracking_overhead(self):
        """Test overhead of token tracking."""
        # Create router
        search_model = MagicMock()
        orchestrator_model = MagicMock()
        router = MultiModelRouter(search_model, orchestrator_model)
        
        # Measure overhead of token tracking
        iterations = 10000
        
        # Without token tracking
        start_time = time.time()
        for _ in range(iterations):
            router._select_model_for_messages([{"role": "user", "content": "test"}])
        time_without = time.time() - start_time
        
        # With token tracking
        start_time = time.time()
        for _ in range(iterations):
            router._select_model_for_messages([{"role": "user", "content": "test"}])
            router._update_token_counts_from_model(search_model)
            router.get_token_counts()
        time_with = time.time() - start_time
        
        # Token tracking should add minimal overhead
        overhead_ratio = time_with / time_without
        assert overhead_ratio < 1.5  # Less than 50% overhead
        
        print(f"Token tracking overhead: {(overhead_ratio - 1) * 100:.2f}%")
    
    @pytest.mark.performance
    @pytest.mark.requires_llm
    def test_real_token_usage(self, runtime, cleanup_agents):
        """Test real token usage tracking."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Run a simple query
        result = agent.run("What is 2 + 2?", return_result=True)
        
        assert isinstance(result, RunResult)
        assert result.token_usage["input"] > 0
        assert result.token_usage["output"] > 0
        assert result.token_usage["total"] == (
            result.token_usage["input"] + result.token_usage["output"]
        )
        
        print(f"Token usage - Input: {result.token_usage['input']}, "
              f"Output: {result.token_usage['output']}, "
              f"Total: {result.token_usage['total']}")
    
    @pytest.mark.performance
    def test_token_usage_aggregation(self, runtime):
        """Test token usage aggregation across multiple calls."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        total_input = 0
        total_output = 0
        
        # Run multiple queries
        queries = [
            "What is 1 + 1?",
            "What is 2 + 2?",
            "What is 3 + 3?"
        ]
        
        for query in queries:
            agent = runtime.create_react_agent()
            result = agent.run(query, return_result=True)
            
            if isinstance(result, RunResult):
                total_input += result.token_usage["input"]
                total_output += result.token_usage["output"]
            
            # Cleanup
            agent.reset_agent_memory()
        
        print(f"Total tokens across {len(queries)} queries - "
              f"Input: {total_input}, Output: {total_output}, "
              f"Total: {total_input + total_output}")
        
        # Verify totals are reasonable
        assert total_input > 0
        assert total_output > 0
    
    @pytest.mark.performance
    def test_model_routing_performance(self):
        """Test performance of model routing decisions."""
        search_model = MagicMock()
        orchestrator_model = MagicMock()
        router = MultiModelRouter(search_model, orchestrator_model)
        
        # Test different message patterns
        test_messages = [
            # Planning messages
            [{"role": "assistant", "content": "Let me check the Facts survey"}],
            [{"role": "assistant", "content": "Creating an Updated facts survey"}],
            # Search messages
            [{"role": "user", "content": "Search for Python tutorials"}],
            [{"role": "assistant", "content": "I'll search for that information"}],
            # Final answer messages
            [{"role": "assistant", "content": "Here's the final answer to your question"}],
            # Complex messages
            [{"role": "assistant", "content": [
                {"type": "text", "text": "Planning the approach"},
                {"type": "text", "text": "Let me update the facts survey"}
            ]}]
        ]
        
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            for messages in test_messages:
                router._select_model_for_messages(messages)
        
        total_time = time.time() - start_time
        avg_time_per_decision = total_time / (iterations * len(test_messages))
        
        print(f"Average model routing decision time: {avg_time_per_decision * 1000:.3f}ms")
        
        # Should be very fast
        assert avg_time_per_decision < 0.001  # Less than 1ms per decision
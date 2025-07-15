#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/performance/test_execution_time.py
# code style: PEP 8

"""
Performance tests for execution time tracking.
"""

import pytest
import time
import statistics
from typing import List

from src.agents.runtime import AgentRuntime
from src.agents.run_result import RunResult


class TestExecutionTimePerformance:
    """Test execution time tracking and performance."""
    
    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        # Reduce steps for faster tests
        test_settings.REACT_MAX_STEPS = 3
        test_settings.CODACT_MAX_STEPS = 3
        runtime = AgentRuntime(settings_obj=test_settings)
        return runtime
    
    @pytest.mark.performance
    def test_execution_time_accuracy(self, runtime, cleanup_agents):
        """Test accuracy of execution time measurement."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Measure execution time manually
        start = time.time()
        result = agent.run("What is 2 + 2?", return_result=True)
        manual_time = time.time() - start
        
        assert isinstance(result, RunResult)
        assert result.execution_time > 0
        
        # Execution time should be close to manual measurement
        # Allow for some variance
        assert abs(result.execution_time - manual_time) < 0.1
        
        print(f"Execution time - Reported: {result.execution_time:.3f}s, "
              f"Manual: {manual_time:.3f}s")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_agent_initialization_time(self, runtime):
        """Test agent initialization performance."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        # Measure ReactAgent initialization
        react_times = []
        for _ in range(5):
            start = time.time()
            agent = runtime.create_react_agent()
            react_times.append(time.time() - start)
            agent.reset_agent_memory()
        
        # Measure CodeActAgent initialization
        codact_times = []
        for _ in range(5):
            start = time.time()
            agent = runtime.create_codact_agent()
            codact_times.append(time.time() - start)
            agent.reset_agent_memory()
        
        # Calculate statistics
        react_avg = statistics.mean(react_times)
        codact_avg = statistics.mean(codact_times)
        
        print(f"ReactAgent init time: {react_avg:.3f}s (±{statistics.stdev(react_times):.3f}s)")
        print(f"CodeActAgent init time: {codact_avg:.3f}s (±{statistics.stdev(codact_times):.3f}s)")
        
        # Initialization should be reasonably fast
        assert react_avg < 1.0  # Less than 1 second
        assert codact_avg < 1.0
    
    @pytest.mark.performance
    def test_memory_reset_performance(self, runtime, cleanup_agents):
        """Test performance of memory reset operations."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Add substantial memory
        if hasattr(agent, 'agent'):
            agent.agent.memory = [f"memory_item_{i}" for i in range(1000)]
            agent.agent.logs = [f"log_item_{i}" for i in range(1000)]
        
        # Measure reset time
        start = time.time()
        agent.reset_agent_memory()
        reset_time = time.time() - start
        
        print(f"Memory reset time for 2000 items: {reset_time * 1000:.2f}ms")
        
        # Should be fast even with large memory
        assert reset_time < 0.1  # Less than 100ms
        
        # Verify memory was cleared
        assert len(agent.agent.memory) == 0
        assert len(agent.agent.logs) == 0
    
    @pytest.mark.performance
    @pytest.mark.requires_llm
    def test_parallel_vs_sequential_execution(self, runtime):
        """Compare parallel vs sequential tool execution performance."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        # Query that might trigger multiple tool calls
        query = "What are the populations of Tokyo and New York?"
        
        # Test with parallel execution (default)
        agent_parallel = runtime.create_react_agent()
        start = time.time()
        result_parallel = agent_parallel.run(query, return_result=True)
        time_parallel = time.time() - start
        agent_parallel.reset_agent_memory()
        
        # Test with sequential execution (single thread)
        agent_seq = runtime.create_react_agent()
        agent_seq.max_tool_threads = 1
        start = time.time()
        result_seq = agent_seq.run(query, return_result=True)
        time_seq = time.time() - start
        agent_seq.reset_agent_memory()
        
        print(f"Parallel execution: {time_parallel:.2f}s")
        print(f"Sequential execution: {time_seq:.2f}s")
        print(f"Speedup: {time_seq / time_parallel:.2f}x")
        
        # Both should complete successfully
        assert result_parallel.success
        assert result_seq.success
    
    @pytest.mark.performance
    def test_agent_cleanup_performance(self, runtime):
        """Test performance of agent cleanup operations."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        cleanup_times = []
        
        for _ in range(10):
            agent = runtime.create_react_agent()
            
            # Use the agent
            agent.run("Simple query")
            
            # Measure cleanup time
            start = time.time()
            agent.__exit__(None, None, None)
            cleanup_times.append(time.time() - start)
        
        avg_cleanup = statistics.mean(cleanup_times)
        print(f"Average cleanup time: {avg_cleanup * 1000:.2f}ms")
        
        # Cleanup should be fast
        assert avg_cleanup < 0.05  # Less than 50ms
    
    @pytest.mark.performance
    def test_runresult_serialization_performance(self):
        """Test performance of RunResult serialization."""
        # Create a large RunResult
        result = RunResult(
            final_answer="Test answer",
            execution_time=1.5,
            token_usage={"input": 1000, "output": 500, "total": 1500},
            agent_type="react"
        )
        
        # Add many steps
        for i in range(100):
            result.add_step({
                "type": f"step_{i % 5}",
                "content": f"Step {i} content with some longer text to simulate real usage",
                "metadata": {"index": i, "timestamp": time.time()}
            })
        
        # Measure serialization time
        iterations = 100
        
        # to_dict performance
        start = time.time()
        for _ in range(iterations):
            _ = result.to_dict()
        dict_time = time.time() - start
        
        # to_json performance
        start = time.time()
        for _ in range(iterations):
            _ = result.to_json()
        json_time = time.time() - start
        
        print(f"to_dict avg time: {dict_time / iterations * 1000:.2f}ms")
        print(f"to_json avg time: {json_time / iterations * 1000:.2f}ms")
        
        # Should be fast even with many steps
        assert dict_time / iterations < 0.01  # Less than 10ms per call
        assert json_time / iterations < 0.02  # Less than 20ms per call
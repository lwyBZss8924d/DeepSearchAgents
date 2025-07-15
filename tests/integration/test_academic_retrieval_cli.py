#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_academic_retrieval_cli.py
# code style: PEP 8

"""
CLI integration tests for AcademicRetrieval Tool.

These tests verify that the AcademicRetrieval tool works correctly
when used through the DeepSearchAgents CLI with both React and CodeAct agents.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch
from io import StringIO

from src.agents.runtime import AgentRuntime
from src.tools.academic_retrieval import AcademicRetrieval


@pytest.mark.integration
@pytest.mark.requires_llm
class TestAcademicRetrievalCLI:
    """Test AcademicRetrieval tool through CLI agents."""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        api_key = os.getenv("FUTUREHOUSE_API_KEY")
        if not api_key:
            pytest.skip("FUTUREHOUSE_API_KEY not set")
        return api_key

    @pytest.fixture
    def runtime(self, api_key):
        """Create agent runtime with API keys."""
        # Ensure API key is set in environment
        os.environ["FUTUREHOUSE_API_KEY"] = api_key
        
        runtime = AgentRuntime()
        
        # Verify AcademicRetrieval tool is available
        tool_names = [tool.name for tool in runtime._tools]
        assert "academic_retrieval" in tool_names, (
            f"AcademicRetrieval tool not found. Available tools: {tool_names}"
        )
        
        return runtime

    @pytest.mark.asyncio
    async def test_react_agent_search_papers(self, runtime):
        """Test Case 1: React agent searching for AI-LLM Agent papers."""
        print("\n=== Test Case 1: React Agent - Academic Search ===")
        
        query = (
            "Use the academic_retrieval tool to search AI-LLM Agent papers "
            "about [ReAct] agent methodology and find the Top 20 papers on "
            "derived methods. Provide a summary of the key findings."
        )
        
        # Create React agent
        agent = runtime.create_react_agent(debug_mode=False)
        
        print(f"Query: {query}")
        print("\nExecuting with React agent...")
        
        # Run the agent
        result = await asyncio.to_thread(agent.run, query)
        
        # Verify result
        assert result is not None
        print(f"\nResult preview: {str(result)[:500]}...")
        
        # Check if academic_retrieval was used
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'memory'):
            # Check if the tool was called
            tool_calls = [
                step for step in agent.agent.memory 
                if hasattr(step, 'tool_name') and step.tool_name == 'academic_retrieval'
            ]
            assert len(tool_calls) > 0, "academic_retrieval tool was not used"
            print(f"\nTool was called {len(tool_calls)} times")

    @pytest.mark.asyncio
    async def test_codact_agent_research_hira(self, runtime):
        """Test Case 2: CodeAct agent researching HiRA framework."""
        print("\n=== Test Case 2: CodeAct Agent - Academic Research ===")
        
        query = (
            'Use the academic_retrieval tool with operation="research" to '
            'search, read, and research the paper about "HiRA" '
            '(a hierarchical framework that decouples strategic planning '
            'from specialized execution in deep search tasks). '
            'Summarize:\n'
            '1. HiRA Framework architecture\n'
            '2. HiRA Framework pipeline & workflow\n'
            '3. HiRA Framework CORE methods & algorithm principles\n'
            'The final report should be in Chinese (最终报告用中文).'
        )
        
        # Create CodeAct agent
        agent = runtime.create_codact_agent(debug_mode=False)
        
        print(f"Query: {query[:200]}...")
        print("\nExecuting with CodeAct agent (this may take several minutes)...")
        
        # Run the agent
        result = await asyncio.to_thread(agent.run, query)
        
        # Verify result
        assert result is not None
        print(f"\nResult preview: {str(result)[:500]}...")
        
        # Check for Chinese content
        result_str = str(result)
        chinese_chars = ["框架", "架构", "方法", "算法", "流程"]
        has_chinese = any(char in result_str for char in chinese_chars)
        
        if has_chinese:
            print("\n✓ Chinese output detected in result")
        else:
            print("\n⚠ Warning: Expected Chinese output not detected")

    @pytest.mark.asyncio
    async def test_react_agent_combined_workflow(self, runtime):
        """Test combined search and analysis workflow with React agent."""
        print("\n=== Test Case 3: React Agent - Combined Workflow ===")
        
        query = (
            "First, use academic_retrieval to search for papers about "
            "'Large Language Model agent architectures'. "
            "Then analyze the results and identify the top 3 most cited papers. "
            "Finally, provide a brief summary of each paper's main contributions."
        )
        
        agent = runtime.create_react_agent(debug_mode=False)
        
        print(f"Query: {query}")
        print("\nExecuting combined workflow...")
        
        result = await asyncio.to_thread(agent.run, query)
        
        assert result is not None
        print(f"\nWorkflow completed. Result length: {len(str(result))} chars")

    @pytest.mark.asyncio
    async def test_codact_agent_code_generation(self, runtime):
        """Test CodeAct agent generating code to use academic tool."""
        print("\n=== Test Case 4: CodeAct Agent - Code Generation ===")
        
        query = (
            "Write Python code that uses the academic_retrieval tool to:\n"
            "1. Search for 'transformer architecture' papers\n"
            "2. Filter results to only include papers from 2023-2024\n"
            "3. Extract and print the titles and URLs\n"
            "Then execute the code and show the results."
        )
        
        agent = runtime.create_codact_agent(debug_mode=False)
        
        print(f"Query: {query}")
        print("\nExecuting with code generation...")
        
        result = await asyncio.to_thread(agent.run, query)
        
        assert result is not None
        print(f"\nCode execution completed")

    def test_tool_availability_in_agents(self, runtime):
        """Verify AcademicRetrieval tool is available in both agent types."""
        print("\n=== Testing Tool Availability ===")
        
        # Check React agent
        react_agent = runtime.create_react_agent(debug_mode=False)
        react_tools = {tool.name for tool in react_agent.tools}
        assert "academic_retrieval" in react_tools
        print("✓ AcademicRetrieval available in React agent")
        
        # Check CodeAct agent
        codact_agent = runtime.create_codact_agent(debug_mode=False)
        codact_tools = {tool.name for tool in codact_agent.tools}
        assert "academic_retrieval" in codact_tools
        print("✓ AcademicRetrieval available in CodeAct agent")
        
        # Find the tool instance
        academic_tool = None
        for tool in react_agent.tools:
            if tool.name == "academic_retrieval":
                academic_tool = tool
                break
                
        assert academic_tool is not None
        assert isinstance(academic_tool, AcademicRetrieval)
        
        # Check tool description
        print(f"\nTool name: {academic_tool.name}")
        print(f"Tool description: {academic_tool.description}")
        print(f"Tool inputs: {list(academic_tool.inputs.keys())}")

    @pytest.mark.asyncio
    async def test_error_handling_missing_params(self, runtime):
        """Test error handling when required parameters are missing."""
        print("\n=== Test Case 5: Error Handling ===")
        
        query = (
            "Use the academic_retrieval tool but don't specify any query. "
            "This should fail gracefully."
        )
        
        agent = runtime.create_react_agent(debug_mode=False)
        
        print(f"Query: {query}")
        print("\nTesting error handling...")
        
        result = await asyncio.to_thread(agent.run, query)
        
        # Agent should handle the error gracefully
        assert result is not None
        print("\n✓ Agent handled missing parameters gracefully")

    @pytest.mark.asyncio
    async def test_streaming_output(self, runtime):
        """Test streaming output with academic retrieval."""
        print("\n=== Test Case 6: Streaming Output ===")
        
        query = (
            "Search for 'neural network optimization' papers using "
            "academic_retrieval and show me the first 5 results."
        )
        
        # Create agent with streaming enabled
        agent = runtime.create_react_agent(debug_mode=False)
        if hasattr(agent, 'stream_outputs'):
            agent.stream_outputs = True
        
        print(f"Query: {query}")
        print("\nTesting with streaming enabled...")
        
        # Run with streaming
        result_gen = agent.run(query, stream=True)
        
        if hasattr(result_gen, '__aiter__'):
            # Async generator
            chunks = []
            async for chunk in result_gen:
                chunks.append(str(chunk))
                if len(chunks) % 10 == 0:
                    print(".", end="", flush=True)
            
            result = "".join(chunks)
            print(f"\n✓ Streamed {len(chunks)} chunks")
        else:
            # Non-streaming fallback
            result = await asyncio.to_thread(lambda: result_gen)
            print("\n✓ Non-streaming result received")
        
        assert result is not None

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_manager_agent_with_academic_tool(self, runtime):
        """Test Manager agent orchestrating academic research."""
        print("\n=== Test Case 7: Manager Agent - Team Research ===")
        
        query = (
            "Research the topic 'Multi-Agent Systems in AI' by:\n"
            "1. Having one agent search for recent papers\n"
            "2. Having another agent analyze the findings\n"
            "3. Synthesize a comprehensive report"
        )
        
        # Create Manager agent
        agent = runtime.get_or_create_agent("manager")
        
        print(f"Query: {query}")
        print("\nExecuting with Manager agent team...")
        
        result = await asyncio.to_thread(agent.run, query)
        
        assert result is not None
        print(f"\nTeam research completed. Result length: {len(str(result))} chars")


if __name__ == "__main__":
    # Run specific test for debugging
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        pytest.main(["-xvs", __file__, f"-k", test_name])
    else:
        # Run all tests
        pytest.main(["-xvs", __file__])
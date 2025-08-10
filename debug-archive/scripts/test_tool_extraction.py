#!/usr/bin/env python3
"""
Test tool extraction logic from web_ui.py
"""
import re
from typing import List

def _extract_tools_from_code(code: str) -> List[str]:
    """
    Extract tool names from Python code.
    
    Args:
        code: Python code to analyze.
        
    Returns:
        List of tool names found in the code.
    """
    if not code:
        return []
    
    # Known tool names from toolbox.py
    known_tools = [
        "search_links", "search_fast", "read_url", "github_repo_qa",
        "xcom_deep_qa", "chunk_text", "embed_texts", "rerank_texts",
        "wolfram", "academic_retrieval", "final_answer"
    ]
    
    tool_calls = []
    
    # Check for tool calls using various patterns
    for tool in known_tools:
        # Pattern 1: Direct function call: tool_name(...)
        pattern1 = rf'\b{tool}\s*\('
        # Pattern 2: Variable assignment: var = tool_name(...)
        pattern2 = rf'=\s*{tool}\s*\('
        # Pattern 3: Method call: obj.tool_name(...)
        pattern3 = rf'\.{tool}\s*\('
        # Pattern 4: In list: [tool_name(...)]
        pattern4 = rf'\[\s*{tool}\s*\('
        
        if (re.search(pattern1, code) or re.search(pattern2, code) or
                re.search(pattern3, code) or re.search(pattern4, code)):
            if tool not in tool_calls:  # Avoid duplicates
                tool_calls.append(tool)
                print(f"Found tool in code: {tool}")
    
    return tool_calls

# Test with various code samples
test_cases = [
    # Case 1: Direct search and read
    """
search_results = search_links("quantum computing")
for url in search_results[:3]:
    content = read_url(url)
    print(content)
""",
    
    # Case 2: Academic research
    """
papers = academic_retrieval("quantum computing", max_results=5)
for paper in papers:
    summary = read_url(paper.url)
    chunks = chunk_text(summary)
    embeddings = embed_texts(chunks)
    
relevant_chunks = rerank_texts(query, chunks)
final_answer(f"Summary: {relevant_chunks[0]}")
""",
    
    # Case 3: Complex search with multiple tools
    """
# Search for information
results1 = search_links("quantum computing basics")
results2 = search_fast("quantum computing applications")

# Deep analysis
xcom_result = xcom_deep_qa("What is quantum computing?")

# Math calculation
calc_result = wolfram("solve x^2 + 2x + 1 = 0")

# GitHub search
repo_info = github_repo_qa("quantum computing simulator")

# Final processing
all_info = [results1, results2, xcom_result, calc_result, repo_info]
final_answer("Comprehensive quantum computing overview: " + str(all_info))
"""
]

print("Tool Extraction Test")
print("=" * 50)

for i, code in enumerate(test_cases, 1):
    print(f"\nTest Case {i}:")
    print("-" * 30)
    print("Code:")
    print(code.strip())
    print("\nExtracted tools:")
    tools = _extract_tools_from_code(code)
    print(f"Found {len(tools)} tools: {tools}")
    print()
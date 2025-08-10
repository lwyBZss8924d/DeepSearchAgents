
## simple search test case 1


```bash
Hello! Please search for the US weather data sources in {{ CITY: "New York" }} city today. --- Current time: {{ CURRENT_TIME: 2025-05-06 }} --- first and provide me with the Zh(Chinese) weather table forecast report.
```

```bash
Hi bro! 1.Please websearch for the US weather data sources in {{ CITY: "New York" }} city today. --- Current time: {{ CURRENT_TIME: 2025-05-06 }} --- first, 2. and provide me with the Zh(Chinese) butiful markdown table of forecast report(all units need to be converted to metric units).
```

## simple search test case 2

```bash
Hello! Please websearch about Qwen new LLM model "Qwen3" model card and provide me with the "Qwen3" model performance, and any other information summary in beautiful markdown table report. --- Current time: {{ CURRENT_TIME: 2025-05-06 }}
```

```bash
Hello! Please websearch about Qwen new LLM model "Qwen3" model card and provide me with the "Qwen3" LLM model information summary report. --- Current time: {{ CURRENT_TIME: 2025-05-06 }}
```

## test mcp tools: arxiv

```bash
Hello! Please search about [Executable Code Actions Elicit Better LLM Agents](https://arxiv.org/html/2402.01030v4) arXiv paper, and provide me with the paper summary with beautiful markdown table report use Zh(Chinese). --- Current time: {{ CURRENT_TIME: 2025-05-06 }}
```

===

```bash
Hello! Please Web-Search about 1. Open AI —— "[Codex] Software engineering Agent `chatgpt.com/codex`" New Product info (https://platform.openai.com/docs/codex) 2. Use Zh(中文) summary AI Agent Report for me. --- Current time: {{ CURRENT_TIME: 2025-05-16 }}
```

===

```bash
Hi! Please Web Search latest news and twitter(x.com)Trending Top tweets about the deepseek-r1 latest releases version(deepseek-r1-0528) LLM update news and new version multiple-Benchmark(Platforms e.g. coding / Math reasoning / Computer Use / long context comprehension/etc.). Get all you need deep-search info for analysis. End of research job summary output with a fulltable report with MUST use Zh(中文) for me --- CURRENT_TIME: {{ CURRENT_TIME: 2025-05-29 }} ---
```

## Academic Retrieval Test Cases

### Test Case 1: Search Academic Papers

```bash
Use the academic_retrieval tool to search AI-LLM Agent papers about [ReAct] agent methodology and find the Top 20 papers on derived methods. --- Current time: {{ CURRENT_TIME: 2025-05-30 }}
```

### Test Case 2: Deep Academic Research

```bash
Use the academic_retrieval tool with operation="research" to search, read, and research the paper about "HiRA" (a hierarchical framework that decouples strategic planning from specialized execution in deep search tasks). Summarize the paper core work about "Decoupled Planning and Execution: A Hierarchical Reasoning(HiRA) Framework for Deep Search":
- "HiRA" Framework architecture;
- "HiRA" Framework base pipeline & workflow (mermaid Flowchart & sequenceDiagram);
- "HiRA" Framework CORE methods & algorithm principles;
Output: End of your research job output result research report MUST be in Zh(最终报告用中文) for me, BUT you reasoning process MUST be in English (EN). --- Current time: {{ CURRENT_TIME: 2025-05-30 }}
```

### Test Case 3: Combined Academic Search and Analysis

```bash
First, use academic_retrieval to search for papers about "Large Language Model agent architectures CodeAct ReAct". Then analyze the results and compare these methodologies. Finally, provide a comprehensive analysis with a summary table in Chinese (用中文总结). --- Current time: {{ CURRENT_TIME: 2025-05-30 }}
```

### Test Case 4: Multi-Query Academic Search

```bash
Use academic_retrieval to search for multiple topics:
1. "Transformer architecture optimization techniques"
2. "Multi-agent reinforcement learning"
3. "Neural architecture search methods"
Provide a comparative analysis of the findings across these three areas. --- Current time: {{ CURRENT_TIME: 2025-05-30 }}
```
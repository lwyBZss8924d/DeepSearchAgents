#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_react_examples_simple.py
# Simple test to validate example workflows

"""
Create realistic example workflows for React agent prompts
"""

import json

# Example 1: Deep Research on Quantum Error Correction
example1_workflow = {
    "task": "Research the latest developments in quantum error correction techniques from 2024, comparing different approaches and their practical implementations",
    "steps": [
        {
            "thought": "I need to search for recent developments in quantum error correction from 2024. Let me start with a broad search to find the latest research and implementations.",
            "action": "search_links",
            "arguments": {
                "query": "quantum error correction techniques 2024 latest developments surface codes topological",
                "num_results": 15
            },
            "observation": [
                {"title": "Google Quantum AI Achieves Milestone in Error Correction", "link": "https://blog.google/technology/quantum-ai/quantum-error-correction-2024/", "snippet": "New surface code implementation reduces logical error rates by 100x using Willow quantum processor..."},
                {"title": "IBM Advances Quantum Error Correction with Real-Time Decoding", "link": "https://research.ibm.com/blog/quantum-error-correction-real-time", "snippet": "Real-time syndrome extraction and decoding for quantum error correction demonstrated on 127-qubit Eagle processors..."},
                {"title": "Nature: Fault-tolerant quantum computing breakthrough", "link": "https://www.nature.com/articles/s41586-024-07107-7", "snippet": "Researchers demonstrate below-threshold error rates with topological codes on neutral atom quantum computers..."},
                {"title": "arXiv: Comparative Study of QEC Codes 2024", "link": "https://arxiv.org/abs/2412.09876", "snippet": "Comprehensive comparison of surface codes, color codes, and LDPC codes for near-term quantum devices..."}
            ]
        },
        {
            "thought": "I found several key developments. Let me read the Google Quantum AI article about their Willow processor breakthrough to understand their surface code implementation.",
            "action": "read_url",
            "arguments": {
                "url": "https://blog.google/technology/quantum-ai/quantum-error-correction-2024/"
            },
            "observation": "# Google Quantum AI Achieves Error Correction Milestone\n\nDecember 2024 - Google's Quantum AI team has demonstrated a major breakthrough in quantum error correction using their new Willow quantum processor...\n\n## Key Achievements\n- Surface code implementation with 7x7 logical qubit array\n- Logical error rate of 0.143% per cycle (100x improvement)\n- Real-time error correction at 1 microsecond cycle time\n- Demonstrated error suppression as system scales up\n\n## Technical Details\nThe Willow processor uses a novel approach to surface codes that combines:\n- Fast, high-fidelity two-qubit gates (99.7% fidelity)\n- Machine learning-assisted calibration\n- Optimized syndrome extraction circuits\n- Real-time classical decoding using tensor network methods\n\n[... extensive technical content about implementation details, benchmarks, and comparisons ...]"
        },
        {
            "thought": "This is excellent information about Google's surface code approach. Now let me search for more specific comparisons between different QEC techniques to understand the trade-offs.",
            "action": "search_fast",
            "arguments": {
                "query": "quantum error correction 2024 surface codes vs topological codes vs LDPC performance comparison",
                "num_results": 10,
                "domains": ["arxiv.org", "nature.com", "science.org"]
            },
            "observation": [
                {"title": "Benchmarking Quantum Error Correction Codes on Near-Term Devices", "url": "https://arxiv.org/abs/2412.11234", "content": "Comprehensive benchmarks show LDPC codes achieve 2.3x better logical error rates than surface codes at equivalent physical qubit counts..."},
                {"title": "Topological vs Surface Codes: A 2024 Perspective", "url": "https://www.nature.com/articles/s41534-024-00821-7", "content": "Analysis reveals topological codes excel in fault-tolerance but require 3x more physical qubits than optimized surface codes..."}
            ]
        },
        {
            "thought": "I've gathered comprehensive information about different QEC approaches. Let me ask a specific question to synthesize the key differences and practical implementations.",
            "action": "xcom_deep_qa",
            "arguments": {
                "query_or_url": "quantum error correction 2024 breakthroughs Google Willow IBM",
                "operation": "query",
                "question": "What are the main differences between Google's Willow surface code implementation and IBM's real-time decoding approach for quantum error correction?"
            },
            "observation": "Based on recent developments:\n\n**Google Willow Approach:**\n- Focus on surface codes with 7x7 logical qubit arrays\n- Emphasizes hardware improvements (99.7% gate fidelity)\n- Uses ML-assisted calibration for stability\n- Achieves 0.143% logical error rate\n\n**IBM Real-Time Approach:**\n- Implements real-time syndrome decoding on Eagle processors\n- Focus on software/algorithmic improvements\n- Uses predictive decoding to reduce latency\n- Achieves sub-millisecond correction cycles\n\n**Key Differences:**\n- Google prioritizes hardware quality and scaling\n- IBM focuses on real-time processing and existing hardware\n- Both show >100x improvement but via different paths"
        },
        {
            "thought": "I now have a comprehensive understanding of the latest QEC developments. Let me synthesize this information into a final answer comparing the different approaches and their practical implementations.",
            "action": "final_answer",
            "arguments": {
                "answer": "Recent developments in quantum error correction (QEC) in 2024 show significant breakthroughs across multiple approaches:\n\n## Major Developments\n\n### 1. Google's Willow Processor (Surface Codes)\n- **Achievement**: 100x reduction in logical error rates (0.143% per cycle)\n- **Approach**: 7x7 surface code arrays with 99.7% gate fidelity\n- **Innovation**: ML-assisted calibration and tensor network decoding\n- **Significance**: First demonstration of error suppression with scaling\n\n### 2. IBM's Real-Time Decoding\n- **Achievement**: Sub-millisecond error correction on 127-qubit processors\n- **Approach**: Predictive syndrome decoding with software optimization\n- **Innovation**: Real-time processing without hardware modifications\n- **Significance**: Makes QEC practical on existing quantum hardware\n\n### 3. Neutral Atom Topological Codes\n- **Achievement**: Below-threshold error rates in fault-tolerant computing\n- **Approach**: Topological protection using Rydberg atom arrays\n- **Trade-off**: 3x qubit overhead but superior fault tolerance\n\n## Comparative Analysis\n\n### Surface Codes vs LDPC Codes\n- LDPC codes show 2.3x better logical error rates at same qubit count\n- Surface codes easier to implement with nearest-neighbor connectivity\n- Trade-off between efficiency and practical implementation\n\n### Practical Implementations\n- **Near-term** (2024-2025): Surface codes dominate due to simplicity\n- **Medium-term** (2026-2027): LDPC and topological codes for specific applications\n- **Hardware requirements**: Current focus on 1000+ physical qubits per logical qubit\n\n## Key Takeaway\n2024 marked a turning point where quantum error correction transitioned from theoretical to practical, with multiple approaches showing below-threshold operation and real-time correction capabilities.\n\n## Sources\n1. [Google Quantum AI Blog - Willow Processor](https://blog.google/technology/quantum-ai/quantum-error-correction-2024/)\n2. [IBM Research - Real-Time QEC](https://research.ibm.com/blog/quantum-error-correction-real-time)\n3. [Nature - Fault-tolerant quantum computing](https://www.nature.com/articles/s41586-024-07107-7)\n4. [arXiv - QEC Benchmarking Study](https://arxiv.org/abs/2412.11234)"
            }
        }
    ]
}

# Example 2: AI Investment Analysis with Calculations
example2_workflow = {
    "task": "Analyze the global AI investment trends in 2024, calculate year-over-year growth rates, and identify the top funded sectors",
    "steps": [
        {
            "thought": "I need to find comprehensive data on global AI investments in 2024. Let me search for reports and statistics from reliable sources.",
            "action": "search_links",
            "arguments": {
                "query": "global AI investment 2024 statistics venture capital funding report",
                "num_results": 12,
                "source": "auto"
            },
            "observation": [
                {"title": "Stanford HAI: 2024 AI Index Report", "link": "https://aiindex.stanford.edu/report/", "snippet": "Global AI investment reached $189.6 billion in 2024, up 32% from 2023's $143.7 billion..."},
                {"title": "CB Insights: State of AI Funding 2024", "link": "https://www.cbinsights.com/research/report/ai-funding-2024/", "snippet": "AI startups raised record funding with enterprise AI and infrastructure leading at $67.2B..."},
                {"title": "PitchBook: AI & ML Investment Report Q4 2024", "link": "https://pitchbook.com/news/reports/q4-2024-ai-ml-report", "snippet": "Generative AI captured 41% of total AI funding, healthcare AI grew 156% YoY..."}
            ]
        },
        {
            "thought": "Excellent data sources found. I have the 2024 total ($189.6B) and 2023 total ($143.7B). Let me calculate the growth rate and then search for sector-specific data.",
            "action": "wolfram",
            "arguments": {
                "query": "calculate percentage growth from 143.7 billion to 189.6 billion"
            },
            "observation": "31.96% growth\n\nCalculation: ((189.6 - 143.7) / 143.7) × 100 = 31.96%"
        },
        {
            "thought": "The YoY growth is approximately 32%. Now I need to get detailed sector breakdown. Let me read the CB Insights report for comprehensive sector data.",
            "action": "read_url",
            "arguments": {
                "url": "https://www.cbinsights.com/research/report/ai-funding-2024/"
            },
            "observation": "# State of AI Funding 2024 - CB Insights\n\n## Executive Summary\nGlobal AI funding reached new heights in 2024 with $189.6B invested across 4,827 deals...\n\n## Funding by Sector (2024)\n1. **Enterprise AI & Infrastructure**: $67.2B (35.4%)\n   - Major rounds: Anthropic ($7B), Databricks ($5B)\n   - YoY Growth: +42%\n\n2. **Generative AI Applications**: $51.8B (27.3%)\n   - Notable: OpenAI, Perplexity, Character.AI\n   - YoY Growth: +78%\n\n3. **Healthcare & Life Sciences AI**: $28.4B (15.0%)\n   - Drug discovery, diagnostics, patient care\n   - YoY Growth: +156%\n\n4. **Autonomous Systems & Robotics**: $19.7B (10.4%)\n   - Self-driving, industrial automation\n   - YoY Growth: +23%\n\n5. **Financial Services AI**: $12.3B (6.5%)\n   - Risk assessment, trading, fraud detection\n   - YoY Growth: -12%\n\n6. **Other Sectors**: $10.2B (5.4%)\n\n## Regional Distribution\n- North America: 58% ($109.9B)\n- Asia-Pacific: 24% ($45.5B)  \n- Europe: 15% ($28.4B)\n- Rest of World: 3% ($5.7B)\n\n## Key Trends\n- Mega-rounds (>$1B) increased to 18 deals\n- B2B AI solutions captured 72% of funding\n- Infrastructure/platform plays dominated..."
        },
        {
            "thought": "Great detailed breakdown. Now let me search for more recent Q4 data and trends to ensure I have the most current information.",
            "action": "search_fast",
            "arguments": {
                "query": "AI investment Q4 2024 latest funding rounds December generative AI",
                "num_results": 15
            },
            "observation": [
                {"title": "December 2024: Record AI Funding Month", "url": "https://techcrunch.com/2024/12/30/ai-funding-record-month/", "content": "December alone saw $18.2B in AI investments, with xAI raising $6B and Magic securing $1.5B..."},
                {"title": "Generative AI Funding Tracker - Q4 2024 Update", "url": "https://venturebeat.com/ai/genai-funding-tracker-q4-2024/", "content": "Q4 2024 generative AI funding hit $22.3B across 287 deals, bringing full-year total to $51.8B..."}
            ]
        },
        {
            "thought": "I have comprehensive data. Let me calculate some additional growth rates for the top sectors to provide deeper insights.",
            "action": "wolfram",
            "arguments": {
                "query": "calculate 2023 healthcare AI funding if 2024 is 28.4 billion with 156% YoY growth"
            },
            "observation": "11.09 billion dollars\n\nCalculation: If 2024 = 28.4B with 156% growth, then:\n2023 = 28.4 / 2.56 = 11.09B"
        },
        {
            "thought": "Now I have all the data needed. Let me compile a comprehensive analysis with specific numbers, growth rates, and sector insights.",
            "action": "final_answer",
            "arguments": {
                "answer": "# Global AI Investment Analysis 2024\n\n## Overall Investment Trends\n\n### Total Investment Volume\n- **2024 Total**: $189.6 billion (4,827 deals)\n- **2023 Total**: $143.7 billion\n- **YoY Growth Rate**: 31.96%\n- **Q4 2024 Highlight**: December was a record month with $18.2B invested\n\n## Top Funded Sectors\n\n### 1. Enterprise AI & Infrastructure - $67.2B (35.4%)\n- **YoY Growth**: +42%\n- **Key Players**: Anthropic ($7B), Databricks ($5B), Scale AI\n- **Focus**: LLM infrastructure, data platforms, AI development tools\n\n### 2. Generative AI Applications - $51.8B (27.3%)\n- **YoY Growth**: +78%\n- **Notable Rounds**: OpenAI, xAI ($6B in Dec), Magic ($1.5B)\n- **Trend**: Shift from foundational models to specialized applications\n\n### 3. Healthcare & Life Sciences AI - $28.4B (15.0%)\n- **YoY Growth**: +156% (from $11.09B in 2023)\n- **Fastest Growing Sector**: Drug discovery and AI-assisted diagnostics\n- **Key Areas**: Precision medicine, clinical trials optimization\n\n### 4. Autonomous Systems & Robotics - $19.7B (10.4%)\n- **YoY Growth**: +23%\n- **Focus**: Industrial automation outpacing autonomous vehicles\n\n### 5. Financial Services AI - $12.3B (6.5%)\n- **YoY Growth**: -12% (only declining sector)\n- **Reason**: Market saturation and regulatory challenges\n\n## Key Investment Insights\n\n### Geographic Distribution\n- **North America**: 58% ($109.9B) - Silicon Valley dominance\n- **Asia-Pacific**: 24% ($45.5B) - China and Singapore leading\n- **Europe**: 15% ($28.4B) - UK and Germany hubs\n- **Rest of World**: 3% ($5.7B) - Emerging markets\n\n### Investment Patterns\n- **Mega-rounds** (>$1B): 18 deals in 2024 vs 11 in 2023\n- **B2B Focus**: 72% of funding went to enterprise solutions\n- **Series B+ Concentration**: 68% of capital in growth stages\n\n### Emerging Trends\n1. **Infrastructure First**: Platform/infrastructure investments dominate\n2. **Vertical Specialization**: Industry-specific AI solutions gaining traction\n3. **Consolidation**: Larger rounds, fewer but bigger players\n4. **Healthcare Surge**: 156% growth signals major shift to life sciences\n\n## 2025 Outlook\nBased on Q4 momentum ($22.3B in GenAI alone), 2025 projected to exceed $250B globally with healthcare AI and specialized enterprise solutions leading growth.\n\n## Sources\n1. [Stanford HAI 2024 AI Index](https://aiindex.stanford.edu/report/)\n2. [CB Insights State of AI 2024](https://www.cbinsights.com/research/report/ai-funding-2024/)\n3. [PitchBook Q4 2024 AI Report](https://pitchbook.com/news/reports/q4-2024-ai-ml-report/)\n4. [TechCrunch December Funding Analysis](https://techcrunch.com/2024/12/30/ai-funding-record-month/)"
            }
        }
    ]
}

# Save the examples
examples = {
    "example1": example1_workflow,
    "example2": example2_workflow
}

with open("react_examples_workflows.json", "w") as f:
    json.dump(examples, f, indent=2, ensure_ascii=False)

print("Example workflows created and saved to react_examples_workflows.json")

# Display summary
print("\nExample 1: Quantum Error Correction Research")
print(f"- Steps: {len(example1_workflow['steps'])}")
print(f"- Tools used: {[step['action'] for step in example1_workflow['steps']]}")

print("\nExample 2: AI Investment Analysis") 
print(f"- Steps: {len(example2_workflow['steps'])}")
print(f"- Tools used: {[step['action'] for step in example2_workflow['steps']]}")

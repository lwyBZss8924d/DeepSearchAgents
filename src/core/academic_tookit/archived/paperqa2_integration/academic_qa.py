#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/academic_qa.py
# code style: PEP 8

"""
High-level Academic QA System API.

This module provides a user-friendly interface for academic paper
research and question answering using PaperQA2 and our toolkit.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from paperqa import Answer

from ..models import Paper, SearchParams
from ..paper_retrievaler import PaperRetriever
from .manager import PaperQA2Manager
from .config import PaperQA2Config, SearchConfig, load_config_from_env
from .mistral_ocr_reader import MistralOCRReader

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Result from academic research query."""

    question: str
    answer: str
    confidence: Optional[float] = None
    papers_found: int = 0
    papers_analyzed: int = 0
    sources: List[Dict[str, Any]] = None
    search_query: Optional[str] = None
    processing_time: Optional[float] = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "papers_found": self.papers_found,
            "papers_analyzed": self.papers_analyzed,
            "sources": self.sources,
            "search_query": self.search_query,
            "processing_time": self.processing_time
        }


class AcademicQASystem:
    """
    High-level interface for academic Q&A.

    This system provides:
    - Simple API for paper search and Q&A
    - Automatic paper retrieval and processing
    - Citation tracking and verification
    - Trend analysis and contradiction detection
    - Export capabilities for research results
    """

    def __init__(
        self,
        config: Optional[PaperQA2Config] = None,
        search_config: Optional[SearchConfig] = None
    ):
        """
        Initialize Academic QA System.

        Args:
            config: PaperQA2 configuration
            search_config: Search configuration
        """
        # Load config from environment if not provided
        self.config = config or load_config_from_env()
        self.search_config = search_config or SearchConfig()

        # Initialize components
        self.manager = PaperQA2Manager(**self.config.to_manager_kwargs())

        # Initialize custom reader if configured
        if self.config.use_mistral_ocr:
            self.mistral_reader = MistralOCRReader(
                config=self.config.to_mistral_config(),
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )

        logger.info("Initialized AcademicQASystem")

    async def ask(
        self,
        question: str,
        search_query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        max_papers: int = 10,
        papers: Optional[List[Union[Paper, str]]] = None
    ) -> ResearchResult:
        """
        Ask a research question.

        This is the main entry point for the system. It will:
        1. Search for relevant papers (if not provided)
        2. Process and analyze them
        3. Generate a comprehensive answer

        Args:
            question: Research question to answer
            search_query: Query for finding papers (uses question if None)
            sources: Paper sources to search
            max_papers: Maximum papers to analyze
            papers: Specific papers to analyze (skips search)

        Returns:
            ResearchResult with answer and metadata
        """
        start_time = datetime.now()

        # Use provided papers or search for them
        if papers:
            logger.info(f"Using {len(papers)} provided papers")
            papers_found = len(papers)
            answer = await self.manager.ask_about_papers(
                question=question,
                papers=papers,
                use_agent=self.config.use_agent
            )
        else:
            # Search for papers
            sources = sources or self.search_config.default_sources
            answer = await self.manager.ask_about_topic(
                question=question,
                search_query=search_query,
                sources=sources,
                max_papers=max_papers,
                use_agent=self.config.use_agent
            )
            papers_found = max_papers  # Approximate

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Extract sources
        sources_list = []
        if hasattr(answer, 'sources') and answer.sources:
            for source in answer.sources:
                sources_list.append({
                    "text": source.text if hasattr(source, 'text') else str(source),
                    "score": source.score if hasattr(source, 'score') else None
                })

        # Create result
        result = ResearchResult(
            question=question,
            answer=answer.answer if hasattr(answer, 'answer') else str(answer),
            papers_found=papers_found,
            papers_analyzed=len(sources_list),
            sources=sources_list,
            search_query=search_query or question,
            processing_time=processing_time
        )

        logger.info(
            f"Answered question in {processing_time:.2f}s, "
            f"analyzed {result.papers_analyzed} papers"
        )

        return result

    async def analyze_trends(
        self,
        topic: str,
        time_period: Optional[str] = None,
        sources: Optional[List[str]] = None,
        max_papers: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze research trends for a topic.

        Args:
            topic: Research topic
            time_period: Time period (e.g., "2023-2024")
            sources: Paper sources to search
            max_papers: Maximum papers to analyze

        Returns:
            Trend analysis results
        """
        sources = sources or self.search_config.default_sources

        # Use manager's trend analysis
        results = await self.manager.analyze_paper_trends(
            topic=topic,
            time_period=time_period,
            max_papers=max_papers
        )

        # Enhance results
        results["sources_searched"] = sources
        results["time_period"] = time_period or "all time"

        return results

    async def find_contradictions(
        self,
        topic: str,
        papers: Optional[List[Paper]] = None,
        sources: Optional[List[str]] = None,
        max_papers: int = 15
    ) -> Dict[str, Any]:
        """
        Find contradictions in research about a topic.

        Args:
            topic: Research topic
            papers: Specific papers to analyze
            sources: Sources to search if papers not provided
            max_papers: Maximum papers if searching

        Returns:
            Contradiction analysis
        """
        # Search for papers if not provided
        if papers is None:
            sources = sources or self.search_config.default_sources
            papers = await self.manager.paper_retriever.search(
                query=topic,
                sources=sources,
                max_results=max_papers
            )

        # Find contradictions
        results = await self.manager.find_contradictions(
            topic=topic,
            papers=papers,
            max_papers=max_papers
        )

        return results

    async def verify_claim(
        self,
        claim: str,
        context: Optional[str] = None,
        sources: Optional[List[str]] = None,
        max_papers: int = 10
    ) -> Dict[str, Any]:
        """
        Verify a scientific claim.

        Args:
            claim: Claim to verify
            context: Additional context
            sources: Sources to search
            max_papers: Maximum papers to check

        Returns:
            Verification results with evidence
        """
        # Build verification question
        question = f"Is the following claim supported by scientific evidence: '{claim}'?"
        if context:
            question += f" Context: {context}"
        question += " Provide evidence for and against this claim."

        # Search and analyze
        result = await self.ask(
            question=question,
            search_query=claim,
            sources=sources,
            max_papers=max_papers
        )

        # Structure verification result
        return {
            "claim": claim,
            "context": context,
            "verdict": self._extract_verdict(result.answer),
            "evidence": result.answer,
            "sources": result.sources,
            "papers_analyzed": result.papers_analyzed
        }

    async def summarize_paper(
        self,
        paper: Union[Paper, str],
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed summary of a paper.

        Args:
            paper: Paper object or paper ID
            focus: Specific aspect to focus on

        Returns:
            Paper summary
        """
        # Build summary question
        question = "Provide a comprehensive summary of this paper including: "
        question += "1) Main contributions, 2) Methodology, 3) Key findings, "
        question += "4) Limitations, 5) Future work."

        if focus:
            question += f" Pay special attention to: {focus}"

        # Analyze single paper
        result = await self.ask(
            question=question,
            papers=[paper]
        )

        # Extract paper title
        paper_title = paper.title if isinstance(paper, Paper) else paper

        return {
            "paper": paper_title,
            "summary": result.answer,
            "focus": focus,
            "processing_time": result.processing_time
        }

    async def compare_papers(
        self,
        papers: List[Union[Paper, str]],
        aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple papers.

        Args:
            papers: Papers to compare
            aspects: Specific aspects to compare

        Returns:
            Comparison results
        """
        # Build comparison question
        question = "Compare and contrast these papers"

        if aspects:
            question += f" focusing on: {', '.join(aspects)}"
        else:
            question += " in terms of methodology, findings, and contributions"

        # Analyze papers
        result = await self.ask(
            question=question,
            papers=papers
        )

        return {
            "papers_compared": len(papers),
            "aspects": aspects or ["methodology", "findings", "contributions"],
            "comparison": result.answer,
            "sources": result.sources
        }

    async def export_research(
        self,
        results: List[ResearchResult],
        format: str = "markdown",
        output_path: Optional[Path] = None
    ) -> str:
        """
        Export research results.

        Args:
            results: Research results to export
            format: Export format (markdown, json, html)
            output_path: Path to save (returns string if None)

        Returns:
            Exported content as string
        """
        if format == "markdown":
            content = self._export_markdown(results)
        elif format == "json":
            import json
            content = json.dumps(
                [r.to_dict() for r in results],
                indent=2
            )
        elif format == "html":
            content = self._export_html(results)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Save to file if path provided
        if output_path:
            output_path.write_text(content)
            logger.info(f"Exported research to {output_path}")

        return content

    def _extract_verdict(self, answer: str) -> str:
        """Extract verdict from verification answer."""
        answer_lower = answer.lower()

        if "supported" in answer_lower and "not supported" not in answer_lower:
            return "SUPPORTED"
        elif "not supported" in answer_lower or "unsupported" in answer_lower:
            return "NOT SUPPORTED"
        elif "mixed" in answer_lower or "partial" in answer_lower:
            return "MIXED EVIDENCE"
        else:
            return "UNCLEAR"

    def _export_markdown(self, results: List[ResearchResult]) -> str:
        """Export results as markdown."""
        lines = ["# Academic Research Results\n"]
        lines.append(f"Generated: {datetime.now().isoformat()}\n")

        for i, result in enumerate(results, 1):
            lines.append(f"## {i}. {result.question}\n")
            lines.append(f"**Answer:**\n{result.answer}\n")

            if result.sources:
                lines.append("**Sources:**")
                for j, source in enumerate(result.sources, 1):
                    lines.append(f"{j}. {source['text']}")
                lines.append("")

            lines.append(f"**Metadata:**")
            lines.append(f"- Papers found: {result.papers_found}")
            lines.append(f"- Papers analyzed: {result.papers_analyzed}")
            lines.append(f"- Processing time: {result.processing_time:.2f}s")
            lines.append("")

        return "\n".join(lines)

    def _export_html(self, results: List[ResearchResult]) -> str:
        """Export results as HTML."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Academic Research Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        .answer { background: #f5f5f5; padding: 15px; border-radius: 5px; }
        .sources { margin-top: 15px; }
        .metadata { color: #888; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>Academic Research Results</h1>
    <p>Generated: {timestamp}</p>
""".format(timestamp=datetime.now().isoformat())

        for i, result in enumerate(results, 1):
            html += f"""
    <h2>{i}. {result.question}</h2>
    <div class="answer">
        <strong>Answer:</strong><br>
        {result.answer.replace(chr(10), '<br>')}
    </div>
"""

            if result.sources:
                html += """
    <div class="sources">
        <strong>Sources:</strong>
        <ol>
"""
                for source in result.sources:
                    html += f"            <li>{source['text']}</li>\n"
                html += "        </ol>\n    </div>\n"

            html += f"""
    <div class="metadata">
        Papers found: {result.papers_found} |
        Papers analyzed: {result.papers_analyzed} |
        Processing time: {result.processing_time:.2f}s
    </div>
"""

        html += """
</body>
</html>"""

        return html

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/manager.py
# code style: PEP 8

"""
PaperQA2 manager for orchestrating academic paper Q&A.

This module provides the main interface for using PaperQA2 with our
academic toolkit's search capabilities.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import tempfile
import aiohttp

from paperqa import Docs, Settings, Answer
from paperqa.clients import DocMetadataClient
from paperqa.agents import agent_query
from paperqa.settings import AnswerSettings, ParsingSettings, AgentSettings

from ..paper_retrievaler import PaperRetriever
from ..models import Paper, PaperSource, SearchParams
from .arxiv_provider import ArxivPaperQA2Provider

logger = logging.getLogger(__name__)


class PaperQA2Manager:
    """
    Manages PaperQA2 integration with academic toolkit.

    This class:
    - Configures PaperQA2 with our custom providers
    - Manages paper collection building from searches
    - Handles document processing and caching
    - Provides high-level Q&A interface
    """

    def __init__(
        self,
        llm_model: str = "openai/gemini-2.5-pro",
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 5000,
        evidence_k: int = 10,
        use_custom_providers: bool = True,
        cache_dir: Optional[Path] = None,
        pdf_parser: Optional[Any] = None,
        settings: Optional[Settings] = None
    ):
        """
        Initialize PaperQA2 manager.

        Args:
            llm_model: LLM to use for Q&A
            embedding_model: Embedding model for retrieval
            chunk_size: Size of text chunks
            evidence_k: Number of evidence pieces to retrieve
            use_custom_providers: Whether to use our custom providers
            cache_dir: Directory for caching papers
            pdf_parser: Optional custom PDF parser function
            settings: Optional pre-configured Settings object
        """
        # Store model names for reference
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.use_custom_providers = use_custom_providers

        # Initialize components
        self.paper_retriever = PaperRetriever()
        self.arxiv_provider = ArxivPaperQA2Provider()
        self.pdf_parser = pdf_parser

        # Setup cache directory - use a unique subdirectory to avoid conflicts
        self.cache_dir = (
            cache_dir or Path(tempfile.gettempdir()) / "paperqa2_cache" / "academic_research"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Use provided settings or build new ones
        if settings:
            self.settings = settings
        else:
            # Configure settings
            self.settings = self._build_settings(
                llm_model=llm_model,
                embedding_model=embedding_model,
                chunk_size=chunk_size,
                evidence_k=evidence_k
            )

        # Setup metadata client
        if use_custom_providers:
            # Only use our ArXiv provider, no fallback to defaults
            # This prevents PaperQA2 from trying to fetch metadata for local files
            self.metadata_client = DocMetadataClient(
                clients=[[self.arxiv_provider]]  # Only our provider, no defaults
            )
        else:
            self.metadata_client = DocMetadataClient()
            
        # IMPORTANT: Set environment to disable unwanted metadata providers
        # This prevents them from being called even if PaperQA2 tries to use them
        import os
        if "SEMANTIC_SCHOLAR_API_KEY" not in os.environ:
            os.environ["SEMANTIC_SCHOLAR_API_KEY"] = "disabled"
        if "CROSSREF_MAILTO" not in os.environ:
            os.environ["CROSSREF_MAILTO"] = "disabled@example.com"
        if "CROSSREF_API_KEY" not in os.environ:
            os.environ["CROSSREF_API_KEY"] = "disabled"

        logger.info(
            f"Initialized PaperQA2Manager with model={llm_model}, "
            f"embedding={embedding_model}"
        )

    async def ask_about_papers(
        self,
        question: str,
        papers: Union[List[Paper], List[str]],
        use_agent: bool = True
    ) -> Answer:
        """
        Ask a question about specific papers.

        Args:
            question: Question to answer
            papers: List of Paper objects or paper IDs
            use_agent: Whether to use agent for multi-step reasoning

        Returns:
            PaperQA2 Answer object with response and sources
        """
        # Create Docs collection
        docs = Docs()

        # Add papers to collection
        await self._add_papers_to_docs(docs, papers)

        # Answer question
        if use_agent:
            # Import and create custom tools
            from .custom_tools import create_custom_tools
            custom_tools = create_custom_tools(self.settings, docs)
            
            # Use agent for complex multi-step reasoning
            answer = await agent_query(
                query=question,
                docs=docs,
                settings=self.settings,
                tools=custom_tools  # Use our custom tools
            )
        else:
            # Direct query for simple questions
            answer = await docs.aquery(question)

        return answer

    async def ask_about_topic(
        self,
        question: str,
        search_query: Optional[str] = None,
        sources: List[str] = ["arxiv"],
        max_papers: int = 10,
        use_agent: bool = True
    ) -> Answer:
        """
        Search for papers and answer a question about them.

        Args:
            question: Question to answer
            search_query: Query for finding papers (uses question if None)
            sources: Paper sources to search
            max_papers: Maximum papers to retrieve
            use_agent: Whether to use agent

        Returns:
            Answer with response and sources
        """
        # Search for relevant papers
        search_q = search_query or question

        logger.info(
            f"Searching for papers about '{search_q}' to answer: {question}"
        )

        papers = await self.paper_retriever.search(
            query=search_q,
            sources=sources,
            max_results=max_papers
        )

        if not papers:
            logger.warning("No papers found for query")
            return Answer(
                question=question,
                answer="No relevant papers found for your query.",
                sources=[]
            )

        logger.info(f"Found {len(papers)} papers, building Q&A context")

        # Answer question about found papers
        return await self.ask_about_papers(
            question=question,
            papers=papers,
            use_agent=use_agent
        )

    async def analyze_paper_trends(
        self,
        topic: str,
        time_period: Optional[str] = None,
        max_papers: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze trends in papers about a topic.

        Args:
            topic: Topic to analyze
            time_period: Time period (e.g., "2023-2024")
            max_papers: Maximum papers to analyze

        Returns:
            Analysis results including trends and key findings
        """
        # Build search parameters
        kwargs = {}
        if time_period:
            # Parse time period
            parts = time_period.split('-')
            if len(parts) == 2:
                kwargs['date_from'] = f"{parts[0]}-01-01"
                kwargs['date_to'] = f"{parts[1]}-12-31"

        # Search for papers
        papers = await self.paper_retriever.search(
            query=topic,
            max_results=max_papers,
            **kwargs
        )

        if not papers:
            return {
                "topic": topic,
                "papers_found": 0,
                "trends": [],
                "key_findings": []
            }

        # Ask about trends
        trend_question = (
            f"What are the main research trends and key findings "
            f"in these papers about {topic}? "
            "Identify common themes, methodologies, and breakthroughs."
        )

        answer = await self.ask_about_papers(
            question=trend_question,
            papers=papers,
            use_agent=True
        )

        return {
            "topic": topic,
            "papers_found": len(papers),
            "papers_analyzed": [p.title for p in papers[:5]],  # Top 5
            "analysis": answer.answer,
            "sources": answer.sources
        }

    async def find_contradictions(
        self,
        topic: str,
        papers: Optional[List[Paper]] = None,
        max_papers: int = 15
    ) -> Dict[str, Any]:
        """
        Find contradictions or disagreements in papers.

        Args:
            topic: Topic to analyze
            papers: Specific papers to analyze (searches if None)
            max_papers: Maximum papers if searching

        Returns:
            Analysis of contradictions and disagreements
        """
        # Get papers if not provided
        if papers is None:
            papers = await self.paper_retriever.search(
                query=topic,
                max_results=max_papers
            )

        if len(papers) < 2:
            return {
                "topic": topic,
                "papers_analyzed": len(papers),
                "contradictions": [],
                "message": "Need at least 2 papers to find contradictions"
            }

        # Ask about contradictions
        contradiction_question = (
            "What are the main contradictions, disagreements, or "
            "conflicting findings between these papers? "
            "Identify specific claims that differ and explain the nature "
            "of the disagreements."
        )

        answer = await self.ask_about_papers(
            question=contradiction_question,
            papers=papers,
            use_agent=True
        )

        return {
            "topic": topic,
            "papers_analyzed": len(papers),
            "analysis": answer.answer,
            "sources": answer.sources
        }

    async def search_with_agent_refinement(
        self,
        initial_query: str,
        sources: List[str] = ["arxiv"],
        max_iterations: int = 3,
        max_papers: int = 20
    ) -> Tuple[List[Paper], Answer]:
        """
        Use PaperQA2 agent to iteratively refine search and ranking.

        The agent will:
        1. Parse the natural language query
        2. Search for initial papers
        3. Analyze results and refine query
        4. Re-search with better parameters
        5. Rank and select diverse, relevant papers

        Args:
            initial_query: Natural language research query
            sources: Paper sources to search
            max_iterations: Maximum refinement iterations
            max_papers: Maximum papers to return

        Returns:
            Tuple of (papers, answer) where answer contains agent's reasoning
        """
        # Let the agent handle the entire search workflow
        search_instruction = (
            f"Find the most relevant and diverse papers about: {initial_query}\n\n"
            f"Instructions:\n"
            f"1. Search for papers using appropriate keywords\n"
            f"2. Analyze the initial results to identify key themes\n"
            f"3. Refine the search query if needed to find more relevant papers\n"
            f"4. Select up to {max_papers} papers that:\n"
            f"   - Are highly relevant to the query\n"
            f"   - Represent diverse perspectives or approaches\n"
            f"   - Include both foundational and recent work\n"
            f"5. Explain your search strategy and paper selection\n\n"
            f"Use up to {max_iterations} search iterations if needed."
        )

        # Create docs
        docs = Docs()
        
        # Pre-populate docs with initial search results
        # This avoids the agent trying to search local files
        # Simple search using paper retriever
        initial_papers = await self.paper_retriever.search(
            query=initial_query,
            sources=sources,
            max_results=max_papers * 2  # Get more for selection
        )
        
        # Add initial papers to docs
        if initial_papers:
            await self._add_papers_to_docs(docs, initial_papers[:10])
            
        # Now let agent refine and analyze
        refinement_instruction = (
            f"Analyze the papers already loaded about: {initial_query}\n\n"
            f"Instructions:\n"
            f"1. Review the current papers to identify gaps or missing perspectives\n"
            f"2. If needed, search for additional papers to fill those gaps\n"
            f"3. Select the best {max_papers} papers that:\n"
            f"   - Are highly relevant to the query\n"
            f"   - Represent diverse perspectives\n"
            f"   - Include both foundational and recent work\n"
            f"4. Explain your selection criteria and reasoning"
        )

        # Import and create custom tools
        from .custom_tools import create_custom_tools
        
        # Create custom tools with our search implementation
        custom_tools = create_custom_tools(self.settings, docs)
        
        # Execute agent query with pre-populated docs and custom tools
        answer = await agent_query(
            query=refinement_instruction,
            docs=docs,
            settings=self.settings,
            tools=custom_tools  # Use our custom tools
        )

        # Extract papers that were added to docs
        papers = []
        for doc_key, doc_info in docs.docs.items():
            # Convert doc info back to Paper objects
            paper = self._doc_to_paper(doc_info)
            if paper:
                papers.append(paper)

        return papers, answer

    async def rank_papers_with_agent(
        self,
        papers: List[Paper],
        ranking_criteria: str = "relevance and diversity",
        max_papers: Optional[int] = None
    ) -> Tuple[List[Paper], str]:
        """
        Use PaperQA2 agent to rank and select papers.

        Args:
            papers: Papers to rank
            ranking_criteria: Criteria for ranking (e.g., "relevance", "diversity", "impact")
            max_papers: Maximum papers to return (None = all)

        Returns:
            Tuple of (ranked_papers, ranking_explanation)
        """
        # Create Docs with all papers
        docs = Docs()
        await self._add_papers_to_docs(docs, papers)

        # Ask agent to rank papers
        ranking_question = (
            f"Analyze these {len(papers)} papers and rank them by {ranking_criteria}.\n"
            f"Consider:\n"
            f"- Relevance to the research topic\n"
            f"- Quality and rigor of the research\n"
            f"- Diversity of perspectives\n"
            f"- Recency and impact\n\n"
        )

        if max_papers:
            ranking_question += f"Select the top {max_papers} papers and explain your ranking.\n"
        else:
            ranking_question += "Rank all papers and explain your reasoning.\n"

        # Import and create custom tools
        from .custom_tools import create_custom_tools
        custom_tools = create_custom_tools(self.settings, docs)
        
        answer = await agent_query(
            query=ranking_question,
            docs=docs,
            settings=self.settings,
            tools=custom_tools  # Use our custom tools
        )

        # Extract ranking from answer
        # For now, return original order with explanation
        # TODO: Parse agent's ranking from the answer
        ranked_papers = papers[:max_papers] if max_papers else papers

        return ranked_papers, answer.answer

    def _doc_to_paper(self, doc_info: Any) -> Optional[Paper]:
        """
        Convert PaperQA2 document info back to Paper object.

        Args:
            doc_info: Document information from PaperQA2

        Returns:
            Paper object if conversion successful, None otherwise
        """
        try:
            # Extract metadata from doc_info
            # This is a simplified version - enhance based on actual doc structure
            return Paper(
                paper_id=doc_info.docname,
                title=doc_info.docname,
                authors=[],  # TODO: Extract from metadata
                abstract="",  # TODO: Extract if available
                source=PaperSource.ARXIV,
                published_date=None,
                url="",
                pdf_url=getattr(doc_info, 'file_location', None),
                html_url=None,
                doi=None,
                venue=None,
                volume=None,
                issue=None,
                pages=None,
                citations_count=0,
                keywords=[],
                categories=[],
                extra={},
                updated_date=None
            )
        except Exception as e:
            logger.error(f"Failed to convert doc to paper: {e}")
            return None

    async def _add_papers_to_docs(
        self,
        docs: Docs,
        papers: Union[List[Paper], List[str]]
    ) -> None:
        """
        Add papers to PaperQA2 Docs collection.

        Args:
            docs: PaperQA2 Docs instance
            papers: List of Paper objects or paper IDs
        """
        # Handle paper IDs
        if papers and isinstance(papers[0], str):
            # Assume ArXiv IDs for now
            paper_objects = []
            for paper_id in papers:
                paper = await self.paper_retriever.get_paper(
                    paper_id,
                    PaperSource.ARXIV
                )
                if paper:
                    paper_objects.append(paper)
            papers = paper_objects

        # Add each paper
        for paper in papers:
            try:
                await self._add_single_paper(docs, paper)
            except Exception as e:
                logger.error(f"Failed to add paper {paper.title}: {e}")

    async def _add_single_paper(self, docs: Docs, paper: Paper) -> None:
        """
        Add a single paper to Docs collection.

        Args:
            docs: PaperQA2 Docs instance
            paper: Paper to add
        """
        # Try to find PDF URL
        pdf_url = paper.pdf_url
        html_url = paper.html_url or paper.url

        # Prefer PDF but fall back to HTML
        url_to_add = pdf_url or html_url

        if not url_to_add:
            logger.warning(f"No URL found for paper: {paper.title}")
            return

        # Check if already in cache
        cached_path = self.cache_dir / f"{paper.paper_id}.pdf"

        if cached_path.exists():
            # Add from cache
            kwargs = {}
            if self.pdf_parser:
                kwargs['parse_pdf'] = self.pdf_parser

            await docs.aadd(
                cached_path,
                docname=paper.title,
                settings=self.settings,
                disable_doc_details_retrieval=True,  # Don't fetch metadata
                **kwargs
            )
            logger.info(f"Added paper from cache: {paper.title}")
        else:
            # Add from URL
            try:
                # Download if PDF
                if pdf_url:
                    await self._download_pdf(pdf_url, cached_path)
                    kwargs = {}
                    if self.pdf_parser:
                        kwargs['parse_pdf'] = self.pdf_parser

                    await docs.aadd(
                        cached_path,
                        docname=paper.title,
                        settings=self.settings,
                        disable_doc_details_retrieval=True,  # Don't fetch metadata
                        **kwargs
                    )
                else:
                    # Add URL directly (for HTML)
                    await docs.aadd_url(
                        url_to_add,
                        docname=paper.title,
                        settings=self.settings
                    )

                logger.info(f"Added paper: {paper.title}")

            except Exception as e:
                logger.error(f"Failed to add paper from URL: {e}")

    async def _download_pdf(self, url: str, path: Path) -> None:
        """
        Download PDF to local path.

        Args:
            url: PDF URL
            path: Local path to save
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                # Save to file
                with open(path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

    def _build_settings(
        self,
        llm_model: str,
        embedding_model: str,
        chunk_size: int,
        evidence_k: int
    ) -> Settings:
        """
        Build PaperQA2 settings.

        Args:
            llm_model: LLM model name
            embedding_model: Embedding model name
            chunk_size: Chunk size for parsing
            evidence_k: Number of evidence pieces

        Returns:
            Configured Settings object
        """
        # Create settings with all parameters at once
        settings = Settings(
            llm=llm_model,
            summary_llm=llm_model,  # Also set summary_llm to our model
            embedding=embedding_model,
            index_directory=str(self.cache_dir / "index"),
            answer=AnswerSettings(
                evidence_k=evidence_k,
                answer_max_sources=5,
                answer_length="detailed",
                evidence_summary_length="detailed",
            ),
            parsing=ParsingSettings(
                chunk_size=chunk_size,
                overlap=200
            ),
            # Configure agent to not use directory indexing
            agent=AgentSettings(
                agent_llm=llm_model,
                search_count=3,
                agent_type="ToolSelector",
                tool_names=["paper_search", "gather_evidence", 
                           "gen_answer", "reset", "complete"],
                # Disable directory indexing behaviors
                rebuild_index=False,  # Don't rebuild index
                should_pre_search=False  # Don't pre-search directory
            )
        )

        return settings

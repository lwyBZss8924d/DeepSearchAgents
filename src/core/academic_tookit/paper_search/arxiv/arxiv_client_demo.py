# Currently a demo design version, various client methods need to be optimized
# & changed to Pydantic models & optimized code structure & code naming
"""
Need to optimize the code structure & code naming:

- [To be optimized] **search_papers**: Searches arXiv papers filtered by the Software Engineering category (`cs.SE`).
  - Parameters: `query`, `max_results`, `start_date`, `end_date`, `sort_by_relevance`, `category`
  - Returns: Dictionary with the query used and the results.

- [To be optimized] **search_by_author**: Searches for papers by author, with optional category and date filters.
  - Parameters: `author_name`, `max_results`, `category`, `start_date`, `end_date`
  - Returns: List of found papers.

- [To be optimized] **get_paper_details**: Gets detailed information about a paper by its arXiv ID.
  - Parameters: `arxiv_id`
  - Returns: Title, authors, abstract, dates, categories, DOI, etc.

- [To be optimized] **get_arxiv_categories**: Returns the list of arXiv categories and their descriptions.
  - Parameters: None
  - Returns: Dictionary of categories and usage notes.

- [To be optimized] **analyze_paper_trends**: Analyzes trends in a collection of papers (authors, keywords, timeline, categories).
  - Parameters: `papers`, `analysis_type`
  - Returns: Statistics and analysis according to the requested type.

- [TODO] get paper url: prioritize /html url,  then /pdf url
    - **download paper pdf file save to temp path using for paper_reader (paper reader using HTML url first, then pdf url priority, later upload pdf file to paper_reader)**:
      - Parameters: `pdf_url`, `save_path`, `filename`
      - Returns: Path and status of the download.

- [TODO only need json]**export_search_results**: Exports search results to various formats (`bibtex`, `csv`, `json`, `markdown`).
  - Parameters: `results`, `format`, `filename`, `save_path`
  - Returns: Path to the exported file and a preview of the content.

- [TODO] (To be extracted as a shared utility for paper_search all paper search sources) **paper ranking pipeline**
  [Needs to be refactored to use the jina.ai `'https://api.jina.ai/v1/rerank'` reRanking `jina-reranker-m0` model
  @.cursor/rules/jina-ai-api-rules.mdc (Multilingual multimodal reranker model
  for ranking visual documents) to reorder retrieval results and query requests.]
  - **find_related_papers**: Finds related papers based on the title of a reference paper, using keyword similarity.
    - Parameters: `paper_title`, `max_results`, `similarity_threshold`, `category`
    - Returns: List of similar papers.
    * https://jina.ai/news/submodular-optimization-for-text-selection-passage-reranking-context-engineering/
    * https://jina.ai/news/jina-reranker-m0-multilingual-multimodal-document-reranker/
    * https://github.com/jina-ai/submodular-optimization

"""

# import  src/core/academic_tookit/paper_search/arxiv/arxiv_sdk/__init__.py
import arxiv
import re
import json
import os
import requests
import pandas as pd
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any
from sklearn.feature_extraction.text import TfidfVectorizer


def search_papers(
    query: str,
    max_results: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    sort_by_relevance: bool = True,
    category: str = "cs.SE",
) -> dict:
    """
    Search for papers on arXiv.
    It can parse natural language queries, extracting keywords and years for filtering.

    :param query: The base search query. Can be natural language.
    :param max_results: The maximum number of results to return.
    :param start_date: The start date for the search period (YYYY-MM-DD or YYYY). Overrides years in query.
    :param end_date: The end date for the search period (YYYY-MM-DD or YYYY). Overrides years in query.
    :param sort_by_relevance: If True, sorts by relevance. If False, sorts by submission date.
    :param category: The arXiv category to search in (e.g., 'cs.AI', 'cs.CL', 'cs.SE').
    """
    STOP_WORDS = {
        "a", "an", "and", "the", "of", "in", "for", "to", "with", "on", "is", "are", "was", "were", "it",
    }

    # Extract years from query to use as date filters if not provided explicitly
    years_in_query = re.findall(r'\b(20\d{2})\b', query)
    query_text = re.sub(r'\b(20\d{2})\b', "", query).strip()

    # Use provided dates or fall back to dates from query
    effective_start_date = start_date
    if not effective_start_date and years_in_query:
        effective_start_date = min(years_in_query)

    effective_end_date = end_date
    if not effective_end_date and years_in_query:
        effective_end_date = max(years_in_query)

    # Process keywords from the query text
    keywords = [
        word
        for word in query_text.split()
        if word.lower() not in STOP_WORDS and len(word) > 2
    ]

    if keywords:
        # Build a structured query from keywords, joining with OR for broader results
        keyword_query = " OR ".join([f'(ti:"{kw}" OR abs:"{kw}")' for kw in keywords])
        query_parts = [f"({keyword_query})"]
    else:
        # Fallback to using the original query text if no keywords are left
        query_parts = [f'(ti:"{query_text}" OR abs:"{query_text}")']

    if category:
        query_parts.append(f"cat:{category}")

    # Add date range to the query
    if effective_start_date or effective_end_date:
        start = "19910814"
        if effective_start_date:
            try:
                dt = datetime.strptime(effective_start_date, "%Y-%m-%d")
            except ValueError:
                dt = datetime.strptime(effective_start_date, "%Y")
            start = dt.strftime("%Y%m%d")

        end = datetime.now().strftime("%Y%m%d")
        if effective_end_date:
            try:
                dt = datetime.strptime(effective_end_date, "%Y-%m-%d")
            except ValueError:
                dt = datetime.strptime(effective_end_date, "%Y")
                dt = dt.replace(month=12, day=31)
            end = dt.strftime("%Y%m%d")

        query_parts.append(f"submittedDate:[{start} TO {end}]")

    final_query = " AND ".join(query_parts)
    print(f"[arxiv-search] Query sent: {final_query}")

    sort_criterion = (
        arxiv.SortCriterion.Relevance
        if sort_by_relevance
        else arxiv.SortCriterion.SubmittedDate
    )

    search = arxiv.Search(
        query=final_query,
        max_results=max_results,
        sort_by=sort_criterion,
        sort_order=arxiv.SortOrder.Descending,
    )
    results = []
    for r in search.results():
        results.append(
            {
                "title": r.title,
                "authors": [a.name for a in r.authors],
                "summary": r.summary,
                "pdf_url": r.pdf_url,
                "published_date": r.published.strftime("%Y-%m-%d"),
            }
        )
    return {"query_used": final_query, "results": results}


def get_paper_details(arxiv_id: str) -> dict:
    """
    Get detailed information about a specific paper by ArXiv ID.

    :param arxiv_id: The ArXiv ID (e.g., '2301.12345')
    """
    try:
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(search.results())

        return {
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "summary": paper.summary,
            "pdf_url": paper.pdf_url,
            "published_date": paper.published.strftime("%Y-%m-%d"),
            "updated_date": paper.updated.strftime("%Y-%m-%d"),
            "categories": paper.categories,
            "primary_category": paper.primary_category,
            "arxiv_id": paper.entry_id.split("/")[-1],
            "doi": paper.doi,
            "journal_ref": paper.journal_ref,
            "comment": paper.comment,
        }
    except Exception as e:
        return {"error": f"Failed to fetch paper details: {str(e)}"}


def search_by_author(
    author_name: str,
    max_results: int = 20,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Search papers by a specific author.

    :param author_name: Name of the author to search for
    :param max_results: Maximum number of results
    :param category: Optional category filter (e.g., 'cs.SE', 'cs.AI')
    :param start_date: Optional start date filter (YYYY-MM-DD or YYYY)
    :param end_date: Optional end date filter (YYYY-MM-DD or YYYY)
    """
    query_parts = [f'au:"{author_name}"']

    if category:
        query_parts.append(f"cat:{category}")

    # Add date range if specified
    if start_date or end_date:
        start = "19910814"
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                dt = datetime.strptime(start_date, "%Y")
            start = dt.strftime("%Y%m%d")

        end = datetime.now().strftime("%Y%m%d")
        if end_date:
            try:
                dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                dt = datetime.strptime(end_date, "%Y")
                dt = dt.replace(month=12, day=31)
            end = dt.strftime("%Y%m%d")

        query_parts.append(f"submittedDate:[{start} TO {end}]")

    final_query = " AND ".join(query_parts)
    print(f"[arxiv-search] Author query: {final_query}")

    search = arxiv.Search(
        query=final_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = []
    for r in search.results():
        results.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "summary": r.summary,
            "pdf_url": r.pdf_url,
            "published_date": r.published.strftime("%Y-%m-%d"),
            "arxiv_id": r.entry_id.split("/")[-1],
            "categories": r.categories,
        })

    return {
        "author": author_name,
        "query_used": final_query,
        "total_results": len(results),
        "results": results
    }


def analyze_paper_trends(
    papers: List[Dict[str, Any]],
    analysis_type: str = "authors"
) -> dict:
    """
    Analyze trends in a collection of papers.

    :param papers: List of papers from search_papers results
    :param analysis_type: Type of analysis ('authors', 'keywords', 'timeline', 'categories')
    """
    if not papers or "results" not in papers:
        if isinstance(papers, list):
            results = papers
        else:
            return {"error": "Invalid papers format. Expected list or dict with 'results' key."}
    else:
        results = papers["results"]

    if not results:
        return {"error": "No papers to analyze"}

    analysis = {}

    if analysis_type == "authors":
        author_counts = Counter()
        for paper in results:
            for author in paper.get("authors", []):
                author_counts[author] += 1

        analysis = {
            "type": "authors",
            "total_unique_authors": len(author_counts),
            "most_prolific_authors": author_counts.most_common(10),
            "collaboration_stats": {
                "avg_authors_per_paper": sum(len(p.get("authors", [])) for p in results) / len(results),
                "single_author_papers": sum(1 for p in results if len(p.get("authors", [])) == 1),
                "multi_author_papers": sum(1 for p in results if len(p.get("authors", [])) > 1),
            }
        }

    elif analysis_type == "timeline":
        date_counts = Counter()
        for paper in results:
            date = paper.get("published_date", "")
            if date:
                year = date.split("-")[0]
                date_counts[year] += 1

        analysis = {
            "type": "timeline",
            "papers_by_year": dict(sorted(date_counts.items())),
            "most_active_year": date_counts.most_common(1)[0] if date_counts else None,
            "total_years_span": len(date_counts),
        }

    elif analysis_type == "categories":
        category_counts = Counter()
        for paper in results:
            categories = paper.get("categories", [])
            for cat in categories:
                category_counts[cat] += 1

        analysis = {
            "type": "categories",
            "total_categories": len(category_counts),
            "most_common_categories": category_counts.most_common(10),
            "category_distribution": dict(category_counts),
        }

    elif analysis_type == "keywords":
        # Extract keywords from titles and abstracts
        text_content = []
        for paper in results:
            title = paper.get("title", "")
            summary = paper.get("summary", "")
            text_content.append(f"{title} {summary}")

        if text_content:
            try:
                # Use TF-IDF to find important terms
                vectorizer = TfidfVectorizer(
                    max_features=50,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=2
                )
                tfidf_matrix = vectorizer.fit_transform(text_content)
                feature_names = vectorizer.get_feature_names_out()
                scores = tfidf_matrix.sum(axis=0).A1

                keyword_scores = list(zip(feature_names, scores))
                keyword_scores.sort(key=lambda x: x[1], reverse=True)

                analysis = {
                    "type": "keywords",
                    "top_keywords": keyword_scores[:20],
                    "total_unique_terms": len(feature_names),
                }
            except Exception as e:
                analysis = {
                    "type": "keywords",
                    "error": f"Could not perform keyword analysis: {str(e)}",
                    "fallback_word_count": Counter()
                }

    analysis["total_papers_analyzed"] = len(results)
    return analysis


def find_related_papers(
    paper_title: str,
    max_results: int = 10,
    similarity_threshold: float = 0.7,
    category: str | None = None,
) -> dict:
    """
    Find papers related to a given paper title using keyword similarity.

    :param paper_title: Title of the reference paper
    :param max_results: Maximum number of related papers to return
    :param similarity_threshold: Minimum similarity score (0.0 to 1.0)
    :param category: Optional category filter
    """
    try:
        # Extract keywords from the title
        stop_words = {
            "a", "an", "and", "the", "of", "in", "for", "to", "with", "on", "is", "are", "was", "were", "it"
        }

        keywords = [
            word.lower()
            for word in re.findall(r'\b\w+\b', paper_title)
            if word.lower() not in stop_words and len(word) > 2
        ]

        if not keywords:
            return {"error": "No meaningful keywords found in title"}

        # Create search query from keywords
        keyword_query = " OR ".join([f'(ti:"{kw}" OR abs:"{kw}")' for kw in keywords])
        query_parts = [f"({keyword_query})"]

        if category:
            query_parts.append(f"cat:{category}")

        final_query = " AND ".join(query_parts)

        # Search for related papers
        search = arxiv.Search(
            query=final_query,
            max_results=max_results * 2,  # Get more results to filter by similarity
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )

        results = []

        for r in search.results():
            # Calculate simple similarity based on keyword overlap
            paper_text = f"{r.title} {r.summary}".lower()

            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in paper_text)
            similarity = matches / len(keywords) if keywords else 0

            if similarity >= similarity_threshold:
                results.append({
                    "title": r.title,
                    "authors": [a.name for a in r.authors],
                    "summary": r.summary[:500] + "..." if len(r.summary) > 500 else r.summary,
                    "pdf_url": r.pdf_url,
                    "published_date": r.published.strftime("%Y-%m-%d"),
                    "similarity_score": round(similarity, 3),
                    "arxiv_id": r.entry_id.split("/")[-1],
                })

        # Sort by similarity score and limit results
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:max_results]

        return {
            "reference_title": paper_title,
            "keywords_used": keywords,
            "similarity_threshold": similarity_threshold,
            "total_related_found": len(results),
            "related_papers": results
        }

    except Exception as e:
        return {"error": f"Failed to find related papers: {str(e)}"}


def download_paper_pdf(
    pdf_url: str,
    save_path: str | None = None,
    filename: str | None = None
) -> dict:
    """
    Download a paper's PDF from ArXiv.

    :param pdf_url: The PDF URL from search results
    :param save_path: Directory to save the PDF (default: current directory)
    :param filename: Custom filename for the PDF (default: extracted from URL)
    """
    try:
        if save_path is None:
            save_path = os.getcwd()

        # Create directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)

        if filename is None:
            # Extract filename from URL
            arxiv_id = pdf_url.split("/")[-1].replace(".pdf", "")
            filename = f"{arxiv_id}.pdf"

        if not filename.endswith('.pdf'):
            filename += '.pdf'

        full_path = os.path.join(save_path, filename)

        # Download the PDF
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()

        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(full_path)

        return {
            "success": True,
            "pdf_url": pdf_url,
            "saved_path": full_path,
            "filename": filename,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to download PDF: {str(e)}",
            "pdf_url": pdf_url
        }


def export_search_results(
    results: Dict[str, Any],
    format: str = "bibtex",
    filename: str | None = None,
    save_path: str | None = None
) -> dict:
    """
    Export search results to various formats.

    :param results: Results from search_papers or other search functions
    :param format: Export format ('bibtex', 'csv', 'json', 'markdown')
    :param filename: Output filename (without extension)
    :param save_path: Directory to save the file (default: current directory)
    """
    try:
        if save_path is None:
            save_path = os.getcwd()

        os.makedirs(save_path, exist_ok=True)

        # Extract papers from results
        if isinstance(results, dict) and "results" in results:
            papers = results["results"]
        elif isinstance(results, list):
            papers = results
        else:
            return {"error": "Invalid results format. Expected a list of papers or a dict with a 'results' key."}

        if not papers:
            return {"error": "No papers to export."}

        # Generate default filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arxiv_search_{timestamp}"

        full_path = os.path.join(save_path, f"{filename}.{format}")

        if format == "bibtex":
            bibtex_entries = []
            query_info = results.get('query_used', 'N/A')
            export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            header = f"""% Query: {query_info}
% Exported: {export_time}
"""
            bibtex_entries.append(header)

            bibtex_keys = set()
            for i, paper in enumerate(papers):
                authors = paper.get("authors", ["unknown"])
                year = paper.get("published_date", "unknown").split("-")[0]

                first_author_lastname = "unknown"
                if authors and isinstance(authors, list) and authors[0] != "unknown":
                    name_parts = authors[0].split(" ")
                    if name_parts:
                        first_author_lastname = name_parts[-1]

                first_author_lastname = re.sub(r'[^a-zA-Z0-9]', '', first_author_lastname).lower()

                key = f"{first_author_lastname}{year}"

                # Handle duplicates
                original_key = key
                suffix = 1
                while key in bibtex_keys:
                    key = f"{original_key}_{suffix}"
                    suffix += 1
                bibtex_keys.add(key)

                title = paper.get("title", "No Title Provided")
                author_str = " and ".join(paper.get("authors", []))
                pdf_url = paper.get("pdf_url", "")

                arxiv_id_match = re.search(r'/pdf/([^v]+)', pdf_url) if pdf_url else None
                if arxiv_id_match:
                    arxiv_id = arxiv_id_match.group(1)
                    journal = f"arXiv preprint arXiv:{arxiv_id}"
                else:
                    journal = f"arXiv preprint arXiv:{key}"

                entry = f"""@article{{{key},
    title = {{{title}}},
    author = {{{author_str}}},
    year = {{{year}}},
    journal = {{{journal}}},
    url = {{{pdf_url}}}
}}"""
                bibtex_entries.append(entry)

            content = "\n\n".join(bibtex_entries)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        elif format == "csv":
            df = pd.DataFrame(papers)
            df.to_csv(full_path, index=False, encoding='utf-8-sig')
            content = df.to_string()

        elif format == "json":
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(papers, f, indent=4)
            content = json.dumps(papers, indent=4)

        elif format == "markdown":
            md_entries = []
            for paper in papers:
                title = paper.get("title", "N/A")
                authors = ", ".join(paper.get("authors", ["N/A"]))
                date = paper.get("published_date", "N/A")
                url = paper.get("pdf_url", "#")
                summary = paper.get("summary", "N/A").replace("\n", " ")

                md_entries.append(f"""### {title}\n**Authors:** {authors}\n**Published:** {date}\n**[PDF Link]({url})**\n> {summary}\n""")

            content = "\n---\n".join(md_entries)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        else:
            return {"error": f"Unsupported format: {format}"}

        return {
            "success": True,
            "format": format,
            "saved_path": full_path,
            "papers_exported": len(papers),
            "content_preview": content[:500] + ("..." if len(content) > 500 else "")
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to export results: {str(e)}"
        }


def get_arxiv_categories() -> dict:
    """
    Get a list of available ArXiv categories and their descriptions.
    """
    categories = {
        "Computer Science": {
            "cs.AI": "Artificial Intelligence",
            "cs.AR": "Hardware Architecture",
            "cs.CC": "Computational Complexity",
            "cs.CE": "Computational Engineering, Finance, and Science",
            "cs.CG": "Computational Geometry",
            "cs.CL": "Computation and Language",
            "cs.CR": "Cryptography and Security",
            "cs.CV": "Computer Vision and Pattern Recognition",
            "cs.CY": "Computers and Society",
            "cs.DB": "Databases",
            "cs.DC": "Distributed, Parallel, and Cluster Computing",
            "cs.DL": "Digital Libraries",
            "cs.DM": "Discrete Mathematics",
            "cs.DS": "Data Structures and Algorithms",
            "cs.ET": "Emerging Technologies",
            "cs.FL": "Formal Languages and Automata Theory",
            "cs.GL": "General Literature",
            "cs.GR": "Graphics",
            "cs.GT": "Computer Science and Game Theory",
            "cs.HC": "Human-Computer Interaction",
            "cs.IR": "Information Retrieval",
            "cs.IT": "Information Theory",
            "cs.LG": "Machine Learning",
            "cs.LO": "Logic in Computer Science",
            "cs.MA": "Multiagent Systems",
            "cs.MM": "Multimedia",
            "cs.MS": "Mathematical Software",
            "cs.NA": "Numerical Analysis",
            "cs.NE": "Neural and Evolutionary Computing",
            "cs.NI": "Networking and Internet Architecture",
            "cs.OH": "Other Computer Science",
            "cs.OS": "Operating Systems",
            "cs.PF": "Performance",
            "cs.PL": "Programming Languages",
            "cs.RO": "Robotics",
            "cs.SC": "Symbolic Computation",
            "cs.SD": "Sound",
            "cs.SE": "Software Engineering",
            "cs.SI": "Social and Information Networks",
            "cs.SY": "Systems and Control"
        },
        "Mathematics": {
            "math.AG": "Algebraic Geometry",
            "math.AT": "Algebraic Topology",
            "math.AP": "Analysis of PDEs",
            "math.CT": "Category Theory",
            "math.CA": "Classical Analysis and ODEs",
            "math.CO": "Combinatorics",
            "math.AC": "Commutative Algebra",
            "math.CV": "Complex Variables",
            "math.DG": "Differential Geometry",
            "math.DS": "Dynamical Systems",
            "math.FA": "Functional Analysis",
            "math.GM": "General Mathematics",
            "math.GN": "General Topology",
            "math.GT": "Geometric Topology",
            "math.GR": "Group Theory",
            "math.HO": "History and Overview",
            "math.IT": "Information Theory",
            "math.KT": "K-Theory and Homology",
            "math.LO": "Logic",
            "math.MP": "Mathematical Physics",
            "math.MG": "Metric Geometry",
            "math.NT": "Number Theory",
            "math.NA": "Numerical Analysis",
            "math.OA": "Operator Algebras",
            "math.OC": "Optimization and Control",
            "math.PR": "Probability",
            "math.QA": "Quantum Algebra",
            "math.RT": "Representation Theory",
            "math.RA": "Rings and Algebras",
            "math.SP": "Spectral Theory",
            "math.ST": "Statistics Theory",
            "math.SG": "Symplectic Geometry"
        }
    }

    return {
        "categories": categories,
        "total_categories": sum(len(cats) for cats in categories.values()),
        "popular_cs_categories": ["cs.LG", "cs.AI", "cs.CV", "cs.CL", "cs.SE", "cs.RO"],
        "usage_note": "Use category codes (e.g., 'cs.AI') in search functions"
    }

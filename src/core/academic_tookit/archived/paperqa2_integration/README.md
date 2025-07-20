# PaperQA2 Integration for Academic Toolkit

This module integrates [PaperQA2](https://github.com/whitead/paper-qa) with our academic toolkit to provide advanced question-answering capabilities on scientific papers.

## Current Status

✅ **Working Components:**
- `ArxivPaperQA2Provider` - Successfully searches and retrieves papers from ArXiv
- `PaperQA2Manager` - Orchestrates paper collection and Q&A workflows
- `PaperQA2Config` - Configuration management with environment variable support
- `AcademicQASystem` - High-level API for research workflows

⚠️ **Known Issues:**
- **DOI Search** - ArXiv DOI search may not work for all DOI formats
- **API Compatibility** - Code updated for recent PaperQA2 API changes (v5.x)

✅ **Fixed Issues:**
- **Mistral OCR Integration** - Now working with PaperQA2's PDF parser interface
- **Mistral API** - Updated to use stable `client.ocr.process` API

## Features

- **Unified Search & QA**: Search papers using our toolkit, analyze them with PaperQA2
- **Custom ArXiv Provider**: Native integration with our ArXiv search client
- **Mistral OCR Support**: Enhanced PDF processing with figure/table extraction
- **High-Level API**: Simple interface for complex research tasks
- **Multi-Source Support**: Extensible to other paper sources beyond ArXiv

## Installation

```bash
# Install PaperQA2 and dependencies
pip install paper-qa>=5.24.0,<5.25.0
pip install mistralai  # For OCR support (optional)
```

## Quick Start

### Basic Usage

```python
import asyncio
from src.core.academic_tookit.paperqa2_integration import AcademicQASystem

async def main():
    # Initialize the system
    qa_system = AcademicQASystem()
    
    # Ask a research question
    result = await qa_system.ask(
        question="What are the key innovations in transformer architectures?",
        max_papers=10
    )
    
    print(f"Answer: {result.answer}")
    print(f"Papers analyzed: {result.papers_analyzed}")

# Run
asyncio.run(main())
```

### Working Example - ArXiv Provider

```python
import asyncio
import aiohttp
from paperqa.clients.client_models import TitleAuthorQuery
from src.core.academic_tookit.paperqa2_integration import ArxivPaperQA2Provider

async def search_paper():
    provider = ArxivPaperQA2Provider()
    
    async with aiohttp.ClientSession() as session:
        query = TitleAuthorQuery(
            title="Attention is All You Need",
            authors=["Vaswani"],
            session=session
        )
        
        result = await provider._query(query)
        if result:
            print(f"Found: {result.title}")
            print(f"Year: {result.year}")
            print(f"PDF: {result.pdf_url}")

asyncio.run(search_paper())
```

### Using Mistral OCR

```python
import asyncio
from paperqa import Docs
from src.core.academic_tookit.paperqa2_integration import create_mistral_ocr_parser

async def use_mistral_ocr():
    # Create Mistral OCR parser
    mistral_parser = create_mistral_ocr_parser(
        extract_references=True,
        extract_figures=True
    )
    
    # Use with PaperQA2
    docs = Docs()
    await docs.aadd(
        "paper.pdf",
        parse_pdf=mistral_parser  # Use Mistral OCR instead of default
    )
    
    # The parser extracts additional metadata
    # Check docs.docs[0].metadata for references, figures, tables

asyncio.run(use_mistral_ocr())
```

### Configuration

```python
from src.core.academic_tookit.paperqa2_integration import PaperQA2Config

# Custom configuration
config = PaperQA2Config(
    llm_model="openai/gemini-2.5-pro",  # Or other custom large context window ChatCompletion LLM
    embedding_model="gemini-embedding-001",
    chunk_size=5000,
    evidence_k=10,
    use_mistral_ocr=True,  # Enable advanced OCR
    cache_dir="./paperqa_cache"
)

qa_system = AcademicQASystem(config=config)
```

### Environment Variables

Set these environment variables for API access:

```bash
export OPENAI_API_KEY="your-key"      # Required for PaperQA2
export MISTRAL_API_KEY="your-key"     # Optional, for OCR
```

## Advanced Features

### 1. Trend Analysis

```python
trends = await qa_system.analyze_trends(
    topic="large language models",
    time_period="2023-2024",
    max_papers=20
)
```

### 2. Contradiction Detection

```python
contradictions = await qa_system.find_contradictions(
    topic="effectiveness of dropout regularization",
    max_papers=15
)
```

### 3. Claim Verification

```python
verification = await qa_system.verify_claim(
    claim="Attention mechanisms improve translation quality",
    context="neural machine translation",
    max_papers=10
)
print(f"Verdict: {verification['verdict']}")
```

### 4. Paper Summarization

```python
summary = await qa_system.summarize_paper(
    paper=paper_object,  # Or paper ID
    focus="methodology"  # Optional focus area
)
```

### 5. Paper Comparison

```python
comparison = await qa_system.compare_papers(
    papers=[paper1, paper2],
    aspects=["methodology", "results", "limitations"]
)
```

### 6. Export Results

```python
# Export to different formats
await qa_system.export_research(
    results=[result1, result2],
    format="markdown",  # or "json", "html"
    output_path="research_results.md"
)
```

## Architecture

### Components

1. **ArxivPaperQA2Provider**: Adapts our ArXiv client to PaperQA2's metadata system
2. **MistralOCRReader**: Custom PDF reader with advanced OCR capabilities
3. **PaperQA2Manager**: Orchestrates paper collection and Q&A workflows
4. **AcademicQASystem**: High-level API for research tasks

### Integration Flow

```
User Query → AcademicQASystem → PaperRetriever → ArXiv/Other Sources
                ↓
            PaperQA2Manager → Add Papers to Docs
                ↓
            Mistral OCR (if PDF) → Text Extraction
                ↓
            PaperQA2 Agent → Multi-step Reasoning
                ↓
            ResearchResult → User
```

## Extending the System

### Adding New Paper Sources

1. Create a provider implementing PaperQA2's interface:

```python
from paperqa.clients import DOIOrTitleBasedProvider

class MySourceProvider(DOIOrTitleBasedProvider):
    async def get_by_doi(self, doi_query):
        # Implementation
        pass
    
    async def get_by_title(self, title_query):
        # Implementation
        pass
```

2. Register with the manager:

```python
manager.metadata_client.clients.append([my_provider])
```

### Custom Processing

Override the Mistral OCR reader for custom PDF processing:

```python
class CustomReader(MistralOCRReader):
    async def parse(self, doc_path, doc):
        # Custom processing logic
        return super().parse(doc_path, doc)
```

## Performance Tips

1. **Caching**: Papers are cached locally to avoid re-downloading
2. **Batch Processing**: Process multiple questions on the same papers
3. **Model Selection**: Use `openai/gemini-2.5-pro` for faster/cheaper processing
4. **Chunk Size**: Adjust based on your needs (smaller = more precise, larger = more context)

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure environment variables are set
2. **Rate Limits**: The system respects ArXiv rate limits (3s delay)
3. **Memory Usage**: Large paper collections may use significant memory
4. **OCR Failures**: System falls back to standard PDF parsing if OCR fails

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Examples

See `example_usage.py` for comprehensive examples of all features.

## Future Enhancements

- [ ] Support for more paper sources (Semantic Scholar, PubMed)
- [ ] Advanced citation network analysis
- [ ] Batch processing optimizations
- [ ] GUI interface for research workflows
- [ ] Integration with reference managers

## License

This integration follows the licenses of both the academic toolkit and PaperQA2.

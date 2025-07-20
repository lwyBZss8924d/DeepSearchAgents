# Academic Toolkit

The Academic Toolkit provides capabilities for searching and retrieving academic papers from various sources. Currently focused on ArXiv integration with plans for expanded functionality.

## Architecture Overview

```
academic_tookit/
├── models/              # Data models (Paper, SearchParams)
├── paper_search/        # Paper search implementations
│   └── arxiv/          # ArXiv search client
├── paper_reader/        # Paper reading and parsing
│   └── mistral_ocr.py  # Advanced OCR for PDFs
├── ranking/            # Paper ranking and deduplication
├── paper_retrievaler.py # Unified paper retrieval interface
└── archived/           # Archived experimental features
    └── paperqa2_integration/ # PaperQA2 integration (for future development)
```

## Key Components

### 1. Paper Models (`models/`)
- **Paper**: Comprehensive paper metadata model
- **SearchParams**: Flexible search parameter specification
- **PaperSource**: Enum for different paper sources

### 2. Paper Search (`paper_search/`)
Currently implements ArXiv search with:
- Natural language query support
- Category and date filtering
- Author search
- Related paper discovery

### 3. Paper Reading (`paper_reader/`)
- **Mistral OCR**: Advanced PDF processing with figure/table extraction
- **Reference Extraction**: Parse citations and references
- **Structured Output**: Convert papers to LLM-friendly formats

### 4. Ranking & Deduplication (`ranking/`)
- **Multi-criteria ranking**: By relevance, diversity, impact
- **Deduplication**: Handle papers from multiple sources
- **Source prioritization**: Prefer authoritative sources

## Usage with DeepSearchAgents

The toolkit is exposed through the AcademicRetrieval tool:

```python
# Search for papers
papers = academic_retrieval(
    operation="search",
    query="transformer architectures",
    num_results=20
)

# Get specific paper
paper = academic_retrieval(
    operation="get_paper",
    query="2301.12345",
    source="arxiv"
)

# Find related papers
related = academic_retrieval(
    operation="related",
    query="2301.12345",
    source="arxiv",
    num_results=10
)
```

## Configuration

### Environment Variables
```bash
# Optional for advanced features
export MISTRAL_API_KEY="your-key"  # For OCR capabilities
```

## Extending the Toolkit

### Adding New Paper Sources
1. Create client in `paper_search/<source>/`
2. Implement `BasePaperSearchClient` interface
3. Add to `PaperRetriever` sources

### Custom PDF Parsers
The toolkit supports custom PDF parsing through the paper_reader module.

## Performance Considerations

1. **Caching**: Papers cached locally to avoid re-downloading
2. **Concurrent Search**: Multiple sources searched in parallel
3. **Batch Processing**: Process multiple queries efficiently
4. **Rate Limiting**: Respects source API limits

## Future Enhancements

- [ ] Additional sources (Semantic Scholar, PubMed, bioRxiv)
- [ ] Advanced Q&A capabilities (currently in archived/paperqa2_integration)
- [ ] Citation network visualization
- [ ] Export to reference managers

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **API Keys**: Set environment variables for optional features
3. **Rate Limits**: Reduce `num_results` or add delays
4. **Memory Usage**: Large paper sets may require more RAM

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This toolkit is part of DeepSearchAgents and follows the project's licensing terms.
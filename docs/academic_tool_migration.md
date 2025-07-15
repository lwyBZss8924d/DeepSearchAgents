# Academic Tool Migration Plan

## Overview
The AcademicRetrieval tool has been temporarily disabled due to severe rate limiting issues with the FutureHouse Platform API (429 errors). This document outlines the migration plan to direct paper database APIs.

## Changes Made

### 1. Tool Disabling (Minimal Impact)
- **Files Modified:**
  - `src/tools/__init__.py` - Added try-except for missing import
  - `src/tools/toolbox.py` - Added conditional registration
  - `src/core/academic_tookit/__init__.py` - Commented out FutureHouse imports
  - `pyproject.toml` - Downgraded smolagents to fix callback bug

- **Files Preserved:**
  - All UI constants (icons, colors)
  - All prompt templates
  - All agent callbacks
  - Tool name remains "academic_retrieval"

### 2. Code Preservation
- Renamed `src/tools/academic_retrieval.py` to `academic_retrieval.py.bk`
- Kept all FutureHouse client implementations in `src/core/academic_tookit/`

### 3. New Structure Created
```
src/core/academic_tookit/
├── __init__.py
├── paper_retrievaler.py          # New unified retrieval interface
├── paper_search/                 # Direct API implementations
│   ├── arxiv.py
│   ├── biorxiv.py
│   ├── google_scholar.py
│   ├── hub.py
│   ├── medrxiv.py
│   └── semantic.py
├── paper_reader/                 # Content extraction
│   └── scraper.py
├── academic_research_client.py   # Legacy FutureHouse FALCON
└── scholar_search_client.py      # Legacy FutureHouse CROW
```

## Migration Path

### Phase 1: Direct API Integration (Current)
1. Implement direct API clients for each paper source
2. Create unified search interface in `paper_retrievaler.py`
3. Handle rate limiting with exponential backoff
4. Add result caching layer

### Phase 2: Tool Recreation
1. Create new `src/tools/academic_retrieval.py` with same class name
2. Use `paper_retrievaler.py` as backend
3. Maintain same tool interface for agent compatibility
4. System automatically detects and uses new implementation

### Phase 3: Enhancement
1. Add more paper sources (PubMed, IEEE, ACM, etc.)
2. Implement intelligent source selection
3. Add PDF extraction capabilities
4. Enhance search relevance ranking

## Benefits of This Approach
1. **Zero disruption** - Agents continue working without the tool
2. **Clean migration** - Same tool name and interface
3. **Better reliability** - Direct APIs avoid single point of failure
4. **More sources** - Can add unlimited paper databases
5. **Cost effective** - Most academic APIs are free

## Rollback Instructions
If needed to re-enable FutureHouse API:
1. Rename `academic_retrieval.py.bk` back to `academic_retrieval.py`
2. Uncomment imports in `src/core/academic_tookit/__init__.py`
3. Set `FUTUREHOUSE_API_KEY` in environment

## Testing
Once new implementation is ready:
1. Unit tests with mocked API responses
2. Integration tests with real APIs (rate limit aware)
3. Agent compatibility tests
4. Performance benchmarks

## Related Commits
- `refactor(tools): temporarily disable AcademicRetrieval tool due to API limitations`
- `chore(tools): rename academic_retrieval.py to .bk pending redesign`
- `feat(academic): add new academic_tookit module structure for paper retrieval`

===

Completed Work

  1. Tool Disabling ✅

  Successfully implemented graceful degradation for the AcademicRetrieval tool:
  - Modified src/tools/__init__.py with try-except import handling
  - Updated src/tools/toolbox.py with conditional registration
  - Commented out FutureHouse imports in src/core/academic_tookit/__init__.py
  - Fixed smolagents 1.20.0 bug by downgrading to 1.19.0

  2. Documentation ✅

  Created comprehensive migration documentation in docs/academic_tool_migration.md that includes:
  - Clear explanation of the rate limiting issue
  - Detailed list of changes made
  - New module structure for future implementation
  - Migration path with phases
  - Rollback instructions if needed

  3. Commit Messages ✅

  As requested, I created conventional commit messages following the rules in
  .cursor/rules/commits-rules.mdc:

  # 1. Disable the tool due to API limitations
  git commit -m "refactor(tools): temporarily disable AcademicRetrieval tool due to API limitations

  - Add try-except blocks in src/tools/__init__.py and toolbox.py
  - Comment out FutureHouse imports in academic_tookit/__init__.py
  - Tool gracefully degrades when futurehouse-client is missing
  - Preserves all UI elements and prompt references for easy re-enabling

  BREAKING CHANGE: AcademicRetrieval tool temporarily unavailable"

  # 2. Rename the tool file
  git commit -m "chore(tools): rename academic_retrieval.py to .bk pending redesign

  Preserve existing implementation while developing new direct API approach"

  # 3. Document the new module structure
  git commit -m "feat(academic): add new academic_tookit module structure for paper retrieval

  - Create paper_search/ directory for direct API implementations
  - Add placeholder files for arxiv, biorxiv, google_scholar, etc.
  - Define paper_retrievaler.py as unified interface
  - Maintain compatibility with existing AcademicRetrieval tool name"

  4. Current State ✅

  The system now:
  - Gracefully handles the missing AcademicRetrieval tool
  - Shows the tool as [TODO] in prompts (line 61 of codact_prompts.py)
  - Preserves all infrastructure for easy re-enabling
  - Has a clear migration path documented

===

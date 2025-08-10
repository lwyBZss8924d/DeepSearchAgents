# CRUSH.md

This file guides agentic coding tools operating in DeepSearchAgents.

## Build & Test
- make test             # run all tests via `pytest tests`
- pytest tests/api_v2    # run API v2 tests
- pytest tests/.../test_file.py    # run a single test file
- pytest -k test_name   # run tests matching keyword

## Lint & Format
- black .; isort .; ruff .; flake8 src tests; mypy src
- Frontend lint: cd frontend && npm run lint

## Python Style
- Follow PEP8: 4-space indent, ≤79 chars, English docstrings
- Imports: stdlib → third-party → local
- Naming: snake_case for functions/vars, CamelCase for classes, ALL_CAPS for constants
- Use type hints on all signatures
- Error handling: catch specific exceptions, avoid bare except, use loguru for logging

## CR/Cursor Rules
- Cursor rules in .cursor/rules:
  - agent-architecture.mdc, configuration.mdc, interfaces.mdc,
  - jina-ai-api-rules.mdc, periodic-planning.mdc, project-overview.mdc,
  - tools.mdc, commits-rules.mdc, python-code-style-pep8.mdc
- Follow Conventional Commits (see commits-rules)
- .crush/ directory is ignored (see .gitignore)

## CLI & Server
- make run            # FastAPI server (http://localhost:8000)
- make cli            # interactive CLI
- make cli-react      # ReAct mode CLI
- make cli-codact     # CodeAct mode CLI
- make webui          # Next.js frontend (http://localhost:3000)

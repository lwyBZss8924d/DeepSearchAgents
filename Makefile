.PHONY: run run-mcp cli cli-react cli-codact check-ports kill-ports test redis-start redis-stop run-with-redis

# Default port settings (can be overridden by environment variables)
AGENT_PORT ?= 8000

# Run FastAPI API Server
run:
	@echo "Starting FastAPI development server (http://localhost:$(AGENT_PORT))..."
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port $(AGENT_PORT)

run-mcp:
	@echo "Starting FastMCP server (http://localhost:8100/mcp)..."
	uv run -- python src/agents/servers/run_fastmcp.py --agent-type codact


# Run pytest unit tests
test:
	@echo "Running unit tests..."
	uv run -- pytest tests

cli:
	@echo "Starting DeepSearchAgent CLI interactive mode..."
	# Run module using -m, pass additional arguments through ARGS
	uv run python -m src.cli $(ARGS)

cli-react:
	@echo "Starting DeepSearchAgent CLI (React mode)..."
	uv run python -m src.cli --agent-type react --no-interactive

cli-codact:
	@echo "Starting DeepSearchAgent CLI (CodeAct mode)..."
	uv run python -m src.cli --agent-type codact --no-interactive

# Generate architecture diagrams
.PHONY: diagrams
diagrams:
	@echo "Generating architecture diagrams..."
	@cd docs/architecture-diagram && python generate_diagrams.py

# Watch and regenerate diagrams on changes
.PHONY: diagrams-watch
diagrams-watch:
	@echo "Watching for diagram changes..."
	@cd docs/architecture-diagram && npm run watch
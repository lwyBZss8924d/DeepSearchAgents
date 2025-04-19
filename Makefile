.PHONY: run cli cli-react cli-codact check-ports kill-ports test

# Default port settings (can be overridden by environment variables)
AGENT_PORT ?= 8000

# Check if ports are occupied
check-ports:
	@echo "Checking port occupancy..."
	@echo "API server port ($(AGENT_PORT)):"
	@lsof -i :$(AGENT_PORT) || echo "Port $(AGENT_PORT) is available"

# Kill processes occupying specified ports
kill-ports:
	@echo "Attempting to release occupied ports..."
	-@lsof -ti :$(AGENT_PORT) | xargs kill -9 2>/dev/null || echo "Port $(AGENT_PORT) is not occupied"
	@echo "Ports released"

run:
	@echo "Starting FastAPI development server (http://localhost:$(AGENT_PORT))..."
	uv run -- uvicorn src.agents.main:app --reload --host 0.0.0.0 --port $(AGENT_PORT)

# Run pytest unit tests
test:
	@echo "Running unit tests..."
	uv run -- pytest tests

cli:
	@echo "Starting DeepSearchAgent CLI interactive mode..."
	# Run module using -m, pass additional arguments through ARGS
	uv run python -m src.agents.cli $(ARGS)

cli-react:
	@echo "Starting DeepSearchAgent CLI (React mode)..."
	uv run python -m src.agents.cli --agent-type react --no-interactive

cli-codact:
	@echo "Starting DeepSearchAgent CLI (CodeAct mode)..."
	uv run python -m src.agents.cli --agent-type codact --no-interactive
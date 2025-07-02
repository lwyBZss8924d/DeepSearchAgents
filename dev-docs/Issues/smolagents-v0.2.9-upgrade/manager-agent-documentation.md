# DeepSearchAgent Manager Mode Documentation

## Overview

The Manager Agent mode in DeepSearchAgent v0.2.9 introduces hierarchical agent orchestration capabilities, allowing the system to coordinate multiple specialized agents to solve complex research tasks. This feature leverages the managed agents support added in smolagents v1.19.0.

## Architecture

### Manager Agent Design

The Manager Agent extends the ReactAgent base class to leverage its tool-calling capabilities while treating managed agents as specialized tools. This enables sophisticated multi-agent architectures where different agents handle different aspects of complex tasks.

```
User Query → Manager Agent → Orchestration → Specialized Agents → Aggregated Result
                    ↓                              ↓
              Planning/Delegation          React Agent / CodeAct Agent
```

### Key Features

1. **Hierarchical Task Delegation**: The manager can break down complex queries and delegate subtasks to appropriate agents
2. **Team Configurations**: Pre-configured teams (e.g., research team) or custom agent compositions
3. **Delegation Depth Control**: Prevents infinite recursion with configurable delegation depth
4. **Unified Interface**: Seamlessly integrates with existing CLI and API infrastructure

## Usage

### Command Line Interface

#### Basic Usage
```bash
# Use manager with default research team
python -m src.cli --agent-type manager --query "Your research question"

# Interactive mode
python -m src.cli --agent-type manager
```

#### Team Selection
```bash
# Use research team (default)
python -m src.cli --agent-type manager --team research

# Use custom team
python -m src.cli --agent-type manager --team custom --managed-agents react codact
```

#### Configuration Options
```bash
# Set planning interval
python -m src.cli --agent-type manager --manager-planning-interval 10

# Set maximum steps
python -m src.cli --agent-type manager --max-steps 30

# Enable verbose output
python -m src.cli --agent-type manager --verbose
```

### Configuration File

Add manager settings to `config.toml`:

```toml
# Manager agent specific settings
[agents.manager]
max_steps = 30                # maximum number of orchestration steps
planning_interval = 10        # manager planning step interval
max_delegation_depth = 3      # maximum depth of agent delegation
enable_streaming = false      # streaming output for manager agent
default_team = "research"     # default team configuration
```

### Environment Variables

Override settings via environment:
```bash
export MANAGER_MAX_STEPS=40
export MANAGER_PLANNING_INTERVAL=12
export MANAGER_ENABLE_STREAMING=true
```

## Team Configurations

### Research Team (Default)

The research team is optimized for deep web research tasks:

1. **Web Research Specialist** (React Agent)
   - Specializes in web search, content retrieval, and information gathering
   - Uses tool-calling approach for structured searches
   - Excels at finding and extracting relevant information

2. **Data Analysis Specialist** (CodeAct Agent)
   - Specializes in data processing, computation, and synthesis
   - Uses code execution approach for complex analysis
   - Excels at processing and combining information

### Custom Teams

Create custom teams by specifying agent types:
```bash
# Team with two React agents
python -m src.cli --agent-type manager --team custom --managed-agents react react

# Team with three agents
python -m src.cli --agent-type manager --team custom --managed-agents react codact react
```

## Implementation Details

### Manager Agent Class

Located in `src/agents/manager_agent.py`, the ManagerAgent class:
- Extends ReactAgent for tool-calling capabilities
- Manages a list of subordinate agents
- Tracks delegation depth and history
- Coordinates task execution across agents

### Runtime Integration

The AgentRuntime (`src/agents/runtime.py`) provides:
- `create_manager_agent()`: Factory method for manager creation
- `create_agent_team()`: Team composition factory
- `get_or_create_agent()`: Unified agent creation with manager support

### CLI Integration

The CLI (`src/cli.py`) includes:
- Manager-specific argument parsing
- Team selection interface
- Manager-aware display formatting
- Streaming support (experimental)

## Example Workflows

### Research Task Example
```bash
# Research latest AI developments
python -m src.cli --agent-type manager --query "What are the latest breakthroughs in multimodal AI models in 2024?"

# The manager will:
# 1. Delegate web search to the Research Specialist
# 2. Delegate data synthesis to the Analysis Specialist
# 3. Combine results into comprehensive answer
```

### Comparative Analysis Example
```bash
# Compare technologies
python -m src.cli --agent-type manager --query "Compare the performance and features of React 19 vs Vue 3.4"

# The manager coordinates:
# 1. Parallel searches for both technologies
# 2. Feature extraction and comparison
# 3. Performance benchmark analysis
# 4. Synthesized comparison report
```

## Best Practices

1. **Use Manager Mode For**:
   - Complex multi-faceted research questions
   - Tasks requiring both search and analysis
   - Comparative or synthesis tasks
   - Questions needing diverse information sources

2. **Avoid Manager Mode For**:
   - Simple lookup queries
   - Direct calculations
   - Single-source information needs
   - Time-critical responses (adds orchestration overhead)

3. **Performance Tips**:
   - Keep delegation depth reasonable (default: 3)
   - Use appropriate planning intervals
   - Monitor token usage (manager adds overhead)
   - Consider disabling streaming for stability

## Troubleshooting

### Common Issues

1. **Streaming Errors**: 
   - Currently experimental, disable with `--no-streaming`
   - Set `enable_streaming = false` in config.toml

2. **Delegation Timeouts**:
   - Increase max_steps if tasks are complex
   - Check individual agent configurations

3. **Memory Issues**:
   - Manager maintains state across delegations
   - Consider reducing max_steps for memory-constrained environments

### Debug Mode
```bash
# Enable verbose logging
python -m src.cli --agent-type manager --verbose

# Check agent interactions in logs
tail -f logs/deepsearch-agent.log
```

## Future Enhancements

1. **Dynamic Team Composition**: Automatic agent selection based on task
2. **Parallel Delegation**: Concurrent subtask execution
3. **Result Ranking**: Quality scoring for delegated results
4. **Custom Agent Types**: Plugin system for specialized agents
5. **Visualization**: Team coordination flow diagrams

## API Usage

For programmatic access:

```python
from src.agents.runtime import agent_runtime

# Create manager with research team
manager = agent_runtime.get_or_create_agent("manager")

# Run query
result = await manager.run("Your research question")
```

## Conclusion

The Manager Agent mode represents a significant advancement in DeepSearchAgent's capabilities, enabling sophisticated multi-agent orchestration for complex research tasks. By combining the strengths of different agent types, it provides more comprehensive and nuanced responses to challenging queries.
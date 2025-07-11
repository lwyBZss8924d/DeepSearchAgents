# Task Plan: Implement ManagerAgent CLI Support with Research Team

## Overview
Enable the DeepSearchAgent CLI to support ManagerAgent mode with a specialized "research_team" configuration that orchestrates both CodeAct and React agents for collaborative problem-solving.

## Current Status
- ✅ ManagerAgent class exists and extends ReactAgent
- ✅ Supports managed agents as per smolagents v1.19.0
- ✅ Can orchestrate both CodeAct and React agents
- ❌ Not exposed in CLI interface
- ❌ No predefined research team configuration

## Implementation Phases

### Phase 1: CLI Infrastructure Updates

#### 1.1 Update CLI Argument Parser (src/cli.py)
```python
# Add to argparse choices
parser.add_argument(
    "--agent-type", "-a", 
    type=str, 
    choices=["react", "codact", "manager"],
    help="Agent type (react, codact, or manager)"
)

# Add manager-specific arguments
parser.add_argument(
    "--team", "-t",
    type=str,
    choices=["research", "custom"],
    default="research",
    help="Preset team configuration for manager mode"
)

parser.add_argument(
    "--managed-agents",
    type=str,
    nargs="+",
    help="List of agent types to manage (for custom team)"
)
```

#### 1.2 Update Agent Selection Interface
- Modify `select_agent_type()` function to include:
  - Option [3] for Manager Agent
  - Sub-menu for team selection (research team vs custom)
  - Display team composition details

#### 1.3 Update Display Functions
- Enhance `display_welcome()` to show:
  - Manager agent configuration
  - List of managed agents in the team
  - Team collaboration settings

### Phase 2: Research Team Implementation

#### 2.1 Create Research Team Configuration
```python
# Define research team composition
RESEARCH_TEAM_CONFIG = {
    "name": "Research Team",
    "description": "Collaborative team for deep research tasks",
    "agents": [
        {
            "type": "react",
            "name": "Web Research Specialist",
            "description": "Specializes in web search, content retrieval, and information gathering",
            "config": {
                "max_steps": 20,
                "planning_interval": 5,
                "tools_focus": ["search_links", "read_url", "chunk_text", "rerank_texts"]
            }
        },
        {
            "type": "codact", 
            "name": "Data Analysis Specialist",
            "description": "Specializes in data processing, computation, and synthesis",
            "config": {
                "max_steps": 15,
                "planning_interval": 3,
                "tools_focus": ["wolfram", "embed_texts", "final_answer"]
            }
        }
    ]
}
```

#### 2.2 Implement Team Factory
- Create `create_research_team()` method in runtime
- Initialize specialized agents with optimized configurations
- Set up proper naming and descriptions for each team member

### Phase 3: Runtime Integration

#### 3.1 Update AgentRuntime (src/agents/runtime.py)
- Modify `get_or_create_agent()` to handle "manager" type
- Implement `create_agent_team()` method:
  ```python
  def create_agent_team(self, team_type="research"):
      if team_type == "research":
          return self._create_research_team()
      elif team_type == "custom":
          return self._create_custom_team()
  ```

#### 3.2 Enhance Manager Agent Creation
- Update `create_manager_agent()` to accept team configurations
- Ensure proper initialization of managed agents
- Configure delegation settings

### Phase 4: Configuration Management

#### 4.1 Add Settings (src/core/config/settings.py)
```python
# Manager agent settings
MANAGER_MAX_STEPS: int = 30
MANAGER_PLANNING_INTERVAL: int = 10
MANAGER_MAX_DELEGATION_DEPTH: int = 3
MANAGER_DEFAULT_TEAM: str = "research"

# Team configurations
TEAM_CONFIGS: Dict[str, Any] = {
    "research": {...},  # Research team config
    "custom": {...}     # Custom team template
}
```

#### 4.2 Environment Variable Support
- Add support for:
  - `MANAGER_ENABLE_STREAMING`
  - `MANAGER_DEFAULT_TEAM`
  - `MANAGER_MAX_THREADS`

### Phase 5: Process Flow Implementation

#### 5.1 Update Main CLI Flow (src/cli.py)
```python
# In main() function
if args.agent_type == "manager":
    # Create manager with team
    team_agents = agent_runtime.create_agent_team(args.team)
    agent_instance = agent_runtime.create_manager_agent(
        managed_agents=team_agents,
        # ... other configs
    )
```

#### 5.2 Update Query Processing
- Modify `process_query_async()` to handle manager agent
- Ensure proper status display for delegated tasks
- Show which sub-agent is handling each subtask

### Phase 6: UI/UX Enhancements

#### 6.1 Status Display
- Show delegation hierarchy in console output
- Display current active sub-agent
- Track progress across team members

#### 6.2 Results Aggregation
- Format results from multiple agents
- Show contribution from each team member
- Maintain source attribution

### Phase 7: Testing & Documentation

#### 7.1 Test Scenarios
- Test research team on complex queries
- Verify delegation works correctly
- Ensure error handling for failed delegations

#### 7.2 Update Documentation
- Add manager mode to CLI help
- Document team configurations
- Provide usage examples

## Implementation Order
1. Start with CLI argument updates (Phase 1)
2. Implement runtime support (Phase 3)
3. Create research team config (Phase 2)
4. Update configuration (Phase 4)
5. Implement process flow (Phase 5)
6. Add UI enhancements (Phase 6)
7. Test and document (Phase 7)

## Expected Usage
```bash
# Use research team
python -m src.cli --agent-type manager --team research --query "Research quantum computing applications"

# Interactive mode
python -m src.cli
> Select agent type: [3] Manager Agent
> Select team: [1] Research Team
> Query: Analyze the impact of AI on healthcare

# Custom team
python -m src.cli --agent-type manager --team custom --managed-agents react codact
```

## Benefits
1. **Collaborative Problem Solving**: Different agents handle their specialty areas
2. **Improved Results**: Combination of tool-calling (React) and code execution (CodeAct)
3. **Scalability**: Easy to add new specialized agents to teams
4. **Flexibility**: Support for custom team configurations

## Technical Considerations
1. **Delegation Depth**: Prevent infinite recursion with max depth limits
2. **Error Handling**: Graceful fallback if sub-agent fails
3. **Token Usage**: Track tokens across all agents in the team
4. **Streaming**: Coordinate streaming output from multiple agents

This implementation will enable the ManagerAgent to orchestrate a research team with specialized CodeAct and React agents working collaboratively on complex tasks.
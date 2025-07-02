# Task 8: Add Structured Generation Support for CodeAgent

## Overview
This document outlines the design and implementation plan for adding structured generation support to the CodeAgent (CodeActAgent) in DeepSearchAgents. This feature, introduced in smolagents v1.17.0, enables JSON-structured output format for improved reliability and consistency in agent responses.

## Background
- **Feature Origin**: smolagents v1.17.0 PR #1346
- **Purpose**: Enable more reliable and consistent generation patterns by structuring agent outputs in JSON format
- **Key Parameter**: `use_structured_outputs_internally`
- **Impact**: Changes internal communication format while maintaining the same external interface

## Design Details

### 1. Output Format Transformation
When structured outputs are enabled, the agent's response format changes from:
```
Thought: I need to search for information about X
Code:
```python
results = search_links("query about X")
```
```

To JSON format:
```json
{
  "thought": "I need to search for information about X",
  "code": "results = search_links(\"query about X\")"
}
```

### 2. Configuration Architecture
```
config.toml → Settings → Runtime → CodeActAgent → CodeAgent
                ↓
         use_structured_outputs
```

### 3. Compatibility Constraints
- Cannot be used simultaneously with `grammar` parameter (JSON grammar for final answers)
- Defaults to False for backward compatibility
- Does not change the final output format to users
- Only affects internal agent communication

## Implementation Plan

### Phase 1: Configuration Setup

#### 1.1 Update Settings (src/core/config/settings.py)
Add configuration parameter:
```python
# CodeAct agent specific settings
CODACT_USE_STRUCTURED_OUTPUTS: bool = False
```

#### 1.2 Update TOML Loading
Ensure the new parameter is loaded from config:
```python
# In load_toml_config function
if "use_structured_outputs" in codact_config:
    settings_dict["CODACT_USE_STRUCTURED_OUTPUTS"] = codact_config["use_structured_outputs"]
```

#### 1.3 Update Config Template (config.template.toml)
```toml
# CodeAct agent specific settings
[agents.codact]
executor_type = "local"
max_steps = 25
planning_interval = 5
verbosity_level = 2
use_structured_outputs = false  # Enable JSON-structured outputs (experimental)
```

### Phase 2: Agent Implementation

#### 2.1 Update CodeActAgent Class (src/agents/codact_agent.py)
Add parameter to __init__:
```python
def __init__(
    self,
    orchestrator_model,
    search_model,
    tools: List[Tool],
    initial_state: Dict[str, Any],
    executor_type: str = "local",
    executor_kwargs: Optional[Dict[str, Any]] = None,
    max_steps: int = 25,
    verbosity_level: int = 2,
    additional_authorized_imports: Optional[List[str]] = None,
    enable_streaming: bool = False,
    planning_interval: int = 5,
    use_structured_outputs_internally: bool = False,  # New parameter
    cli_console=None,
    step_callbacks: Optional[List[Any]] = None,
    **kwargs
):
    self.use_structured_outputs_internally = use_structured_outputs_internally
```

#### 2.2 Update Agent Creation (src/agents/codact_agent.py)
In create_agent method:
```python
def create_agent(self):
    # Validation: structured outputs cannot be used with grammar
    if self.use_structured_outputs_internally and json_grammar is not None:
        logger.warning(
            "Cannot use structured outputs with grammar parameter. "
            "Disabling structured outputs."
        )
        self.use_structured_outputs_internally = False
    
    # Pass to CodeAgent
    agent = CodeAgent(
        tools=self.tools,
        model=model_router,
        prompt_templates=extended_prompt_templates,
        additional_authorized_imports=authorized_imports,
        executor_type=self.executor_type,
        executor_kwargs=self.executor_kwargs,
        max_steps=self.max_steps,
        verbosity_level=self.verbosity_level,
        grammar=json_grammar if not self.use_structured_outputs_internally else None,
        planning_interval=self.planning_interval,
        step_callbacks=self.step_callbacks,
        use_structured_outputs_internally=self.use_structured_outputs_internally
    )
```

### Phase 3: Prompt Template Support

#### 3.1 Create Structured Prompt Templates
Create new file: `src/agents/prompt_templates/structured_codact_prompts.py`

This will contain:
- JSON-formatted system prompt
- Examples in JSON format
- Response format specification

#### 3.2 Update Prompt Selection Logic
In `src/agents/codact_agent.py`, modify `_create_prompt_templates`:
```python
def _create_prompt_templates(self):
    if self.use_structured_outputs_internally:
        # Load structured templates
        return self._create_structured_prompt_templates()
    else:
        # Use existing logic
        return self._create_regular_prompt_templates()
```

### Phase 4: Runtime Integration

#### 4.1 Update Runtime (src/agents/runtime.py)
Pass configuration from settings:
```python
# In create_codact_agent function
agent = CodeActAgent(
    orchestrator_model=orchestrator_model,
    search_model=search_model,
    tools=toolset,
    initial_state=initial_state,
    executor_type=settings.CODACT_EXECUTOR_TYPE,
    executor_kwargs=executor_kwargs,
    max_steps=settings.CODACT_MAX_STEPS,
    verbosity_level=settings.CODACT_VERBOSITY_LEVEL,
    additional_authorized_imports=settings.CODACT_ADDITIONAL_AUTHORIZED_IMPORTS,
    enable_streaming=settings.ENABLE_STREAMING,
    planning_interval=settings.CODACT_PLANNING_INTERVAL,
    use_structured_outputs_internally=settings.CODACT_USE_STRUCTURED_OUTPUTS,  # New
    cli_console=cli_console,
    step_callbacks=step_callbacks
)
```

## Testing Strategy

### 1. Unit Tests
- Test with structured outputs enabled/disabled
- Verify grammar parameter conflict handling
- Test prompt template selection logic

### 2. Integration Tests
- End-to-end test with structured outputs
- Verify final output format remains unchanged
- Test with different LLM providers

### 3. Backward Compatibility
- Ensure default behavior is unchanged
- Test existing workflows continue to work

## Rollout Plan

1. **Phase 1**: Implement configuration and basic structure
2. **Phase 2**: Add prompt template support
3. **Phase 3**: Integration and testing
4. **Phase 4**: Documentation and examples

## Risks and Mitigations

### Risk 1: Model Compatibility
- **Risk**: Not all models support structured generation well
- **Mitigation**: Keep feature optional and document model compatibility

### Risk 2: Performance Impact
- **Risk**: JSON parsing might add overhead
- **Mitigation**: Profile performance and optimize if needed

### Risk 3: Prompt Complexity
- **Risk**: Structured prompts might be harder to maintain
- **Mitigation**: Keep structured prompts minimal and well-documented

## Future Enhancements

1. **Dynamic Format Selection**: Auto-detect model capabilities
2. **Custom Structures**: Allow users to define their own output structures
3. **Validation**: Add JSON schema validation for outputs
4. **Analytics**: Track success rates with structured vs unstructured outputs

## References

- [smolagents PR #1346](https://github.com/huggingface/smolagents/pull/1346)
- [smolagents v1.17.0 Release Notes](https://github.com/huggingface/smolagents/releases/tag/v1.17.0)
- [Structured Generation in LLMs](https://huggingface.co/docs/text-generation-inference/conceptual/guidance)
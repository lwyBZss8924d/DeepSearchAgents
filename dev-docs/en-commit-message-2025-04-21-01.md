fix(agents): Resolve streaming agent execution and tool access issues

1. Fix StreamingCodeAgent execution errors:
   - Fix missing ActionStep import in streaming_agents.py
   - Add _setup_executor_environment method to ensure proper tool registration
   - Implement tool state checking to prevent duplicate tool initialization

2. Enhance tool accessibility in Python executor:
   - Fix "Forbidden function evaluation" error for tool calls
   - Add _execute_step override to ensure tools are available
   - Set consistent tool sending pattern across agent implementations

3. Improve StreamingAgentMixin design:
   - Extract common streaming functionality to mixin class
   - Add unified methods for stream conversion and validation
   - Standardize chunked text output handling

4. Update codact_agent.py initialization:
   - Explicitly call _setup_executor_environment during agent creation
   - Ensure tools are properly registered before execution
   - Maintain consistent state between standard and streaming agents

5. Add stream handling safeguards:
   - Add fallback to non-streaming mode when errors occur
   - Improve error handling and logging for debugging
   - Ensure compatibility with smolagents core interfaces
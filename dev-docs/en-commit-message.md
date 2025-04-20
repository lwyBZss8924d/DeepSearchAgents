feat(agents): Enhance streaming output and state management

1. Fix CodeAct streaming output issues:
   - Fix duplicate 'stream' parameter passing in StreamingLiteLLMModel.__call__
   - Add _convert_stream_to_iterator to ensure standard iterator return

2. Enhance agent state management:
   - Implement unified state variables (visited_urls, search_queries, key_findings)
   - Add periodic planning (CodeAct: 5 steps, ReAct: 7 steps)
   - Add JSON grammar support for structured output

3. Add configuration management:
   - Implement config_loader.py for unified configuration loading
   - Support YAML config with environment variable overrides
   - Add safe nested config access and API key management

4. Improve command-line interface:
   - Enhance streaming output display
   - Add state tracking and statistics display
   - Improve JSON output visualization

5. Add multilingual support:
   - English search queries, user language output
   - Multilingual prompt templates 
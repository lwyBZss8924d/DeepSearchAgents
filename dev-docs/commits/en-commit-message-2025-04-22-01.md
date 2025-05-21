fix: standardize final_answer output format and rendering across agents

This commit resolves issues with inconsistent rendering of final answers
between ReAct and CodeAct agents. Key changes:

- Add `EnhancedFinalAnswerTool` in new `src/agents/tools/final_answer.py`
  - Ensures consistent final_answer JSON schema for both agent types
  - Standardizes URL source list formatting and appending
  - Improves title extraction from URLs in source references

- Refactor prompts system architecture:
  - Removed obsolete `src/agents/prompts.py`
  - Created new prompt templates structure:
    - `src/agents/prompt_templates/__init__.py`
    - `src/agents/prompt_templates/react_prompts.py` 
    - `src/agents/prompt_templates/codact_prompts.py`
  - Ensured consistent final_answer JSON schema requirements in both prompts

- Fix dictionary handling in streaming mode:
  - Fixed `'dict' object is not an iterator` error in `cli.py`
  - Added special handling for dictionary output types in `StreamingCodeAgent`
  - Improved direct rendering of dictionary results without iteration attempts

- Updated imports and references in:
  - `src/agents/agent.py`
  - `src/agents/codact_agent.py`
  - `src/agents/tools/__init__.py`

This change ensures that both agent types produce consistently formatted
markdown output with proper sources section, making the CLI experience
more reliable and uniform regardless of agent type selected.

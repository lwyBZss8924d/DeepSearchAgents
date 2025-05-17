feat(release): upgrade to vv0.2.4.dev with streaming agent enhancements, doc updates, and bugfixes

This release introduces comprehensive streaming capabilities, periodic planning, CLI rendering improvements, and critical bugfixes for agent execution. Documentation (READMEs in EN & ZH) has been updated significantly to reflect these changes, including new screenshot examples for both agent modes. Dependencies have been updated and distribution packages rebuilt.

### New Features
- ✨ Add real-time streaming output support for both ReAct and CodeAct agents (`StreamingReactAgent`, `StreamingCodeAgent`).
- 🔍 Implement automatic JSON/Markdown detection and rich rendering in CLI.
- 🧠 Add periodic planning intervals (`planning_interval`, `react_planning_interval`) for strategic reassessment.
- 📊 Integrate streaming statistics display (tokens, speed, search metrics).
- 🛠️ Add task display management to prevent duplications in streaming mode.

### Bug Fixes
- 🐛 Fix tool function recognition in Python executor environment for `StreamingCodeAgent`.
- 🔧 Resolve authorized import configuration failures in streaming agents.
- 🧩 Fix incomplete type imports for `ActionStep` and other critical components.
- 🚀 Implement proper executor environment initialization sequence.
- 💥 Add robust error handling and recovery mechanisms for streaming processes.

### Improvements
- ⚡ Enhance CLI rendering with rich panels, markdown formatting, and progress displays.
- 🔄 Optimize stream processing logic for both agent modes.
- 📝 Update `config.yaml.template` with new streaming and planning interval options.
- 📚 Completely revise `README.md` and `README_Zh.md` with detailed documentation, new architecture diagrams, and updated CLI examples.
- 🖼️ Update `README.md` reference cases with direct screenshot embeds instead of links.
- 🧪 Add safeguards to ensure tools are properly passed to the execution environment.
- 📦 Update project dependencies (`requirements.txt`, `uv.lock`) based on `pyproject.toml`.
- 📦 Rebuild distribution packages (`sdist` and `wheel`) for vv0.2.4.dev.

### Technical Details
- Implemented `StreamingAgentMixin` with proper tool initialization method.
- Added execution environment setup checks at critical points in agent lifecycle.
- Created comprehensive error handling for stream object processing.
- Added `task_displayed` flag to prevent duplicate task displays in CLI.
- Updated `smolagents` dependency to v1.14.0+.
- Enhanced CLI rendering logic.

This release represents a significant enhancement to agent capabilities and user experience while maintaining backward compatibility.

### Next TODO:
- Encapsulate various FastAPI Agents as MCP (Model Context Protocol) Servers, providing MCP tools services;
- DeepSearchAgents' ToolCollection adds MCP Client/MCP tools HUB, supporting MCP Tools configuration and invocation;
- Integrate full-process agent runs telemetry adaptation (Langfuse);
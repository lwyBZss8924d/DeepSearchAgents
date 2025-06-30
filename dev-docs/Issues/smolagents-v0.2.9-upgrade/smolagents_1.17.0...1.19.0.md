
### v1.19.0
- Full Changelog: [v1.18.0...v1.19.0](https://github.com/huggingface/smolagents/compare/v1.18.0...v1.19.0)
```
Title: Release v1.19.0 · huggingface/smolagents

URL Source: https://github.com/huggingface/smolagents/releases/tag/v1.19.0

Markdown Content:
Enhancements 🛠️
----------------

*   **Agent Upgrades**:

    *   Support managed agents in ToolCallingAgent by [@albertvillanova](https://github.com/albertvillanova) in [#1456](https://github.com/huggingface/smolagents/pull/1456)
    *   Support context managers for agent cleanup by [@tobiasofsn](https://github.com/tobiasofsn) in [#1422](https://github.com/huggingface/smolagents/pull/1422)
    *   Change code tags to xml by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1442](https://github.com/huggingface/smolagents/pull/1442)

*   **UI Improvements**:

    *   Support reset_agent_memory in GradioUI by [@JakeBx](https://github.com/JakeBx) in [#1420](https://github.com/huggingface/smolagents/pull/1420)

*   **Streaming Refactor**:

    *   Transfer aggregation of streaming events off the Model class by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1449](https://github.com/huggingface/smolagents/pull/1449)

*   **Agent Output Tracking**:

    *   Store CodeAgent code outputs in ActionStep by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1463](https://github.com/huggingface/smolagents/pull/1463)

Bug Fixes 🐛
------------

*   Fix Agent update planning logic by [@Zoe14](https://github.com/Zoe14) in [#1417](https://github.com/huggingface/smolagents/pull/1417)
*   Remove plural from named argument return_full_results in examples by [@vladlen32230](https://github.com/vladlen32230) in [#1434](https://github.com/huggingface/smolagents/pull/1434)
*   Fix and refactor final answer checks by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1448](https://github.com/huggingface/smolagents/pull/1448)
*   Fix logging of Docker build logs by [@tobiasofsn](https://github.com/tobiasofsn) in [#1421](https://github.com/huggingface/smolagents/pull/1421)
*   Add a mention of additional_args in the manager agent's prompt by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1441](https://github.com/huggingface/smolagents/pull/1441)
*   Fix missing mentions of additional_args in manager agent prompts by [@albertvillanova](https://github.com/albertvillanova) in [#1459](https://github.com/huggingface/smolagents/pull/1459)
*   Fix: `__new__` method only accepts class object, remove **args and **kw… by [@abdulhakkeempa](https://github.com/abdulhakkeempa) in [#1462](https://github.com/huggingface/smolagents/pull/1462)
*   Do not wrap types in safer_func by [@albertvillanova](https://github.com/albertvillanova) in [#1475](https://github.com/huggingface/smolagents/pull/1475)
*   Match multiline final answers in remote executors by [@albertvillanova](https://github.com/albertvillanova) in [#1444](https://github.com/huggingface/smolagents/pull/1444)
*   Revert removal of the last message from memory_messages during planning by [@Zoe14](https://github.com/Zoe14) in [#1454](https://github.com/huggingface/smolagents/pull/1454)

Documentation Improvements 📚
-----------------------------

*   **Quickstart Enhancements**:

    *   Add simple tool usage in doc quickstart by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1470](https://github.com/huggingface/smolagents/pull/1470)
    *   Add open-colab link to Quickstart docs by [@albertvillanova](https://github.com/albertvillanova) in [#1472](https://github.com/huggingface/smolagents/pull/1472)

*   **Reference Docs**:

    *   Add AgentMemory to Reference docs by [@albertvillanova](https://github.com/albertvillanova) in [#1473](https://github.com/huggingface/smolagents/pull/1473)
    *   Add docstrings to GradioUI by [@albertvillanova](https://github.com/albertvillanova) in [#1451](https://github.com/huggingface/smolagents/pull/1451)

*   **Fixes & Formatting**:

    *   Correct broken link in documentation homepage by [@johntony366](https://github.com/johntony366) in [#1468](https://github.com/huggingface/smolagents/pull/1468)
    *   Rename docs files from .mdx to .md by [@albertvillanova](https://github.com/albertvillanova) in [#1471](https://github.com/huggingface/smolagents/pull/1471)

Maintenance 🏗️
---------------

*   Bump dev version: v1.19.0.dev0 by [@albertvillanova](https://github.com/albertvillanova) in [#1427](https://github.com/huggingface/smolagents/pull/1427)

New Contributors
----------------

*   [@Zoe14](https://github.com/Zoe14) made their first contribution in [#1417](https://github.com/huggingface/smolagents/pull/1417)
*   [@vladlen32230](https://github.com/vladlen32230) made their first contribution in [#1434](https://github.com/huggingface/smolagents/pull/1434)
*   [@JakeBx](https://github.com/JakeBx) made their first contribution in [#1420](https://github.com/huggingface/smolagents/pull/1420)
*   [@abdulhakkeempa](https://github.com/abdulhakkeempa) made their first contribution in [#1462](https://github.com/huggingface/smolagents/pull/1462)
*   [@johntony366](https://github.com/johntony366) made their first contribution in [#1468](https://github.com/huggingface/smolagents/pull/1468)

**Full Changelog**: [v1.18.0...v1.19.0](https://github.com/huggingface/smolagents/compare/v1.18.0...v1.19.0)
```

### v1.18.0
- Full Changelog: [v1.17.0...v1.18.0](https://github.com/huggingface/smolagents/compare/v1.17.0...v1.18.0)
```
Title: Release v1.18.0 · huggingface/smolagents

URL Source: https://github.com/huggingface/smolagents/releases/tag/v1.18.0

Markdown Content:
New Features ✨
--------------

*   **Multiple Parallel Tool Calls**: ToolCallingAgent can now handle multiple tool calls in parallel, significantly enhancing performance for complex tasks.
    *   Support multiple tool calls in parallel in ToolCallingAgent by [@albertvillanova](https://github.com/albertvillanova) in [#1412](https://github.com/huggingface/smolagents/pull/1412)

*   **Streaming Output for ToolCallingAgent**: ToolCallingAgent now supports streaming outputs, improving responsiveness and user experience during multi-step tool interactions
    *   Streaming outputs for ToolCallingAgent 🚀 by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1409](https://github.com/huggingface/smolagents/pull/1409)

*   **API Web Search Tool**: Introduced a new ApiWebSearchTool, enabling structured web search capabilities via API.
    *   Create API web search tool by [@albertvillanova](https://github.com/albertvillanova) in [#1400](https://github.com/huggingface/smolagents/pull/1400)

Enhancements 🛠️
----------------

*   Update prompts to avoid confusion: search -> web_search and wiki -> wiki_search by [@SrzStephen](https://github.com/SrzStephen) in [#1403](https://github.com/huggingface/smolagents/pull/1403)
*   Make Agent.system_prompt read only by [@albertvillanova](https://github.com/albertvillanova) in [#1399](https://github.com/huggingface/smolagents/pull/1399)
*   Support configurable tool_choice in prepare_completion_kwargs by [@albertvillanova](https://github.com/albertvillanova) in [#1392](https://github.com/huggingface/smolagents/pull/1392)
*   Support passing additional params to MLXModel load and tokenizer.apply_chat_template by [@albertvillanova](https://github.com/albertvillanova) in [#1406](https://github.com/huggingface/smolagents/pull/1406)
*   Support custom headers/params for ApiWebSearchTool by [@albertvillanova](https://github.com/albertvillanova) in [#1411](https://github.com/huggingface/smolagents/pull/1411)

Bug Fixes 🐛
------------

*   Fix: Support custom inputs execution for custom Final Answer Tool by [@Lrakotoson](https://github.com/Lrakotoson) in [#1383](https://github.com/huggingface/smolagents/pull/1383)
*   Fix [@tool](https://github.com/tool) decorator for remote Python executor by [@tobiasofsn](https://github.com/tobiasofsn) in [#1334](https://github.com/huggingface/smolagents/pull/1334)
*   Always pass add_generation_prompt=True to apply_chat_template by [@albertvillanova](https://github.com/albertvillanova) in [#1416](https://github.com/huggingface/smolagents/pull/1416)

Documentation Improvements 📚
-----------------------------

*   Make docs neutral about agent types by [@julien-c](https://github.com/julien-c) in [#1376](https://github.com/huggingface/smolagents/pull/1376)
*   Add MCP tools doc section by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1394](https://github.com/huggingface/smolagents/pull/1394)
*   Update ToolCollection.from_mcp docstring examples by [@neonwatty](https://github.com/neonwatty) in [#1398](https://github.com/huggingface/smolagents/pull/1398)
*   Document better final_answer_checks by [@albertvillanova](https://github.com/albertvillanova) in [#1407](https://github.com/huggingface/smolagents/pull/1407)
*   Fix typo in secure code execution documentation by [@chahn](https://github.com/chahn) in [#1414](https://github.com/huggingface/smolagents/pull/1414)
*   Add chat server demo to examples by [@albertvillanova](https://github.com/albertvillanova) in [#1415](https://github.com/huggingface/smolagents/pull/1415)
*   Fix VLM model in web_browser example docs by [@albertvillanova](https://github.com/albertvillanova) in [#1424](https://github.com/huggingface/smolagents/pull/1424)
*   Fix ValueError on Guided Tour docs by [@albertvillanova](https://github.com/albertvillanova) in [#1425](https://github.com/huggingface/smolagents/pull/1425)
*   Explain agent types better in Guided tour docs by [@albertvillanova](https://github.com/albertvillanova) in [#1426](https://github.com/huggingface/smolagents/pull/1426)
*   Add Quickstart page to docs by [@albertvillanova](https://github.com/albertvillanova) in [#1413](https://github.com/huggingface/smolagents/pull/1413)

Maintenance 🏗️
---------------

*   Bump dev version: v1.18.0.dev0 by [@albertvillanova](https://github.com/albertvillanova) in [#1390](https://github.com/huggingface/smolagents/pull/1390)

New Contributors
----------------

*   [@Lrakotoson](https://github.com/Lrakotoson) made their first contribution in [#1383](https://github.com/huggingface/smolagents/pull/1383)
*   [@neonwatty](https://github.com/neonwatty) made their first contribution in [#1398](https://github.com/huggingface/smolagents/pull/1398)
*   [@SrzStephen](https://github.com/SrzStephen) made their first contribution in [#1403](https://github.com/huggingface/smolagents/pull/1403)
*   [@chahn](https://github.com/chahn) made their first contribution in [#1414](https://github.com/huggingface/smolagents/pull/1414)

**Full Changelog**: [v1.17.0...v1.18.0](https://github.com/huggingface/smolagents/compare/v1.17.0...v1.18.0)
```

### v1.17.0
- Full Changelog: [v1.16.1...v1.17.0](https://github.com/huggingface/smolagents/compare/v1.16.1...v1.17.0)
```
Title: Release v1.17.0 · huggingface/smolagents

URL Source: https://github.com/huggingface/smolagents/releases/tag/v1.17.0

Markdown Content:
New Features ✨
--------------

*   **Structured Generation in CodeAgent**: Add optional support for structured outputs in `CodeAgent`, enabling more reliable and consistent generation patterns
    *   Adding optional structured generation to CodeAgent by [@akseljoonas](https://github.com/akseljoonas) in [#1346](https://github.com/huggingface/smolagents/pull/1346)

*   **Support for Streamable HTTP MCP Servers**: Expand compatibility with new server types to support streamable HTTP MCP implementations
    *   Support Streamable HTTP MCP servers by [@albertvillanova](https://github.com/albertvillanova) in [#1384](https://github.com/huggingface/smolagents/pull/1384)

*   **Run Results from `Agent.run()`**: The `Agent.run()` method can now return a `RunResult` object, providing richer metadata on agent execution
    *   Agent.run() can return RunResult object by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1337](https://github.com/huggingface/smolagents/pull/1337)

Security Enhancements 🔒
------------------------

*   **Safer LocalPythonExecutor**: Prevent indirect submodule access via attribute resolution, mitigating potential security risks in user-defined code
    *   Prevent submodules through indirect attribute access in LocalPythonExecutor by [@albertvillanova](https://github.com/albertvillanova) in [#1375](https://github.com/huggingface/smolagents/pull/1375)

Enhancements 🛠️
----------------

*   **LocalPythonExecutor Enhancements**:
    *   Support annotated assignments within class definition in LocalPythonExecutor by [@albertvillanova](https://github.com/albertvillanova) in [#1355](https://github.com/huggingface/smolagents/pull/1355)
    *   Fix evaluate_class_def for Assign Attribute target in LocalPythonExecutor by [@albertvillanova](https://github.com/albertvillanova) in [#1357](https://github.com/huggingface/smolagents/pull/1357)
    *   Support 'pass' statement in class definition in LocalPythonExecutor by [@albertvillanova](https://github.com/albertvillanova) in [#1358](https://github.com/huggingface/smolagents/pull/1358)
    *   Refactor tests of LocalPythonExecutor by [@albertvillanova](https://github.com/albertvillanova) in [#1356](https://github.com/huggingface/smolagents/pull/1356)

*   Improve LaTeX rendering in GradioUI with extended delimiter support by [@albertvillanova](https://github.com/albertvillanova) in [#1387](https://github.com/huggingface/smolagents/pull/1387)

Bug Fixes 🐛
------------

*   **Streaming fixes**
    *   Fix live streaming when generating planning steps by [@FlorianVal](https://github.com/FlorianVal) in [#1348](https://github.com/huggingface/smolagents/pull/1348)
    *   Stop streaming if LiteLLM provide a finish_reason by [@FlorianVal](https://github.com/FlorianVal) in [#1350](https://github.com/huggingface/smolagents/pull/1350)
    *   add api_base and api_keys to preparation of kwargs for generate stream by [@FlorianVal](https://github.com/FlorianVal) in [#1344](https://github.com/huggingface/smolagents/pull/1344)

*   Fix WebSearchTool validation error by [@albertvillanova](https://github.com/albertvillanova) in [#1367](https://github.com/huggingface/smolagents/pull/1367)
*   Fix smolagents benchmark by [@aymeric-roucher](https://github.com/aymeric-roucher) in [#1377](https://github.com/huggingface/smolagents/pull/1377)

Documentation Improvements 📚
-----------------------------

*   Add example docs about using OpenRouter models by [@albertvillanova](https://github.com/albertvillanova) in [#1364](https://github.com/huggingface/smolagents/pull/1364)
*   Fix Llama model name in docs example by [@SaiDunoyer](https://github.com/SaiDunoyer) in [#1379](https://github.com/huggingface/smolagents/pull/1379)
*   fix typo in docstring in mcp_client.py by [@grll](https://github.com/grll) in [#1380](https://github.com/huggingface/smolagents/pull/1380)
*   Document use_structured_outputs_internally with version added by [@albertvillanova](https://github.com/albertvillanova) in [#1388](https://github.com/huggingface/smolagents/pull/1388)
*   Fix rendering of version added in docs by [@albertvillanova](https://github.com/albertvillanova) in [#1389](https://github.com/huggingface/smolagents/pull/1389)
*   Fix broken link in agentic RAG examples page by [@vksx](https://github.com/vksx) in [#1363](https://github.com/huggingface/smolagents/pull/1363)

Maintenance 🏗️
---------------

*   Bump dev version: v1.17.0.dev0 by [@albertvillanova](https://github.com/albertvillanova) in [#1336](https://github.com/huggingface/smolagents/pull/1336)
*   Remove deprecated from_hf_api methods by [@albertvillanova](https://github.com/albertvillanova) in [#1351](https://github.com/huggingface/smolagents/pull/1351)

New Contributors
----------------

*   [@FlorianVal](https://github.com/FlorianVal) made their first contribution in [#1344](https://github.com/huggingface/smolagents/pull/1344)
*   [@vksx](https://github.com/vksx) made their first contribution in [#1363](https://github.com/huggingface/smolagents/pull/1363)
*   [@akseljoonas](https://github.com/akseljoonas) made their first contribution in [#1346](https://github.com/huggingface/smolagents/pull/1346)
*   [@SaiDunoyer](https://github.com/SaiDunoyer) made their first contribution in [#1379](https://github.com/huggingface/smolagents/pull/1379)

**Full Changelog**: [v1.16.1...v1.17.0](https://github.com/huggingface/smolagents/compare/v1.16.1...v1.17.0)
```

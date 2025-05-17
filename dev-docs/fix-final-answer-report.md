# fix-final-answer-report

**修复 codact 模式下 "Final Formatted Output:" 与标准正确的 react 模式的"Final Markdown Output:" CLI 输出 final_answer_report markdown 渲染效果进行统一对齐**
1. final_answer_report markdown 渲染: 统一按照 ReAct Agent final_answer_repor 的 markdown 渲染效果去渲染;
2. sources_URL_list 渲染: 统一在 markdown 正文最后部分总是以 Markdown URL 引用的语法`1. [标题](URL);` 列出引用 URL 来源的列表,CLI 的 markdown 渲染时在 final_answer_report 渲染最下方嵌入 sources_URL_list 的引用来源格式的内容块. (可能需要修改&统一两种 Agent 输出时使用 FinalAnswerTool 的结构化格式 json schema & Prompts 里的FinalAnswer部分需要利用 src/smolagents/agents.py `PromptTemplates` 的`FinalAnswerPromptTemplate(TypedDict))` 以使得 `src/agents/tools/__init__.p`y src/smolagents/default_tools.py `class FinalAnswerTool(Tool)` 使用"The final answer to the problem"正确处理 "final answer report Prompt"以 JSON 模式(json schema)构造结构化输出要求的LLM请求,
3. 注意: FinalAnswerTool 的FinalAnswerPrompt构造& final_answer_report 的 json schema 解析输出最终待 CLI 渲染的 final_answer_report 正文和sources_URL_list 应该在 Agents 的 LLM FinalAnswerTool --> output final_answer Action 响应的 JSON 解析处理逻辑中进行统一实现, 而不是在 CLI, CLI 只负责接受 final_answer_report 和 sources_URL_list 的Markdown 块的优雅的 TUI 渲染.

其他 src/smolagents/agents.py CodeAgent&ToolCallingAgent 基类接口源码中可以利用来辅助实现上述需求的可扩展参数:

- `tool_parser` (`Callable`, *optional*): Function used to parse the tool calls from the LLM output.
- `final_answer_checks` (`list`, *optional*): List of Callables to run before returning a final answer for checking validity.

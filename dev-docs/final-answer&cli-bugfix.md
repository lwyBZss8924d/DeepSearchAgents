# DeepSearchAgents 技术实现笔记 - final-answer&cli-bugfix经验记录

## 问题背景

在DeepSearchAgents项目中，我们遇到了流式输出模式（Streaming Mode）下的几个关键问题：

1. 在CLI界面中，任务描述（"New run"）重复显示
2. JSON格式化输出在流式模式下无法正确渲染
3. Markdown格式内容未能正确识别和渲染
4. 工具调用处理在流式输出中不稳定

## 解决方案概述

### 1. 任务重复显示问题

- 在`StreamingReactAgent`和`StreamingCodeAgent`类中添加`task_displayed`标志
- 在CLI代码中提前设置该标志，阻止重复显示任务描述

### 2. JSON和Markdown输出渲染问题

- 改进`StreamingAgentMixin`中对流数据的处理
- 增强CLI代码中的格式检测和渲染逻辑
- 添加对特殊格式（如Final Answer块）的检测和处理

### 3. 工具调用处理增强

- 改进`_convert_stream_to_iterator`方法对各种流格式的处理能力
- 统一处理tool_calls和tool_call属性

## 详细实现记录

### StreamingAgentMixin改进

在`streaming_agents.py`文件中，我们对`StreamingAgentMixin`类的`_convert_stream_to_iterator`方法进行了改进：

```python
def _convert_stream_to_iterator(
    self, 
    stream_obj: Any
) -> Iterator[StepsAndFinalAnswerStreamingData]:
    """
    Convert a streaming object to an iterator of text chunks.
    
    Args:
        stream_obj: The streaming object to convert
        
    Returns:
        An iterator of StepsAndFinalAnswerStreamingData objects
    """
    # 添加对各种流格式的统一处理
    # 统一处理 tool_calls 和 tool_call 属性
    tool_calls = None
    # 先检查 tool_calls (复数)
    if (hasattr(stream, "tool_calls") and 
            not hasattr(stream, "content")):
        tool_calls = stream.tool_calls
    # 再检查 tool_call (单数)
    elif (hasattr(stream, "tool_call") and 
         not hasattr(stream, "content")):
        tool_calls = [stream.tool_call]
        
    if tool_calls:
        # 创建一个带有 tool_calls 文本表示的内容
        tool_calls_text = str(tool_calls)
        content = f"[Tool Calls: {tool_calls_text}]"
        
        return iter([
            StepsAndFinalAnswerStreamingData(
                step=step,
                text_chunk=content,
                full_text=content
            )
        ])
```

### StreamingReactAgent和StreamingCodeAgent改进

在这两个类中添加了`task_displayed`标志，防止任务描述重复显示：

```python
class StreamingReactAgent(ToolCallingAgent, StreamingAgentMixin):
    def __init__(self, **kwargs):
        # ...前面的代码...
        self.task_displayed = False  # 添加标志，跟踪任务是否已显示
    
    def run(self, task: str, stream: bool = False, **kwargs):
        # 设置标记，表明任务已经在CLI中显示，以避免重复显示
        self.task_displayed = True
        # ...后面的代码...
```

类似地，在`StreamingCodeAgent`中也添加了相同的标志：

```python
class StreamingCodeAgent(CodeAgent, StreamingAgentMixin):
    def __init__(self, **kwargs):
        # ...前面的代码...
        self.task_displayed = False  # 添加标志，跟踪任务是否已显示
    
    def run(self, task: str, stream: bool = False, **kwargs):
        # 设置标志，防止重复显示
        self.task_displayed = True
        # ...后面的代码...
```

### CLI渲染逻辑改进

在`cli.py`的`process_query_async`函数中，我们添加了对`task_displayed`属性的检查和设置：

```python
# 集中处理task_displayed逻辑 - 提前设置标识，防止重复显示任务
# 如果agent对象有task_displayed属性，设置为True (这适用于StreamingReactAgent和StreamingCodeAgent)
if hasattr(agent_instance, 'task_displayed'):
    agent_instance.task_displayed = True

# 在函数中也保持一个标志，确保本地显示控制也有相同设置
task_displayed = True
```

同时，在处理流式输出的代码中，添加了避免重复显示"New run"的逻辑：

```python
# 避免重复显示"New run"
if not task_displayed and collected_text:
    task_displayed = True
    
    # 显示任务请求
    task_panel = Panel(
        Text(query),
        title="[bold blue]Task Request[/bold blue]",
        border_style="blue",
        expand=True
    )
    live_display.update(task_panel)
    # 暂停一下让用户看到任务
    await asyncio.sleep(0.5)
```

### JSON结构化输出和Markdown格式检测

增强了CLI中对JSON和Markdown格式的检测与渲染：

```python
# 检查是否出现了Markdown报告特定的格式标记
is_markdown_report = False
if collected_text and (
    "# " in collected_text or 
    "## " in collected_text or
    "```" in collected_text
):
    is_markdown_report = True

# 尝试解析JSON结构化输出
try:
    # Check if it's a JSON structure
    if (collected_text.strip().startswith('{') and 
        collected_text.strip().endswith('}')):
        try:
            json_data = json.loads(collected_text)
            # If successful JSON parsing
            if (isinstance(json_data, dict) and 
                'title' in json_data and 
                'content' in json_data):
                # 创建可视化面板展示结构化数据
                # ...
        except json.JSONDecodeError:
            # Not a complete JSON, continue with regular display
            pass
except Exception:
    # JSON processing error, ignore and continue with regular display
    pass
```

### 最终答案块检测与提取

添加了对Final Answer特殊格式块的检测与内容提取：

```python
# 检查是否有特殊格式的块（React模式下的Final Answer）
if (isinstance(chunk, str) and 
    chunk.startswith("\n<Final Answer>\n") and 
    "</Final Answer>" in chunk):
    # 这是React模式下的最终答案块，需要提取内容
    final_answer_content = (
        chunk.split("\n<Final Answer>\n")[1]
        .split("\n</Final Answer>")[0]
    )
    # 更新收集的文本
    collected_text = final_answer_content
    content = final_answer_content
elif (isinstance(chunk, str) and 
     chunk.startswith("<Final Answer>") and 
     "</Final Answer>" in chunk):
    # 另一种可能的格式
    final_answer_content = (
        chunk.split("<Final Answer>")[1]
        .split("</Final Answer>")[0]
    )
    collected_text = final_answer_content
    content = final_answer_content
```

## 总结与经验教训

1. **输出标志统一管理**: 在流式输出中，需要在多个层次（Agent类和CLI处理）中统一管理显示状态标志
2. **结构化数据检测**: 在流式输出中需要不断检测累积文本是否形成了完整的结构（JSON/Markdown）
3. **多重格式兼容**: 需要处理多种可能的流数据格式和特殊标记
4. **错误处理增强**: 在流式处理过程中需要更强的错误捕获和恢复机制

这些改进使得DeepSearchAgent能够在流式输出模式下提供更一致、更友好的用户体验，特别是对于复杂的结构化输出内容

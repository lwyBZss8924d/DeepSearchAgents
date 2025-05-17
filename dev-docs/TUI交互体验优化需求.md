## TUI交互体验优化需求

改进DeepSearchAgent的TUI界面以区分不同Agent动作类型和状态。分析是否以下几个是可以优化的方向：

### 当前实现分析

1. **Emoji定义与使用流程**:
   - `codact_prompts.py`和`react_prompts.py`中定义了相同的Emoji常量
   - 这些Emoji通过格式化字符串插入到系统提示中(`{0}`, `{1}`等)
   - `cli.py`中直接定义了一组相同的Emoji用于界面显示，而不是引用prompt文件中的定义

2. **状态检测机制**:
   - `cli.py`中的`detect_operation_type`根据消息内容判断当前操作类型
   - `update_progress_status`负责更新进度条显示

3. **工具调用拦截**:
   - 两种Agent执行工具调用时的拦截方式不同:
     - ReAct: 拦截`_run_tool`方法
     - CodeAct: 通过正则表达式识别Python代码中的函数调用(还应该拦截 log&print 进行定制化文本高亮或字体的的 TUI 显示)

### 优化

1. **统一Emoji定义源**:
```python
# 创建一个共享的constants.py文件
from typing import Dict, Any

# Agent状态Emoji
AGENT_EMOJIS = {
    "thinking": "🤔",
    "planning": "📝",
    "replanning": "🔄",
    "action": "⚙️",
    "final": "✅",
    "error": "❌"
}

# 工具图标
TOOL_ICONS = {
    "search_links": "🔍",  # 搜索
    "read_url": "📄",      # 阅读URL
    "chunk_text": "✂️",    # 文本分块
    "embed_texts": "🧩",   # 嵌入文本
    "rerank_texts": "🏆",  # 重新排序
    "wolfram": "🧮",       # 计算
    "final_answer": "✅"   # 最终答案
}

# 然后在各文件中导入这个模块而不是重复定义
```

2. **增强工具执行状态可视化**:
```python
def show_tool_execution(tool_name, args, spinner_style="dots"):
    """显示工具执行状态,支持动画效果"""
    icon, color = get_tool_display_info(tool_name)
    with Progress(
        SpinnerColumn(spinner_name=spinner_style),
        TextColumn(f"[{color}]{icon} 正在执行 {tool_name}...[/{color}]"),
        TimeElapsedColumn(),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("", total=None)
        yield progress, task  # 使用生成器模式允许在执行期间更新进度
```

3. **代码执行的可视化增强**:
```python
def enhance_code_execution_display(code_block, tool_match):
    """增强代码执行的显示效果"""
    # 语法高亮
    highlighted_code = Syntax(code_block, "python", theme="monokai")

    # 工具调用突出显示
    if tool_match:
        tool_name = tool_match.group(1)
        icon, color = get_tool_display_info(tool_name)
        console.print(f"[{color}]{icon} 执行工具: {tool_name}[/{color}]")

    # 显示执行中状态
    console.print(Panel(
        highlighted_code,
        title="[bold blue]执行代码中...[/bold blue]",
        border_style="blue"
    ))
```

4. **执行状态区分**:
```python
# 区分ReAct和CodeAct的执行状态显示
def update_agent_status(agent_type, operation_type, tool_name=None):
    """根据代理类型和操作类型更新状态显示"""
    if agent_type == "react":
        # ReAct特定的状态显示
        if operation_type == "action":
            return f"[bold cyan]⚙️ ReAct执行工具调用: {tool_name or '未知'}[/bold cyan]"
    elif agent_type == "codact":
        # CodeAct特定的状态显示
        if operation_type == "action":
            return f"[bold green]💻 CodeAct执行代码: {tool_name or '代码块'}[/bold green]"

    # 通用状态显示
    emojis = {
        "thinking": "🤔", # 普通的 React 模式Agent 除了 Planing&更新 Planing 以及final answer 时都是 thinking
        "thinking & coding" "?" #CodeAgent 除了 Planing&更新 Planing&final answer 时都是 thinking & coding 需要设计
        "planning": "📝", # 两种Agent模式共用
        "replanning": "🔄", # 两种Agent模式共用
        "final_answer": "✅" # 两种Agent模式共用
    }
    return f"[bold blue]{emojis.get(operation_type, '⏳')} {operation_type.capitalize()}[/bold blue]"
```

5. **观察者模式增强**:
```python
class AgentObserver:
    """代理观察者,用于监控和显示代理状态变化"""
    def __init__(self, console, agent_type):
        self.console = console
        self.agent_type = agent_type
        self.current_state = "init"
        self.steps_count = 0
        self.tools_used = set()

    def on_state_change(self, new_state, context=None):
        """处理状态变化"""
        self.current_state = new_state
        self.steps_count += 1

        # 根据状态类型显示不同的UI
        if new_state == "tool_call":
            tool_name = context.get("tool_name", "未知工具")
            self.tools_used.add(tool_name)
            icon, color = get_tool_display_info(tool_name)

            # 不同代理类型的显示差异
            if self.agent_type == "react":
                self.console.print(f"[{color}]{icon} ReAct调用工具: {tool_name}[/{color}]")
            else:
                self.console.print(f"[{color}]{icon} CodeAct执行工具: {tool_name}[/{color}]")
```

### 目标: CLI 更优雅,清晰的 DeepSearch Agent 自主多步骤深度搜索的执行过程(LLM 输出等待中/LLM-Agent-不同的 Action 等待中)的完成透明给用户展示 &开发者遥测

为了让用户更好地观察两种Agent的动作区别，目标`cli.py`中实现以下增强：

1. **区分代理类型的视觉风格**:
   - ReAct: 使用蓝色主题和JSON图标
   - CodeAct: 使用绿色主题和代码图标

2. **增强工具调用显示**:
   - 可折叠的工具参数和结果面板
   - 工具执行时间统计
   - 动态进度指示

3. **代码执行增强**:
   - 代码块语法高亮
   - 执行结果与代码的视觉分离
   - 变量状态显示

更清晰地观察两种Agent模式的不同工作方式，特别是在执行复杂的多步骤任务时。

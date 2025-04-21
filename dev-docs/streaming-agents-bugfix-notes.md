# DeepSearchAgents 技术实现笔记 - 流式代理修复

`{{May 15th, 2023}}`

重要经验:

- MUST use English for all code comments.
- Code style note: comments & Print content & Prompt MUST use English.

## 流式代理执行问题修复

### 问题分析

在实现 StreamingCodeAgent 和 StreamingReactAgent 时，我们发现以下关键问题：

1. 工具函数无法在 Python 执行器中识别:
   ```
   InterpreterError: Forbidden function evaluation: 'search_links' is 
   not among the explicitly allowed tools
   ```

2. 授权导入配置失效:
   ```
   InterpreterError: Import of requests is not allowed. Authorized imports are: 
   ['stat', 'collections', 'json', ...]
   ```

3. 类型导入不完整:
   ```
   NameError: name 'ActionStep' is not defined
   ```

根本原因是在重构流式代理代码时，我们注重了消息流处理逻辑，但忽略了 CodeAgent 中 Python 执行环境的初始化步骤，导致工具函数没有正确传递给执行器。

### 解决方案

1. **添加必要的类型导入**:
   ```python
   from smolagents import (
       CodeAgent, ToolCallingAgent, MessageRole,
       FinalAnswerStep, LogLevel
   )
   from smolagents.memory import TaskStep, ActionStep  # Add ActionStep import
   from smolagents.agents import populate_template
   from .streaming_models import StreamingLiteLLMModel
   ```

2. **实现通用工具初始化方法**:
   ```python
   class StreamingAgentMixin:
       """Streaming agent mixin class that provides common streaming functionality."""
       
       # Other methods...
       
       def _setup_executor_environment(self):
           """Ensure the execution environment is correctly set up"""
           if hasattr(self, "python_executor"):
               self.python_executor.send_variables(variables=self.state)
               self.python_executor.send_tools(
                   {**self.tools, **self.managed_agents}
               )
   ```

3. **在代理执行步骤中检查工具状态**:
   ```python
   def _execute_step(self, task: str, memory_step: ActionStep) -> Union[None, Any]:
       """Override execute step method to ensure tools are available"""
       # Ensure python executor is correctly set
       if hasattr(self, "python_executor"):
           # Check if tools have been sent, if not send them
           if not getattr(self.python_executor, "_tools_sent", False):
               self.python_executor.send_tools({**self.tools, **self.managed_agents})
               setattr(self.python_executor, "_tools_sent", True)
       
       # Call parent class execute method
       return super()._execute_step(task, memory_step)
   ```

4. **在代理初始化时确保环境设置**:
   ```python
   # 更新codact_agent.py中的代码
   
   # Initialize agent state
   streaming_agent.state.update(initial_state)

   # Ensure execution environment is correctly set up
   streaming_agent._setup_executor_environment()
   ```

5. **在代理运行时确保环境初始化**:
   ```python
   def run(self, task: str, stream: bool = False, ...):
       # Initialize execution environment
       self._setup_executor_environment()
       
       # If non-streaming mode, use parent class run method
       if not stream:
           return super().run(...)
           
       # Rest of streaming implementation...
   ```

## 工具传递机制详解

在 smolagents 框架中，CodeAgent 使用 Python 执行器运行代码。要使工具函数在代码中可用，必须将它们传递给执行器：

1. **工具传递流程**:
   ```
   CodeAgent.__init__() -> create_python_executor() 
       -> 创建执行器但不传递工具
   CodeAgent.run() -> 传递状态变量和工具 
       -> python_executor.send_variables() & python_executor.send_tools()
   ```

2. **实际执行过程**:
   ```
   CodeAgent._run() -> 遍历执行步骤
   CodeAgent._execute_step() -> 处理单个步骤
   CodeAgent.step() -> 调用 python_executor() 执行代码
   ```

3. **关键问题**: 在流式实现中，我们需要确保:
   - 在执行任何代码前工具已传递给执行器
   - 状态变量也正确传递
   - 避免重复传递导致的性能问题

## 经验与最佳实践

1. **工具初始化时机**:
   - 最佳做法是在代理 `run()` 方法最开始就初始化执行环境
   - 添加状态检查避免重复初始化
   - 在 `_execute_step()` 中增加额外检查作为保障

2. **类型导入重要性**:
   - 总是检查所有需要的类型是否导入
   - 特别是像 ActionStep 这样的参数类型，缺少会导致运行时错误

3. **Mixin 设计模式使用**:
   - 将公共功能抽象到 Mixin 类中
   - 确保 Mixin 方法不依赖特定的初始化顺序
   - 使用可选访问模式，检查属性是否存在

4. **错误处理与恢复**:
   - 添加详细的日志，帮助识别问题
   - 提供明确的错误信息，指出问题根源
   - 设计回退机制，在流式模式失败时可切换到非流式模式

5. **测试策略**:
   - 创建专门的测试用例验证工具传递
   - 测试不同的流式场景和错误恢复路径
   - 使用 mock 对象模拟执行器行为
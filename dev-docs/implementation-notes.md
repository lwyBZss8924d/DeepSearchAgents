# DeepSearchAgents 技术实现笔记

## 流式输出实现

### 问题分析

原有代码在以下几个方面存在问题：
1. `StreamingLiteLLMModel.__call__` 方法中 `stream` 参数重复传递
2. `CustomStreamWrapper` 对象无法直接作为 agent.run 的返回值
3. 消息历史构建逻辑不完整

### 解决方案

1. **StreamingLiteLLMModel 修复**:
   ```python
   # 从kwargs中移除stream参数，避免重复传递
   stream_mode = kwargs.pop("stream", False)  
   # 确保只传递一次stream=True参数
   completion_kwargs = self._prepare_completion_kwargs(
       messages=messages,
       # 其他参数
       stream=True,  # 显式设置stream参数
       **kwargs,
   )
   ```

2. **StreamingFinalAnswerWrapper 实现**:
   - 创建 `_convert_stream_to_iterator` 方法处理各种流对象:
   ```python
   def _convert_stream_to_iterator(self, stream_obj):
       try:
           # 尝试直接迭代流对象
           for token in stream_obj:
               yield token
       except (TypeError, AttributeError) as e:
           # 处理不可迭代的流对象
           if hasattr(stream_obj, 'content'):
               yield stream_obj.content
           elif hasattr(stream_obj, 'get_content'):
               yield stream_obj.get_content()
           # 更多回退选项...
   ```
   
   - 简化消息构建逻辑，不再依赖 `write_to_messages()` 方法:
   ```python
   # 创建简单的消息列表用于模型
   messages = [
       {"role": "system", "content": [{"type": "text", "text": "..."}]},
       {"role": "user", "content": [{"type": "text", "text": final_prompt}]}
   ]
   
   # 调用模型获取流式输出并转换为迭代器
   stream_result = self.model(messages, stream=True)
   return self._convert_stream_to_iterator(stream_result)
   ```

## 状态管理实现

### 问题分析

1. 原有代码缺乏结构化状态跟踪
2. ReAct和CodeAct代理状态管理不一致
3. 搜索策略缺乏周期性评估和调整

### 解决方案

1. **统一状态变量定义**:
   ```python
   # ReAct和CodeAct代理统一使用相同的状态变量结构
   initial_state = {
       "visited_urls": set(),        # 已访问的URL
       "search_queries": [],         # 已执行的搜索查询
       "key_findings": {},           # 关键发现，按主题索引
       "search_depth": 0,            # 当前搜索深度
       "reranking_history": [],      # 重排序历史
       "content_quality": {}         # URL内容质量评分
   }
   ```

2. **周期性规划实现**:
   ```python
   # CodeAct代理设置
   search_planning_interval = 5  # 每执行5步重新规划一次
   
   # ReAct代理设置
   react_planning_interval = 7  # ReAct代理的规划间隔略大一些
   
   # 初始化代理时设置规划间隔
   agent = AgentClass(
       # 其他参数
       planning_interval=planning_interval
   )
   ```

3. **状态更新和访问机制**:
   ```python
   # Python代码中安全访问状态变量
   try:
       visited_urls
   except NameError:
       visited_urls = set()
   
   # 访问和更新
   if url not in visited_urls:
       visited_urls.add(url)
   ```

## 日志和错误处理

### 错误处理改进

1. **流式输出异常捕获**:
   ```python
   try:
       stream_result = self.model(messages, stream=True)
       return self._convert_stream_to_iterator(stream_result)
   except Exception as e:
       logger.exception("生成流式最终答案时出错: %s", str(e))
       return f"生成流式最终答案时出错: {str(e)}"
   ```

2. **CLI中的流式显示异常处理**:
   ```python
   try:
       # 尝试直接迭代流对象
       for token in stream_generator:
           # 处理和显示token
   except Exception as e:
       console.print(f"[yellow]获取值时出错: {e}[/yellow]")
   ```

## 配置管理实现

1. **YAML配置加载**:
   ```python
   def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
       load_dotenv()  # 加载.env文件
       # 从文件加载YAML配置
       with open(actual_config_path, 'r') as f:
           yaml_config = yaml.safe_load(f)
       # 验证和设置默认值
       if 'service' not in final_config:
           final_config['service'] = {}
       # 更多验证...
       return final_config
   ```

2. **嵌套配置安全访问**:
   ```python
   def get_config_value(config, key_path, default=None):
       keys = key_path.split('.')
       value = config
       try:
           for key in keys:
               value = value[key]
           return value
       except KeyError:
           return default
   ```

## JSON结构化输出

1. **Grammar定义**:
   ```python
   json_grammar = {
       "json_object": {
           "type": "object",
           "properties": {
               "title": {"type": "string"},
               "content": {"type": "string"},
               "sources": {"type": "array", "items": {"type": "string"}},
               "confidence": {"type": "number"}
           }
       }
   }
   ```

2. **最终答案格式化**:
   ```python
   import json
   
   final_answer(json.dumps({
       "title": "简洁的查询答案",
       "content": "带支持证据的详细解释",
       "sources": ["URL1", "URL2", "URL3"],  # 所查询的来源
       "confidence": 0.85  # 0到1之间的置信度分数
   }, ensure_ascii=False))
   ```

## 多语言支持

1. **提示模板指导**:
   ```
   **ALWAYS use English for search queries.** Regardless of the user's original language, 
   ALWAYS formulate search queries in English for best results.
   
   **Translate to the user's original language in the final answer.** 
   Conduct research in English, but provide the final answer in the user's original language.
   ```

2. **代码中实现**:
   ```python
   # 搜索查询时使用英文
   query = "Microsoft markitdown-mcp document conversion project"
   results_json = search_links(query=query, num_results=10)
   
   # 最终答案时使用用户语言
   final_answer(json.dumps({
       "title": "MarkItDown‑MCP 文档转换 MCP 项目概述及技术实现",  # 中文标题
       "content": "MarkItDown 是微软开源的轻量级 Python 工具...",  # 中文内容
       # 其他字段
   }, ensure_ascii=False))
   ``` 
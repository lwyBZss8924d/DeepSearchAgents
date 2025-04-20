feat(agents): 增强流式输出与状态管理

1. 修复 CodeAct 流式输出错误:
   - 修复 stream 参数重复传递问题
   - 添加 _convert_stream_to_iterator 确保返回标准迭代器

2. 增强代理状态管理:
   - 实现统一状态变量 (visited_urls, search_queries, key_findings)
   - 添加周期性规划支持 (CodeAct 5步, ReAct 7步)
   - 添加 JSON 结构化输出支持

3. 新增配置管理:
   - 添加 config_loader.py 统一配置加载
   - 支持 YAML 配置与环境变量重写
   - 安全访问嵌套配置与API密钥管理

4. 改进命令行界面:
   - 增强流式输出显示
   - 添加状态跟踪与统计显示
   - 改进 JSON 输出可视化

5. 多语言支持:
   - 英文搜索，用户语言输出
   - 多语言提示模板 
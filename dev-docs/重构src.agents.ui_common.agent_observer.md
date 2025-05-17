```
src/agents/
├── __init__.py
├── servers/ # 新增 agent run 相关系统服务组件的目录
│   ├── __init__.py
│   ├── agent_observer.py # 会话管理（原AgentStepObserver）
│   └── agent_callbacks.py # Agent步骤回调（原AgentStepCallback）
└── ui_common/
    ├── __init__.py
    ├── constants.py
    └── console_formatter.py  # UI格式化（原AgentObserver）
```

当前的`agent_observer.py`承担了四项不同职责：

1. **会话管理** - 创建、跟踪和存储执行会话
2. **WebSocket通知** - 向前端广播更新
3. **步骤回调处理** - 与smolagents.memory集成
4. **UI格式化** - 终端展示和Rich格式化

这违反了**单一职责原则**，增加了维护难度和理解成本。

## 具体实现建议

### 1. agent_observer.py
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/servers/agent_observer.py

"""
Agent Session Manager
负责创建、存储和管理Agent执行会话及其状态
提供API以记录执行步骤、最终结果和错误
"""

import json
import time
import uuid
import logging
import threading
import asyncio
from typing import Dict, Any, Optional, Union

# 会话管理的核心功能
# 原AgentStepObserver中的会话管理和WebSocket通知逻辑
```

### 2. agent_callbacks.py
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/agent_callbacks.py
# ⚠️注意: 实现时注意所有代码注释要统一为 EN

"""
Agent步骤回调处理
为smolagents.memory提供回调接口
记录Agent执行过程中的步骤、结果和错误
"""

from smolagents.memory import (
    ActionStep, PlanningStep, TaskStep, SystemPromptStep
)
from .session_manager import session_manager  # 引用新的会话管理器
```

### 3. console_formatter.py
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/console_formatter.py
# ⚠️注意: 实现时注意所有代码注释要统一为 EN

"""
Agent步骤UI格式化
将Agent执行步骤格式化为Rich组件
提供终端友好的展示和日志
"""

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table

from .constants import (
    THINKING_EMOJI, PLANNING_EMOJI, ACTION_EMOJI, FINAL_EMOJI,
    CODE_EXECUTION_EMOJI,
    THINKING_COLOR, PLANNING_COLOR, ACTION_COLOR, FINAL_COLOR,
    CODE_EXECUTION_COLOR, TOOL_ICONS
)

# 原AgentObserver的UI格式化逻辑
```

1. **更清晰的职责划分**：
   - 会话管理独立处理状态存储
   - 回调函数专注于smolagents集成
   - UI格式化仅关注终端展示

2. **更好的可测试性**：
   - 每个组件都可以单独测试
   - 模拟前端测试不再需要了解UI格式化细节

3. **更易于维护**：
   - 错误更容易定位
   - 功能扩展不会影响其他部分

4. **减少循环依赖**：
   - 移除文件间的隐性依赖
   - 遵循更清晰的依赖方向

创建新文件，逐步迁移现有功能，保持兼容性，确保WebSocket通知和代理步骤观察功能正常工作。这样可以最小化重构风险。
修改后的`src/agents/__init__.py`应该导出新的模块，确保API兼容性：

```python
from .servers.agent_observer import AgentStepObserver
from .servers.agent_callbacks import AgentStepCallback

__all__ = [
    "agent_runtime",
    "AgentStepObserver",
    "AgentStepCallback"
]
```

同时检查原有 `src/agents/ui_common/agent_observer.py` 所有旧的导入导出路径确保拆分后正确.

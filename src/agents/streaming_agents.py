"""
流式输出的智能代理实现，扩展 smolagents 的代理类。
"""
import logging
import textwrap
from typing import Dict, List, Optional, Union, Iterator, Callable

from smolagents import (
    CodeAgent, ToolCallingAgent, MessageRole, 
    FinalAnswerStep, LogLevel
)
from smolagents.agents import populate_template
from smolagents.memory import TaskStep
from .streaming_models import StreamingLiteLLMModel

logger = logging.getLogger(__name__)


class StreamingCodeAgent(CodeAgent):
    """扩展的 CodeAgent 类，支持流式输出最终答案。

    与标准 CodeAgent 的主要区别是，当以 stream=True 调用 run 方法时，
    此代理会正常执行所有步骤，但最终答案生成会使用 LiteLLM 的流式输出，
    使最终答案逐个标记返回，而不是一次性返回完整答案。

    Args:
        tools (List[Tool]): 代理可使用的工具
        model (StreamingLiteLLMModel): 生成代理行为的模型
        prompt_templates (Dict, 可选): 提示模板
        grammar (Dict[str, str], 可选): 解析 LLM 输出的语法
        additional_authorized_imports (List[str], 可选): 额外授权的导入
        planning_interval (int, 可选): 代理运行计划步骤的间隔
        executor_type (str, 默认 "local"): 执行器类型
        executor_kwargs (Dict, 可选): 传递给执行器的额外参数
        max_print_outputs_length (int, 可选): 打印输出的最大长度
        **kwargs: 传递给父类的其他参数
    """

    def run(
        self,
        task: str,
        stream: bool = False,
        reset: bool = True,
        images: Optional[List] = None,
        additional_args: Optional[Dict] = None,
        max_steps: Optional[int] = None,
    ) -> Union[str, Iterator[str]]:
        """运行代理处理指定任务，支持流式输出或标准输出。

        Args:
            task (str): 要执行的任务
            stream (bool): 是否以流式模式运行
                如为 True，最终答案将以流式方式返回
                如为 False，执行所有步骤并返回最终答案字符串
            reset (bool): 是否重置对话或从上一次运行继续
            images (List, 可选): 图像对象
            additional_args (Dict, 可选): 其他传递给代理运行的变量
            max_steps (int, 可选): 代理可执行的最大步骤数

        Returns:
            Union[str, Iterator[str]]: 如为流式模式，返回最终答案流；
                                    否则返回最终答案字符串
        """
        # 如果非流式模式，使用父类的运行方法
        if not stream:
            return super().run(
                task=task,
                stream=False,  # 确保传递 False 以遵循常规流程
                reset=reset,
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

        # 保存任务并设置最大步骤
        max_steps = max_steps or self.max_steps
        self.task = task
        self.interrupt_switch = False

        # 初始化附加参数（如果有）
        if additional_args is not None:
            self.state.update(additional_args)
            additional_args_str = str(additional_args)
            self.task += textwrap.dedent(f"""
                You have been provided with these additional arguments: 
                {additional_args_str}.""")

        # 初始化并重置系统提示和内存（如果需要）
        self.system_prompt = self.initialize_system_prompt()
        self.memory.system_prompt.system_prompt = self.system_prompt
        if reset:
            self.memory.reset()
            self.monitor.reset()

        # 记录任务信息
        model_id = (
            self.model.model_id 
            if hasattr(self.model, 'model_id') 
            else ''
        )
        self.logger.log_task(
            content=self.task.strip(),
            subtitle=f"{type(self.model).__name__} - {model_id}",
            level=LogLevel.INFO,
            title=self.name if hasattr(self, "name") else None,
        )
        self.memory.steps.append(TaskStep(task=self.task, task_images=images))

        # 检查模型是否支持流式输出
        if not isinstance(self.model, StreamingLiteLLMModel):
            logger.warning(
                "流式模式需要 StreamingLiteLLMModel，但当前使用的是 %s。"
                "将以非流式模式继续执行。", 
                type(self.model).__name__
            )
            return super().run(
                task=task,
                stream=False,
                reset=False,  # 因为已经在上面重置过了
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

        # 保存任务和图像以供处理
        self.task = task
        self.task_images = images

        # 执行主要的执行逻辑
        final_step = None
        step_counter = 0

        # 执行代理步骤直到找到最终答案
        for step in self._run(task=self.task, max_steps=max_steps, images=images):
            # 添加步骤到内存并递增计数器
            self.memory.steps.append(step)
            step_counter += 1

            # 检查是否为最终答案步骤
            if isinstance(step, FinalAnswerStep):
                final_step = step
                break

        # 如果找到最终答案，获取答案文本
        if final_step is not None:
            final_answer = final_step.final_answer
        else:
            # 如果没有找到但执行了一些步骤，则生成最终答案
            if step_counter > 0:
                # 准备提示和消息
                final_prompt = self.prompt_templates["final_answer"]
                post_msg = populate_template(
                    final_prompt["post_messages"],
                    variables={"task": task}
                )

                # 构建消息列表
                messages = self.memory.write_to_messages()
                messages.append(
                    {
                        "role": MessageRole.USER,
                        "content": [{"type": "text", "text": post_msg}],
                    }
                )
                # 为流式输出和最终答案调用模型
                final_answer = self.model(messages, stream=True)
            else:
                # 如果没有执行任何步骤，返回错误消息
                return "代理未能执行任何步骤。请检查配置和提示。"

        # 返回流式输出或字符串结果
        return final_answer


class StreamingReactAgent(ToolCallingAgent):
    """扩展的 ToolCallingAgent 类，支持流式输出所有步骤和最终答案。

    与标准 ToolCallingAgent 的主要区别是，在以 stream=True 调用 run 方法时，
    此代理会流式输出所有的思考步骤和最终答案，而不是仅在最后输出最终答案。
    
    此版本修复了之前的错误，确保提供所有必要的模板。

    Args:
        tools (List[Tool]): 代理可使用的工具
        model (StreamingLiteLLMModel): 生成代理行为的模型
        prompt_templates (Dict, 可选): 提示模板
        max_steps (int, 默认 20): 代理可执行的最大步骤数
        add_base_tools (bool, 默认 False): 是否添加基础工具
        verbosity_level (LogLevel, 默认 LogLevel.INFO): 代理日志的详细级别
        grammar (Dict[str, str], 可选): 解析 LLM 输出的语法
        managed_agents (List, 可选): 代理可以调用的受管代理
        step_callbacks (List[Callable], 可选): 每步完成时调用的回调
        planning_interval (int, 可选): 代理运行计划步骤的间隔
        **kwargs: 其他参数
    """

    def __init__(
        self,
        tools: List,
        model,
        prompt_templates: Optional[Dict] = None,
        max_steps: int = 20,
        add_base_tools: bool = False,
        verbosity_level=LogLevel.INFO,
        grammar: Optional[Dict[str, str]] = None,
        managed_agents=None,
        step_callbacks: Optional[List[Callable]] = None,
        planning_interval: Optional[int] = None,
        **kwargs,
    ):
        """初始化 StreamingReactAgent 实例。
        
        在初始化时确保提供所有必要的提示模板。
        """
        # 确保所有必要的模板在初始化时就准备好
        # 首先保存原始模板（如果有）
        original_templates = prompt_templates or {}
        
        # 创建一个包含所有必要模板的新字典
        complete_templates = {
            # 基本的提示模板，如果用户提供则使用用户的，否则使用默认值
            "planning": {
                "initial_plan": original_templates.get("planning", {}).get(
                    "initial_plan", 
                    "Based on the task, create a plan to search and gather information.\n\n{{task}}\n\n<end_plan>"
                ),
                "update_plan_pre_messages": original_templates.get("planning", {}).get(
                    "update_plan_pre_messages", 
                    "Review your progress and update your plan."
                ),
                "update_plan_post_messages": original_templates.get("planning", {}).get(
                    "update_plan_post_messages", 
                    "Update your plan based on new information.\n\n{{task}}\n\n<end_plan>"
                )
            },
            "managed_agent": original_templates.get("managed_agent", {
                "task": "{{name}}: {{task}}",
                "report": "{{name}} final report: {{final_answer}}"
            }),
            "final_answer": original_templates.get("final_answer", {
                "pre_messages": (
                    "请根据您目前收集的所有信息，为用户的问题提供最终答案。"
                ),
                "post_messages": (
                    "基于我收集的信息，请提供对以下问题的最终综合答案: {{task}}"
                )
            })
        }
        
        # 添加原始模板中的其他键（如果有）
        for key, value in original_templates.items():
            if key not in complete_templates:
                complete_templates[key] = value
        
        # 确保系统提示存在
        if "system_prompt" not in complete_templates and "system_prompt" in original_templates:
            complete_templates["system_prompt"] = original_templates["system_prompt"]
        
        # 记录提示模板处理日志，帮助调试
        logger.debug(
            f"StreamingReactAgent 初始化: 处理提示模板 "
            f"原始键: {list(original_templates.keys() if original_templates else [])} "
            f"最终键: {list(complete_templates.keys())}"
        )
        
        # 用完整的模板集合调用父类的初始化方法
        super().__init__(
            tools=tools,
            model=model,
            prompt_templates=complete_templates,
            max_steps=max_steps,
            add_base_tools=add_base_tools,
            verbosity_level=verbosity_level,
            grammar=grammar,
            managed_agents=managed_agents,
            step_callbacks=step_callbacks,
            planning_interval=planning_interval,
            **kwargs,
        )

    def run(
        self,
        task: str,
        stream: bool = False,
        reset: bool = True,
        images: Optional[List] = None,
        additional_args: Optional[Dict] = None,
        max_steps: Optional[int] = None,
    ) -> Union[str, Iterator[str]]:
        """运行代理处理指定任务，支持流式输出或标准输出。

        Args:
            task (str): 要执行的任务
            stream (bool): 是否以流式模式运行
                如为 True，所有思考步骤和最终答案都会流式输出
                如为 False，执行所有步骤并返回最终答案字符串
            reset (bool): 是否重置对话或从上一次运行继续
            images (List, 可选): 图像对象
            additional_args (Dict, 可选): 其他传递给代理运行的变量
            max_steps (int, 可选): 代理可执行的最大步骤数

        Returns:
            Union[str, Iterator[str]]: 
                如为流式模式，返回思考和行动的流式输出；
                否则返回最终答案字符串
        """
        if not stream:
            # 当 stream=False，使用父类的标准行为
            return super().run(
                task=task,
                stream=False,  # 确保传递 False，遵循常规流程
                reset=reset,
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )
        
        # 当 stream=True，执行流式处理所有步骤
        max_steps = max_steps or self.max_steps
        self.task = task
        self.interrupt_switch = False
        
        # 复制自父类 run 方法的初始化代码，确保一致性
        if additional_args is not None:
            self.state.update(additional_args)
            additional_args_str = str(additional_args)
            self.task += textwrap.dedent(f"""
                You have been provided with these additional arguments: 
                {additional_args_str}.""")

        self.system_prompt = self.initialize_system_prompt()
        self.memory.system_prompt.system_prompt = self.system_prompt
        if reset:
            self.memory.reset()
            self.monitor.reset()
            
        # 记录任务
        model_id = (
            self.model.model_id 
            if hasattr(self.model, 'model_id') 
            else ''
        )
        self.logger.log_task(
            content=self.task.strip(),
            subtitle=f"{type(self.model).__name__} - {model_id}",
            level=LogLevel.INFO,
            title=self.name if hasattr(self, "name") else None,
        )
        self.memory.steps.append(TaskStep(task=self.task, task_images=images))

        # 检查模型是否支持流式输出
        if not isinstance(self.model, StreamingLiteLLMModel):
            logger.warning(
                "流式模式需要 StreamingLiteLLMModel，"
                "但当前使用的是 %s。将以非流式模式继续执行。", 
                type(self.model).__name__
            )
            return super().run(
                task=task,
                stream=False,
                reset=False,  # 这里改为False，因为我们已经重置过了
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )
        
        # 创建一个生成器函数来处理流式输出
        def stream_all_steps():
            # 准备内容标记
            thinking_prefix = "\n<思考>\n"
            thinking_suffix = "\n</思考>\n"
            action_prefix = "\n<执行>\n"
            action_suffix = "\n</执行>\n"
            observation_prefix = "\n<观察>\n"
            observation_suffix = "\n</观察>\n"
            final_answer_prefix = "\n<最终答案>\n"
            final_answer_suffix = "\n</最终答案>\n"
            
            step_count = 0
            final_answer = None
            
            # 开始流式处理
            yield f"开始处理任务: {task}\n"
            
            # 运行代理步骤
            # 获取步骤生成器
            step_generator = self._run(
                task=self.task, 
                max_steps=max_steps, 
                images=images
            )
            
            # 对每个步骤进行流式处理
            for step in step_generator:
                step_count += 1
                
                # 检查是否是最终答案步骤
                if isinstance(step, FinalAnswerStep):
                    # 提取最终答案
                    final_answer = step.final_answer
                    
                    # 流式输出最终答案
                    yield final_answer_prefix
                    
                    # 检查最终答案是否可迭代（流式）
                    try:
                        # 尝试作为流式内容迭代输出
                        for token in final_answer:
                            yield token
                    except TypeError:
                        # 如果不可迭代，则作为字符串直接输出
                        yield str(final_answer)
                        
                    yield final_answer_suffix
                    break
                
                # 将非最终答案步骤添加到内存
                self.memory.steps.append(step)
                
                # 流式输出思考过程（如果有）
                if hasattr(step, 'thought') and step.thought:
                    yield thinking_prefix
                    
                    # 尝试流式输出思考内容
                    try:
                        # 对于对话式（流式）思考
                        for token in step.thought:
                            yield token
                    except (TypeError, AttributeError):
                        # 对于字符串思考或其他类型
                        yield str(step.thought)
                            
                    yield thinking_suffix
                
                # 流式输出行动（如果有）
                if hasattr(step, 'action') and step.action:
                    yield action_prefix
                    # 格式化JSON以更好的可读性（如果是字典）
                    if isinstance(step.action, dict):
                        import json
                        yield json.dumps(step.action, ensure_ascii=False, indent=2)
                    else:
                        yield str(step.action)
                    yield action_suffix
                
                # 流式输出观察结果（如果有）
                if hasattr(step, 'observation') and step.observation:
                    yield observation_prefix
                    
                    # 处理观察结果
                    observation_str = str(step.observation)
                    # 对于长观察结果分段输出
                    chunk_size = 4000  # 更小的区块以提高响应性
                    if len(observation_str) > chunk_size * 2:
                        for i in range(0, len(observation_str), chunk_size):
                            yield observation_str[i:i+chunk_size]
                    else:
                        yield observation_str
                        
                    yield observation_suffix
            
            # 如果没有生成最终答案但运行了一些步骤，手动生成最终答案
            if final_answer is None and step_count > 0:
                yield final_answer_prefix
                
                # 准备简单的提示以流式生成最终答案
                final_prompt = self.prompt_templates["final_answer"]
                post_msg = populate_template(
                    final_prompt.get(
                        "post_messages", 
                        "基于我收集的信息，请提供对以下问题的最终综合答案: {{task}}"
                    ),
                    variables={"task": task}
                )
                
                # 创建一个简单的消息列表来生成最终答案
                messages = [
                    {
                        "role": MessageRole.SYSTEM,
                        "content": [
                            {
                                "type": "text",
                                "text": "你是一位专业的研究助手，擅长总结和呈现信息。"
                            }
                        ]
                    },
                    {
                        "role": MessageRole.USER,
                        "content": [
                            {
                                "type": "text",
                                "text": post_msg
                            }
                        ]
                    }
                ]
                
                # 使用流式模型生成最终答案
                try:
                    stream_response = self.model(messages, stream=True)
                    for token in stream_response:
                        yield token
                except Exception as e:
                    logger.exception("生成最终答案时发生错误: %s", str(e))
                    yield f"生成最终答案时发生错误: {str(e)}"
                
                yield final_answer_suffix
            
        # 返回生成器
        return stream_all_steps() 
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/streaming_agents.py

"""
Streaming agent implementations that extend smolagents base agent classes.

Current version is so so so, like "monkey code", need to be improved and optimized.
"""
import logging
import textwrap
from typing import (
    Dict, List, Optional, Union, Iterator, Callable, Any
)
import collections
import re

from smolagents import (
    MessageRole,
    FinalAnswerStep,
    LogLevel,
    ChatMessage
)
from smolagents.agents import populate_template
from smolagents.memory import TaskStep, ActionStep
from .streaming_models import StreamingLiteLLMModel
from src.agents.codact_agent import CodeAgent
from src.agents.agent import ToolCallingAgent


class StepsAndFinalAnswerStreamingData:
    """
    For carrying step and final answer streaming data.

    Attributes:
        step: Current step
        text_chunk: Text chunk
        full_text: Full text
    """
    def __init__(self, step, text_chunk, full_text):
        self.step = step
        self.text_chunk = text_chunk
        self.full_text = full_text


logger = logging.getLogger(__name__)

# Standard output block markers
THINKING_PREFIX = "\n<Thinking>\n"
THINKING_SUFFIX = "\n</Thinking>\n"
ACTION_PREFIX = "\n<Action>\n"
ACTION_SUFFIX = "\n</Action>\n"
OBSERVATION_PREFIX = "\n<Observation>\n"
OBSERVATION_SUFFIX = "\n</Observation>\n"
FINAL_ANSWER_PREFIX = "\n<Final Answer>\n"
FINAL_ANSWER_SUFFIX = "\n</Final Answer>\n"

# Observation result chunk size
OBSERVATION_CHUNK_SIZE = 4000


class StreamingAgentMixin:
    """Streaming agent mixin class that provides common
      streaming functionality."""

    def __init__(
        self, stream_contents: bool = False, async_mode: bool = False, **kwargs
    ):
        """
        Initialize the streaming agent mixin.

        Args:
            stream_contents: Whether to stream the contents of the model responses.
            async_mode: Whether to use async mode.
        """
        super().__init__(**kwargs)
        self.stream_contents = stream_contents
        self.async_mode = async_mode

    def validate_streaming_model(self, model):
        """
        Validate that the model supports streaming.

        Args:
            model: The model to validate.

        Raises:
            ValueError: If the model does not support streaming.
        """
        if not isinstance(model, StreamingLiteLLMModel):
            raise ValueError(
                "Streaming agent requires a model that supports streaming. "
                "Use StreamingLiteLLMModel with this agent."
            )

    def _convert_stream_to_iterator(
        self, stream, step, chunk_text: bool = False
    ) -> Iterator[StepsAndFinalAnswerStreamingData]:
        """
        Convert a stream object to an iterator.

        Args:
            stream: The stream object.
            step: The current task step.
            chunk_text: Whether to chunk the text output.

        Returns:
            An iterator for the stream.
        """
        try:
            # Check if the stream is an AsyncIterator
            if hasattr(stream, "__aiter__"):
                # Already an async iterator, return it
                return stream

            # Check if the stream is a CustomStreamWrapper
            # If it is StreamResponseAdapter or an object with similar interfaces, use it directly
            if hasattr(stream, "tool_calls") and hasattr(stream, "__iter__"):
                content = stream.content if hasattr(stream, "content") else ""
                # Check if there is a tool_calls attribute and has content
                if hasattr(stream, "tool_calls") and stream.tool_calls:
                    tool_calls_text = str(stream.tool_calls)
                    if not content.endswith(tool_calls_text):
                        content += (f"\n[Tool Calls: {tool_calls_text}]")

                # Return an iterator for a single item
                return iter([
                    StepsAndFinalAnswerStreamingData(
                        step=step,
                        text_chunk=content,
                        full_text=content
                    )
                ])

            # Check if tool_call information is needed
            # Some streams may have tool_call information but lack other necessary attributes
            has_tool_calls = (
                (hasattr(stream, "tool_calls") and stream.tool_calls) or
                (hasattr(stream, "tool_call") and stream.tool_call) or
                (hasattr(stream, "function") and stream.function)
            )

            if has_tool_calls:
                # Ensure tool call information is extracted from the stream
                tool_calls = None

                # Try to get tool call information from different positions
                if hasattr(stream, "tool_calls"):
                    tool_calls = stream.tool_calls
                elif hasattr(stream, "tool_call"):
                    tool_calls = [stream.tool_call]
                elif hasattr(stream, "function"):
                    import uuid
                    tool_call = {
                        'id': getattr(stream, 'id', str(uuid.uuid4())),
                        'type': getattr(stream, 'type', 'function'),
                        'function': stream.function
                    }
                    tool_calls = [tool_call]

                # If tool calls are found, generate a response
                if tool_calls:
                    tool_calls_text = str(tool_calls)
                    content = f"[Tool Calls: {tool_calls_text}]"

                    # Ensure there is content
                    if not content:
                        content = "[Stream with Tool Calls]"

                    return iter([
                        StepsAndFinalAnswerStreamingData(
                            step=step,
                            text_chunk=content,
                            full_text=content
                        )
                    ])

            # Check if the stream is an Iterator
            if hasattr(stream, "__iter__"):
                # Create a partial message to build up as we get chunks
                partial_message = None
                is_first_chunk = True

                # Create a generator function to yield stream data
                def generator():
                    nonlocal partial_message, is_first_chunk

                    for chunk in stream:
                        # Initialize the partial message on first chunk
                        if is_first_chunk:
                            if hasattr(chunk, "choices") and chunk.choices:
                                delta = chunk.choices[0].delta

                                # Initialize with role if present
                                if hasattr(delta, "role") and delta.role:
                                    partial_message = ChatMessage(
                                        role=delta.role, content=""
                                    )
                                else:
                                    # Default to assistant role
                                    partial_message = ChatMessage(
                                        role=MessageRole.ASSISTANT.value,
                                        content=""
                                    )

                                is_first_chunk = False
                            else:
                                # Unknown format, return empty message
                                partial_message = ChatMessage(
                                    role=MessageRole.ASSISTANT.value,
                                    content=""
                                )
                                is_first_chunk = False

                        # Process the chunk content
                        content_delta = ""
                        if hasattr(chunk, "choices") and chunk.choices:
                            delta = chunk.choices[0].delta

                            # Process the content attribute
                            if hasattr(delta, "content") and delta.content:
                                content_delta = delta.content
                                partial_message.content += content_delta

                            # Process the tool_calls and tool_call attributes
                            tool_calls = None
                            # First check tool_calls (plural)
                            if (hasattr(delta, "tool_calls") and
                                delta.tool_calls):
                                tool_calls = delta.tool_calls
                            # Second check tool_call (singular)
                            elif (hasattr(delta, "tool_call") and
                                 delta.tool_call):
                                tool_calls = [delta.tool_call]

                            if tool_calls:
                                # If the partial message does not have the tool_calls attribute, create one
                                if not hasattr(partial_message, "tool_calls"):
                                    partial_message.tool_calls = []

                                # Merge tool_calls data into the partial message
                                partial_message.tool_calls.extend(tool_calls)

                                # Convert tool_calls to text representation for streaming output
                                tool_call_text = str(tool_calls)
                                tool_call_msg = f"\n[Tool Call: {tool_call_text}]"
                                content_delta += tool_call_msg

                        # Only yield if there's content to send
                        if chunk_text and content_delta:
                            yield StepsAndFinalAnswerStreamingData(
                                step=step,
                                text_chunk=content_delta,
                                full_text=partial_message.content
                            )

                    # Yield the final complete message
                    if not chunk_text and partial_message:
                        # Process the tool_calls attribute
                        final_content = partial_message.content
                        if (hasattr(partial_message, "tool_calls") and
                                partial_message.tool_calls):
                            tool_calls_text = str(
                                partial_message.tool_calls
                            )
                            if not final_content.endswith(tool_calls_text):
                                final_content += (
                                    f"\n[Tool Calls: {tool_calls_text}]"
                                )

                        yield StepsAndFinalAnswerStreamingData(
                            step=step,
                            text_chunk=final_content,
                            full_text=final_content
                        )

                return generator()

            # For a single message or completion object, wrap it
            if hasattr(stream, "choices") and stream.choices:
                content = stream.choices[0].message.content or ""

                # Process the tool_calls and tool_call attributes
                tool_calls = None
                # First check tool_calls (plural)
                if (hasattr(stream.choices[0].message, "tool_calls") and
                        stream.choices[0].message.tool_calls):
                    tool_calls = stream.choices[0].message.tool_calls
                # Second check tool_call (singular)
                elif (hasattr(stream.choices[0].message, "tool_call") and
                     stream.choices[0].message.tool_call):
                    tool_calls = [stream.choices[0].message.tool_call]

                if tool_calls:
                    tool_calls_text = str(tool_calls)
                    content += f"\n[Tool Calls: {tool_calls_text}]"

                return iter([
                    StepsAndFinalAnswerStreamingData(
                        step=step,
                        text_chunk=content,
                        full_text=content
                    )
                ])

            # Process the special attribute cases (tool_calls/tool_call, but no content)
            tool_calls = None
            # First check tool_calls (plural)
            if (hasattr(stream, "tool_calls") and
                    not hasattr(stream, "content")):
                tool_calls = stream.tool_calls
            # Second check tool_call (singular)
            elif (hasattr(stream, "tool_call") and
                 not hasattr(stream, "content")):
                tool_calls = [stream.tool_call]

            if tool_calls:
                # Create a content with tool_calls text representation
                tool_calls_text = str(tool_calls)
                content = f"[Tool Calls: {tool_calls_text}]"

                return iter([
                    StepsAndFinalAnswerStreamingData(
                        step=step,
                        text_chunk=content,
                        full_text=content
                    )
                ])

            # Return an empty iterator if all else fails
            return iter([])

        except Exception as e:
            logging.error(f"Error converting stream to iterator: {str(e)}")
            return iter([])

    def _yield_chunked_text(self, text, chunk_size=OBSERVATION_CHUNK_SIZE):
        """Outputs long text in chunks."""
        if len(text) > chunk_size * 2:
            for i in range(0, len(text), chunk_size):
                yield text[i:i+chunk_size]
        else:
            yield text

    def _setup_executor_environment(self):
        """Ensure the execution environment is correctly set up"""
        if hasattr(self, "python_executor"):
            self.python_executor.send_variables(variables=self.state)
            self.python_executor.send_tools(
                {**self.tools, **self.managed_agents}
            )


class StreamingCodeAgent(CodeAgent, StreamingAgentMixin):
    """Extended CodeAgent class with streaming final answer support.

    The main difference from standard CodeAgent is that when run method is
    called with stream=True, this agent will execute all steps normally but
    will use LiteLLM streaming output for the final answer generation,
    returning the final answer token by token rather than all at once.

    This implementation replaces the previous StreamingFinalAnswerWrapper to
    provide more consistent code structure across the codebase.

    Args:
        tools (List[Tool]): Tools available to the agent
        model (StreamingLiteLLMModel): Model generating agent behavior
        prompt_templates (Dict, optional): Prompt templates (recommended to use CODACT_ACTION_PROMPT)
        grammar (Dict[str, str], optional): Grammar for parsing LLM output
        additional_authorized_imports (List[str], optional): Additional
        authorized imports
        planning_interval (int, optional): Interval for agent planning steps
        executor_type (str, default "local"): Executor type
        executor_kwargs (Dict, optional): Extra parameters for executor
        max_print_outputs_length (int, optional): Maximum length for print
        outputs
        **kwargs: Other parameters passed to parent class
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
        """Run the agent to process the specified task, with streaming or
        standard output.

        Args:
            task (str): Task to execute
            stream (bool): Whether to run in streaming mode
                If True, final answer will be returned as a stream
                If False, all steps will be executed and final answer returned as string
            reset (bool): Whether to reset conversation or continue from
            previous run
            images (List, optional): Image objects
            additional_args (Dict, optional): Other variables passed to agent run
            max_steps (int, optional): Maximum steps agent can execute

        Returns:
            Union[str, Iterator[str]]: If streaming mode, returns final answer stream;
            otherwise returns final answer string
        """
        # Initialize execution environment
        self._setup_executor_environment()

        # If non-streaming mode, use parent class run method
        if not stream:
            final_answer = super().run(
                task=task,
                stream=False,  # Ensure False is passed to follow regular flow
                reset=reset,
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

            # Process non-streaming output for JSON
            if (isinstance(final_answer, str) and
                    final_answer.strip().startswith('{') and
                    final_answer.strip().endswith('}')):
                try:
                    import json
                    json_data = json.loads(final_answer)
                    if isinstance(json_data, dict) and 'content' in json_data:
                        return json_data['content']
                except Exception as e:
                    logger.error(f"Error extracting content from JSON: {e}")

            return final_answer

        # Save task and set maximum steps
        max_steps = max_steps or self.max_steps
        self.task = task
        self.interrupt_switch = False

        # Initialize additional parameters (if any)
        if additional_args is not None:
            self.state.update(additional_args)
            additional_args_str = str(additional_args)
            self.task += textwrap.dedent(f"""
                You have been provided with these additional arguments:
                {additional_args_str}.""")

        # Initialize and reset system prompt and memory (if needed)
        self.system_prompt = self.initialize_system_prompt()
        self.memory.system_prompt.system_prompt = self.system_prompt
        if reset:
            self.memory.reset()
            self.monitor.reset()

        # Log task information
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

        # Check if model supports streaming output
        if not self.validate_streaming_model(self.model):
            return super().run(
                task=task,
                stream=False,
                reset=False,  # Already reset above
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

        # Save task and images for processing
        self.task = task
        self.task_images = images

        # Execute main execution logic
        final_step = None
        step_counter = 0

        # Flag indicating if task has been displayed
        self.task_displayed = True

        # Execute agent steps until final answer is found
        for step in self._run(
            task=self.task,
            max_steps=max_steps,
            images=images
        ):
            # Add step to memory and increment counter
            self.memory.steps.append(step)
            step_counter += 1

            # Check if this is the final answer step
            if isinstance(step, FinalAnswerStep):
                final_step = step
                break

        # If final answer found, get answer text
        if final_step is not None:
            final_answer = final_step.final_answer
            # Check if result is JSON format, if so, try to extract content field
            if (isinstance(final_answer, str) and
                    final_answer.strip().startswith('{') and
                    final_answer.strip().endswith('}')):
                try:
                    import json
                    json_data = json.loads(final_answer)
                    if isinstance(json_data, dict) and 'content' in json_data:
                        # For streaming output, return the original JSON text
                        if stream:
                            return final_answer
                        # For non-streaming output, return content directly
                        return json_data['content']
                except Exception as e:
                    logger.error(f"Error extracting content from JSON: {e}")
                    # When an error occurs, return the original text
            
            # 特殊处理dict类型的final_answer，不用转换成生成器
            if isinstance(final_answer, dict) and stream:
                # 遵循smolagents的行为，直接返回dict
                # CLI会有专门的错误捕获机制来处理dict
                return final_answer
                
            # For streaming output, return the original text
            return self._generate_streaming_final_answer(
                self.task, final_answer
            )
        return "No final answer was produced"

    def _generate_streaming_final_answer(self, task: str, final_answer: Any) -> Iterator[str]:
        """
        Generate a streaming final answer from a final answer object.
        
        This method wraps any final answer object (string, dictionary, etc.)
        into an iterable stream for consumption by the CLI.
        
        Args:
            task: The original task
            final_answer: The final answer object (could be string, dict, etc.)
            
        Returns:
            An iterator that yields the final answer content
        """
        # 关键修改：处理字典类型的final_answer
        # 不再尝试将其转换为迭代器，而是作为单个值返回
        if isinstance(final_answer, dict):
            # 直接将dict转为JSON字符串，但不创建生成器
            # 这样，调用方可以直接获取结果而不是迭代
            import json
            try:
                # Ensure proper JSON formatting with ensure_ascii=False for better Unicode handling
                json_str = json.dumps(final_answer, ensure_ascii=False)
                # 只yield一次，与smolagents代码执行器的行为保持一致
                yield json_str
                return
            except Exception as e:
                logger.error(f"Error converting dictionary to JSON: {e}")
                yield str(final_answer)
                return
        
        # 如果是字符串类型的final_answer
        if isinstance(final_answer, str):
            # 如果是JSON格式字符串，直接返回
            if final_answer.strip().startswith('{') and final_answer.strip().endswith('}'):
                yield final_answer
                return
                
            # 处理可能包含URL的普通文本
            import re
            url_pattern = r'https?://[^\s)>]+'
            found_urls = re.findall(url_pattern, final_answer)
            
            # 如果包含URL，格式化为标准JSON结构
            if found_urls:
                import json
                formatted_json = {
                    "title": "Final Answer",
                    "content": final_answer,
                    "sources": found_urls
                }
                yield json.dumps(formatted_json, ensure_ascii=False)
                return
                
            # 普通文本，直接返回
            yield final_answer
            return
            
        # 处理其他可迭代对象(但不是字典)
        if hasattr(final_answer, '__iter__') and not isinstance(final_answer, (str, dict)):
            try:
                for chunk in final_answer:
                    yield str(chunk)
            except Exception as e:
                logger.error(f"Error iterating through final answer: {e}")
                yield f"[Error processing stream: {str(e)}]"
            return
                
        # 其他类型，转为字符串
        yield str(final_answer)

    def _execute_step(self, task: str, memory_step: ActionStep) -> Union[None, Any]:
        """Override execute step method to ensure tools are available"""
        # Ensure python executor is correctly set
        if hasattr(self, "python_executor"):
            # Check if tools have been sent, if not send them
            if not getattr(self.python_executor, "_tools_sent", False):
                self.python_executor.send_tools(
                    {**self.tools, **self.managed_agents}
                )
                setattr(self.python_executor, "_tools_sent", True)

        try:
            # Call parent class execute method
            result = super()._execute_step(task, memory_step)
            return result
        except AttributeError as e:
            # Catch possible CustomStreamWrapper missing content attribute error
            if "'CustomStreamWrapper' object has no attribute 'content'" in str(e):
                logger.warning(
                    "Caught CustomStreamWrapper error, providing compatibility layer"
                )
                # If it is processing plan_message, create an object with content attribute
                if hasattr(memory_step, 'output') and memory_step.output is not None:
                    # Provide a placeholder object with content attribute
                    class StreamContentWrapper:
                        def __init__(self, stream_obj):
                            self.stream_obj = stream_obj
                            self.content = "[Stream Content Placeholder]"

                        def __iter__(self):
                            return iter(self.stream_obj)

                    # Replace the stream object in memory step with the wrapper object
                    memory_step.output = StreamContentWrapper(memory_step.output)
                    # Retry execution
                    return super()._execute_step(task, memory_step)
            # If it is not a known streaming processing error, raise it
            raise
        except ValueError as e:
            # Process code parsing errors, especially when "[Stream Content]" and regex pattern do not match
            if "regex pattern" in str(e) and "[Stream Content]" in str(e):
                logger.warning(
                    "Processing stream content code parsing error, providing compatible code block"
                )
                # If it is processing code parsing, create a simple code response
                if hasattr(memory_step, 'message') and memory_step.message is not None:
                    # Create a simple response with correct code format
                    from smolagents.memory import Message
                    formatted_content = (
                        "Thoughts: Processing stream content\n"
                        "Code:\n```python\n"
                        "# Handle stream content\n"
                        "def process_stream():\n"
                        "    return '[Stream Content processing]'\n"
                        "```<end_code>"
                    )
                    # Use formatted content to replace message
                    memory_step.message = Message(
                        role="assistant",
                        content=formatted_content
                    )
                    # Retry execution
                    return super()._execute_step(task, memory_step)
            # If it is not a known code parsing error, raise it
            raise


class StreamingReactAgent(ToolCallingAgent, StreamingAgentMixin):
    """Extended ToolCallingAgent class with streaming for all steps and final answer.

    The main difference from standard ToolCallingAgent is that when run method is
    called with stream=True, this agent will stream all thinking steps and final 
    answer, rather than only outputting the final answer at the end.

    This version fixes previous errors and ensures all necessary templates are provided.

    Args:
        tools (List[Tool]): Tools available to the agent
        model (StreamingLiteLLMModel): Model generating agent behavior
        prompt_templates (Dict, optional): Prompt templates
        max_steps (int, default 20): Maximum steps agent can execute
        add_base_tools (bool, default False): Whether to add base tools
        verbosity_level (LogLevel, default LogLevel.INFO): Agent log verbosity level
        grammar (Dict[str, str], optional): Grammar for parsing LLM output
        managed_agents (List, optional): Managed agents that agent can call
        step_callbacks (List[Callable], optional): Callbacks called at each step
        planning_interval (int, optional): Interval for agent planning steps
        **kwargs: Other parameters
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
        """Initialize StreamingReactAgent instance.

        Ensures all necessary prompt templates are provided at initialization.
        """
        # Ensure all necessary templates are ready at initialization
        # First save original templates (if any)
        original_templates = prompt_templates or {}

        # Create a new dictionary with all necessary templates
        complete_templates = {
            # Basic prompt templates, use user's if provided, otherwise use defaults
            "planning": {
                "initial_plan": original_templates.get("planning", {}).get(
                    "initial_plan",
                    "Based on the task, create a plan to search and gather "
                    "information.\n\n{{task}}\n\n<end_plan>"
                ),
                "update_plan_pre_messages": original_templates.get(
                    "planning", {}
                ).get(
                    "update_plan_pre_messages",
                    "Review your progress and update your plan."
                ),
                "update_plan_post_messages": original_templates.get(
                    "planning", {}
                ).get(
                    "update_plan_post_messages",
                    "Update your plan based on new information.\n\n"
                    "{{task}}\n\n<end_plan>"
                )
            },
            "managed_agent": original_templates.get("managed_agent", {
                "task": "{{name}}: {{task}}",
                "report": "{{name}} final report: {{final_answer}}"
            }),
            "final_answer": original_templates.get("final_answer", {
                "pre_messages": (
                    "Please provide a final answer based on all information collected."
                ),
                "post_messages": (
                    "Based on the information I've collected, please provide a "
                    "comprehensive final answer to: {{task}}"
                )
            })
        }

        # Add other keys from original templates (if any)
        for key, value in original_templates.items():
            if key not in complete_templates:
                complete_templates[key] = value

        # Ensure system prompt exists
        if ("system_prompt" not in complete_templates and
                "system_prompt" in original_templates):
            complete_templates["system_prompt"] = original_templates[
                "system_prompt"
            ]

        # Log prompt template processing for debugging
        logger.debug(
            "StreamingReactAgent init: Processing prompt templates - "
            f"Original keys: {list(original_templates.keys() if original_templates else [])} "
            f"Final keys: {list(complete_templates.keys())}"
        )

        # Call parent class initialization with complete template set
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

        # Initialize task_images attribute and task_displayed flag
        self.task_images = None
        self.task_displayed = False

    def run(
        self,
        task: str,
        stream: bool = False,
        reset: bool = True,
        images: Optional[List] = None,
        additional_args: Optional[Dict] = None,
        max_steps: Optional[int] = None,
    ) -> Union[str, Iterator[str]]:
        """Run the agent to process the specified task, with streaming or
        standard output.

        Args:
            task (str): Task to execute
            stream (bool): Whether to run in streaming mode
                If True, all thinking steps and final answer will be streamed
                If False, all steps will be executed and final answer returned as string
            reset (bool): Whether to reset conversation or continue from previous run
            images (List, optional): Image objects
            additional_args (Dict, optional): Other variables passed to agent run
            max_steps (int, optional): Maximum steps agent can execute

        Returns:
            Union[str, Iterator[str]]:
                If streaming mode, returns thoughts and actions as streaming output;
                otherwise returns final answer string
        """
        # Set flag indicating task has been displayed in CLI to avoid repetition
        self.task_displayed = True

        if not stream:
            # When stream=False, use parent class standard behavior
            final_answer = super().run(
                task=task,
                stream=False,  # Ensure False is passed to follow regular flow
                reset=reset,
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

            # Check if result is JSON format, if so, try to extract content field
            if (isinstance(final_answer, str) and 
                    final_answer.strip().startswith('{') and 
                    final_answer.strip().endswith('}')):
                try:
                    import json
                    json_data = json.loads(final_answer)
                    if isinstance(json_data, dict) and 'content' in json_data:
                        return json_data['content']
                except Exception as e:
                    logger.error(f"Error extracting content from JSON: {e}")

            return final_answer

        # When stream=True, process all steps with streaming
        max_steps = max_steps or self.max_steps
        self.task = task
        self.task_images = images  # Save images for use in _stream_all_steps
        self.interrupt_switch = False

        # Return streaming generator
        if not self.validate_streaming_model(self.model):
            logger.warning(
                "Model does not support streaming. "
                "Falling back to non-streaming mode."
            )
            return super().run(
                task=task,
                stream=False,
                reset=reset,
                images=images,
                additional_args=additional_args,
                max_steps=max_steps,
            )

        # Initialize system and environment
        self.system_prompt = self.initialize_system_prompt()
        self.memory.system_prompt.system_prompt = self.system_prompt
        if reset:
            self.memory.reset()
            self.monitor.reset()

        return self._stream_all_steps()

    def _stream_all_steps(self):
        """Create generator function to handle streaming all steps."""
        # Since the task_displayed flag has been set in the run method
        # So here we do not output task information again to avoid repetition
        # yield f"Starting task: {self.task}\n"

        step_count = 0
        final_answer = None

        # Get step generator
        step_generator = self._run(
            task=self.task,
            max_steps=self.max_steps,
            images=self.task_images  # Use saved task_images here
        )

        # Process each step with streaming
        try:
            for step in step_generator:
                step_count += 1

                # Check if this is the final answer step
                if isinstance(step, FinalAnswerStep):
                    # Extract final answer
                    final_answer = step.final_answer

                    # Check if final_answer is JSON format, if so, try to extract content field
                    # But keep original JSON for CLI formatting
                    json_data = None
                    json_content = None
                    if (isinstance(final_answer, str) and
                        final_answer.strip().startswith('{') and
                        final_answer.strip().endswith('}')):
                        try:
                            import json
                            json_data = json.loads(final_answer)
                            if isinstance(json_data, dict) and 'content' in json_data:
                                json_content = json_data['content']
                                # In Stream process, keep original JSON for CLI formatting
                        except Exception as e:
                            logger.error(f"Error extracting content from JSON: {e}")

                    # Stream final answer
                    yield FINAL_ANSWER_PREFIX

                    # Process streaming response object
                    if (isinstance(final_answer, collections.abc.Iterable) and
                            not isinstance(final_answer, str)):
                        # This is a stream object, need to iterate processing
                        try:
                            for text_chunk in self._convert_stream_to_iterator(
                                    final_answer, step):
                                yield text_chunk.text_chunk
                        except Exception as e:
                            logger.error(f"Error processing final answer stream: {str(e)}")
                            yield f"[Stream processing error: {str(e)}]"
                    else:
                        # If there is parsed JSON, ensure output original JSON for CLI rendering
                        if json_data and json_content:
                            # Output original JSON string, let CLI handle formatting
                            yield final_answer
                        else:
                            # Check if the answer is a string that should be converted to JSON format
                            # for consistent formatting and URL handling
                            if isinstance(final_answer, str) and not (final_answer.strip().startswith('{') and final_answer.strip().endswith('}')):
                                # Extract URLs from final answer
                                url_pattern = r'https?://[^\s)>]+'
                                found_urls = re.findall(url_pattern, final_answer)
                                
                                if found_urls:
                                    # Create properly formatted JSON with sources
                                    formatted_json = {
                                        "title": "Final Answer",
                                        "content": final_answer,
                                        "sources": found_urls
                                    }
                                    import json
                                    yield json.dumps(formatted_json, ensure_ascii=False)
                                else:
                                    # Normal string without URLs
                                    yield str(final_answer)
                            else:
                                # Normal string or other objects
                                yield str(final_answer)

                    yield FINAL_ANSWER_SUFFIX
                    break

                # Add non-final answer step to memory
                self.memory.steps.append(step)

                # Stream thinking process (if any)
                if hasattr(step, 'thought') and step.thought:
                    yield THINKING_PREFIX

                    # Process streaming response of thinking process
                    if (isinstance(step.thought, collections.abc.Iterable) and
                            not isinstance(step.thought, str)):
                        try:
                            for text_chunk in self._convert_stream_to_iterator(
                                    step.thought, step):
                                yield text_chunk.text_chunk
                        except Exception as e:
                            logger.error(f"Error processing thinking process stream: {str(e)}")
                            yield f"[Stream processing error: {str(e)}]"
                    else:
                        yield str(step.thought)

                    yield THINKING_SUFFIX

                # Stream action (if any)
                if hasattr(step, 'action') and step.action:
                    yield ACTION_PREFIX
                    # Format JSON for better readability (if dictionary)
                    if isinstance(step.action, dict):
                        import json
                        yield json.dumps(
                            step.action,
                            ensure_ascii=False,
                            indent=2
                        )
                    else:
                        yield str(step.action)
                    yield ACTION_SUFFIX

                # Stream observation results (if any)
                if hasattr(step, 'observation') and step.observation:
                    yield OBSERVATION_PREFIX

                    # Process observation results
                    observation_str = str(step.observation)
                    # Output long observation results in chunks
                    for chunk in self._yield_chunked_text(observation_str):
                        yield chunk

                    yield OBSERVATION_SUFFIX
        except AttributeError as e:
            # Process possible CustomStreamWrapper missing content attribute error
            if "'CustomStreamWrapper' object has no attribute 'content'" in str(e):
                logger.warning("Captured CustomStreamWrapper error, providing compatibility layer")
                yield "\n[Note: Stream processing error captured, but task continues]\n"

                # Provide a final answer, inform the user what happened
                yield FINAL_ANSWER_PREFIX
                yield ("Due to stream processing error, the complete thinking process cannot be displayed, but the Agent has completed processing."
                       "Please try again or use non-streaming mode.")
                yield FINAL_ANSWER_SUFFIX
            else:
                # If it is other types of AttributeError, raise it
                raise
        except Exception as e:
            # Process other types of exceptions
            logger.exception(f"Error processing steps: {str(e)}")
            yield f"\n[Error processing steps: {str(e)}]\n"

        # If no final answer generated but ran some steps, manually generate final answer
        if final_answer is None and step_count > 0:
            yield FINAL_ANSWER_PREFIX

            # Prepare simple prompt to generate final answer with streaming
            final_prompt = self.prompt_templates["final_answer"]
            post_msg = populate_template(
                final_prompt.get(
                    "post_messages",
                    "Based on the information I've collected, please provide a "
                    "comprehensive final answer to: {{task}}"
                ),
                variables={"task": self.task}
            )

            # Create a simple message list to generate final answer
            messages = [
                {
                    "role": MessageRole.SYSTEM,
                    "content": [
                        {
                            "type": "text",
                            "text": ("You are a professional research "
                                   "assistant, skilled in summarizing "
                                   "and presenting information.")
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

            # Use streaming model to generate final answer
            try:
                stream_response = self.model(messages, stream=True)
                # Use _convert_stream_to_iterator instead of directly accessing
                for token in self._convert_stream_to_iterator(stream_response, None):
                    yield token.text_chunk
            except Exception as e:
                logger.exception(f"Error generating final answer: {str(e)}")
                yield f"Error generating final answer: {str(e)}"

            yield FINAL_ANSWER_SUFFIX

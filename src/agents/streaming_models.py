"""
流式输出的模型实现，扩展 smolagents.models 中的模型类。
"""
from typing import List, Dict, Optional, Any, Union
import logging
from smolagents import LiteLLMModel, Tool, ChatMessage

logger = logging.getLogger(__name__)


class StreamingLiteLLMModel(LiteLLMModel):
    """扩展 LiteLLMModel 以支持在最终答案生成时返回原始流对象。

    当作为 final_answer 生成时传入 stream=True 参数，此模型将返回
    litellm.completion 的原始流对象，而不是将其转换为 ChatMessage。
    对于其他步骤的调用，它会正常返回 ChatMessage。
    
    Args:
        model_id (str): LiteLLM 模型标识符
        api_base (str, 可选): API 基础 URL
        api_key (str, 可选): API 密钥
        custom_role_conversions (dict, 可选): 自定义角色转换映射
        flatten_messages_as_text (bool, 可选): 是否将消息扁平化为文本
        **kwargs: 传递给 LiteLLM API 的其他参数
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_role_conversions: Optional[Dict[str, str]] = None,
        flatten_messages_as_text: Optional[bool] = None,
        **kwargs,
    ):
        super().__init__(
            model_id=model_id,
            api_base=api_base,
            api_key=api_key,
            custom_role_conversions=custom_role_conversions,
            flatten_messages_as_text=flatten_messages_as_text,
            **kwargs,
        )
        # 记录初始化的日志，便于调试
        logger.debug(
            f"初始化 StreamingLiteLLMModel: "
            f"model_id={model_id}, api_base={api_base}"
        )

    def __call__(
        self,
        messages: List[Dict[str, str]],
        stop_sequences: Optional[List[str]] = None,
        grammar: Optional[str] = None,
        tools_to_call_from: Optional[List[Tool]] = None,
        **kwargs,
    ) -> Union[Any, ChatMessage]:
        """处理输入消息并返回模型响应或原始流对象。

        特别注意，当 kwargs 中包含 stream=True 时，此方法返回原始流对象
        而不是标准的 ChatMessage 对象，调用者需要相应地处理。

        Args:
            messages (List[Dict[str, str]]): 要处理的消息列表
            stop_sequences (List[str], 可选): 终止序列列表
            grammar (str, 可选): 格式化规则
            tools_to_call_from (List[Tool], 可选): 模型可使用的工具列表
            **kwargs: 额外的关键字参数

        Returns:
            Union[Any, ChatMessage]: 如果 stream=True，返回原始流对象；
                                    否则返回 ChatMessage 对象
        """
        # 获取 stream 参数，默认为 False
        stream_mode = kwargs.pop("stream", False)  # 从kwargs中移除stream参数
        # 如果是最终流式输出模式
        if stream_mode:
            # 准备完整的参数，不在kwargs中包含stream
            completion_kwargs = self._prepare_completion_kwargs(
                messages=messages,
                stop_sequences=stop_sequences,
                grammar=grammar,
                tools_to_call_from=tools_to_call_from,
                model=self.model_id,
                api_base=self.api_base,
                api_key=self.api_key,
                convert_images_to_image_urls=True,
                custom_role_conversions=self.custom_role_conversions,
                stream=True,  # 显式设置stream参数
                **kwargs,
            )
            
            logger.debug(f"在流式模式下调用 LiteLLM API: {completion_kwargs}")
            
            # 直接返回流对象，不进行处理
            return self.client.completion(**completion_kwargs)
        else:
            # 对于非流式调用，使用父类的标准行为，确保不传递stream参数
            return super().__call__(
                messages=messages,
                stop_sequences=stop_sequences,
                grammar=grammar,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            ) 
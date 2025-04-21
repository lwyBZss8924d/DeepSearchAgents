#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/streaming_models.py

"""
Streaming output model implementation, extending the model class in smolagents.models.

Current version is so so so, like "monkey code", need to be improved and optimized.
"""
from typing import List, Dict, Optional, Any, Union
import logging
from smolagents import LiteLLMModel, Tool, ChatMessage
import uuid

logger = logging.getLogger(__name__)


class StreamResponseAdapter:
    """
    Adapter class providing compatibility interfaces for streaming response objects.

    The smolagents library requires objects to have a content attribute, but
    CustomStreamWrapper and other streaming objects do not have it. This adapter
    class will wrap the streaming object and provide the required content attribute.

    Attributes:
        stream_obj: The original streaming object
        content: The content string provided to smolagents
    """

    def __init__(self, stream_obj):
        self.stream_obj = stream_obj
        self._content = self._get_content_from_stream()
        self._tool_calls = self._get_tool_calls_from_stream()

    def _get_content_from_stream(self):
        """
        Try to get content from the streaming object.
        For CustomStreamWrapper and other special streaming objects, we return a special mark.
        """
        try:
            # Check if there is a get_chunk_text method
            if hasattr(self.stream_obj, 'get_chunk_text'):
                return "[Streaming object - content will be processed during iteration]"

            # Check if there is a content attribute
            if hasattr(self.stream_obj, 'content'):
                return self.stream_obj.content

            # Default return a mark
            return "[Streaming content is unavailable]"
        except Exception as e:
            logger.warning(f"Error getting content from stream: {e}")
            return "[Streaming content is unavailable]"

    def _get_tool_calls_from_stream(self):
        """
        Try to get tool_calls from the streaming object.
        Handle the case where the naming is inconsistent: some objects use tool_call,
        some use tool_calls.
        """
        try:
            # First check if there is a tool_calls attribute
            if hasattr(self.stream_obj, 'tool_calls'):
                return self.stream_obj.tool_calls

            # Check if there is a tool_call attribute (singular form)
            if hasattr(self.stream_obj, 'tool_call'):
                # Convert tool_call to tool_calls format
                tool_call = self.stream_obj.tool_call
                return [tool_call] if tool_call else []

            # Check if there is a tool_call attribute (singular form)
            if hasattr(self.stream_obj, 'choices') and self.stream_obj.choices:
                choice = self.stream_obj.choices[0]
                if hasattr(choice, 'message'):
                    message = choice.message
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        return message.tool_calls
                    if hasattr(message, 'tool_call') and message.tool_call:
                        return [message.tool_call]

            # Check if there is a tool_call attribute (singular form)
            if hasattr(self.stream_obj, 'message'):
                message = self.stream_obj.message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    return message.tool_calls
                if hasattr(message, 'tool_call') and message.tool_call:
                    return [message.tool_call]

            # If the streaming object itself seems to be a tool call
            if hasattr(self.stream_obj, 'function'):
                tool_call = {
                    'id': getattr(self.stream_obj, 'id', str(uuid.uuid4())),
                    'type': getattr(self.stream_obj, 'type', 'function'),
                    'function': self.stream_obj.function
                }
                return [tool_call]

            # If none of the above, return an empty list
            return []
        except Exception as e:
            logger.warning(f"Error getting tool_calls from stream: {e}")
            return []

    @property
    def content(self):
        """Provide the content attribute"""
        return self._content

    @property
    def tool_calls(self):
        """Provide the tool_calls attribute, compatible with smolagents interface requirements"""
        return self._tool_calls

    def __iter__(self):
        """Delegate to the original streaming object iterator"""
        return iter(self.stream_obj)

    def __next__(self):
        """Delegate to the original streaming object next method"""
        return next(self.stream_obj)

    def __getattr__(self, name):
        """
        Delegate all other attributes to the original streaming object,
        and handle the naming differences of special attributes
        """
        # Special handling for tool_calls/tool_call attributes
        if name == 'tool_calls' and not hasattr(self.stream_obj, 'tool_calls'):
            if hasattr(self.stream_obj, 'tool_call'):
                tool_call = getattr(self.stream_obj, 'tool_call')
                return [tool_call] if tool_call else []
            return []

        return getattr(self.stream_obj, name)


class StreamingLiteLLMModel(LiteLLMModel):
    """Extend LiteLLMModel to support returning the original stream object for final answer generation.

    When the stream=True parameter is passed in for final answer generation,
    this model will return the original litellm.completion stream object,
    rather than converting it to a ChatMessage. For other step calls, it will
    return a ChatMessage as usual.

    Args:
        model_id (str): LiteLLM model identifier
        api_base (str, optional): API base URL
        api_key (str, optional): API key
        custom_role_conversions (dict, optional): Custom role conversion mapping
        flatten_messages_as_text (bool, optional): Whether to flatten messages as text
        **kwargs: Additional parameters passed to LiteLLM API
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
        """Process input messages and return model response or original stream object.

        Note: When the stream=True parameter is passed in kwargs, this method
        returns the original litellm.completion stream object rather than a
        ChatMessage. Callers need to handle this appropriately.

        Args:
            messages (List[Dict[str, str]]): The list of messages to process
            stop_sequences (List[str], optional): The list of stop sequences
            grammar (str, optional): The formatting rules
            tools_to_call_from (List[Tool], optional): The list of tools the model can use
            **kwargs: Additional keyword arguments

        Returns:
            Union[Any, ChatMessage]: If stream=True, return the original stream object;
                                     otherwise return a ChatMessage object
        """
        stream_mode = kwargs.pop("stream", False)

        # Check if it is a planning related call, if so, force non-streaming mode
        is_planning_call = False
        is_code_generation_call = False
        is_final_answer_call = False

        # Check the message content to determine the type of current call
        for message in messages:
            if isinstance(message, dict) and message.get("role") == "user":
                content = message.get("content", "")

                # Check the string content
                if isinstance(content, str):
                    # Check if it is a planning call
                    if any(
                        planning_keyword in content.lower()
                        for planning_keyword in [
                            "plan your action", "planning step",
                            "create a plan", "update your plan"
                        ]
                    ):
                        is_planning_call = True
                        break

                    # Check if it is a code generation call
                    if any(
                        code_keyword in content.lower()
                        for code_keyword in [
                            "write code", "generate python",
                            "implement the following", "write a function",
                            "code to solve", "python code"
                        ]
                    ):
                        is_code_generation_call = True
                        break

                    # Check if it is a final answer call
                    if any(
                        final_answer_keyword in content.lower()
                        for final_answer_keyword in [
                            "final answer", "comprehensive answer",
                            "provide final", "synthesize findings"
                        ]
                    ):
                        is_final_answer_call = True
                        break

                # Check the content list
                elif isinstance(content, list):
                    for item in content:
                        if (isinstance(item, dict) and
                                item.get("type") == "text"):
                            text = item.get("text", "")

                            # Check if it is a planning call
                            if any(
                                planning_keyword in text.lower()
                                for planning_keyword in [
                                    "plan your action", "planning step",
                                    "create a plan", "update your plan"
                                ]
                            ):
                                is_planning_call = True
                                break

                            # Check if it is a code generation call
                            if any(
                                code_keyword in text.lower()
                                for code_keyword in [
                                    "write code", "generate python",
                                    "implement the following",
                                    "write a function", "code to solve",
                                    "python code"
                                ]
                            ):
                                is_code_generation_call = True
                                break

                            # Check if it is a final answer call
                            if any(
                                final_answer_keyword in text.lower()
                                for final_answer_keyword in [
                                    "final answer", "comprehensive answer",
                                    "provide final", "synthesize findings"
                                ]
                            ):
                                is_final_answer_call = True
                                break

        # Determine if streaming mode is used
        use_streaming = stream_mode and not is_code_generation_call

        # For planning calls or code generation calls, always use non-streaming mode
        if is_planning_call or is_code_generation_call:
            logger.debug(
                f"{'Planning' if is_planning_call else 'Code generation'}"
                f" call detected, using non-streaming mode"
            )
            return super().__call__(
                messages=messages,
                stop_sequences=stop_sequences,
                grammar=grammar,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )

        # If it is a final answer call and requests streaming mode, use streaming response
        if is_final_answer_call and stream_mode:
            logger.debug("Final answer call detected, using streaming mode")

        # If final answer streaming mode
        if use_streaming:
            # Prepare complete parameters, not including stream in kwargs
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
                stream=True,
                **kwargs,
            )

            logger.debug(f"Calling LiteLLM API in streaming mode: {completion_kwargs}")

            # Get the original stream object
            response = self.client.completion(**completion_kwargs)

            # Use the adapter to wrap the stream object, providing content attribute compatibility
            adapted_response = StreamResponseAdapter(response)

            # Return the wrapped stream object
            return adapted_response
        else:
            # For non-streaming calls, use the standard behavior of the parent class,
            # ensuring that the stream parameter is not passed
            return super().__call__(
                messages=messages,
                stop_sequences=stop_sequences,
                grammar=grammar,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )

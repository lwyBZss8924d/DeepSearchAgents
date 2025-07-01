#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/stream_aggregator.py
# code style: PEP 8

"""
Stream Aggregator for smolagents v1.19.0
Handles streaming aggregation outside of Model class
"""

from typing import Generator, Dict, Any, Optional
from smolagents.models import ChatMessageStreamDelta
import logging

logger = logging.getLogger(__name__)


class StreamAggregator:
    """Aggregates streaming responses from models
    
    Following smolagents v1.19.0 pattern where streaming aggregation
    is handled outside the Model class
    """
    
    def __init__(self):
        """Initialize the stream aggregator"""
        self.current_content = ""
        self.token_count = 0
        self.metadata = {}
    
    def aggregate_stream(
        self, 
        stream_generator: Generator[ChatMessageStreamDelta, None, None],
        track_tokens: bool = True
    ) -> Generator[ChatMessageStreamDelta, None, None]:
        """Aggregate streaming deltas and yield them
        
        Args:
            stream_generator: Generator yielding ChatMessageStreamDelta objects
            track_tokens: Whether to track token counts
            
        Yields:
            ChatMessageStreamDelta: Aggregated stream deltas
        """
        try:
            for delta in stream_generator:
                # Aggregate content
                if delta.content:
                    self.current_content += delta.content
                    if track_tokens:
                        # Simple token estimation (actual counting would use tokenizer)
                        self.token_count += len(delta.content.split())
                
                # Yield the delta as-is
                yield delta
                
        except Exception as e:
            logger.error(f"Error in stream aggregation: {str(e)}")
            # Yield error delta
            yield ChatMessageStreamDelta(content=f"Error: {str(e)}")
    
    def get_aggregated_content(self) -> str:
        """Get the full aggregated content"""
        return self.current_content
    
    def get_token_count(self) -> int:
        """Get estimated token count"""
        return self.token_count
    
    def reset(self):
        """Reset the aggregator state"""
        self.current_content = ""
        self.token_count = 0
        self.metadata = {}


class ModelStreamWrapper:
    """Wrapper for model streaming that uses StreamAggregator
    
    This separates streaming logic from the model itself,
    following smolagents v1.19.0 architecture
    """
    
    def __init__(self, model):
        """Initialize with a model instance
        
        Args:
            model: The underlying model (e.g., LiteLLMModel)
        """
        self.model = model
        self.aggregator = StreamAggregator()
    
    def generate_stream(
        self,
        messages: list,
        **kwargs
    ) -> Generator[ChatMessageStreamDelta, None, None]:
        """Generate streaming response with aggregation
        
        Args:
            messages: List of messages to send to model
            **kwargs: Additional arguments for the model
            
        Yields:
            ChatMessageStreamDelta: Stream deltas
        """
        # Reset aggregator for new stream
        self.aggregator.reset()
        
        # Get base stream from model
        if hasattr(self.model, 'generate_stream'):
            base_stream = self.model.generate_stream(messages, **kwargs)
        else:
            # Fallback for models without streaming
            response = self.model.generate(messages, **kwargs)
            yield ChatMessageStreamDelta(content=response.content or "")
            return
        
        # Aggregate and yield
        for delta in self.aggregator.aggregate_stream(base_stream):
            yield delta
    
    def get_aggregated_response(self) -> Dict[str, Any]:
        """Get aggregated response data after streaming"""
        return {
            "content": self.aggregator.get_aggregated_content(),
            "token_count": self.aggregator.get_token_count()
        }
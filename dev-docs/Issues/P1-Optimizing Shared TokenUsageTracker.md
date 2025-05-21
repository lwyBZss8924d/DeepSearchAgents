# P1: Optimizing Shared TokenUsageTracker Component

> **HIGHEST PRIORITY TASK** - Must be implemented first before other tool optimizations.
> All other tool optimizations (Chunking, Embedding, ReadURL, Rerank, Search) should reference and utilize this shared component.

## Overview

Multiple Agent Tools (Chunking, Embedding, ReadURL, Rerank, Search) currently require similar token usage tracking functionality. To avoid code duplication and ensure consistency across implementations, we need to create a shared `TokenUsageTracker` component.

## 1. Centralized Token Tracking Component

Python implementation of a shared component based on the TypeScript version of `token-tracker.ts`:

```python
# src/agents/core/token_tracking.py
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import threading
from enum import Enum

class TokenUsageTool(str, Enum):
    """Enumeration of all supported tool types"""
    SEARCH = "search"
    EMBED = "embed"
    READ = "read"
    RERANK = "rerank"
    CHUNK = "chunk"
    WOLFRAM = "wolfram"
    FINAL_ANSWER = "final_answer"
    CUSTOM = "custom"

@dataclass
class TokenUsage:
    """Token usage for a single API call"""
    tool: str
    timestamp: float = field(default_factory=time.time)
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None  # Additional info such as URL, query, etc.

class TokenUsageTracker:
    """
    Track token usage for Jina API calls
    
    This component is responsible for tracking token usage across all tools, supporting:
    - Recording usage for each tool
    - Calculating total usage
    - Categorizing usage by tool type
    - Supporting budget limits and warnings
    - Generating usage reports
    """
    
    def __init__(self, budget: Optional[int] = None):
        """
        Initialize token tracker
        
        Args:
            budget: Optional token budget limit
        """
        self.usages: List[TokenUsage] = []
        self.budget = budget
        self._lock = threading.Lock()  # Thread-safety support
        self._usage_callbacks = []
        
    def track_usage(
        self, 
        tool: Union[str, TokenUsageTool], 
        usage_data: Dict[str, int], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record token usage for a tool
        
        Args:
            tool: Tool name or TokenUsageTool enum
            usage_data: Dictionary containing prompt_tokens, completion_tokens, and total_tokens
            metadata: Optional additional metadata
        """
        usage = {
            'promptTokens': usage_data.get('prompt_tokens', 0),
            'completionTokens': usage_data.get('completion_tokens', 0),
            'totalTokens': usage_data.get('total_tokens', 0),
        }
        
        tool_name = tool.value if isinstance(tool, TokenUsageTool) else tool
        
        token_usage = TokenUsage(
            tool=tool_name,
            usage=usage,
            metadata=metadata
        )
        
        with self._lock:
            self.usages.append(token_usage)
            
        # Trigger callbacks
        total_usage = self.get_total_usage()
        for callback in self._usage_callbacks:
            callback(tool_name, usage, total_usage)
            
        # Output usage information
        print(f"[{tool_name}] Added {usage['totalTokens']} tokens. Total: {total_usage['totalTokens']}")
        
        # Check budget
        if self.budget and total_usage['totalTokens'] > self.budget:
            print(f"WARNING: Token budget exceeded! Budget: {self.budget}, Used: {total_usage['totalTokens']}")
        
    def get_total_usage(self) -> Dict[str, int]:
        """Get total token usage"""
        totals = {
            'promptTokens': 0,
            'completionTokens': 0,
            'totalTokens': 0
        }
        
        with self._lock:
            for item in self.usages:
                usage = item.usage
                totals['promptTokens'] += usage['promptTokens']
                totals['completionTokens'] += usage['completionTokens']
                totals['totalTokens'] += usage['totalTokens']
                
        return totals
    
    def get_total_usage_snake_case(self) -> Dict[str, int]:
        """Get total token usage (snake_case format)"""
        totals = self.get_total_usage()
        return {
            'prompt_tokens': totals['promptTokens'],
            'completion_tokens': totals['completionTokens'],
            'total_tokens': totals['totalTokens']
        }
        
    def get_usage_breakdown(self) -> Dict[str, int]:
        """Get token usage breakdown by tool"""
        breakdown = {}
        
        with self._lock:
            for item in self.usages:
                tool = item.tool
                tokens = item.usage['totalTokens']
                breakdown[tool] = breakdown.get(tool, 0) + tokens
                
        return breakdown
    
    def get_usage_by_tool(self, tool: Union[str, TokenUsageTool]) -> Dict[str, int]:
        """Get token usage for a specific tool"""
        tool_name = tool.value if isinstance(tool, TokenUsageTool) else tool
        totals = {
            'promptTokens': 0,
            'completionTokens': 0,
            'totalTokens': 0
        }
        
        with self._lock:
            for item in self.usages:
                if item.tool == tool_name:
                    usage = item.usage
                    totals['promptTokens'] += usage['promptTokens']
                    totals['completionTokens'] += usage['completionTokens']
                    totals['totalTokens'] += usage['totalTokens']
                    
        return totals
    
    def get_usage_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of usage with timestamps"""
        timeline = []
        
        with self._lock:
            for item in self.usages:
                timeline.append({
                    'tool': item.tool,
                    'timestamp': item.timestamp,
                    'tokens': item.usage['totalTokens'],
                    'metadata': item.metadata
                })
                
        return timeline
    
    def add_usage_callback(self, callback) -> None:
        """Add usage update callback"""
        self._usage_callbacks.append(callback)
        
    def print_summary(self) -> None:
        """Print usage summary"""
        breakdown = self.get_usage_breakdown()
        total = self.get_total_usage()
        
        print("Token Usage Summary:")
        print(f"  Budget: {self.budget or 'Unlimited'}")
        print(f"  Total Usage: {total['totalTokens']} tokens")
        print(f"    - Prompt: {total['promptTokens']} tokens")
        print(f"    - Completion: {total['completionTokens']} tokens")
        print("  Breakdown by Tool:")
        
        for tool, tokens in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {tool}: {tokens} tokens")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed usage report"""
        return {
            "budget": self.budget,
            "total": self.get_total_usage(),
            "breakdown": self.get_usage_breakdown(),
            "timeline": self.get_usage_timeline(),
            "timestamp": time.time()
        }
        
    def reset(self) -> None:
        """Reset usage statistics"""
        with self._lock:
            self.usages = []


# Global singleton instance, can be shared across the application
_global_tracker = None

def get_token_tracker(budget: Optional[int] = None) -> TokenUsageTracker:
    """Get or create global token tracker instance"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenUsageTracker(budget=budget)
    return _global_tracker
```

## 2. Tool Integration Example

```python
# Example of integrating TokenUsageTracker in various tools

# 1. Import and get tracker instance
from ..core.token_tracking import get_token_tracker, TokenUsageTool

# 2. Use in tool's forward method
def forward(self, ...):
    # ...processing logic...
    
    # Track token usage
    tracker = get_token_tracker()
    tracker.track_usage(
        tool=TokenUsageTool.READ,  # or "read"
        usage_data={
            'prompt_tokens': len(url),  # if applicable
            'completion_tokens': tokens,
            'total_tokens': tokens
        },
        metadata={
            'url': url,
            'format': output_format
        }
    )
    
    # Return result
    return result
```

## 3. Global Configuration and Budget Settings

```python
# Add token budget settings to config loader
def load_config():
    # ...existing code...
    
    # Set global token tracker budget
    if config.get('token_budget'):
        from ..core.token_tracking import get_token_tracker
        tracker = get_token_tracker(budget=config['token_budget'])
        print(f"Token budget set to {config['token_budget']}")
```

## 4. CLI Integration

```python
# Add token usage reporting to CLI
def main():
    # ...process query...
    
    # Print token usage summary
    from ..core.token_tracking import get_token_tracker
    tracker = get_token_tracker()
    tracker.print_summary()
```

## 5. Periodic Reporting Mechanism

```python
# Add periodic reporting mechanism
def setup_reporting(interval_seconds=60):
    from ..core.token_tracking import get_token_tracker
    import threading
    import time
    
    def report_usage():
        while True:
            time.sleep(interval_seconds)
            tracker = get_token_tracker()
            usage = tracker.get_total_usage()
            print(f"Periodic usage report: {usage['totalTokens']} tokens used")
            
    reporter_thread = threading.Thread(target=report_usage, daemon=True)
    reporter_thread.start()
```

## 6. Implementation Steps

1. Create new `src/agents/core/token_tracking.py` module
2. Remove duplicate token tracking implementations from individual tools
3. Update tools to use the shared `TokenUsageTracker` component
4. Add token budget settings to configuration file
5. Update CLI to display usage summary
6. Provide APIs for accessing various usage statistics

## Implementation Benefits

1. **Reduced Code Duplication**: Avoid implementing similar token tracking logic in each tool
2. **Global Budget Management**: Set and monitor token usage across the entire application
3. **Consistent Statistical Methods**: Ensure all tools use the same methods to calculate and report usage
4. **Centralized Reporting**: View token usage for all tools in one place
5. **Enhanced Scalability**: Added more features than the original implementation, such as timelines, callbacks, thread safety, etc.
6. **Better Developer Experience**: Tool developers only need to focus on tool logic, with token tracking handled by the shared component

## Priority and Dependencies

**This shared component has the HIGHEST PRIORITY** for implementation for the following reasons:

1. It's a common dependency for multiple tools
2. It provides global token usage monitoring, which is critical for cost control
3. Once implemented, it will immediately simplify the code of all tools
4. It provides ready-to-use token tracking functionality for future tools

**Implementation Order**: This shared component should be implemented BEFORE optimizing any individual tools (Chunking, Embedding, ReadURL, Rerank, Search). 
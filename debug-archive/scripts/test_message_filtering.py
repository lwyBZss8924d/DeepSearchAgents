#!/usr/bin/env python
"""
Unit test to verify message filtering logic would work correctly.
Simulates the frontend filtering without needing the full UI.
"""

from typing import Dict, Any, Optional


def should_skip_message(message: Dict[str, Any]) -> bool:
    """
    Simulates the frontend filtering logic from agent-chat.tsx.
    Returns True if message should be skipped (not rendered).
    """
    metadata = message.get('metadata', {})
    content = message.get('content', '')
    
    # Skip separator messages
    if metadata.get('message_type') == 'separator':
        print(f"  → Would filter: separator message")
        return True
    
    # Skip empty content (except planning_header and final answers)
    is_final = (
        metadata.get('message_type') == 'final_answer' or
        metadata.get('has_structured_data') or
        'final answer' in content.lower()
    )
    
    if (not content.strip() and 
        metadata.get('message_type') != 'planning_header' and
        not is_final):
        print(f"  → Would filter: empty {metadata.get('message_type', 'unknown')}")
        return True
    
    print(f"  ✓ Would render: {metadata.get('message_type', 'unknown')}")
    return False


def test_filtering():
    """Test various message types against filtering logic."""
    
    test_messages = [
        # Separator - should be filtered
        {
            'content': '-----',
            'metadata': {'message_type': 'separator'}
        },
        # Empty tool_call - should be filtered
        {
            'content': '',
            'metadata': {'message_type': 'tool_call'}
        },
        # Empty planning_header - should NOT be filtered
        {
            'content': '',
            'metadata': {'message_type': 'planning_header'}
        },
        # Action header - should NOT be filtered
        {
            'content': '**Step 1**',
            'metadata': {'message_type': 'action_header'}
        },
        # Normal message - should NOT be filtered
        {
            'content': 'Some actual content',
            'metadata': {'message_type': 'action_thought'}
        },
        # Empty final answer - should NOT be filtered
        {
            'content': '',
            'metadata': {
                'message_type': 'final_answer',
                'has_structured_data': True
            }
        }
    ]
    
    print("Testing message filtering logic:\n")
    
    filtered_count = 0
    rendered_count = 0
    
    for i, msg in enumerate(test_messages, 1):
        print(f"Test {i}: {msg['metadata'].get('message_type', 'unknown')}")
        print(f"  Content: '{msg['content']}'")
        
        if should_skip_message(msg):
            filtered_count += 1
        else:
            rendered_count += 1
        print()
    
    print(f"\nSummary:")
    print(f"  Messages that would be filtered: {filtered_count}")
    print(f"  Messages that would be rendered: {rendered_count}")
    
    # Verify expected results
    expected_filtered = ['separator', 'tool_call']
    expected_rendered = ['planning_header', 'action_header', 'action_thought', 'final_answer']
    
    print(f"\n{'✅' if filtered_count == 2 else '❌'} Expected 2 filtered, got {filtered_count}")
    print(f"{'✅' if rendered_count == 4 else '❌'} Expected 4 rendered, got {rendered_count}")


if __name__ == "__main__":
    test_filtering()
refactor(api/v2)!: simplify to direct Gradio message pass-through architecture

Complete architectural overhaul of Web API v2, replacing the complex event-driven
system with a simplified direct message pass-through approach that leverages
smolagents' proven stream_to_gradio interface.

## Motivation

The initial event-driven architecture proved overly complex and fragile:
- Regex-based message parsing was error-prone
- Event transformation pipeline added unnecessary overhead
- Maintenance burden was high with ~5000 lines of custom code
- Testing revealed edge cases in message parsing logic

## Solution

Implement direct pass-through of Gradio ChatMessages:
- Leverage smolagents' battle-tested streaming infrastructure
- Simple field renaming instead of complex transformations
- Minimal custom code reduces bugs and maintenance
- Proven reliability from existing Gradio UI usage

## Changes

### Removed Components (-4,787 lines)
- `src/api/v2/events.py` - Complex event system
- `src/api/v2/pipeline.py` - Event processing pipeline
- `src/app.py` - Legacy Gradio UI server
- `src/agents/servers/run_gaia.py` - Custom Gradio implementation
- `src/agents/ui_common/gradio_adapter.py` - Gradio adapters
- `src/agents/ui_common/web_adapter.py` - Web adapters
- `src/agents/servers/gradio_patch.py` - Gradio patches
- All TypeScript definitions (to be regenerated from OpenAPI)
- `src/api/v2/test_api.py` - Old test file

### New Components (+522 lines)
- `src/api/v2/models.py` - Simple Pydantic models
- `src/api/v2/gradio_passthrough_processor.py` - Core pass-through logic
- `src/api/v2/main.py` - Standalone API server
- `src/api/v2/openapi.yaml` - Complete API specification
- `src/api/v2/WebAPIv2-GUI-Interface-API-Docs.md` - API documentation
- `tests/api_v2/` - Comprehensive test suite
- Example scripts in `src/api/v2/examples/`

### Modified Components
- Simplified endpoints.py to use direct message pass-through
- Updated session.py for streamlined session management
- Cleaned up imports and dependencies across multiple files

## Testing

Comprehensive test suite validates:
- Real-time WebSocket streaming
- All message types (query, ping, get_messages, get_state)
- Agent step progression
- Final answer delivery
- Error handling
- Session management

## API Features

- Real-time WebSocket streaming via `/api/v2/ws/{session_id}`
- Session states: idle, processing, completed, error, expired
- Multiple message operations with proper request/response patterns
- REST endpoints for session management
- OpenAPI specification for frontend development

BREAKING CHANGE: Complete API redesign - all v2 endpoints and message formats 
have changed. Clients must update to use new DSAgentRunMessage format and 
simplified WebSocket protocol. The event-driven EventBus system no longer exists.

Co-authored-by: Assistant <assistant@anthropic.com>
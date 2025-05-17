# DeepSearchAgents Streaming API Module

This module contains code related to the real-time streaming data (Streamable HTTP & SSE) functionalities of DeepSearchAgents. Since these features are currently unavailable, they have been decoupled from the main codebase and placed into this separate module.

## Module Contents

- `agent_callbacks.py`: Monitors agent execution step events and retrieves step data, used for wrapping event notifications and streaming data transmission.

- `agent_response.py`: Provides real-time agent execution events and step data for the MQ server.

- `v1/faststream.py`: Integrates FastStream for Redis messaging.

- `v1/responses.py`: Implements streamable HTTP responses supporting the Streamable HTTP standard.

## Usage Instructions

Currently, this module is unavailable and has been decoupled from the main DeepSearchAgents functionalities. To utilize these features, further development and debugging are required.

## Development Plan

Future efforts will focus on refactoring and improving this module to enable proper functionality. Key improvement directions include:

1. Optimizing Redis connection and event handling logic

2. Enhancing the performance and stability of real-time data streaming

3. Improving error handling and reconnection mechanisms

4. Adding better API documentation and usage examples

## Notes

- The code within this module is currently not loaded or used by the main application.

- All real-time streaming features have been disabled.

- The main application retains only the basic DeepSearchAgents agent operation API.

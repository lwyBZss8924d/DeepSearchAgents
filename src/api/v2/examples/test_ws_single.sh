#!/bin/bash
# test_ws_single.sh - Test single WebSocket connection

SESSION_ID="9e4c0110-062b-4675-88b0-24b377a47809"
WS_URL="ws://localhost:8000/api/v2/ws/${SESSION_ID}"

echo "Testing WebSocket connection to: $WS_URL"
echo "Commands to test:"
echo "1. Send: {\"type\":\"ping\"}"
echo "2. Send: {\"type\":\"query\",\"query\":\"Solve the quadratic equation x^2 - 5x + 6 = 0\"}"
echo ""

# Connect and send test commands
wscat -c "$WS_URL"
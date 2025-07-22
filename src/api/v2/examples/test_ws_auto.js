#!/usr/bin/env node
// test_ws_auto.js - Automated WebSocket test

const WebSocket = require('ws');

const SESSION_ID = '1d2c02a3-9467-4ef3-bf0d-7f26aaeea740';
const WS_URL = `ws://localhost:8000/api/v2/ws/${SESSION_ID}`;

console.log(`Connecting to: ${WS_URL}`);

const ws = new WebSocket(WS_URL);

ws.on('open', function open() {
    console.log('✓ WebSocket connected!');
    
    // Test 1: Send ping
    console.log('\nTest 1: Sending ping...');
    ws.send(JSON.stringify({ type: 'ping' }));
});

let messageCount = 0;
let queryStartTime = null;

ws.on('message', function message(data) {
    const msg = JSON.parse(data.toString());
    messageCount++;
    
    // Show message summary
    const timestamp = new Date().toISOString();
    console.log(`\n[${timestamp}] Message #${messageCount}:`);
    console.log(`  Type: ${msg.type || 'chat'}`);
    console.log(`  Role: ${msg.role || 'N/A'}`);
    if (msg.content) {
        console.log(`  Content preview: ${msg.content.substring(0, 100)}...`);
    }
    console.log('  Full message:', JSON.stringify(msg, null, 2));
    
    // If we got pong, send a query
    if (msg.type === 'pong') {
        console.log('✓ Ping-pong test passed!');
        
        console.log('\nTest 2: Sending query...');
        queryStartTime = Date.now();
        ws.send(JSON.stringify({
            type: 'query',
            query: 'Solve the quadratic equation x^2 - 5x + 6 = 0'
        }));
        
        // Set timeout to close after 1000 seconds
        setTimeout(() => {
            const elapsed = (Date.now() - queryStartTime) / 1000;
            console.log(`\nClosing connection after ${elapsed.toFixed(1)} seconds...`);
            console.log(`Total messages received: ${messageCount}`);
            ws.close();
        }, 1000000); // 1000 seconds in milliseconds
    }
    
    // Check for final answer
    if (msg.content && msg.content.toLowerCase().includes('final answer')) {
        console.log('\n✓ Received final answer!');
        console.log('Answer content:', msg.content);
        
        // Extract the solution values
        if (msg.content.includes('x = 2') && msg.content.includes('x = 3')) {
            console.log('\n✓ Correct solution found: x = 2 and x = 3');
        }
    }
});

ws.on('error', function error(err) {
    console.error('WebSocket error:', err);
});

ws.on('close', function close() {
    console.log('\nWebSocket connection closed');
    process.exit(0);
});
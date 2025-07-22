#!/usr/bin/env node
// test_agent_steps_full.js - Test full agent steps run with all message types

const WebSocket = require('ws');

// Configuration
const API_BASE = 'http://localhost:8000';
const TIMEOUT_MS = 1000000; // 1000 seconds

// Message type tracking
const messageTypes = {
    user: 0,
    assistant: 0,
    planning: 0,
    action: 0,
    final_answer: 0,
    streaming: 0,
    other: 0
};

// Step tracking
const steps = {
    planning: [],
    action: [],
    final_answer: null,
    allSteps: []
};

async function createSession(agentType = 'codact') {
    const fetch = (await import('node-fetch')).default;
    const response = await fetch(`${API_BASE}/api/v2/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_type: agentType, max_steps: 25 })
    });
    
    if (!response.ok) {
        throw new Error(`Failed to create session: ${response.status}`);
    }
    
    return await response.json();
}

async function testAgentSteps() {
    console.log('=== DeepSearchAgents Web API v2 - Agent Steps Test ===\n');
    
    try {
        // Create session
        console.log('Creating session...');
        const session = await createSession('codact');
        console.log(`Session created: ${session.session_id}`);
        console.log(`WebSocket URL: ${session.websocket_url}\n`);
        
        // Connect to WebSocket
        const wsUrl = `ws://localhost:8000${session.websocket_url}`;
        console.log(`Connecting to: ${wsUrl}`);
        
        const ws = new WebSocket(wsUrl);
        let messageCount = 0;
        let queryStartTime = null;
        
        ws.on('open', () => {
            console.log('✓ WebSocket connected!\n');
            
            // Send the search query
            const query = "Search & query the weather in New York for tomorrow and summarize it into a nice table for me.";
            console.log(`Sending query: "${query}"\n`);
            
            queryStartTime = Date.now();
            ws.send(JSON.stringify({
                type: 'query',
                query: query
            }));
            
            // Set timeout
            setTimeout(() => {
                const elapsed = (Date.now() - queryStartTime) / 1000;
                console.log(`\n\nTimeout reached after ${elapsed.toFixed(1)} seconds`);
                console.log('Closing connection...');
                ws.close();
            }, TIMEOUT_MS);
        });
        
        ws.on('message', (data) => {
            const msg = JSON.parse(data.toString());
            messageCount++;
            
            // Track message types
            if (msg.role === 'user') messageTypes.user++;
            else if (msg.role === 'assistant') messageTypes.assistant++;
            
            if (msg.metadata?.streaming) messageTypes.streaming++;
            
            // Detailed logging for different message types
            const timestamp = new Date().toISOString();
            console.log(`\n[${timestamp}] Message #${messageCount}:`);
            console.log(`  Role: ${msg.role || 'N/A'}`);
            console.log(`  Step: ${msg.step_number !== null ? msg.step_number : 'N/A'}`);
            
            // Check for different step types in content
            if (msg.content) {
                // Planning step detection
                if (msg.content.includes('## 1. Updated facts survey') || 
                    msg.content.includes('## 2. Plan') ||
                    msg.content.includes('### 1. Facts survey')) {
                    messageTypes.planning++;
                    console.log(`  Type: PLANNING STEP`);
                    steps.planning.push({
                        message_id: msg.message_id,
                        step_number: msg.step_number,
                        content_preview: msg.content.substring(0, 150)
                    });
                }
                
                // Action step detection (code execution)
                else if (msg.content.includes('```python') || 
                         msg.content.includes('```bash') ||
                         msg.metadata?.title?.includes('🛠️ Used tool')) {
                    messageTypes.action++;
                    console.log(`  Type: ACTION STEP (Code Execution)`);
                    steps.action.push({
                        message_id: msg.message_id,
                        step_number: msg.step_number,
                        tool: msg.metadata?.title || 'Unknown tool',
                        content_preview: msg.content.substring(0, 150)
                    });
                }
                
                // Final answer detection
                else if (msg.content.toLowerCase().includes('final answer') ||
                         msg.metadata?.title?.includes('Final Answer')) {
                    messageTypes.final_answer++;
                    console.log(`  Type: FINAL ANSWER`);
                    steps.final_answer = {
                        message_id: msg.message_id,
                        content: msg.content
                    };
                }
                
                // Streaming updates
                else if (msg.metadata?.streaming) {
                    console.log(`  Type: STREAMING UPDATE`);
                }
                
                // Content preview
                const preview = msg.content.substring(0, 100).replace(/\n/g, ' ');
                console.log(`  Content: ${preview}${msg.content.length > 100 ? '...' : ''}`);
            }
            
            // Show metadata
            if (msg.metadata && Object.keys(msg.metadata).length > 0) {
                console.log(`  Metadata:`, JSON.stringify(msg.metadata, null, 2));
            }
            
            // Record all steps
            steps.allSteps.push({
                number: messageCount,
                message_id: msg.message_id,
                role: msg.role,
                step_number: msg.step_number,
                has_content: !!msg.content,
                content_length: msg.content?.length || 0,
                metadata: msg.metadata
            });
            
            // Check if we found the final answer with table
            if (msg.content && msg.content.includes('|') && msg.content.includes('New York')) {
                console.log('\n✓ Found table with weather information!');
            }
        });
        
        ws.on('error', (err) => {
            console.error('\nWebSocket error:', err);
        });
        
        ws.on('close', () => {
            const elapsed = queryStartTime ? (Date.now() - queryStartTime) / 1000 : 0;
            
            console.log('\n\n=== Test Summary ===');
            console.log(`Duration: ${elapsed.toFixed(1)} seconds`);
            console.log(`Total messages: ${messageCount}`);
            
            console.log('\nMessage Types:');
            Object.entries(messageTypes).forEach(([type, count]) => {
                if (count > 0) {
                    console.log(`  ${type}: ${count}`);
                }
            });
            
            console.log('\nAgent Steps Summary:');
            console.log(`  Planning steps: ${steps.planning.length}`);
            console.log(`  Action steps: ${steps.action.length}`);
            console.log(`  Final answer: ${steps.final_answer ? 'Yes' : 'No'}`);
            
            if (steps.planning.length > 0) {
                console.log('\nPlanning Steps:');
                steps.planning.forEach((step, i) => {
                    console.log(`  ${i + 1}. Step ${step.step_number}: ${step.content_preview.substring(0, 50)}...`);
                });
            }
            
            if (steps.action.length > 0) {
                console.log('\nAction Steps:');
                steps.action.forEach((step, i) => {
                    console.log(`  ${i + 1}. Step ${step.step_number}: ${step.tool}`);
                });
            }
            
            if (steps.final_answer) {
                console.log('\nFinal Answer Preview:');
                console.log(steps.final_answer.content.substring(0, 300) + '...');
            }
            
            console.log('\n✓ Test completed!');
            process.exit(0);
        });
        
    } catch (error) {
        console.error('Test failed:', error);
        process.exit(1);
    }
}

// Run the test
testAgentSteps();
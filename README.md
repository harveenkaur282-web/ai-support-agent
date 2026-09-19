# AI-SUPPORT-AGENT

Building a fully functional AI customer support agent using Amazon Bedrock AgentCore and the Strands SDK. 
It will serve as an intelligent interface between customers and an e-commerce platform that handles multi-turn conversations while maintaining context across sessions. 

It handles: (using single chat interface)
1. order tracking
2. returns processing
3. product recommendations
4. loyalty rewards calculations

integrating this agent with multiple backend systems through the AgentCore Gateway using Model Context Protocol (MCP), 
1) RETRIEVES grounded product information from a Bedrock Knowledge Base. 
2) remembers customer preferences across sessions using AgentCore Memory
3) performing exact calculations using the AgentCore Code Interpreter. 

the agent will be able to:

a) Track orders and process refunds by calling Lambda functions through the AgentCore Gateway
b) Answer product and policy questions using Retrieval-Augmented Generation (RAG) with a Bedrock Knowledge Base
c) Remember customer names, preferences, and conversation history across separate sessions
d) Calculate exact loyalty discounts using a secure code sandbox
e) Browse live web pages to fetch real-time information

## TASKS given for the project as per Udacity's rubrics:

1. Deploy an AI agent to Amazon Bedrock AgentCore Runtime — using the Strands SDK, BedrockAgentCoreApp, and the @app.entrypoint decorator to create a cloud-deployed agent
2. Integrate external tools through AgentCore Gateway using MCP — connecting Lambda-backed tools (order tracking, refund processing) via MCPClient and streamable_http_client
3. Implement Retrieval Augmented Generation with a Bedrock Knowledge Base — building a search_knowledge_base tool that calls the Retrieve API for grounded, accurate responses
4. Implement cross-session agent memory using AgentCore Memory — creating a MemoryHook that retrieves customer context before each response and saves interactions for future recall
5. Execute computational tasks using AgentCore Code Interpreter — building a loyalty discount calculator that runs precise arithmetic in a secure sandbox
6. Enable web browsing with AgentCore Browser Tool — adding live web access to the agent's capabilities

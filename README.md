# AI-SUPPORT-AGENT

Building a fully functional AI customer support agent using Amazon Bedrock AgentCore and the Strands SDK. 
It will serve as an intelligent interface between customers and an e-commerce platform that handles multi-turn conversations while maintaining context across sessions. 

It handles: (using single chat interface)
1. order tracking
2. returns processing
3. product recommendations
4. loyalty rewards calculations

integrating this agent with multiple backend systems through the AgentCore Gateway using Model Context Protocol (MCP), 
--> RETRIEVES grounded product information from a Bedrock Knowledge Base. 
--> remembers customer preferences across sessions using AgentCore Memory
--> performing exact calculations using the AgentCore Code Interpreter. 

the agent will be able to:

a) Track orders and process refunds by calling Lambda functions through the AgentCore Gateway
b) Answer product and policy questions using Retrieval-Augmented Generation (RAG) with a Bedrock Knowledge Base
c) Remember customer names, preferences, and conversation history across separate sessions
d) Calculate exact loyalty discounts using a secure code sandbox
e) Browse live web pages to fetch real-time information

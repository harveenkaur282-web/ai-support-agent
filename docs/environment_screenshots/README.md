# Environment Setup Screenshots

This directory contains visual confirmation screenshots of the deployed and verified infrastructure resources within the AWS sandbox account (`us-east-1`):

---

### 1. Bedrock AgentCore Gateway (Targets Ready)
Shows `CustomerSupportGateway` with active MCP tools routing to the Lambda functions and API Gateway.
![AgentCore Gateway Ready](01_agentcore_gateway_ready.png)

---

### 2. Bedrock Knowledge Base Overview
Overview of `CustomerSupportKB` connected to OpenSearch Serverless and indexed with `product_catalog.txt`.
![Knowledge Base Overview](02_knowledge_base_overview.png)

---

### 3. Knowledge Base RAG Query Verification
Live query test in the Bedrock console validating retrieval augmented generation against the product catalog.
![Knowledge Base Test RAG](03_knowledge_base_test_rag.png)

---

### 4. Bedrock AgentCore Memory Strategies
Configuration of `CustomerSupportMemory` showing session summary and semantic extraction strategies.
![AgentCore Memory](04_agentcore_memory.png)

---

### 5. Lambda Functions (Order Tracker & Refund Processor)
Deployed Lambda functions for order tracking and refund processing.
![Lambda Functions](05_lambda_functions.png)

---

### 6. API Gateway (REST API & Proxy Routes)
Deployed `CustomerSupportOrderAPI` with REST resources and `prod` stage deployment.
![API Gateway](06_api_gateway_resources.png)

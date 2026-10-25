# Project Verification Screenshots

This directory contains visual confirmation screenshots of the agent deployment, functional query execution, tool usage, memory retention, and browser testing.

---

### 1. Bedrock AgentCore Deployment Success
Visual confirmation of successful packaging, S3 staging, IAM role binding, and runtime deployment to Amazon Bedrock AgentCore (`customer_support_agent-zf9262EdhB`).

![AgentCore Deploy Success](01_agentcore_deploy_success.png)
![AgentCore Deploy Success Part 2](01_agentcore_deploy_success_part2.png)

---

### 2. Test 1 — Order Tracking
Validation of tool calling via AgentCore Gateway and the `order-tracker` Lambda function:
- **Prompt**: `"Can you track order ORD-001?"`
- **Customer ID**: `CUST-123`
- **Outcome**: The agent retrieved order status (`SHIPPED`), item details (`Wireless Headphones Pro`, `$89.99`), carrier (`UPS`), tracking number (`TRK987654321`), and estimated delivery date.

![Test 1 — Order Tracking](02_test1_order_tracking.png)


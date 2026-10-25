# Project Verification Screenshots

Here are screenshots of the agent deployment, functional query execution, tool usage, memory retention, and browser testing.

---

### Bedrock AgentCore Deployment Success
successful packaging, S3 staging, IAM role binding, and runtime deployment to Amazon Bedrock AgentCore (`customer_support_agent-zf9262EdhB`).

![AgentCore Deploy Success](agentcore_deploy_success.png)
![AgentCore Deploy Success Part 2](agentcore_deploy_success_part2.png)

---

### Test 1 — Order Tracking
Validation of tool calling via AgentCore Gateway and the `order-tracker` Lambda function:
- **Prompt**: `"Can you track order ORD-001?"`
- **Customer ID**: `CUST-123`
- **Outcome**: The agent retrieved order status (`SHIPPED`), item details (`Wireless Headphones Pro`, `$89.99`), carrier (`UPS`), tracking number (`TRK987654321`), and estimated delivery date.

![Test 1 — Order Tracking](test1_order_tracking.png)

---

### Test 2 — Refund Processing
Validation of refund initiation via AgentCore Gateway and the `refund-processor` Lambda tool:
- **Prompt**: `"I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund."`
- **Customer ID**: `CUST-123`
- **Outcome**: The agent successfully processed the return for `ORD-002`, approved a refund of `$139.99` back to the customer's payment method, generated refund confirmation ID `REF-BSSB2QTJ`, and offered a prepaid return shipping label.

![Test 2 — Refund Processing](test2_refund_processing.png)

---

### Test 3 — Knowledge Base (RAG)
Validation of RAG search using the `search_knowledge_base` tool connected to Amazon Bedrock Knowledge Base:
- **Prompt**: `"What are the benefits of the Platinum loyalty tier?"`
- **Customer ID**: `CUST-123`
- **Outcome**: The agent retrieved exact policy definitions from `product_catalog.txt` via OpenSearch Serverless:
  - **Free same-day shipping** on eligible items
  - **15% discount** on purchases (compared to 10% for Gold)
  - **Priority customer support** with dedicated assistance
  - Tier threshold: 5,000+ points

![Test 3 — Knowledge Base (RAG)](test3_knowledge_base_rag.png)

---

### Test 4 — Long-Term Memory (Two Sessions)
Validation of cross-session customer facts and preference extraction using Bedrock AgentCore Memory:
- **Session A (`s-A`)**:
  - **Prompt**: `"Hi, I am Jane. I prefer concise responses."`
  - **Customer ID**: `CUST-123`
  - **Extraction**: Bedrock background pipeline extracted facts (*"Jane prefers concise responses."*) and user preferences (*"Prefers concise responses"* for communication style).
- **Session B (`s-B`)**:
  - **Prompt**: `"Do you remember my name and communication preference?"`
  - **Customer ID**: `CUST-123` (new session, same customer)
  - **Outcome**: The agent recalled her name and communication preference from long-term memory: *"Hello Jane! Yes, I remember your name and that you prefer concise responses. How can I assist you today?"*

#### Session A — Introduction
![Test 4 — Session A Introduction](test4_memory_recall_session_a.png)

#### Session B — Memory Recall
![Test 4 — Session B Memory Recall](test4_memory_recall_session_b.png)

---

### Test 5 — Loyalty Discount Calculation
Validation of dynamic arithmetic execution via Bedrock AgentCore Code Interpreter:
- **Prompt**: `"I am a Gold member with 4250 points. Calculate my discount on a $150 standard order."`
- **Customer ID**: `CUST-123`
- **Outcome**: The agent called `calculate_loyalty_discount` and reported the exact breakdown:
  - **Points redeemed**: 4,000 points ($40.00 discount, max 50% of order floored to multiples of 500)
  - **Gold tier discount**: 10% on remaining $110 ($11.00)
  - **Total savings**: $51.00
  - **Final Total**: **$99.00**
  - **Points earned**: 99 points
  - **Remaining Points**: 349 points

![Test 5 — Loyalty Discount Calculation](test5_loyalty_discount.png)



### Test 6 - Browser Tool
- **Prompt**: "Go to https://www.udacity.com and tell me the page title."
- **Customer ID**: `CUST-123`
- **Outcome**: The agent used the browser tool on the live site and returned the title **"Learn the Latest Tech Skills; Advance Your Career | Udacity"**.

![Test 6 - Browser Tool](test6_browser_tool.png)

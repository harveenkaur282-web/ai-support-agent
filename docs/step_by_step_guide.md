# Project Deployment & Implementation Log

This document records each step taken, rationale, and instructions for reproducibility.

---

## Step 1: Project Setup & Dependencies
- **Action**: Updated `pyproject.toml` with required packages (`boto3`, `PyYAML`, `chardet`, `nest-asyncio`, `playwright`, `urllib3`, `bedrock-agentcore`, `strands-agents`).
- **Rationale**: Ensures all required runtime and build dependencies are declared for the AI support agent and AWS integrations.
- **Lockfile**: Ran `uv lock` to generate `uv.lock` pinning 109 transitive dependencies.

---

## Step 2: AWS Credentials Setup
- **Action**: Configured AWS session credentials safely in local `.env` file (git-ignored).
- **Verification**: Verified connection using `boto3.client('sts').get_caller_identity()` which connected to AWS account `057616154556` in region `us-east-1`.

---

## Step 3: Deploying Lambda Functions (Completed)
- **Action**: Created IAM execution role `LambdaBasicExecutionRole-SupportAgent` with `AWSLambdaBasicExecutionRole` policy.
- **Functions Deployed**:
  1. `order-tracker`: `arn:aws:lambda:us-east-1:057616154556:function:order-tracker`
  2. `refund-processor`: `arn:aws:lambda:us-east-1:057616154556:function:refund-processor`
- **Runtime**: Python 3.12 (us-east-1)

---

## Step 4: Configure API Operations (Completed)
- **Action**: Created REST API `CustomerSupportOrderAPI` (ID: `jnq74xt861`) deployed to stage `prod`.
- **Resources & Methods Configured**:
  - `GET /orders/{order_id}` (Operation ID: `get_order`) -> Lambda proxy to `order-tracker`
  - `GET /customers/{customer_id}/orders` (Operation ID: `get_customer_orders`) -> Lambda proxy to `order-tracker`
  - `GET /customers/{customer_id}` (Operation ID: `get_customer`) -> Lambda proxy to `order-tracker`

---

## Step 5: Set up AgentCore Gateway (Completed)
- **Gateway Name**: `CustomerSupportGateway` (`customersupportgateway-yfa07mmavr`)
- **Authorizer**: `NONE`
- **Role**: `arn:aws:iam::057616154556:role/CustomerSupportGatewayRole`
- **Targets Configured**:
  1. `order-tracker`: API Gateway REST API stage (`prod`) exposing `get_order`, `get_customer_orders`, `get_customer`
  2. `refund-processor`: Lambda function `arn:aws:lambda:us-east-1:057616154556:function:refund-processor` with inline schema from `lambda/lambda_schema`
- **Gateway URL**: `https://customersupportgateway-yfa07mmavr.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`

---

## Step 6: Create Knowledge Base (Completed)
- **S3 Bucket**: `s3://support-agent-kb-catalog-057616154556/product_catalog.txt`
- **Knowledge Base Name**: `CustomerSupportKB`
- **Knowledge Base ID**: `CQ0I5EWR3A`
- **Data Source ID**: `TY6ZGXVOL3`
- **Region**: `us-east-1`
- **Status**: Synced and Active

---

## Step 7: Create AgentCore Memory (Completed)
- **Memory Name**: `CustomerSupportMemory`
- **Memory ID**: `CustomerSupportMemory-E2T0yi7ZzC`
- **Region**: `us-east-1`
- **Strategies**:
  - `customer_facts` (`SEMANTIC`) -> `cs_agent/{actorId}/facts`
  - `customer_preferences` (`USER_PREFERENCE`) -> `cs_agent/{actorId}/preferences`
- **Status**: Active

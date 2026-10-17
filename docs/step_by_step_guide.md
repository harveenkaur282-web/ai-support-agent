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
- **Verification**: Verified connection using `boto3.client('sts').get_caller_identity()` which connected to AWS account `057616154556` in region `us-west-2`.

---

## Step 3: Deploying Lambda Functions (In Progress)
- **Goal**: Create and deploy two AWS Lambda functions using **Python 3.12** runtime:
  1. `order-tracker`: Formatted from `lambda/order_tracker.py` for looking up order statuses and customer details via REST API Gateway proxy integration.
  2. `refund-processor`: Formatted from `lambda/refund_processor.py` for handling refund initiation, status checking, and return labels.
- **Execution Role**: Attach an IAM execution role with basic Lambda permissions (`AWSLambdaBasicExecutionRole` for CloudWatch Logs).
- **Output Needed**: ARNs of both deployed Lambda functions for subsequent Gateway setup.

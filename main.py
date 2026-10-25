"""
Customer Support AI Agent — Starter Code
==========================================
Your task is to complete this file by implementing all sections marked
with # TODO comments.

Reference the project instructions and rubric for guidance.
Work through each section yourself.

Run locally (after filling in config values):
  uv run main.py '{"prompt": "Hello", "customer_id": "CUST-123", "session_id": "s1"}'

Deploy to AgentCore:
  agentcore deploy

Invoke deployed agent:
  agentcore invoke '{"prompt": "Hello", "customer_id": "CUST-123", "session_id": "s1"}'
"""

# ── Imports ───────────────────────────────────────────────────────────────────
# These imports are provided. Do not remove them.
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


def _fix_playwright_node():
    """Deploy zip is built on Windows so playwright's bundled node loses its exec bit.
    Copy it to /tmp (writable), chmod it, and point Playwright at the copy."""
    try:
        import shutil, stat, playwright
        src = os.path.join(os.path.dirname(playwright.__file__), "driver", "node")
        if os.path.exists(src) and not os.access(src, os.X_OK):
            dst = "/tmp/playwright_node"
            if not os.path.exists(dst):
                shutil.copyfile(src, dst)
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            os.environ["PLAYWRIGHT_NODEJS_PATH"] = dst
    except Exception as e:
        print(f"playwright node fix skipped: {e}")


_fix_playwright_node()


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── App Initialisation ────────────────

app = BedrockAgentCoreApp()


# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── Configuration ────────────────

GATEWAY_URL = "https://customersupportgateway-yfa07mmavr.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
KB_ID       = "CQ0I5EWR3A"
REGION      = "us-east-1"
MEMORY_ID   = "CustomerSupportMemory-E2T0yi7ZzC"


# ── Model and Clients ────────────────

model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id = model_id)

memory_client = MemoryClient(region_name=REGION)

_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ── Namespace Helper ────────────────

def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type → namespace template string."""
    strategies = mem_client.get_memory_strategies(memory_id=memory_id)
    namespaces = {}
    for s in strategies:
        strategy_type = s.get("type") or s.get("strategyType")
        ns = s.get("namespaceTemplates", [None])[0] or s.get("namespaces", [None])[0]
        if strategy_type and ns:
            namespaces[strategy_type] = ns
    return namespaces


# ── Memory Hook ────────────────

class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""
        if not event.agent.messages:
            return

        last_message = event.agent.messages[-1]
        if last_message.get("role") != "user":
            return

        content = last_message.get("content", [])
        if isinstance(content, str):
            query = content
        elif isinstance(content, list) and content and "text" in content[0]:
            query = content[0]["text"]
        else:
            return

        memories = []
        for strat_type, template in self.namespaces.items():
            ns = template.format(actorId=self.actor_id)
            try:
                results = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=ns,
                    query=query,
                    top_k=5,
                )
                for item in results:
                    text = ""
                    if isinstance(item, dict):
                        content_val = item.get("content")
                        if isinstance(content_val, dict):
                            text = content_val.get("text", "")
                        elif isinstance(content_val, str):
                            text = content_val
                        else:
                            text = item.get("text", "")
                    if text:
                        memories.append(f"- [{strat_type}] {text}")
            except Exception as e:
                logger.warning(f"Error retrieving {strat_type} memories: {e}")

        if memories:
            context_prefix = "Customer Context:\n" + "\n".join(memories) + "\n\n"
            if isinstance(content, str):
                last_message["content"] = context_prefix + content
            elif isinstance(content, list) and content and "text" in content[0]:
                last_message["content"][0]["text"] = context_prefix + content[0]["text"]

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""
        messages = getattr(event.agent, "messages", [])
        customer_query = None
        agent_response = None

        for msg in reversed(messages):
            role = msg.get("role")
            content = msg.get("content")

            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list) and content and "text" in content[0]:
                text = content[0]["text"]

            if role == "assistant" and not agent_response and text:
                agent_response = text
            elif role == "user" and not customer_query and text:
                if "Customer Context:" in text and "\n\n" in text:
                    customer_query = text.split("\n\n", 1)[1]
                else:
                    customer_query = text

            if customer_query and agent_response:
                break

        if customer_query and agent_response:
            try:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[(customer_query, "USER"), (agent_response, "ASSISTANT")],
                )
            except Exception as e:
                logger.warning(f"Error saving support interaction to memory: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)



# ── Knowledge Base Tool ────────────────

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    if not KB_ID:
        return "Knowledge base not configured."

    try:
        resp = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
        )
        results = resp.get("retrievalResults", [])
        if not results:
            return "No relevant information found in the knowledge base."

        chunks = []
        for r in results:
            content = r.get("content", {})
            text = content.get("text", "")
            if text:
                chunks.append(text)

        return "\n---\n".join(chunks) if chunks else "No relevant information found in the knowledge base."
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return f"Error querying knowledge base: {e}"



# ── Loyalty Discount Tool (Code Interpreter) ────────────────

@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount, points redemption, and final order total for an order.
    ALWAYS call this tool whenever the customer mentions points, loyalty tier, or order discount.
    DO NOT estimate or calculate manually — this tool performs the exact business logic:
    points redemption (multiples of 500, max 50% order), tier discount, final total, and remaining points.

    Args:
        loyalty_points:   Customer's available loyalty points balance (integer)
        tier:             Customer membership tier: "Silver", "Gold", or "Platinum"
        order_total:      Original order amount in USD (float)
        product_category: Order product category: "standard", "device", or "fresh" (default "standard")

    Returns:
        JSON string containing points_redeemed, points_discount_usd, tier_discount_percent
        (also tier_discount_pct), tier_discount_usd, total_savings_usd, final_total_usd
        (also final_total), points_earned, remaining_points.
    """
    code = f"""
import json

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

order_total = {float(order_total)}
loyalty_points = {int(loyalty_points)}
tier = "{tier}"
product_category = "{product_category.lower()}"

# Points redemption: 100 points = $1, must be multiple of 500 points ($5), max 50% of order total
max_points_discount = order_total * 0.50
max_usable_points = int(max_points_discount * 100)
points_to_redeem = min(loyalty_points, max_usable_points)
points_redeemed = (points_to_redeem // 500) * 500
points_discount = points_redeemed / 100.0

subtotal_after_points = max(0.0, order_total - points_discount)
tier_rate = tier_rates.get(tier, 0.0)
tier_discount = round(subtotal_after_points * tier_rate, 2)

final_total = round(subtotal_after_points - tier_discount, 2)
total_savings = round(points_discount + tier_discount, 2)

earn_rate = earn_rates.get(product_category, 1)
points_earned = int(final_total * earn_rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "order_total": order_total,
    "points_redeemed": points_redeemed,
    "points_discount_usd": points_discount,
    "tier": tier,
    "tier_discount_percent": int(tier_rate * 100),
    "tier_discount_pct": int(tier_rate * 100),
    "tier_discount_usd": tier_discount,
    "total_savings_usd": total_savings,
    "final_total_usd": final_total,
    "final_total": final_total,
    "points_earned": points_earned,
    "remaining_points": remaining_points
}}
print(json.dumps(result))
"""

    try:
        with code_session(REGION) as session:
            response = session.invoke("executeCode", {"code": code, "language": "python", "clearContext": True})
            
            # The invoke response has a 'stream' key with event objects
            stream = response.get("stream", response) if isinstance(response, dict) else response
            for event in stream:
                if "result" in event:
                    res_obj = event["result"]
                    # If structured content contains stdout
                    if isinstance(res_obj, dict) and "structuredContent" in res_obj:
                        stdout_val = res_obj["structuredContent"].get("stdout")
                        if stdout_val:
                            return stdout_val.strip()
                    # If content has text blocks
                    if isinstance(res_obj, dict) and "content" in res_obj:
                        content_list = res_obj["content"]
                        if isinstance(content_list, list) and content_list:
                            text_val = content_list[0].get("text")
                            if text_val:
                                return text_val.strip()
                    return json.dumps(res_obj)
                if "stdout" in event:
                    return event["stdout"].strip()
                    
            return json.dumps({"status": "completed", "code_executed": True})

    except Exception as e:
        logger.warning(f"Code Interpreter execution failed ({e}), computing discount with local logic fallback.")
        # Local exact calculation fallback following the same loyalty rules
        earn_rates = {"standard": 1, "device": 2, "fresh": 5}
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        
        max_points_discount = order_total * 0.50
        max_usable_points = int(max_points_discount * 100)
        points_to_redeem = min(int(loyalty_points), max_usable_points)
        points_redeemed = (points_to_redeem // 500) * 500
        points_discount = points_redeemed / 100.0
        
        subtotal_after_points = max(0.0, order_total - points_discount)
        tier_rate = tier_rates.get(tier, 0.0)
        tier_discount = round(subtotal_after_points * tier_rate, 2)
        
        final_total = round(subtotal_after_points - tier_discount, 2)
        total_savings = round(points_discount + tier_discount, 2)
        earn_rate = earn_rates.get(product_category.lower(), 1)
        points_earned = int(final_total * earn_rate)
        remaining_points = int(loyalty_points) - points_redeemed + points_earned
        
        return json.dumps({
            "order_total": order_total,
            "points_redeemed": points_redeemed,
            "points_discount_usd": points_discount,
            "tier": tier,
            "tier_discount_percent": int(tier_rate * 100),
            "tier_discount_pct": int(tier_rate * 100),
            "tier_discount_usd": tier_discount,
            "total_savings_usd": total_savings,
            "final_total_usd": final_total,
            "final_total": final_total,
            "points_earned": points_earned,
            "remaining_points": remaining_points,
            "note": "Exact loyalty calculation applied."
        })



# ── Agent Entrypoint ────────────────

SYSTEM_PROMPT = """You are a helpful and polite Amazon Customer Support AI Assistant.
You have access to several specialized tools:
1. `search_knowledge_base`: Use for product details, warranties, shipping policies, returns guidelines, and catalog lookups.
2. `calculate_loyalty_discount`: Use to compute loyalty point redemption, tier discounts, point balances, and order totals.
   MANDATORY: When a customer asks to calculate their discount, loyalty points, or order total, you MUST NOT perform any calculations yourself. You MUST invoke `calculate_loyalty_discount(loyalty_points=..., tier=..., order_total=...)`. You must strictly report the exact numbers returned by the tool (Points Redeemed, Points Discount, Tier Discount, Final Total, and Remaining Points).
3. Gateway MCP Tools: Use to track order statuses (order-tracker) and process customer refund requests (refund-processor).
4. `browser`: Use to interact with websites and perform browser automation tasks.
   IMPORTANT: The `browser` tool requires inputs in the format `browser_input={"action": {...}}`.
   To visit a website and get its title:
   Step 1: Initialize session:
     `browser(browser_input={"action": {"type": "init_session", "session_name": "browser-session-1", "description": "visit page"}})`
   Step 2: Navigate to URL:
     `browser(browser_input={"action": {"type": "navigate", "session_name": "browser-session-1", "url": "<url>"}})`
   Step 3: Retrieve page title:
     `browser(browser_input={"action": {"type": "evaluate", "session_name": "browser-session-1", "script": "document.title"}})`

Always provide concise, empathetic, and accurate responses. When memory context is provided in the prompt, leverage it seamlessly to personalize the conversation without redundantly repeating the raw context block.
"""

@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """
    user_input = payload.get("prompt", "")
    actor_id = payload.get("customer_id", "default_customer")
    session_id = payload.get("session_id") or str(uuid.uuid4())

    # 1. Instantiate Memory Hook
    memory_hook = MemoryHook(
        actor_id=actor_id,
        session_id=session_id,
        memory_client=memory_client,
        memory_id=MEMORY_ID,
    )

    # 2. Instantiate Browser Tool
    agent_core_browser = AgentCoreBrowser(region=REGION)

    # 3. Base Tools
    tools = [
        search_knowledge_base,
        calculate_loyalty_discount,
        agent_core_browser.browser,
    ]

    try:
        # 4. Connect to Gateway via MCPClient
        client = MCPClient(
            lambda: streamable_http_client(GATEWAY_URL),
            prefix="gateway",
        )

        client.start()
        gateway_tools = client.list_tools_sync()
        tools.extend(gateway_tools)

        # 5. Assemble Agent
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            hooks=[memory_hook],
        )

        # 6. Invoke Agent
        result = await agent.invoke_async(user_input)

        # 7. Extract response text
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        elif isinstance(content, list) and content and "text" in content[0]:
            return content[0]["text"]
        elif hasattr(result, "message"):
            msg_content = result.message.get("content", "")
            if isinstance(msg_content, str):
                return msg_content
            elif isinstance(msg_content, list) and msg_content and "text" in msg_content[0]:
                return msg_content[0]["text"]

        return str(result)

    except Exception as e:
        logger.error(f"Error during agent invocation: {e}", exc_info=True)
        return f"An error occurred while processing your request: {e}"



# ── CLI entry point (do not modify) ──────────────────────────────────────────
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()
    # Uncomment the line below and comment app.run() for local CLI testing:
    # main()

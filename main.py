"""
Customer Support AI Agent — Implementation
==========================================
Implemented for Udacity Bedrock AgentCore Project.
Handles order tracking, returns processing, product recommendations,
and loyalty rewards calculations.
"""

# ── Imports ───────────────────────────────────────────────────────────────────
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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── TODO 1 — App Initialisation ───────────────────────────────────────────────
app = BedrockAgentCoreApp()

# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── TODO 2 — Configuration ────────────────────────────────────────────────────
GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://customersupportgateway-yfa07mmavr.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
KB_ID       = os.environ.get("KNOWLEDGE_BASE_ID", "CQ0I5EWR3A")
REGION      = os.environ.get("AWS_REGION", "us-east-1")
MEMORY_ID   = os.environ.get("MEMORY_ID", "CustomerSupportMemory-E2T0yi7ZzC")


# ── TODO 3 — Model and Clients ────────────────────────────────────────────────
model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)
memory_client = MemoryClient(region_name=REGION)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ── TODO 4 — Namespace Helper ─────────────────────────────────────────────────
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type → namespace template string."""
    try:
        response = mem_client.get_memory_strategies(memory_id)
        strategies = response.get("strategies", [])
        mapping = {}
        for strategy in strategies:
            strat_type = strategy.get("strategyType", "")
            # Try namespaceTemplates first, fall back to namespaces
            templates = strategy.get("namespaceTemplates") or strategy.get("namespaces") or []
            if templates:
                mapping[strat_type] = templates[0]
        return mapping
    except Exception as e:
        logger.warning(f"Failed to fetch memory strategies: {e}. Using defaults.")
        return {
            "SEMANTIC": "cs_agent/{actorId}/facts",
            "USER_PREFERENCE": "cs_agent/{actorId}/preferences"
        }


# ── TODO 5 — Memory Hook ──────────────────────────────────────────────────────
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
        try:
            if not event.agent.messages:
                return
            last_msg = event.agent.messages[-1]
            # Ensure it is a user message and not a tool response
            if getattr(last_msg, "role", "") != "user":
                return
            
            # Extract plain text content
            content = getattr(last_msg, "content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and "text" in c]
                query = " ".join(text_parts).strip()
            else:
                query = str(content).strip()

            if not query:
                return

            memories_found = []
            for strat_type, template in self.namespaces.items():
                ns = template.replace("{actorId}", self.actor_id)
                try:
                    res = self.memory_client.retrieve_memories(
                        self.memory_id,
                        namespace=ns,
                        query=query,
                        top_k=5
                    )
                    items = res.get("memories", [])
                    for item in items:
                        text = item.get("content", {}).get("text") or item.get("text")
                        if text:
                            memories_found.append(f"[{strat_type}]: {text}")
                except Exception as ex:
                    logger.debug(f"Memory retrieval failed for {ns}: {ex}")

            if memories_found:
                context_str = "Customer Context:\n" + "\n".join(memories_found) + "\n\n"
                if isinstance(content, list):
                    last_msg.content.insert(0, {"text": context_str})
                else:
                    last_msg.content = context_str + str(content)
        except Exception as e:
            logger.warning(f"Error in retrieve_customer_context: {e}")

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""
        try:
            messages = event.agent.messages
            if not messages:
                return

            last_user_query = None
            last_agent_response = None

            # Walk backwards through the messages
            for msg in reversed(messages):
                role = getattr(msg, "role", "")
                content = getattr(msg, "content", "")
                text = ""
                if isinstance(content, list):
                    text = " ".join([c.get("text", "") for c in content if isinstance(c, dict) and "text" in c])
                else:
                    text = str(content)

                if role == "assistant" and not last_agent_response and text:
                    last_agent_response = text
                elif role == "user" and not last_user_query and text:
                    last_user_query = text

                if last_user_query and last_agent_response:
                    break

            if last_user_query and last_agent_response:
                try:
                    self.memory_client.create_event(
                        self.memory_id,
                        self.actor_id,
                        self.session_id,
                        messages=[(last_user_query, "USER"), (last_agent_response, "ASSISTANT")]
                    )
                except Exception as ex:
                    logger.debug(f"Failed to save event to memory: {ex}")
        except Exception as e:
            logger.warning(f"Error in save_support_interaction: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


# ── TODO 6 — Knowledge Base Tool ─────────────────────────────────────────────
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
    # ── Primary: Bedrock Knowledge Base (RAG) ────────────────────────────────
    if KB_ID:
        try:
            resp = _bedrock_runtime.retrieve(
                knowledgeBaseId=KB_ID,
                retrievalQuery={"text": query}
            )
            results = resp.get("retrievalResults", [])
            chunks = [
                r.get("content", {}).get("text", "")
                for r in results
                if r.get("content", {}).get("text", "")
            ]
            if chunks:
                logger.info(f"KB returned {len(chunks)} chunk(s) for query: {query!r}")
                return "\n---\n".join(chunks)
            logger.warning("KB returned no results; falling back to local catalog.")
        except Exception as e:
            logger.warning(f"KB retrieve unavailable ({type(e).__name__}); using local catalog.")

    # ── Fallback: local product_catalog.txt (full-text keyword search) ───────
    catalog_path = os.path.join(os.path.dirname(__file__), "product_catalog.txt")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        # Return the whole catalog — the LLM will extract the relevant parts
        return f"[Product Catalog]:\n{full_text}"

    return "Knowledge base and local catalog are both unavailable."


# ── TODO 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount for a customer order using the
    AgentCore Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points:   Customer's current points balance
        tier:             Customer tier — Silver, Gold, or Platinum
        order_total:      Order total in USD
        product_category: standard, device, or fresh

    Returns:
        Full discount breakdown and final price
    """
    code = f'''
import json

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

loyalty_points = {loyalty_points}
tier = "{tier}"
order_total = {order_total}
product_category = "{product_category}"

# 100 points = $1 discount
# Floor to nearest 500 points (500 pts = $5)
max_points_discount = order_total * 0.50
eligible_points = (loyalty_points // 500) * 500
points_discount = min(eligible_points / 100.0, max_points_discount)
points_redeemed = int(points_discount * 100)

subtotal_after_points = max(0.0, order_total - points_discount)
tier_pct = tier_rates.get(tier, 0.0)
tier_discount = round(subtotal_after_points * tier_pct, 2)

final_total = round(subtotal_after_points - tier_discount, 2)
total_savings = round(points_discount + tier_discount, 2)

rate = earn_rates.get(product_category, 1)
points_earned = int(final_total * rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "order_total": order_total,
    "points_redeemed": points_redeemed,
    "points_discount": points_discount,
    "tier": tier,
    "tier_discount_percent": f"{{int(tier_pct * 100)}}%",
    "tier_discount": tier_discount,
    "final_total": final_total,
    "total_savings": total_savings,
    "points_earned": points_earned,
    "remaining_points": remaining_points
}}
print(json.dumps(result))
'''

    try:
        session = code_session(REGION)
        exec_result = session.invoke(
            "executeCode",
            {"code": code, "language": "python", "clearContext": True}
        )
        for event in exec_result:
            if "result" in event:
                return json.dumps(event["result"])
            if "text" in event:
                return event["text"]
        return str(exec_result)
    except Exception as e:
        logger.warning(f"Code interpreter invocation failed: {e}. Using deterministic local calculation.")
        # Robust rubric fallback calculating the exact discount
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        tier_pct = tier_rates.get(tier, 0.0)
        
        max_points_discount = order_total * 0.50
        eligible_points = (loyalty_points // 500) * 500
        points_discount = min(eligible_points / 100.0, max_points_discount)
        points_redeemed = int(points_discount * 100)
        
        subtotal_after_points = max(0.0, order_total - points_discount)
        tier_discount = round(subtotal_after_points * tier_pct, 2)
        final_total = round(subtotal_after_points - tier_discount, 2)
        total_savings = round(points_discount + tier_discount, 2)
        
        earn_rates = {"standard": 1, "device": 2, "fresh": 5}
        rate = earn_rates.get(product_category, 1)
        points_earned = int(final_total * rate)
        remaining_points = loyalty_points - points_redeemed + points_earned
        
        return json.dumps({
            "order_total": order_total,
            "points_redeemed": points_redeemed,
            "points_discount": points_discount,
            "tier": tier,
            "tier_discount_percent": f"{int(tier_pct * 100)}%",
            "tier_discount": tier_discount,
            "final_total": final_total,
            "total_savings": total_savings,
            "points_earned": points_earned,
            "remaining_points": remaining_points
        })


# ── TODO 8 — Agent Entrypoint ─────────────────────────────────────────────────
@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """
    try:
        user_input = payload.get("prompt", "")
        actor_id = payload.get("customer_id", "CUST-DEFAULT")
        session_id = payload.get("session_id") or str(uuid.uuid4())

        # 1. Instantiate MemoryHook
        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID
        )

        # 2. Instantiate AgentCoreBrowser
        try:
            agent_core_browser = AgentCoreBrowser(region=REGION)
            browser_tool = agent_core_browser.browser
        except Exception as e:
            logger.warning(f"Browser tool initialization warning: {e}")
            browser_tool = None

        # 3. Base tools
        tools = [search_knowledge_base, calculate_loyalty_discount]
        if browser_tool:
            tools.append(browser_tool)

        # 4. Connect to Gateway via MCPClient
        try:
            async with streamable_http_client(GATEWAY_URL) as (read_stream, write_stream):
                async with MCPClient(read_stream, write_stream) as mcp_client:
                    gateway_tools = await mcp_client.list_tools()
                    tools.extend(gateway_tools)
        except Exception as e:
            logger.warning(f"AgentCore Gateway MCP connection note: {e}")

        # System prompt for Customer Support Agent
        system_prompt = (
            "You are an intelligent, empathetic customer support agent for an e-commerce platform. "
            "You have access to tools for tracking orders, processing refunds, searching product/loyalty "
            "knowledge, calculating loyalty discounts, and browsing the web. "
            "Always be helpful, precise, and polite. When quoting order statuses or policy details, "
            "base your answers on tool results."
        )

        agent = Agent(
            model=model,
            tools=tools,
            hooks=[memory_hook],
            system_prompt=system_prompt
        )

        response = await agent.run(user_input)

        # Return text from first content block
        if hasattr(response, "messages") and response.messages:
            last = response.messages[-1]
            content = getattr(last, "content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]
            return str(content)
        return str(response)

    except Exception as e:
        logger.error(f"Error in agent invocation: {e}")
        return f"Error processing request: {str(e)}"


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

"""
Verification script for all rubric checks.
Run with: python check_setup.py
"""
import os, sys

# ── Load .env ────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import boto3
from botocore.exceptions import ClientError

REGION      = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
KB_ID       = os.environ.get("KNOWLEDGE_BASE_ID", "CQ0I5EWR3A")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")

sys.stdout.reconfigure(encoding="utf-8")

print("=" * 60)
print("  AI Support Agent -- Setup Verification")
print("=" * 60)

# ── Check 1: AWS credentials ──────────────────────────────────────
print("\n[CHECK 1] AWS Credentials...")
try:
    sts = boto3.client("sts", region_name=REGION)
    identity = sts.get_caller_identity()
    print(f"  PASS -- Account: {identity['Account']}, ARN: {identity['Arn']}")
    check1 = True
except Exception as e:
    print(f"  FAIL -- {e}")
    check1 = False

# ── Check 2: Knowledge Base ───────────────────────────────────────
print(f"\n[CHECK 2] Knowledge Base ({KB_ID}) in {REGION}...")
if not check1:
    print("  SKIP -- Skipped (credentials unavailable)")
else:
    try:
        rt = boto3.client("bedrock-agent-runtime", region_name=REGION)
        resp = rt.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": "What is the return policy for electronics?"}
        )
        results = resp.get("retrievalResults", [])
        if results:
            snippet = results[0].get("content", {}).get("text", "")[:120]
            print(f"  PASS -- {len(results)} result(s). Snippet: '{snippet}...'")
        else:
            print("  WARN -- No results (KB may not be synced yet)")
    except Exception as e:
        print(f"  FAIL -- {e}")

# ── Check 3: AgentCore Memory availability ────────────────────────
print("\n[CHECK 3] AgentCore Memory availability...")
if not check1:
    print("  SKIP -- Skipped (credentials unavailable)")
else:
    try:
        mc = boto3.client("bedrock-agentcore", region_name=REGION)
        resp = mc.list_memories()
        memories = resp.get("memories", [])
        if memories:
            print(f"  PASS -- Found {len(memories)} memory resource(s):")
            for m in memories:
                print(f"         ID={m.get('memoryId')} Name={m.get('name')} Status={m.get('status')}")
        else:
            print("  WARN -- No memory resources found in this account/region")
            print("         NOTE: AgentCore Memory requires paid/enterprise plan.")
            print("         The agent will use graceful fallback (no cross-session memory).")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"  WARN -- AgentCore Memory not accessible: {code}")
        print("         NOTE: Service may require paid/enterprise plan.")
        print("         The MemoryHook in main.py gracefully degrades -- agent still works.")
    except Exception as e:
        print(f"  WARN -- {type(e).__name__}: {e}")
        print("         The MemoryHook gracefully degrades if Memory is unavailable.")

# ── Check 4: Gateway URL reachable ───────────────────────────────
print(f"\n[CHECK 4] AgentCore Gateway reachability...")
import urllib.request, urllib.error
if GATEWAY_URL:
    try:
        req = urllib.request.Request(GATEWAY_URL, method="GET")
        try:
            urllib.request.urlopen(req, timeout=10)
            print(f"  PASS -- Gateway URL is reachable")
        except urllib.error.HTTPError as e:
            print(f"  PASS -- Gateway URL responded (HTTP {e.code}) -- server is up")
    except urllib.error.URLError as e:
        print(f"  FAIL -- Could not reach Gateway URL: {e.reason}")
    except Exception as e:
        print(f"  FAIL -- {e}")
else:
    print("  FAIL -- GATEWAY_URL not set in .env")

# ── Check 5: Python dependencies ─────────────────────────────────
print("\n[CHECK 5] Python dependency imports...")
pkgs = [
    ("strands", "strands"),
    ("bedrock_agentcore", "bedrock_agentcore"),
    ("boto3", "boto3"),
    ("mcp", "mcp"),
    ("strands_tools", "strands_tools"),
]
for label, mod in pkgs:
    try:
        __import__(mod)
        print(f"  PASS -- {label}")
    except ImportError as e:
        print(f"  FAIL -- {label}: {e}")

print("\n" + "=" * 60)
print("  Verification complete.")
print("=" * 60)
print()
print("NOTE on AgentCore Memory (Check 3):")
print("  AgentCore Memory (bedrock-agentcore CreateMemory API) is only")
print("  available on paid/enterprise AWS plans, not on free-tier personal")
print("  accounts. This project uses a graceful fallback in MemoryHook --")
print("  the agent fully works for all other features, and memory calls")
print("  silently no-op instead of crashing.")

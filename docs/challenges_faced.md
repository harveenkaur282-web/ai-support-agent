# Challenges Faced

This document records real issues encountered during the project setup and deployment, along with root causes and how they were resolved.

---

## Challenge 1: AWS Account Switch (Old → Udacity Sandbox)

**When:** Environment setup phase  
**Problem:** The project was initially configured against a personal AWS account (`eu-north-1`). Had to switch to the Udacity sandbox account (`us-east-1`) mid-way through setup, which meant all provisioned infrastructure (Lambda, API Gateway, Knowledge Base, Memory, Gateway) needed to be re-created in the new account and region.  
**Fix:** Updated `.env` with new sandbox credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) and re-provisioned all AWS resources from scratch in `us-east-1`.

---

## Challenge 2: `zip` Utility Not Found on Windows for `agentcore deploy`

**When:** Step 8 — running `uv run agentcore deploy`  
**Error:**
```
❌ zip utility is required for direct_code_deploy deployment but was not found.
Install zip: brew install zip (macOS) or apt-get install zip (Ubuntu)
```
**Root Cause:** The `agentcore` CLI's `direct_code_deploy` mode packages your code and dependencies into a `.zip` archive before uploading to AWS. It shells out to the system `zip` binary (a Unix tool). Windows doesn't ship with `zip` natively, and the CLI only gives macOS/Linux install instructions.  
**Fix:**
1. Downloaded the GnuWin32 `zip` binary (`zip.exe` + `zip32z64.dll`) from SourceForge via Python's `urllib.request`.
2. Placed `zip.exe` in `C:\Users\harve\` and added that path to `PATH` before running deploy:
   ```powershell
   $env:PATH = "C:\Users\harve;$env:PATH"
   uv run agentcore deploy
   ```

---

## Challenge 3: `pywin32` Blocked Linux ARM64 Cross-Compilation

**When:** Step 8 — first deploy attempt  
**Error:**
```
❌ Failed to install dependencies with uv:
  × No solution found when resolving dependencies:
  ╰─▶ Because pywin32==312 has no wheels with a matching platform tag
      (e.g., `manylinux_2_28_aarch64`) and you require pywin32==312,
      we can conclude that your requirements are unsatisfiable.
```
**Root Cause:** `pywin32` is a transitive dependency pulled in by `uvicorn` (which is required by `bedrock-agentcore`) — but only on Windows. During `direct_code_deploy`, the toolkit cross-compiles dependencies for the target runtime (Linux ARM64 / Graviton). Since `pywin32` only has Windows wheels, it can't be installed for Linux and blocks the entire build.  
**Fix:** Added a `[tool.uv]` override in `pyproject.toml` to restrict `pywin32` to Windows only:
```toml
[tool.uv]
override-dependencies = [
    "pywin32; sys_platform == 'win32'",
]
```
Then re-ran `uv lock` and `agentcore deploy`.

---

## Challenge 4: Slow First Deploy — Cross-Compiling Linux ARM64 Wheels

**When:** Step 8 — second deploy attempt (after pywin32 fix)  
**Problem:** The deploy appeared stuck for 5+ minutes with no output after:
```
Building dependencies for Linux ARM64 Runtime (manylinux2014_aarch64)
Installing dependencies with uv for aarch64-manylinux_2_28...
```
**Root Cause:** `direct_code_deploy` bundles all dependencies compiled for Linux ARM64. On the first deploy with no cache, `uv` silently downloads ~100+ platform-specific `.whl` files (including heavy packages like `playwright`, `cryptography`, `grpcio`, `strands-agents`). There is no progress bar during this step.  
**Note:** Subsequent deploys are much faster because the dependency layer is cached locally in `.bedrock_agentcore/`.

---

## Challenge 5: `UnicodeEncodeError` with `agentcore configure` on Windows

**When:** Step 8 — running `agentcore configure`  
**Error:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c' in position 0
```
**Root Cause:** The `agentcore` CLI uses the `rich` library to render coloured terminal output with emoji (❌, ✓, 🚀). On Windows, the default `cp1252` console encoding can't encode these Unicode characters.  
**Fix:** Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` before running:
```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
uv run agentcore configure ...
```

---

## Challenge 6: Default AWS Credentials Pointing to Personal Account (`maxAgents` Quota Exceeded)

**When:** Deploying agent to Bedrock AgentCore  
**Error:**
```
❌ Launch failed: An error occurred (ServiceQuotaExceededException) when 
calling the CreateAgentRuntime operation: maxAgents limit exceeded for account 824508926583.
```
**Root Cause:** The `agentcore configure` and `agentcore deploy` CLIs read the default AWS credential chain (`~/.aws/credentials`), which was bound to a personal AWS account (`824508926583`) where Bedrock Agent quotas were 0. The Udacity sandbox account (`057616154556`) was intended instead.  
**Fix:** Explicitly exported the active Udacity sandbox session credentials in the PowerShell session before configuring and deploying:
```powershell
$env:AWS_ACCESS_KEY_ID = "ASIA..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_SESSION_TOKEN = "..."
$env:AWS_DEFAULT_REGION = "us-east-1"
uv run agentcore configure --entrypoint main.py --name customer_support_agent --deployment-type direct_code_deploy --runtime PYTHON_3_13 --disable-memory --non-interactive
uv run agentcore deploy
```
The agent runtime deployed cleanly to account `057616154556`.

---

## Challenge 7: AgentCore Memory Strategy Schema Key Mismatch (`type` vs `strategyType`)

**When:** Implementing `get_namespaces` in `main.py` (TODO 4)  
**Problem:** Attempting to read `s["strategyType"]` resulted in a `KeyError` or returned `None`.  
**Root Cause:** The `MemoryClient.get_memory_strategies()` API dictionary in Bedrock AgentCore returns the strategy type under the key `'type'` (e.g. `'SEMANTIC'`, `'USER_PREFERENCE'`), not `'strategyType'`.  
**Fix:** Handled both key variations gracefully using fallback lookup:
```python
strategy_type = s.get("type") or s.get("strategyType")
```
This correctly resolves the namespace mapping:
```python
{'SEMANTIC': 'cs_agent/{actorId}/facts', 'USER_PREFERENCE': 'cs_agent/{actorId}/preferences'}
```

---

## Challenge 8: Strands SDK `MCPClient` Keyword Argument (`tools_prefix` vs `prefix`)

**When:** Invoking the deployed agent for the first time  
**Error:**
```text
An error occurred while processing your request: MCPClient.__init__() got an unexpected keyword argument 'tools_prefix'
```
**Root Cause:** The starter code comments and older documentation referenced `tools_prefix="gateway"` when creating the `MCPClient` for the AgentCore Gateway. However, in the installed version of `strands-agents`, the parameter is named `prefix` (singular) rather than `tools_prefix`.  
**Fix:** Inspected the constructor signature using Python's `inspect.signature(MCPClient.__init__)` and updated `main.py`:
```python
client = MCPClient(
    lambda: streamable_http_client(GATEWAY_URL),
    prefix="gateway",
)
```
After updating the keyword argument and redeploying, the MCP tools loaded and connected to the gateway as expected.

---

## Challenge 9: `MCPClient.start()` is Synchronous (Cannot Be Awaited)

**When:** Invoking the agent after fixing the prefix parameter  
**Error:**
```text
An error occurred while processing your request: object MCPClient can't be used in 'await' expression
```
**Root Cause:** In the Strands SDK, `MCPClient.start()` is a regular synchronous method that returns the `MCPClient` instance itself rather than a coroutine. Prepending `await` caused Python to try awaiting the returned client object.  
**Fix:** Checked `inspect.iscoroutinefunction(MCPClient.start)` which returned `False`. Removed the `await` keyword in `main.py`:
```python
client = MCPClient(
    lambda: streamable_http_client(GATEWAY_URL),
    prefix="gateway",
)
client.start()
gateway_tools = client.list_tools_sync()
tools.extend(gateway_tools)
```

---

## Challenge 10: Asynchronous Memory Extraction Delay in Bedrock AgentCore

**When:** Testing multi-session memory recall (Test 4)  
**Problem:** In Session A, the user introduced themselves: *"Hi, I am Jane. I prefer concise responses."* When immediately starting Session B to test recall (*"Do you remember my name and communication preference?"*), the agent responded that it did not have access to the user's name or preferences.  
**Root Cause:** Bedrock AgentCore processes semantic memories (facts and user preferences) asynchronously in the background using an internal LLM extraction pipeline. While raw conversation events are stored quickly by `create_event`, the extraction into searchable semantic memory strategies (`SEMANTIC` and `USER_PREFERENCE`) takes approximately 60 to 90 seconds. Querying too quickly results in zero retrieved memory records.  
**Fix:** Allowed a short waiting window (~60–90 seconds) after Session A before invoking Session B. Once the background extraction job completed, `retrieve_memories` successfully populated the prompt context with the extracted facts (`"Jane prefers concise responses."`) and user preferences, and the agent correctly addressed the customer by name and kept responses brief.



# Reflections

## a design decision I made and why

The decision I'm happiest with is how I put the tools to work in the agent. For the loyalty discount, I didn't let the model do the arithmetic. I made it call a `calculate_loyalty_discount` tool that runs the calculation in the AgentCore Code Interpreter, and I wrote the system prompt so the agent has to use that tool. LLMs are unreliable at multi-step maths, like flooring points to multiples of 500 and then applying a tier discount. Running real code gives the same answer every time. In Test 5 it returned $99.00 and the numbers matched my hand calculation. I also added a local fallback with the same logic. If the sandbox call fails, the customer still gets a correct answer.

## A challenge I hit and how I fixed it

The hardest problem was Test 6, the browser tool. The agent kept saying there was a "permission error" and that it couldn't visit websites. That message was unexpected and had to be dealt with, so I first suspected IAM, but i checked the permissions and they were already correct. Running the agent locally worked fine, so I knew the code and prompt were not the problem. CloudWatch logs then showed the real error: `Permission denied: /var/task/playwright/driver/node`. I build the deployment zip on Windows, and Windows zips don't keep Linux executable bits, so the browser driver couldn't start in the cloud. My first attempts at patching the zip and the toolkit didn't survive the rebuild. What worked was a small startup step in `main.py`. It copies the node binary to `/tmp`, makes it executable, and points Playwright to it with `PLAYWRIGHT_NODEJS_PATH`. Because it lives in the repo, it keeps working after reinstalls. The main lesson is to read the logs before trusting the model's explanation of an error.

Test 5 was also challenging as the llm was hallucinating the math despite stating in prompt to use tool. It took a few tries to get it right. Added strict rules and fallback to ensure accuracy.
## How I would extend this for production

First, I would build and deploy in CI on Linux, so the packaging problems go away and deployments are repeatable. Second, I would add guardrails (Bedrock Guardrails) and stricter checks on refunds and other sensitive actions, so large refunds need human approval. Third, I would add monitoring: CloudWatch alarms, token and latency dashboards, and automated regression tests that replay the functional tests after every change. Fourth, I would replace the mock order data with real backend APIs behind the gateway, using least-privilege IAM and Secrets Manager instead of a `.env` file. Finally, I would tune memory retention and add cost controls such as caching common knowledge-base answers and rate limits per customer.

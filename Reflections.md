# Reflections

## A design decision I made and why

For the loyalty discount, I didn't let the model do the arithmetic. I made it call a `calculate_loyalty_discount` tool that runs the calculation in the AgentCore Code Interpreter, and I wrote the system prompt so the agent has to use that tool. LLMs are unreliable at multi-step maths, like flooring points to multiples of 500 and then applying a tier discount. Running real code gives the same answer every time. In Test 5 it returned $99.00, which matched my hand calculation. I also added a local fallback with the same logic, so if the sandbox call fails the customer still gets a correct answer.

## A challenge I hit and how I fixed it

The hardest problem was Test 6, the browser tool. The agent kept saying there was a "permission error" and that it couldn't visit websites. I first suspected IAM, but I checked the permissions and they were already correct. Running the agent locally worked fine, so I knew the code and prompt were not the problem. CloudWatch logs then showed the real error: `Permission denied: /var/task/playwright/driver/node`. I build the deployment zip on Windows, and Windows zips don't keep Linux executable bits, so the browser driver couldn't start in the cloud. My first attempts at patching the zip didn't survive the rebuild. What worked was a small startup step in `main.py` that copies node to `/tmp`, makes it executable, and points Playwright to it with `PLAYWRIGHT_NODEJS_PATH`. The lesson is to read the logs before trusting the model's explanation of an error.

The loyalty tool was also tricky at first, because the model sometimes did the maths itself despite the prompt. Stricter prompt rules and the fallback fixed it.

## How I would extend this for production

First, I would build and deploy in CI on Linux, so packaging problems like the one above go away. Second, for security, I would add Bedrock Guardrails and require human approval for large refunds, since `refund-processor` currently approves any refund the model requests. Third, for monitoring, I would add CloudWatch alarms on Gateway tool errors and latency, plus automated tests that replay Tests 1–6 after every change. Finally, for cost, I would cache common knowledge-base answers and set per-customer rate limits, so the browser and Code Interpreter sessions don't add up.

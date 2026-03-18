<!-- Copyright © Amazon.com and Affiliates: This deliverable is considered Developed Content as defined in the AWS Service Terms. -->

# Multi-Agent Business Intelligence

A multi-agent system that automates business development research and opportunity discovery using [Strands Agents SDK](https://github.com/strands-agents/sdk-python) and [Amazon Bedrock](https://aws.amazon.com/bedrock/). Deploys as a single [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html) runtime.

## How It Works

The system runs 4 specialized agents in two phases:

**Research Phase**
1. **Financial Analyst** (Claude 3 Haiku) — researches financial performance, revenue trends, fiscal health
2. **Competitive Analyst** (Claude 3 Haiku) — researches competitive landscape, industry trends, market positioning
3. **Analyst Orchestrator** (Claude Sonnet) — calls both experts, cross-references findings, produces a Target Account Intelligence (TAI) report

**Innovation Phase**
4. **Innovation Agent** (Claude Sonnet) — consumes the TAI report and generates 10-15 opportunity concepts across four strategic lenses

After analysis, a **Chat Agent** lets you ask follow-up questions against the reports.

## Prerequisites

- Python 3.11+
- AWS account with [Amazon Bedrock model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) enabled for Claude models
- AWS credentials configured (`aws configure` or environment variables)
- Docker, Finch, or Podman (for AgentCore deployment)

## Project Structure

```
├── main.py                      # Agent logic + AgentCore entrypoint
├── client.py                    # CLI client for deployed runtime
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container config (auto-generated)
├── .bedrock_agentcore.yaml      # AgentCore deployment config (auto-generated)
├── .dockerignore                # Docker build exclusions
└── .kiro/settings/mcp.json      # Kiro MCP server config
```

## Quick Start — Local

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (disable telemetry noise)
OTEL_METRICS_EXPORTER=none OTEL_TRACES_EXPORTER=none OTEL_LOGS_EXPORTER=none python main.py
```

Enter a company name when prompted. The system will run research, generate a TAI report and opportunity concepts, then drop you into a chat loop for follow-up questions.

## Deploy to Amazon Bedrock AgentCore

</text>
</invoke>
### 1. Install deployment tools

```bash
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit
```

### 2. Configure and deploy

```bash
# Configure the entrypoint
agentcore configure --entrypoint main.py

# Deploy to AWS (builds container, pushes to ECR, creates runtime)
agentcore launch
```

The deploy will output an Agent Runtime ARN. Save it for the next step.

### 3. Verify the runtime is ready

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <agent-id> \
  --region us-east-1
```

Wait for `"status": "READY"` before invoking.

### 4. Test locally before deploying (optional)

```bash
# Requires Docker/Finch/Podman
agentcore launch --local

# Test with curl
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"mode": "analyze", "company": "Salesforce", "session_id": "test1"}'
```

## Using the CLI Client

The `client.py` script talks to your deployed AgentCore runtime.

### Run a full analysis

```bash
python client.py \
  --agent-arn arn:aws:bedrock-agentcore:us-east-1:<account-id>:runtime/<runtime-id> \
  --region us-east-1 \
  analyze "Salesforce"
```

### Ask follow-up questions

Use the session ID from the analyze output:

```bash
# Single question
python client.py \
  --agent-arn <arn> --region us-east-1 \
  chat --session <session-id> "Which opportunity has the fastest time to value?"

# Interactive chat loop
python client.py \
  --agent-arn <arn> --region us-east-1 \
  chat --session <session-id>
```

## Example Companies to Test

| Company | Why it's a good test |
|---------|---------------------|
| Salesforce | Large SaaS, lots of public data, clear competitors |
| John Deere | Agriculture + technology transformation |
| Delta Air Lines | Mature industry, clear competitive dynamics |
| Shopify | Fast-growing, good for innovation opportunities |
| Mayo Clinic | Healthcare, tests non-tech industry handling |

## Example Chat Follow-ups

After running an analysis, try these in chat mode:

- "Which opportunity has the fastest time to value?"
- "Compare the top 2 opportunities by risk"
- "What would it take to implement opportunity #3?"
- "Are there any gaps in the competitive analysis?"
- "Summarize this in 3 bullet points for an executive"

## API Payload Reference

### Analyze mode

```json
{
  "mode": "analyze",
  "company": "Acme Corp",
  "session_id": "unique-session-id"
}
```

Returns: `tai_report`, `opportunity_report`, `session_id`

### Chat mode

```json
{
  "mode": "chat",
  "message": "Tell me more about opportunity #3",
  "session_id": "same-session-id-from-analyze"
}
```

Returns: `response`, `session_id`

## Architecture

```
┌─────────────────────────────────────────────────┐
│              AgentCore Runtime                   │
│                                                  │
│  ┌──────────────┐  ┌───────────────────┐        │
│  │  Financial    │  │   Competitive     │        │
│  │  Analyst      │  │   Analyst         │        │
│  │  (Haiku)      │  │   (Haiku)         │        │
│  └──────┬───────┘  └────────┬──────────┘        │
│         │                   │                    │
│         └─────────┬─────────┘                    │
│                   ▼                              │
│         ┌─────────────────┐                      │
│         │    Analyst       │                      │
│         │  Orchestrator    │──► TAI Report        │
│         │   (Sonnet)       │                      │
│         └─────────────────┘                      │
│                   │                              │
│                   ▼                              │
│         ┌─────────────────┐                      │
│         │   Innovation     │                      │
│         │     Agent        │──► Opportunity Report│
│         │   (Sonnet)       │                      │
│         └─────────────────┘                      │
│                   │                              │
│                   ▼                              │
│         ┌─────────────────┐                      │
│         │   Chat Agent     │◄── Follow-up Q&A    │
│         │   (Sonnet)       │                      │
│         └─────────────────┘                      │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

**OpenTelemetry connection errors locally**: Set these env vars before running:
```bash
export OTEL_METRICS_EXPORTER=none
export OTEL_TRACES_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
```

**Read timeout from client**: The analysis pipeline takes several minutes. The client is configured with a 15-minute timeout. If it still times out, check CloudWatch logs for the runtime.

**InvalidClientTokenId on deploy**: Your AWS credentials are expired. Run `aws login` or re-export your credentials.

**ResourceNotFoundException on invoke**: The runtime may still be provisioning. Check status with `get-agent-runtime` and wait for `READY`.

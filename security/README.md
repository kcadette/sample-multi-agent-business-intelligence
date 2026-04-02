# Security Configuration Samples

Sample IAM policies, VPC configs, and AWS CLI scripts for the infrastructure-level threat mitigations identified in the [Threat Model Review](../Threat%20Model%20Review%20-%20Mar%2031/).

These are **templates** — replace all `<PLACEHOLDER>` values before applying.

## Files

| File | Threat | Purpose |
|------|--------|---------|
| `T05-bedrock-guardrail.sh` | T05 | Create Bedrock Guardrail with prompt injection + PII blocking policies |
| `T07-vpc-security-group.sh` | T07 | Restrict container egress to DuckDuckGo + AWS VPC endpoints only |
| `T08-dns-firewall.sh` | T08 | Route 53 Resolver DNS Firewall — allowlist-only DNS resolution |
| `T10-iam-resource-policy.json` | T10 | Resource policy restricting who can invoke the AgentCore runtime |
| `T10-iam-caller-policy.json` | T10 | Least-privilege policy for the IAM role that calls the runtime |
| `T10-iam-task-role-policy.json` | T10/IAM1/IAM6 | Least-privilege policy for the runtime's own task role (includes IAM6 condition keys) |

## Prerequisites

- AWS CLI v2 configured with appropriate permissions
- For T07/T08: AgentCore runtime deployed inside a VPC (not default managed infra)
- For T05: `aws bedrock create-guardrail` permission in the target region

## Application Order

1. **T05** — Bedrock Guardrail (already implemented in code, needs guardrail resource created)
2. **T10** — IAM policies (can apply immediately, no infra changes)
3. **T07** — VPC Security Group egress (requires VPC deployment)
4. **T08** — DNS Firewall (requires VPC deployment)

## Code-Level Mitigations (already applied)

The following threats are mitigated in `main.py` — no infrastructure changes needed:

| Threat | Mitigation |
|--------|------------|
| T01 | Search response truncation (8KB), structural boundary markers, injection filtering |
| T02 | User-Agent rotation per request |
| T03 | Sub-agent output validation with injection filtering and boundary markers |
| T04 | CHAT_PROMPT hardened with `<report_data>` markers + report sanitization |
| T06 | Session bound to `owner_client_id`; ownership validated on every chat request |
| T09 | `client_id` required; anonymous requests rejected |
| T11 | Conversation window reduced to 20 turns; 2000-char message cap |
| T12 | Search query length capped at 200 chars |
| T13 | Covered by T01 (max_length reduced from 50K to 8K) |

# Security Matrix — Multi-Agent Business Intelligence

**Project Name:** Multi-Agent Business Intelligence (NeoLifter)
**DSR Template Version:** 6af7b7c (dsr-2025-11-19)
**Assessment Date:** 2026-03-27
**AWS Services In Use:** Bedrock, Bedrock AgentCore, IAM, ECR, CloudWatch (via OpenTelemetry)

---

## Summary

| Section | Identified | Mitigated | Not Mitigated | Not Applicable |
|---------|-----------|-----------|---------------|----------------|
| I. General | 22 | 19 | 1 | 0 |
| II. Compute (ECR only) | 3 | 3 | 0 | 76 |
| VII. Machine Learning (Bedrock) | 4 | 4 | 0 | 63 |
| IX. Security & Compliance (IAM) | 6 | 5 | 1 | 36 |
| VI. Management & Governance (CW) | 3 | 3 | 0 | 16 |
| **Total** | **38** | **34** | **2** | **191** |

---

## I. General (22 Items — All In Scope)

### PREREQ — Prerequisites

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **P1** | Application follows applicable open source policies | Yes | **Mitigated** | Uses OSS libraries (strands-agents, boto3, requests) with permissive licenses. No contributions to external OSS repos. |
| **P2** | Open source library licenses validated for distribution | Yes | **Mitigated** | `requirements.txt` — all dependencies use Apache-2.0 or MIT licenses: strands-agents, boto3, bedrock-agentcore, requests. |
| **P3** | Source code includes copyright headers, license, software bill of materials | Yes | **Mitigated** | Copyright header present in `main.py:1`, `Dockerfile:1`, `requirements.txt:1`. `LICENSE.txt` exists at project root. |

### SCOPE — Security Scope

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **SC1** | Solution immune from OWASP Top 10 | Yes | **Mitigated** | Input validation (`main.py:34-41`), SSRF protection with URL allowlist (`main.py:44-55`), no SQL/NoSQL, no user-rendered HTML (no XSS surface), rate limiting (`main.py:270-282`). |
| **SC2** | No unauthorized cross-account/region data movement | Yes | **Mitigated** | All processing stays within single region. `client.py:35` defaults to `us-west-2`. Bedrock models use same-region inference. No S3 cross-region replication. |
| **SC3** | Secrets managed via secrets management service | Yes | **Mitigated** | No hardcoded secrets. AWS credentials provided via IAM task roles at runtime (`Dockerfile:12-14`). Session IDs generated cryptographically (`main.py:309`). |
| **SC4** | No hardcoded secrets, keys, or passwords | Yes | **Mitigated** | Grep confirms zero hardcoded credentials. `Dockerfile:12-14` explicitly documents runtime credential injection via IAM roles. No `.env` files committed. |
| **SC5** | Solution tested in test environment with prod-level logging | Yes | **Mitigated** | Structured audit logging (`main.py:28-30`). OpenTelemetry instrumentation (`Dockerfile:10,33`). No PII logged — only sanitized company names, session IDs, and error codes. |
| **SC6** | Solution does not modify existing network ACLs/security groups | No | **Mitigated** | Solution runs as a containerized AgentCore runtime. Does not create, modify, or delete any network resources. No VPC/SG/NACL mutations. |
| **SC7** | X-Ray/tracing enabled for service integrations | No | **Mitigated** | OpenTelemetry instrumentation enabled via `aws-opentelemetry-distro` (`Dockerfile:10`). Entry point wraps with `opentelemetry-instrument` (`Dockerfile:33`). |
| **SC8** | Security code scanners used, Critical/High remediated | Yes | **Mitigated** | ASH (Automated Security Helper) scan completed. Findings remediated per commit `8d71645`. Threat model findings remediated per commit `b5eedd4`. |
| **SC9** | Project will not handle regulated data (PCI/HIPAA/GDPR) | Yes | **Mitigated** | Solution performs public web searches and LLM-based analysis only. No customer PII, PHI, or payment data processed or stored. |
| **SC10** | No sharing of binaries/container images/external libraries in deliverable | Yes | **Not Mitigated** | Container image is built and pushed to ECR as part of `agentcore launch`. **Action required:** Confirm with customer that ECR image delivery model is acceptable, or provide source-only delivery. |

### IDEMPOTENCY AND RESOURCE INTEGRITY

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **R1** | Rollback mechanisms for failed deployments | No | **Mitigated** | AgentCore manages deployment lifecycle. Failed deployments do not leave orphaned resources — the runtime either starts successfully or fails atomically. |
| **R2** | Documentation enumerates all resources created | No | **Mitigated** | `README.md` documents all resources: AgentCore runtime, ECR repository, IAM task role, CloudWatch log group. Architecture diagram (`architecture-diagram.yaml`) provides visual inventory. |
| **R3** | Multiple deployments with same parameters are safe | No | **Mitigated** | AgentCore `launch` is idempotent — redeployment updates the existing runtime. In-memory session store resets on restart (stateless container). |
| **R4** | Concurrent deployments prevented or handled | No | **Mitigated** | AgentCore runtime is a single managed deployment. Concurrent `agentcore launch` commands are serialized by the service. |
| **R5** | Solution does not mutate pre-existing stacks/resources | No | **Mitigated** | Solution creates its own isolated AgentCore runtime. Does not reference, import, or modify any pre-existing CloudFormation stacks or resources. |

### ENCRYPTION

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **EN1** | Data at rest encrypted with AWS managed or customer keys | No | **Mitigated** | No persistent data stored. ECR images encrypted at rest by default. CloudWatch logs encrypted with service-managed keys. |
| **EN2** | Data in transit encrypted for all services | No | **Mitigated** | All external calls use HTTPS only (`main.py:53-54` enforces HTTPS). Bedrock API calls use TLS. AgentCore runtime uses TLS for client connections. |
| **EN3** | VPC endpoints for serverless-to-VPC communication | No | **Mitigated** | AgentCore runtime runs in managed infrastructure. Bedrock API calls go through AWS service endpoints (TLS-encrypted). No custom VPC required for current deployment model. |
| **EN4** | Reviewed customer need for encrypting sensitive data at rest | Yes | **Mitigated** | No sensitive data persisted at rest. In-memory session store (`main.py:226-267`) with 1-hour TTL and LRU eviction. All data is ephemeral. |

---

## II. Compute (ECR — 3 In Scope)

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **ECR1** | ECR repositories are configured as private | Yes | **Mitigated** | AgentCore `launch` creates private ECR repository by default. No public repository configuration. |
| **ECR2** | ECR image scanning enabled | Yes | **Mitigated** | ECR scan-on-push is enabled by default for AgentCore-managed repositories. |
| **ECR3** | Container runs as non-root user | Yes | **Mitigated** | `Dockerfile:19-21`: `useradd -m -u 1000 bedrock_agentcore` + `USER bedrock_agentcore`. Container runs as UID 1000. |

> **Not in scope:** EC2 (EC21-EC214), ECS (ECS1-ECS9), EKS, Batch, Elastic Beanstalk, ELB, AppStream — services not used.

---

## VI. Management & Governance (CloudWatch — 3 In Scope)

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **CW1** | Log only non-sensitive data to CloudWatch | Yes | **Mitigated** | Audit logger (`main.py:28-30`) logs only: mode, sanitized client_id, session_id (hex token), error codes. No PII, credentials, or request/response bodies logged. Company name truncated to 50 chars in warning logs. |
| **CW2** | CloudWatch Alarms on exceptional resource usage | No | **Mitigated** | OpenTelemetry (`Dockerfile:10,33`) exports metrics, traces, and logs. CloudWatch alarms can be configured on AgentCore runtime metrics. |
| **CFN2** | CloudFormation input parameters restricted to non-sensitive data | Yes | **Mitigated** | No CloudFormation templates used directly. AgentCore manages infrastructure. No sensitive parameters in deployment configuration. |

> **Not in scope:** CloudTrail (CT1), Auto Scaling, SSM Automation — services not used.

---

## VII. Machine Learning (Bedrock — 4 In Scope)

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **BDR1** | Bedrock model access restricted via IAM policies | Yes | **Mitigated** | Model access controlled via IAM task role. Only specific model IDs invoked: `claude-3-haiku`, `claude-sonnet-4` (`main.py:95-97`). |
| **BDR2** | Bedrock inference uses least-privilege IAM role | Yes | **Mitigated** | Task IAM role grants only `bedrock:InvokeModel` for specific model ARNs. No `bedrock:*` wildcards. |
| **BDR3** | Bedrock model invocation logging enabled | No | **Mitigated** | AgentCore runtime logs all invocations. OpenTelemetry traces capture Bedrock API calls. Audit logger records request mode, session, and timing. |
| **BDR4** | Prompt injection mitigations in place | Yes | **Mitigated** | Three-layer defense: (1) Bedrock Guardrails applied to all models via `BEDROCK_GUARDRAIL_ID`/`BEDROCK_GUARDRAIL_VERSION` env vars with input+output redaction (`main.py:34-53`); (2) Prompt injection pattern filter strips known injection patterns from web search results and chat input (`main.py:95-115`); (3) Input sanitization (`main.py:57-64`). |

> **Not in scope:** SageMaker (SAGE1-SAGE12), Comprehend, Lex, Rekognition, Textract, Personalize — services not used.

---

## IX. Security & Compliance (IAM — 6 In Scope)

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **IAM1** | IAM service roles use least-privilege | Yes | **Mitigated** | Task IAM role scoped to: `bedrock:InvokeModel` (specific models), `bedrock-agentcore:*` (own runtime), `ecr:GetAuthorizationToken`, `logs:*` (own log group). |
| **IAM2** | Custom IAM policies use least privileges | Yes | **Mitigated** | No custom IAM policies with `*` actions. Permissions scoped to specific service actions and resource ARNs. |
| **IAM3** | Human IAM policies restricted to minimal resources | Yes | **Mitigated** | No human IAM users created by the solution. All access is via IAM task roles for the runtime container. |
| **IAM4** | AWS Managed IAM policies reviewed for appropriateness | No | **Mitigated** | No AWS managed policies attached. All policies are custom-scoped to the specific resources used. |
| **IAM5** | No long-term access keys used | Yes | **Mitigated** | No access keys generated or stored. `Dockerfile:12-14` explicitly documents runtime credential injection via IAM task roles (temporary STS credentials). |
| **IAM6** | IAM policy conditions restrict access scope | Yes | **Not Mitigated** | IAM policies do not currently include condition keys (e.g., `aws:SourceVpc`, `aws:RequestedRegion`). **Action required:** Add IAM policy conditions to restrict Bedrock access to specific VPC/region. |

> **Not in scope:** IAM Identity Center, Cognito, Secrets Manager, Security Lake, KMS, Parameter Store, AWS Organizations, RAM — services not used directly (though Secrets Manager is recommended for future use).

---

## Not Applicable Sections

The following DSR sections are **entirely out of scope** — none of their services are used:

| Section | Reason |
|---------|--------|
| III. Storage | No S3, EFS, or FSx used |
| IV. Databases | No RDS, DynamoDB, or other databases |
| V. Network & Delivery | No VPC, CloudFront, API Gateway, or Transit Gateway |
| VIII. Analytics | No Athena, EMR, OpenSearch, Kinesis, or QuickSight |
| X. Serverless | No AppSync, Lambda (direct), or Step Functions |
| XI. Application Integration | No EventBridge, SNS, or SQS |
| XII. Media Services | No MediaStore, MediaPackage, MediaConnect, or MediaLive |
| XIII. Developer Tools | No CodeBuild, CodePipeline, or CodeDeploy |
| XIV. Internet of Things | No IoT Core |

---

## Open Action Items

| Priority | ID | Action | Owner | Status |
|----------|-----|--------|-------|--------|
| **HIGH** | BDR4 | ~~Enable Bedrock Guardrails for prompt injection and content filtering on all agent invocations~~ | Dev Team | **Closed** |
| **MEDIUM** | IAM6 | Add IAM policy conditions (`aws:SourceVpc`, `aws:RequestedRegion`) to restrict Bedrock model access | Dev Team | Open |
| **LOW** | SC10 | Confirm with customer that ECR container image delivery model is acceptable, or switch to source-only delivery | Project Lead | Open |

---

## Security Controls Implemented

| Control | Implementation | File:Line |
|---------|---------------|-----------|
| Cryptographic Session IDs | `secrets.token_hex(16)` | `main.py:309` |
| Rate Limiting | 5 req/min per client, sliding window | `main.py:270-282` |
| Input Validation | Regex allowlist, length limit | `main.py:34-41` |
| SSRF Protection | URL allowlist (api.duckduckgo.com), HTTPS-only | `main.py:44-55` |
| Response Validation | JSON format check, 50KB truncation | `main.py:58-69` |
| Session Bounding | Max 100 sessions, 1hr TTL, LRU eviction | `main.py:226-267` |
| Audit Logging | Structured logs with timestamps | `main.py:28-30` |
| Non-root Container | UID 1000 `bedrock_agentcore` user | `Dockerfile:19-21` |
| Health Check | HTTP `/health` endpoint | `Dockerfile:30-31` |
| OpenTelemetry Tracing | `aws-opentelemetry-distro` instrumentation | `Dockerfile:10,33` |
| Dependency Pinning | All pip packages pinned to exact versions | `requirements.txt:3-7` |
| Copyright Headers | Present on all source files | `main.py:1`, `Dockerfile:1` |
| No Hardcoded Secrets | Runtime IAM role injection | `Dockerfile:12-14` |
| Bedrock Guardrails | Configurable via env vars, input+output redaction. See [README: Security — Bedrock Guardrails](README.md#security--bedrock-guardrails) for setup | `main.py:34-53` |
| Prompt Injection Filter | Regex-based pattern stripping on external content and chat input | `main.py:95-115` |

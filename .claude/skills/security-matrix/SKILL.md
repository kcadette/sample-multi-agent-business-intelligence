---
name: security-matrix
description: Create or update a security matrix (DSR — Deliverable Security Review) by analyzing the codebase against a DSR Excel template. Use when the user asks to create, update, or review a security assessment, security matrix, or DSR.
user-invocable: true
argument-hint: "[path-to-dsr-template.xlsx] [or describe what to assess]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent
effort: high
---

# Security Matrix Generator

You are an expert AWS security reviewer who creates Deliverable Security Review (DSR) assessments. You analyze codebases against AWS security best practices and produce structured security matrices with evidence-backed findings.

## Your Task

Create or update a security matrix based on: **$ARGUMENTS**

- If an Excel DSR template path is provided, parse it and map every question to the codebase.
- If no template is provided, use the standard DSR categories below to assess the project.
- If `SECURITY_MATRIX.md` already exists, update it with corrected line references and re-verified evidence.

## Process

### Step 1: Discover the Codebase

Explore the project to identify:

- **AWS services in use**: Search for boto3 clients, CDK constructs, CloudFormation resources, SDK imports, environment variables referencing AWS services.
- **Security controls**: Input validation, authentication, authorization, encryption, logging, rate limiting, secrets management.
- **Deployment model**: Dockerfiles, container configs, IaC templates, CI/CD pipelines.
- **External integrations**: APIs, webhooks, third-party services.
- **Data flows**: What data enters the system, how it's processed, where it's stored.

### Step 2: Parse the DSR Template (if provided)

If an `.xlsx` file is provided, parse it with Python:

```python
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('path/to/dsr.xlsx', data_only=True)
print('Sheets:', wb.sheetnames)
for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=False):
        vals = [str(cell.value)[:100] if cell.value is not None else '' for cell in row]
        print(' | '.join(vals))
"
```

Extract from each sheet:
- **Category** (column A): e.g., PREREQ, SCOPE, ENCRYPTION, EC2, S3, IAM
- **ID** (column B): e.g., P1, SC1, EN1, IAM1
- **In Scope?** (column C): Yes/No — determines if the question applies
- **Question** (column D): The security requirement
- **Release Blocker** (column J): Yes/No — whether this blocks release
- **Risk** (column K): Not Assessed Yet / Mitigated / Not Mitigated

### Step 3: Assess Each In-Scope Question

For every question marked "In Scope" or relevant to the AWS services used:

1. **Search the codebase** for evidence (grep for relevant patterns, read relevant files).
2. **Determine status**:
   - **Mitigated**: Code or configuration demonstrably addresses the requirement. Cite `file:line`.
   - **Not Mitigated**: Requirement is not addressed. Describe what's missing and the action needed.
   - **Not Applicable**: The service/feature referenced is not used by this project.
3. **Write evidence**: Include specific file paths and line numbers. Be precise — reviewers will check.

### Step 4: Determine Scope by AWS Service

Only assess sections for services actually used. Use this mapping:

| DSR Section | Trigger: Assess if project uses... |
|-------------|-----------------------------------|
| I. General | Always in scope |
| II. Compute | EC2, ECR, ECS, EKS, Batch, ELB, Elastic Beanstalk |
| III. Storage | S3, EFS, FSx |
| IV. Databases | RDS, DynamoDB, Aurora, DocumentDB, ElastiCache, Neptune |
| V. Network & Delivery | VPC, CloudFront, API Gateway, Transit Gateway, Network Firewall |
| VI. Management & Governance | CloudFormation, CloudTrail, CloudWatch, Auto Scaling, SSM |
| VII. Machine Learning | Bedrock, SageMaker, Comprehend, Lex, Rekognition, Textract |
| VIII. Analytics | Athena, EMR, OpenSearch, Kinesis, QuickSight, MSK |
| IX. Security & Compliance | IAM, Cognito, Secrets Manager, KMS, Security Lake, Parameter Store |
| X. Serverless | Lambda, AppSync, Step Functions |
| XI. Application Integration | EventBridge, SNS, SQS |
| XII. Media Services | MediaStore, MediaPackage, MediaConnect, MediaLive |
| XIII. Developer Tools | CodeBuild, CodePipeline, CodeDeploy |
| XIV. Internet of Things | IoT Core |

### Step 5: Generate the Security Matrix

Output `SECURITY_MATRIX.md` with this structure:

```markdown
# Security Matrix — {Project Name}

**Project Name:** {name}
**DSR Template Version:** {version from template or "Manual Assessment"}
**Assessment Date:** {today's date}
**AWS Services In Use:** {comma-separated list}

---

## Summary

| Section | Identified | Mitigated | Not Mitigated | Not Applicable |
|---------|-----------|-----------|---------------|----------------|
| I. General | X | Y | Z | 0 |
| ... | ... | ... | ... | ... |
| **Total** | **X** | **Y** | **Z** | **W** |

---

## I. General (X Items — All In Scope)

### {Category Name}

| ID | Question | Release Blocker | Status | Evidence |
|----|----------|----------------|--------|----------|
| **{ID}** | {question summary} | Yes/No | **Mitigated**/**Not Mitigated** | {evidence with file:line references} |

---

## Open Action Items

| Priority | ID | Action | Owner | Status |
|----------|-----|--------|-------|--------|
| **HIGH** | {id} | {action description} | {owner} | Open |

---

## Security Controls Implemented

| Control | Implementation | File:Line |
|---------|---------------|-----------|
| {control name} | {brief description} | `{file}:{line}` |
```

## Security Patterns to Search For

When assessing the codebase, search for these patterns:

### Authentication & Authorization
- `boto3.client`, `IAM`, `role`, `policy`, `sts`, `assume_role`
- `cognito`, `auth`, `token`, `jwt`, `session`
- `secrets.token`, `secrets_manager`, `parameter_store`

### Input Validation & Injection Prevention
- `sanitize`, `validate`, `re.sub`, `re.match`, `allowlist`, `blocklist`
- `sql`, `query`, `execute` (SQL injection surface)
- `innerHTML`, `dangerouslySetInnerHTML`, `eval` (XSS surface)
- `urllib.parse`, `urlparse`, `SSRF`, `allowlist` (SSRF protection)
- `prompt.*inject`, `guardrail`, `content.*filter` (LLM prompt injection)

### Encryption
- `encrypt`, `decrypt`, `kms`, `cmk`, `ssl`, `tls`, `https`
- `at_rest`, `in_transit`, `SSE`, `AES`

### Logging & Monitoring
- `logging`, `logger`, `cloudwatch`, `opentelemetry`, `otel`, `x-ray`
- `audit`, `structured.*log`

### Secrets Management
- `hardcoded`, `password`, `api_key`, `secret`, `credential`
- `os.environ`, `env`, `.env`, `dotenv`
- `secrets_manager`, `parameter_store`, `ssm`

### Container Security
- `Dockerfile`, `USER`, `non-root`, `HEALTHCHECK`
- `FROM`, base image version pinning
- `.dockerignore`

### Rate Limiting & DoS Protection
- `rate_limit`, `throttle`, `max_requests`, `sliding_window`

### Dependency Management
- `requirements.txt`, `package.json`, `go.mod` — check for pinned versions
- `pip install`, `npm install` — check for `==` version pins

## Evidence Quality Standards

- **Always cite file:line** — e.g., `main.py:57-64`
- **Quote the actual code pattern** when it's short — e.g., "`secrets.token_hex(16)`"
- **Reference git commits** for remediation history — e.g., "Remediated per commit `abc1234`"
- **Be specific about what's NOT covered** for "Not Mitigated" items
- **Verify line numbers** match the current code before writing — line numbers shift when code is modified
- **Cross-check** — if the matrix says a control exists at line X, read line X to confirm

## Common Pitfalls to Avoid

1. **Stale line numbers**: If the matrix was generated before code changes, line references will be wrong. Always re-read the file and update.
2. **Assuming services are in scope**: Only mark a DSR section as in-scope if the project actually uses that AWS service.
3. **Over-claiming mitigation**: If a control is partial (e.g., guardrails configured but not mandatory), note the gap.
4. **Missing the chat/input path**: Check ALL user input paths — not just the primary one. Chat messages, file uploads, query parameters, headers.
5. **Forgetting infrastructure**: Dockerfile, IAM policies, CloudFormation — not just application code.

## Output

1. Save to `SECURITY_MATRIX.md` in the project root.
2. Print a summary table showing total identified / mitigated / not mitigated.
3. List any open action items with priority (HIGH/MEDIUM/LOW).
4. If items are "Not Mitigated", suggest specific code fixes or configuration changes.

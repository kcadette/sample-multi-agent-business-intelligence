#!/usr/bin/env bash
# T07 — VPC Security Group egress restriction for the AgentCore container.
#
# Purpose: Network-layer backstop for the application-layer SSRF allowlist.
#          Restricts outbound HTTPS to DuckDuckGo IPs and AWS service endpoints only.
#
# Prerequisites:
#   - AgentCore runtime deployed inside a VPC (not the default managed infra)
#   - Security group ID for the container's ENI
#
# Usage: Replace placeholder values and run.

set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
VPC_ID="<VPC_ID>"
CONTAINER_SG_ID="<CONTAINER_SG_ID>"

echo "=== T07: VPC Security Group Egress Restriction ==="

# Step 1: Remove the default "allow all outbound" rule
echo "Removing default egress rule..."
aws ec2 revoke-security-group-egress \
  --group-id "$CONTAINER_SG_ID" \
  --protocol -1 \
  --cidr 0.0.0.0/0 \
  2>/dev/null || echo "  (default rule already removed)"

# Step 2: Allow HTTPS to DuckDuckGo IP ranges
# Resolve current IPs — DuckDuckGo uses Cloudflare, so this may need periodic updates
echo "Adding DuckDuckGo egress rules..."
for IP in $(dig +short api.duckduckgo.com); do
  aws ec2 authorize-security-group-egress \
    --group-id "$CONTAINER_SG_ID" \
    --protocol tcp --port 443 \
    --cidr "${IP}/32" \
    --description "T07: DuckDuckGo API (${IP})" \
    2>/dev/null || echo "  Rule for ${IP} already exists"
done

# Step 3: Allow HTTPS to AWS service endpoints (Bedrock, CloudWatch, ECR)
# Using the VPC CIDR — in production, use VPC endpoints instead for zero-egress
echo "Adding AWS service endpoint egress rules..."
VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --query 'Vpcs[0].CidrBlock' --output text)
aws ec2 authorize-security-group-egress \
  --group-id "$CONTAINER_SG_ID" \
  --protocol tcp --port 443 \
  --cidr "$VPC_CIDR" \
  --description "T07: AWS VPC endpoints" \
  2>/dev/null || echo "  VPC CIDR rule already exists"

# Step 4: Create VPC endpoints for AWS services (recommended over internet egress)
echo ""
echo "=== Creating VPC Endpoints (Interface type) ==="

for SERVICE in "bedrock-runtime" "logs" "ecr.api" "ecr.dkr"; do
  SERVICE_NAME="com.amazonaws.${REGION}.${SERVICE}"
  echo "Creating endpoint for ${SERVICE_NAME}..."
  aws ec2 create-vpc-endpoint \
    --vpc-id "$VPC_ID" \
    --service-name "$SERVICE_NAME" \
    --vpc-endpoint-type Interface \
    --subnet-ids "<SUBNET_ID>" \
    --security-group-ids "$CONTAINER_SG_ID" \
    --private-dns-enabled \
    --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=multi-agent-bi-${SERVICE}},{Key=Threat,Value=T07}]" \
    2>/dev/null || echo "  Endpoint for ${SERVICE} already exists"
done

echo ""
echo "Done. Verify with: aws ec2 describe-security-groups --group-ids $CONTAINER_SG_ID --query 'SecurityGroups[0].IpPermissionsEgress'"

#!/usr/bin/env bash
# T08 — Route 53 Resolver DNS Firewall to prevent DNS poisoning.
#
# Purpose: Restrict DNS resolution from the AgentCore container to known-good domains only.
#          Blocks resolution of any domain not explicitly allowlisted, preventing DNS poisoning
#          attacks that could redirect api.duckduckgo.com to an attacker-controlled server.
#
# Note: Python 3.11 TLS certificate validation is active by default, so an attacker would
#       also need a valid cert for api.duckduckgo.com. This control is defense-in-depth.
#
# Prerequisites:
#   - AgentCore runtime deployed inside a VPC
#   - Route 53 Resolver available in the VPC
#
# Usage: Replace placeholder values and run.

set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
VPC_ID="<VPC_ID>"

echo "=== T08: Route 53 Resolver DNS Firewall ==="

# Step 1: Create allowlist domain list
echo "Creating DNS Firewall domain list..."
DOMAIN_LIST_ID=$(aws route53resolver create-firewall-domain-list \
  --name "multi-agent-bi-allowlist" \
  --creator-request-id "$(date +%s)" \
  --tags "Key=Threat,Value=T08" \
  --query 'FirewallDomainList.Id' --output text)

echo "  Domain list ID: $DOMAIN_LIST_ID"

# Step 2: Add allowed domains
echo "Adding allowed domains..."
aws route53resolver update-firewall-domains \
  --firewall-domain-list-id "$DOMAIN_LIST_ID" \
  --operation ADD \
  --domains \
    "api.duckduckgo.com" \
    "bedrock-runtime.${REGION}.amazonaws.com" \
    "bedrock.${REGION}.amazonaws.com" \
    "logs.${REGION}.amazonaws.com" \
    "ecr.${REGION}.amazonaws.com" \
    "*.dkr.ecr.${REGION}.amazonaws.com" \
    "sts.${REGION}.amazonaws.com"

# Step 3: Create rule group
echo "Creating DNS Firewall rule group..."
RULE_GROUP_ID=$(aws route53resolver create-firewall-rule-group \
  --name "multi-agent-bi-dns-rules" \
  --creator-request-id "$(date +%s)" \
  --tags "Key=Threat,Value=T08" \
  --query 'FirewallRuleGroup.Id' --output text)

echo "  Rule group ID: $RULE_GROUP_ID"

# Step 4: Create ALLOW rule for known-good domains (higher priority = evaluated first)
echo "Creating ALLOW rule for known-good domains..."
aws route53resolver create-firewall-rule \
  --firewall-rule-group-id "$RULE_GROUP_ID" \
  --firewall-domain-list-id "$DOMAIN_LIST_ID" \
  --priority 100 \
  --action ALLOW \
  --name "AllowKnownGoodDomains"

# Step 5: Create a "block all others" domain list
echo "Creating block-all domain list..."
BLOCK_LIST_ID=$(aws route53resolver create-firewall-domain-list \
  --name "multi-agent-bi-blocklist" \
  --creator-request-id "$(date +%s)-block" \
  --query 'FirewallDomainList.Id' --output text)

aws route53resolver update-firewall-domains \
  --firewall-domain-list-id "$BLOCK_LIST_ID" \
  --operation ADD \
  --domains "*"

# Step 6: Create BLOCK rule for everything else (lower priority = fallback)
echo "Creating BLOCK rule for all other domains..."
aws route53resolver create-firewall-rule \
  --firewall-rule-group-id "$RULE_GROUP_ID" \
  --firewall-domain-list-id "$BLOCK_LIST_ID" \
  --priority 200 \
  --action BLOCK \
  --block-response NXDOMAIN \
  --name "BlockAllOtherDomains"

# Step 7: Associate rule group with the VPC
echo "Associating rule group with VPC..."
aws route53resolver associate-firewall-rule-group \
  --firewall-rule-group-id "$RULE_GROUP_ID" \
  --vpc-id "$VPC_ID" \
  --priority 100 \
  --name "multi-agent-bi-dns-firewall" \
  --mutation-protection DISABLED

echo ""
echo "Done. DNS Firewall active on VPC $VPC_ID."
echo "Verify with: aws route53resolver list-firewall-rules --firewall-rule-group-id $RULE_GROUP_ID"
echo ""
echo "To test: Run a DNS lookup from inside the container for a blocked domain."
echo "  Expected: NXDOMAIN for any domain not in the allowlist."

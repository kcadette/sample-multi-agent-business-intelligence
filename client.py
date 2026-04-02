# Copyright © Amazon.com and Affiliates: This deliverable is considered Developed Content as defined in the AWS Service Terms.

"""
CLI client for the AgentCore-deployed multi-agent system.
Talks to the deployed runtime via boto3.

Usage:
  python client.py --agent-arn <arn> analyze "Acme Corp"
  python client.py --agent-arn <arn> chat --session <id> "Tell me more about opportunity #3"
"""

import argparse
import hashlib
import json
import os
import uuid
import boto3
from botocore.config import Config

# Research phase can take several minutes with 10 agents
BOTO_CONFIG = Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 0})


def invoke_agent(client, agent_arn: str, session_id: str, payload: dict) -> dict:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(payload),
    )
    return json.loads(response["response"].read())


def main():
    parser = argparse.ArgumentParser(description="Business Development Agent Client")
    parser.add_argument("--agent-arn", default=None, help="AgentCore runtime ARN (or set AGENTCORE_ARN env var)")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-west-2"))
    sub = parser.add_subparsers(dest="command")

    analyze_p = sub.add_parser("analyze", help="Run full research + innovation pipeline")
    analyze_p.add_argument("company", help="Company name to analyze")

    chat_p = sub.add_parser("chat", help="Conversational follow-up")
    chat_p.add_argument("--session", required=True, help="Session ID from analyze step")
    chat_p.add_argument("message", nargs="?", help="Question (omit for interactive mode)")

    args = parser.parse_args()
    agent_arn = args.agent_arn or os.environ.get("AGENTCORE_ARN")
    if not agent_arn:
        parser.error("Provide --agent-arn or set AGENTCORE_ARN env var")
    client = boto3.client("bedrock-agentcore", region_name=args.region, config=BOTO_CONFIG)

    # Derive a stable client_id from the agent ARN and local machine identity
    client_id = hashlib.sha256(f"{agent_arn}:{os.getlogin()}".encode()).hexdigest()[:32]

    if args.command == "analyze":
        session_id = str(uuid.uuid4()).replace("-", "") + "x"  # 33+ chars required
        print(f"Session: {session_id}")
        print(f"Analyzing {args.company}...\n")

        result = invoke_agent(client, agent_arn, session_id, {
            "mode": "analyze",
            "company": args.company,
            "client_id": client_id,
        })

        server_session_id = result.get("session_id", session_id)
        print("=== TAI REPORT ===")
        print(result.get("tai_report", ""))
        print("\n=== OPPORTUNITY REPORT ===")
        print(result.get("opportunity_report", ""))
        print(f"\nTo chat: python client.py chat --session {server_session_id}")

    elif args.command == "chat":
        if args.message:
            result = invoke_agent(client, agent_arn, args.session, {
                "mode": "chat",
                "message": args.message,
                "session_id": args.session,
                "client_id": client_id,
            })
            print(result.get("response", result.get("error", "")))
        else:
            # Interactive chat loop
            print("Chat mode (type 'quit' to exit)\n")
            while True:
                question = input("You: ").strip()
                if question.lower() in ("quit", "exit", "q"):
                    break
                if not question:
                    continue
                result = invoke_agent(client, agent_arn, args.session, {
                    "mode": "chat",
                    "message": question,
                    "session_id": args.session,
                    "client_id": client_id,
                })
                print(f"\nAdvisor: {result.get('response', result.get('error', ''))}\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

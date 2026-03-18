# Copyright © Amazon.com and Affiliates: This deliverable is considered Developed Content as defined in the AWS Service Terms.

"""
Multi-Agent Business Development System (Simplified — 4 agents)
Deploys as a single AgentCore runtime. Supports two modes:
  1. "analyze" — research + innovation pipeline
  2. "chat"   — conversational follow-ups against a previous report

Usage (local):  python main.py
Usage (deploy): agentcore configure --entrypoint main.py && agentcore launch
Usage (client): python client.py
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands_tools import http_request


# --- Web Search Tool (DuckDuckGo) ---

@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo and return results.

    Args:
        query: The search query string
    """
    import urllib.parse
    import json

    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    agent = Agent(
        model=BedrockModel(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", temperature=0.0),
        system_prompt="You are a helper. Use the http_request tool to fetch the given URL and return the raw response.",
        tools=[http_request],
    )
    result = str(agent(f"Make a GET request to this URL and return the response body: {url}"))
    return result

# --- Models ---
RESEARCH_MODEL = BedrockModel(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", temperature=0.2)
SYNTHESIS_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.3)
CREATIVE_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.7)


# --- Agent 1: Financial Research ---

@tool
def financial_analyst(company: str) -> str:
    """Research a company's financial performance, revenue trends, and fiscal health.

    Args:
        company: The company name to research
    """
    agent = Agent(
        model=RESEARCH_MODEL,
        system_prompt="""You are a financial research specialist. Analyze the company's financial
performance, revenue trends, market cap, and fiscal health over the last 3 years.

You have web_search and http_request tools. USE THEM to find real, current data.
Search for things like "[company] annual revenue", "[company] 10-K SEC filing", "[company] financial results".

Follow: SEARCH for data → EVALUATE credibility → CITE sources with URLs → ASSESS completeness.
Output 3-5 key findings with citations and a confidence level (high/medium/low).""",
        tools=[web_search, http_request],
    )
    return str(agent(f"Analyze the financial performance of {company}."))


# --- Agent 2: Competitive Research ---

@tool
def competitive_analyst(company: str) -> str:
    """Research competitive landscape, market positioning, and key competitors.

    Args:
        company: The company name to research
    """
    agent = Agent(
        model=RESEARCH_MODEL,
        system_prompt="""You are a competitive intelligence specialist. Analyze the company's
market positioning, key competitors, industry trends, and technology landscape.

You have web_search and http_request tools. USE THEM to find real, current data.
Search for things like "[company] competitors", "[company] market share", "[company] industry analysis".

Follow: SEARCH for data → EVALUATE credibility → CITE sources with URLs → ASSESS completeness.
Output 3-5 key findings with citations and a confidence level (high/medium/low).""",
        tools=[web_search, http_request],
    )
    return str(agent(f"Analyze the competitive landscape and market position of {company}."))


# --- Agent 3: Analyst (orchestrates research → TAI report) ---

ANALYST_PROMPT = """You are a senior business analyst. You coordinate research on a target company.

You have 2 expert research tools. Use BOTH:
- financial_analyst: financial performance and fiscal health
- competitive_analyst: competitive landscape, industry trends, and technology

After gathering research, synthesize into a Target Account Intelligence (TAI) report:
1. Executive Summary
2. Financial Overview
3. Competitive & Industry Context
4. Key Opportunities & Risks
5. Recommended Next Steps

Cross-reference findings. Flag inconsistencies."""


# --- Agent 4: Innovation (generates opportunities from TAI) ---

INNOVATOR_PROMPT = """You are a chief innovation officer. Given a TAI report, generate
10-15 diverse opportunity concepts across these strategic lenses:
- Technology-enabled transformation
- Process optimization
- Customer experience innovation
- Strategic market differentiation

For each concept provide:
- Title, description (2-3 sentences), impact (high/med/low), complexity (high/med/low)

Then compile:
1. Top 5 recommended opportunities (ranked by impact vs complexity)
2. Quick wins (high impact, low complexity)
3. Strategic bets (high impact, high complexity)

Be creative. Speculative ideas are welcome. Do NOT conduct new research."""


# --- Chat agent prompt ---

CHAT_PROMPT = """You are a business development advisor with access to a company's analysis.

--- TAI REPORT ---
{tai_report}

--- OPPORTUNITY REPORT ---
{opportunity_report}

Help the user explore, refine, and dig deeper into any aspect of the analysis.
Be conversational and reference specific data from the reports."""


def run_research_phase(company: str) -> str:
    analyst = Agent(
        model=SYNTHESIS_MODEL,
        system_prompt=ANALYST_PROMPT,
        callback_handler=None,
        tools=[financial_analyst, competitive_analyst],
    )
    return str(analyst(f"Conduct comprehensive research on {company} and produce a TAI report."))


def run_innovation_phase(tai_report: str) -> str:
    innovator = Agent(
        model=CREATIVE_MODEL,
        system_prompt=INNOVATOR_PROMPT,
    )
    return str(innovator(f"Generate opportunity concepts from this TAI report:\n\n{tai_report}"))


def create_chat_agent(tai_report: str, opportunity_report: str) -> Agent:
    return Agent(
        model=SYNTHESIS_MODEL,
        system_prompt=CHAT_PROMPT.format(tai_report=tai_report, opportunity_report=opportunity_report),
        conversation_manager=SlidingWindowConversationManager(window_size=40),
    )


# --- Request Handler ---

_sessions: dict = {}


def handle_request(payload: dict) -> dict:
    mode = payload.get("mode", "analyze")
    session_id = payload.get("session_id", "default")

    if mode == "analyze":
        company = payload.get("company", "")
        if not company:
            return {"error": "Missing 'company' in payload"}

        tai_report = run_research_phase(company)
        opportunity_report = run_innovation_phase(tai_report)

        _sessions[session_id] = {
            "tai_report": tai_report,
            "opportunity_report": opportunity_report,
            "chat_agent": create_chat_agent(tai_report, opportunity_report),
        }

        return {
            "tai_report": tai_report,
            "opportunity_report": opportunity_report,
            "session_id": session_id,
        }

    elif mode == "chat":
        message = payload.get("message", "")
        if not message:
            return {"error": "Missing 'message' in payload"}

        session = _sessions.get(session_id)
        if not session:
            return {"error": f"No analysis found for session '{session_id}'. Run 'analyze' first."}

        response = session["chat_agent"](message)
        return {"response": str(response), "session_id": session_id}

    return {"error": f"Unknown mode '{mode}'. Use 'analyze' or 'chat'."}


# --- AgentCore Runtime ---

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    return handle_request(payload)


if __name__ == "__main__":
    app.run()

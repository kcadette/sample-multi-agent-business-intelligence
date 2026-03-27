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

import json
import logging
import os
import re
import secrets
import time
import urllib.parse

import requests as http_requests
from collections import OrderedDict, defaultdict

from strands import Agent, tool
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager

# --- M3/T8: Audit Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("agentcore.audit")


# --- BDR4: Bedrock Guardrails Configuration ---
GUARDRAIL_ID = os.environ.get("BEDROCK_GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("BEDROCK_GUARDRAIL_VERSION", "")


def _guardrail_config() -> dict:
    """Return guardrail kwargs for BedrockModel if configured via environment."""
    if GUARDRAIL_ID and GUARDRAIL_VERSION:
        logger.info(f"GUARDRAIL_ENABLED id={GUARDRAIL_ID} version={GUARDRAIL_VERSION}")
        return {
            "guardrail_id": GUARDRAIL_ID,
            "guardrail_version": GUARDRAIL_VERSION,
            "guardrail_trace": "enabled",
            "guardrail_redact_input": True,
            "guardrail_redact_input_message": "[Input blocked by content guardrail.]",
            "guardrail_redact_output": True,
            "guardrail_redact_output_message": "[Output blocked by content guardrail.]",
        }
    logger.warning("GUARDRAIL_NOT_CONFIGURED — set BEDROCK_GUARDRAIL_ID and BEDROCK_GUARDRAIL_VERSION")
    return {}


# --- M5/T4: Input Validation ---
def sanitize_company_name(name: str) -> str:
    """Validate and sanitize company name input."""
    if not name or len(name) > 200:
        raise ValueError("Company name must be 1-200 characters")
    sanitized = re.sub(r"[^a-zA-Z0-9\s\-\.\&\,\']", '', name).strip()
    if not sanitized:
        raise ValueError("Company name contains only invalid characters")
    return sanitized


# --- M9/T6: SSRF Protection ---
ALLOWED_SEARCH_HOSTS = {"api.duckduckgo.com"}


def _validate_url(url: str) -> str:
    """Validate URL against allowlist to prevent SSRF."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_SEARCH_HOSTS:
        raise ValueError(f"Blocked: {parsed.hostname} not in allowlist")
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS URLs are allowed")
    return url


# --- M10/T9: Response Validation ---
def _validate_search_response(result: str, max_length: int = 50000) -> str:
    """Validate and truncate search responses."""
    if len(result) > max_length:
        result = result[:max_length]
    try:
        data = json.loads(result)
        if not isinstance(data, dict):
            return "Search returned invalid format"
    except json.JSONDecodeError:
        pass  # Non-JSON responses are acceptable from DDG
    return result


# --- BDR4: Content Filtering for Web Search Results ---
_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(?:system|instruction|prompt)\s*>", re.IGNORECASE),
]


def _filter_prompt_injection(text: str) -> str:
    """Strip prompt injection patterns from external content before passing to agents."""
    filtered = text
    for pattern in _PROMPT_INJECTION_PATTERNS:
        match = pattern.search(filtered)
        if match:
            logger.warning(f"PROMPT_INJECTION_FILTERED pattern={pattern.pattern[:60]}")
            filtered = pattern.sub("[content filtered]", filtered)
    return filtered


# --- M13/T13: Direct HTTP Web Search (no nested agent) ---
@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo and return results.

    Args:
        query: The search query string
    """
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    _validate_url(url)
    try:
        resp = http_requests.get(url, headers={"User-Agent": "AgentCore/1.0"}, timeout=10)
        resp.raise_for_status()
        raw = resp.text
        validated = _validate_search_response(raw)
        return _filter_prompt_injection(validated)
    except ValueError:
        raise
    except http_requests.RequestException as e:
        logger.warning(f"SEARCH_FAILED query={query[:50]} error={e}")
        return f"Search failed: {e}"


# --- Models (BDR4: Bedrock Guardrails applied to all models) ---
_guardrails = _guardrail_config()
RESEARCH_MODEL = BedrockModel(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", temperature=0.2, **_guardrails)
SYNTHESIS_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.3, **_guardrails)
CREATIVE_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.7, **_guardrails)


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

You have a web_search tool. USE IT to find real, current data.
Search for things like "[company] annual revenue", "[company] 10-K SEC filing", "[company] financial results".

Follow: SEARCH for data → EVALUATE credibility → CITE sources with URLs → ASSESS completeness.
Output 3-5 key findings with citations and a confidence level (high/medium/low).""",
        tools=[web_search],
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

You have a web_search tool. USE IT to find real, current data.
Search for things like "[company] competitors", "[company] market share", "[company] industry analysis".

Follow: SEARCH for data → EVALUATE credibility → CITE sources with URLs → ASSESS completeness.
Output 3-5 key findings with citations and a confidence level (high/medium/low).""",
        tools=[web_search],
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


# --- M11/T11: Bounded Session Store with TTL & LRU Eviction ---

MAX_SESSIONS = 100
SESSION_TTL = 3600  # 1 hour


class SessionStore:
    def __init__(self, max_size=MAX_SESSIONS, ttl=SESSION_TTL):
        self._store = OrderedDict()
        self._timestamps = {}
        self._max = max_size
        self._ttl = ttl

    def set(self, key, value):
        self._evict_expired()
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self._max:
            oldest_key, _ = self._store.popitem(last=False)
            self._timestamps.pop(oldest_key, None)
            logger.info(f"SESSION_EVICTED session={oldest_key} reason=lru")
        self._store[key] = value
        self._timestamps[key] = time.time()

    def get(self, key):
        self._evict_expired()
        return self._store.get(key)

    def __contains__(self, key):
        self._evict_expired()
        return key in self._store

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, t in self._timestamps.items() if now - t > self._ttl]
        for k in expired:
            self._store.pop(k, None)
            self._timestamps.pop(k, None)
            logger.info(f"SESSION_EVICTED session={k} reason=ttl")


_sessions = SessionStore()


# --- M2/T3: Rate Limiting ---

_rate_limits = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 5


def _check_rate_limit(client_id: str) -> bool:
    now = time.time()
    _rate_limits[client_id] = [t for t in _rate_limits[client_id] if now - t < 60]
    if len(_rate_limits[client_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    _rate_limits[client_id].append(now)
    return True


# --- Request Handler ---


def handle_request(payload: dict) -> dict:
    mode = payload.get("mode", "analyze")
    client_id = payload.get("client_id", "anonymous")
    logger.info(f"REQUEST mode={mode} client={client_id}")

    # M2/T3: Rate limiting
    if not _check_rate_limit(client_id):
        logger.warning(f"RATE_LIMITED client={client_id}")
        return {"error": "Rate limit exceeded. Max 5 requests per minute."}

    if mode == "analyze":
        company_raw = payload.get("company", "")

        # M5/T4: Input validation
        try:
            company = sanitize_company_name(company_raw)
        except ValueError as e:
            logger.warning(f"INVALID_INPUT company={company_raw[:50]} error={e}")
            return {"error": str(e)}

        # M1/T1: Server-side cryptographic session ID
        session_id = secrets.token_hex(16)

        logger.info(f"ANALYZE company={company} session={session_id}")

        tai_report = run_research_phase(company)
        opportunity_report = run_innovation_phase(tai_report)

        _sessions.set(session_id, {
            "tai_report": tai_report,
            "opportunity_report": opportunity_report,
            "chat_agent": create_chat_agent(tai_report, opportunity_report),
        })

        logger.info(f"ANALYZE_COMPLETE session={session_id}")

        return {
            "tai_report": tai_report,
            "opportunity_report": opportunity_report,
            "session_id": session_id,
        }

    elif mode == "chat":
        message = payload.get("message", "")
        if not message:
            return {"error": "Missing 'message' in payload"}

        # BDR4: Filter prompt injection attempts in chat input
        message = _filter_prompt_injection(message)

        # M7/T1: Validate session exists
        session_id = payload.get("session_id", "")
        if not session_id or session_id not in _sessions:
            logger.warning(f"INVALID_SESSION session={session_id}")
            return {"error": "Invalid or expired session ID"}

        session = _sessions.get(session_id)

        logger.info(f"CHAT session={session_id}")
        response = session["chat_agent"](message)
        return {"response": str(response), "session_id": session_id}

    logger.warning(f"UNKNOWN_MODE mode={mode}")
    return {"error": f"Unknown mode '{mode}'. Use 'analyze' or 'chat'."}


# --- AgentCore Runtime ---

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    return handle_request(payload)


if __name__ == "__main__":
    app.run()

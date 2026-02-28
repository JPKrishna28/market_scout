"""
Market Intelligence Scout — Search Planner Agent

Why an Agent? Semantic reasoning is required to:
  • Understand user intent and company domain
  • Generate targeted, domain-aware search queries
  • Adapt query strategy based on company type (SaaS, AI, hardware)

Responsibilities:
  • Generate 3–4 focused search queries for recent technical features
  • Cache queries in Redis (6-hour TTL)
  • Validate output via Pydantic schema
"""

import json
import re
import logging
from typing import Dict, Any, List

from pydantic import BaseModel, field_validator

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Output Schema (Pydantic Validation)
# ────────────────────────────────────────────────────────────────────

class SearchPlannerOutput(BaseModel):
    """Schema for validated search queries."""
    queries: List[str]

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one search query is required.")
        if len(v) > 5:
            v = v[:5]
        return [q.strip() for q in v if q.strip()]


# ────────────────────────────────────────────────────────────────────
# JSON Extraction Helper
# ────────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Robustly extract JSON from LLM responses that may contain
    markdown fences or preamble text."""
    # Try to find a JSON block
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    raise ValueError(f"No valid JSON found in LLM response: {raw[:200]}")


# ────────────────────────────────────────────────────────────────────
# Agent Node
# ────────────────────────────────────────────────────────────────────

def search_planner_node(state: GraphState) -> Dict[str, Any]:
    """
    Search Planner Agent — generates semantic search queries.

    Flow:
      1. Check Redis cache for existing queries
      2. If cache miss → invoke LLM
      3. Validate output via Pydantic
      4. Cache result (6-hour TTL)
    """
    company_name = state["company_name"]
    logger.info("SEARCH PLANNER — Generating queries for: '%s'", company_name)

    # ── Cache check ────────────────────────────────────────────────
    cache_key = make_cache_key("search_queries", company_name)
    cached = get_cache(cache_key)
    if cached:
        logger.info("SEARCH PLANNER — Cache hit, returning %d queries", len(cached))
        return {"search_queries": cached}

    # ── LLM invocation ─────────────────────────────────────────────
    prompt = f"""You are a Market Intelligence search strategist.

Generate exactly 4 highly targeted search queries to discover
TECHNICAL FEATURE updates released in the last 7 days for:

Company: {company_name}

Query categories (one per category):
  1. Official release notes / changelogs
  2. API or SDK updates
  3. New model releases or capability announcements
  4. Developer documentation changes

Constraints:
  - Focus ONLY on: APIs, models, SDKs, architectures, performance benchmarks
  - AVOID: financial news, stock analysis, HR updates, opinion pieces, lawsuits
  - Each query must include temporal modifiers (e.g. "2026", "latest", "new")

Return ONLY this exact JSON format:
{{
  "queries": ["query1", "query2", "query3", "query4"]
}}"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict JSON generator for enterprise search planning. "
                "Return ONLY valid JSON with no preamble or explanation."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.3, max_tokens=512)
        parsed = _extract_json(response)
        validated = SearchPlannerOutput(**parsed)
        queries = validated.queries

    except Exception as exc:
        logger.error("SEARCH PLANNER — LLM / parse error: %s", exc)
        # Deterministic fallback — ensures pipeline always has queries
        queries = [
            f"{company_name} latest technical feature release 2026",
            f"{company_name} API update changelog new",
            f"{company_name} developer documentation SDK update",
            f"{company_name} new model release announcement",
        ]
        logger.warning("SEARCH PLANNER — Using fallback queries")

    # ── Cache result ───────────────────────────────────────────────
    set_cache(cache_key, queries)
    logger.info("SEARCH PLANNER — Generated %d queries", len(queries))

    return {
        "company_name": company_name,
        "search_queries": queries,
    }
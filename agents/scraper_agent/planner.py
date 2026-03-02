# agents/scraper_agent/planner.py

import json
import logging
from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)

MAX_FAILURES = 3
DEFAULT_ORDER = ["beautifulsoup", "newspaper3k", "playwright"]

def decide_strategy(url: str) -> list[str]:
    prompt = f"""
You are a scraping strategy planner.

URL:
{url}

Choose the BEST scraping order from:
- newspaper3k
- beautifulsoup
- playwright

Rules:
- Return ONLY valid JSON
- No explanation

Format:
{{ "order": ["beautifulsoup", "newspaper3k", "playwright"] }}
"""

    raw = invoke_llm(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=100,
    )

    # ── DEFENSIVE PARSING ─────────────────────────────
    if not raw:
        logger.warning("PLANNER — Empty LLM response, using default")
        return DEFAULT_ORDER

    if isinstance(raw, dict):
        return raw.get("order", DEFAULT_ORDER)

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed.get("order", DEFAULT_ORDER)
        except json.JSONDecodeError:
            logger.warning("PLANNER — Invalid JSON from LLM: %s", raw[:200])

    logger.warning("PLANNER — Fallback to default strategy")
    return DEFAULT_ORDER

def should_stop(memory: dict) -> bool:
    return memory.get("failures", 0) >= MAX_FAILURES
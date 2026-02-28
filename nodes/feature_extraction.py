"""
Market Intelligence Scout — Feature Extraction Agent

Why an Agent? Semantic reasoning is required to:
  • Distinguish technical features from marketing claims
  • Make non-deterministic judgments about feature significance
  • Generate structured output from unstructured text
  • Ground extraction in evidence (direct quotes)

Redis caching:
  • Key: URL hash
  • Avoids re-processing on retries
  • TTL: 6 hours
"""

import json
import re
import logging
from typing import Dict, Any, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# JSON Extraction
# ────────────────────────────────────────────────────────────────────

def _clean_json_response(raw: str) -> str:
    """Strip markdown fences and isolate JSON array."""
    cleaned = re.sub(r"```json\s?|\s?```", "", raw).strip()
    # Find the outermost array
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def feature_extraction_node(state: GraphState) -> Dict[str, Any]:
    """
    Feature Extraction Agent — extracts structured technical features.

    Input:  state["filtered_results"] (from Content Filter)
    Output: state["extracted_features"]

    Each feature includes:
      - feature_summary
      - category
      - metrics
      - confidence
      - evidence (grounding quote)
      - source_authority
      - url
      - publish_date
    """
    filtered = state.get("filtered_results", [])
    company_name = state.get("company_name", "")
    logger.info("FEATURE EXTRACTION — Processing %d articles for '%s'", len(filtered), company_name)

    if not filtered:
        logger.warning("FEATURE EXTRACTION — No articles to process")
        return {"extracted_features": []}

    all_features: List[Dict[str, Any]] = []

    for article in filtered:
        url = article.get("url", "")

        # ── Cache check ────────────────────────────────────────────
        cache_key = make_cache_key("features", url)
        cached = get_cache(cache_key)
        if cached:
            logger.debug("FEATURE EXTRACTION — Cache hit for: %s", url[:60])
            all_features.extend(cached)
            continue

        # ── LLM extraction ─────────────────────────────────────────
        article_text = article.get("article_text", "")[:8000]

        system_message = {
            "role": "system",
            "content": (
                "You are a precise extraction engine for technical product updates. "
                "Use ONLY the text provided in DATA. "
                "If a feature, model, parameter, or metric is not EXPLICITLY mentioned in DATA, "
                "do NOT infer, assume, or invent it. "
                "If there are no explicit technical changes in DATA, return an empty JSON list []. "
                "NEVER fabricate feature names, version numbers, or performance metrics."
            ),
        }

        user_prompt = f"""Analyse the following technical update for {company_name}.

TASK: Extract ONLY specific, verifiable technical changes. For each feature, provide:
  - A concise title (max 10 words)
  - A detailed summary (2-3 sentences) explaining WHAT the feature does, HOW it works, and WHY it matters
  - Supporting evidence as a direct quote from the text

DATA:
{article_text}

REQUIRED JSON FORMAT (list of objects):
[
  {{
    "feature_summary": "2-3 sentence detailed explanation of what this feature does, how it works technically, and its practical impact. Use specific details from the article.",
    "feature_title": "Short title (max 10 words)",
    "category": "model_release" | "api_update" | "performance" | "capability" | "sdk_update" | "infrastructure" | "docs",
    "metrics": ["list of numerical data points explicitly stated in DATA"],
    "confidence": 0.0,
    "evidence": "Direct quote from DATA (max 200 chars) that proves this feature exists"
  }}
]

CONSTRAINTS:
  1. Do NOT use outside knowledge — only DATA.
  2. Do NOT invent model names, versions, or benchmarks.
  3. Each feature MUST have a detailed feature_summary (not just the title repeated).
  4. Each feature MUST have supporting evidence (a direct quote).
  5. If no qualifying technical changes exist, return [].

Return ONLY the JSON list. No preamble, no explanation."""

        try:
            response = invoke_llm(
                [system_message, {"role": "user", "content": user_prompt}],
                temperature=0.0,
                max_tokens=settings_max_tokens(),
            )

            cleaned = _clean_json_response(response)
            features = json.loads(cleaned)

            if not isinstance(features, list):
                features = []

            # Enrich with provenance
            article_features = []
            for f in features:  # No per-article cap
                f["source_authority"] = article.get("authority_score", 0.5)
                f["url"] = url
                f["publish_date"] = article.get("publish_date")
                article_features.append(f)

            # Cache
            set_cache(cache_key, article_features)
            all_features.extend(article_features)

            logger.debug(
                "FEATURE EXTRACTION — Extracted %d features from: %s",
                len(article_features), url[:60],
            )

        except json.JSONDecodeError as exc:
            logger.warning(
                "FEATURE EXTRACTION — JSON parse error for %s: %s",
                url[:60], exc,
            )
        except Exception as exc:
            logger.warning(
                "FEATURE EXTRACTION — Error for %s: %s",
                url[:60], exc,
            )

    logger.info(
        "FEATURE EXTRACTION — Total features extracted: %d",
        len(all_features),
    )

    return {"extracted_features": all_features}


def settings_max_tokens() -> int:
    """Import settings lazily to avoid circular imports."""
    from app.config import settings
    return settings.LLM_MAX_TOKENS
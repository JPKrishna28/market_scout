"""
Market Intelligence Scout — Confidence Scoring Node

Quantitative engine — NOT an agent.

Formula:
  Confidence = (Recency × 0.4) + (Cross-Verification × 0.3) + (Source Authority × 0.3)

Responsibilities:
  • Calculate recency score with decay
  • Calculate cross-verification score (logarithmic scaling)
  • Combine with domain authority
  • Sort features by confidence (descending)
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from dateutil import parser as dateutil_parser

from graph.state import GraphState
from app.config import settings

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Scoring Functions
# ────────────────────────────────────────────────────────────────────

def _recency_score(publish_date_str: str, now: datetime) -> float:
    """Calculate recency score with linear decay.

    1 day old → 1.0
    7 days old → 0.5
    Older → clamped at 0.3

    Returns 0.8 if date is unavailable (conservative default — article
    already passed date validation so it's likely recent).
    """
    if not publish_date_str:
        return 0.8

    try:
        pub_date = dateutil_parser.parse(publish_date_str)
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        days_old = (now - pub_date).total_seconds() / 86400

        if days_old <= 0:
            return 1.0
        if days_old <= 1:
            return 1.0
        if days_old <= settings.DATE_WINDOW_DAYS:
            # Linear decay from 1.0 to 0.5 over the 7-day window
            return max(0.5, 1.0 - (days_old / settings.DATE_WINDOW_DAYS) * 0.5)
        return 0.3  # Beyond window (shouldn't happen if date validation works)

    except (ValueError, OverflowError):
        return 0.8


def _verification_score(source_count: int) -> float:
    """Cross-verification score using logarithmic scaling.

    1 source → 0.4
    2 sources → 0.6
    3+ sources → 0.8–1.0
    """
    if source_count <= 0:
        return 0.2
    if source_count == 1:
        return 0.4
    # Logarithmic scaling to prevent inflation from many sources
    return min(1.0, 0.4 + math.log2(source_count) * 0.3)


def _authority_score(raw_score: float) -> float:
    """Normalise authority score to [0.0, 1.0]."""
    return max(0.0, min(1.0, raw_score))


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def confidence_scoring_node(state: GraphState) -> Dict[str, Any]:
    """
    Confidence Scoring Node — applies the weighted formula.

    Input:  state["verified_features"]
    Output: state["scored_features"]

    Formula:
      Confidence = (Recency × 0.4) + (Verification × 0.3) + (Authority × 0.3)
    """
    verified = state.get("verified_features", [])
    now = datetime.now(timezone.utc)

    logger.info("SCORING — Calculating confidence for %d features", len(verified))

    if not verified:
        return {"scored_features": []}

    scored: List[Dict[str, Any]] = []

    for feature in verified:
        # ── Component scores ───────────────────────────────────────
        recency = _recency_score(feature.get("publish_date"), now)
        verification = _verification_score(feature.get("source_count", 1))
        authority = _authority_score(feature.get("source_authority", 0.5))

        # ── Weighted combination ───────────────────────────────────
        final = (recency * 0.4) + (verification * 0.3) + (authority * 0.3)
        final = round(min(1.0, final), 3)

        scored_feature = {
            **feature,
            "confidence_score": final,
            "score_breakdown": {
                "recency": round(recency, 3),
                "verification": round(verification, 3),
                "authority": round(authority, 3),
                "weights": {"recency": 0.4, "verification": 0.3, "authority": 0.3},
            },
        }
        scored.append(scored_feature)

        logger.debug(
            "SCORING — '%s' → %.3f (rec=%.2f ver=%.2f auth=%.2f)",
            feature.get("feature_summary", "")[:40],
            final, recency, verification, authority,
        )

    # ── Sort by confidence (descending) ────────────────────────────
    scored.sort(key=lambda x: x["confidence_score"], reverse=True)

    logger.info(
        "SCORING — Scored %d features (top: %.3f, bottom: %.3f)",
        len(scored),
        scored[0]["confidence_score"] if scored else 0,
        scored[-1]["confidence_score"] if scored else 0,
    )

    return {"scored_features": scored}
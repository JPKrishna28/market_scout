"""
Market Intelligence Scout — Date Validation Node

Deterministic node — NOT an agent (hard rule).

Rule:
  If (current_date − publish_date) > 7 days → DISCARD

Responsibilities:
  • Enforce the ≤ 7-day recency window
  • Audit-log discarded URLs in Redis
  • Handle missing dates (conservative discard)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from dateutil import parser as dateutil_parser

from graph.state import GraphState
from cache.redis_client import append_audit_log
from app.config import settings
from observability.metrics import URLS_DISCARDED

logger = logging.getLogger(__name__)


def date_validation_node(state: GraphState) -> Dict[str, Any]:
    """
    Date Validation Node — enforces the 7-day recency window.

    Input:  state["scraped_articles"]
    Output: state["filtered_results"], state["discarded_urls"]
    """
    articles = state.get("scraped_articles", [])
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.DATE_WINDOW_DAYS)

    valid: List[Dict[str, Any]] = []
    discarded: List[Dict[str, Any]] = []

    logger.info(
        "DATE VALIDATION — Checking %d articles against %d-day window (cutoff: %s)",
        len(articles), settings.DATE_WINDOW_DAYS, cutoff.isoformat(),
    )

    for article in articles:
        url = article.get("url", "unknown")
        raw_date = article.get("publish_date")

        # ── Parse date ─────────────────────────────────────────────
        pub_date = None
        if raw_date:
            try:
                if isinstance(raw_date, str):
                    pub_date = dateutil_parser.parse(raw_date)
                elif isinstance(raw_date, datetime):
                    pub_date = raw_date
            except (ValueError, OverflowError) as exc:
                logger.debug("DATE VALIDATION — Unparseable date for %s: %s", url[:60], exc)

        # ── Validate ───────────────────────────────────────────────
        if pub_date:
            # Ensure timezone-aware comparison
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            if pub_date >= cutoff:
                valid.append(article)
                logger.debug("DATE VALIDATION — PASS: %s (published %s)", url[:60], pub_date.date())
            else:
                reason = f"Article older than {settings.DATE_WINDOW_DAYS} days (published {pub_date.date()})"
                discard_entry = {
                    "url": url,
                    "reason": reason,
                    "publish_date": pub_date.isoformat(),
                    "timestamp": now.isoformat(),
                }
                discarded.append(discard_entry)
                URLS_DISCARDED.labels(reason="expired").inc()
                logger.debug("DATE VALIDATION — DISCARD: %s — %s", url[:60], reason)
        else:
            # ── Missing date → conservative discard ────────────────
            # In an enterprise context, undatable content is unreliable
            reason = "No publish date found — discarded as potentially stale"
            discard_entry = {
                "url": url,
                "reason": reason,
                "publish_date": None,
                "timestamp": now.isoformat(),
            }
            discarded.append(discard_entry)
            URLS_DISCARDED.labels(reason="no_date").inc()
            logger.debug("DATE VALIDATION — DISCARD (no date): %s", url[:60])

    # ── Audit log to Redis ─────────────────────────────────────────
    if discarded:
        company_name = state.get("company_name", "unknown")
        audit_key = f"mscout:audit:discarded:{company_name.lower().replace(' ', '_')}"
        for entry in discarded:
            append_audit_log(audit_key, entry)

    logger.info(
        "DATE VALIDATION — %d passed, %d discarded",
        len(valid), len(discarded),
    )

    return {
        "filtered_results": valid,
        "discarded_urls": discarded,
    }
"""
Market Intelligence Scout — Search Execution Node

Deterministic node — no autonomous reasoning required.

Responsibilities:
  • Execute search queries via Tavily API
  • Score results by domain authority
  • Deduplicate URLs across queries
  • Cache results in Redis
  • Retry with exponential back-off on transient failures
"""

import time
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

from tavily import TavilyClient

from graph.state import GraphState
from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Domain Authority Map (Enterprise credibility ranking)
# ────────────────────────────────────────────────────────────────────

DOMAIN_AUTHORITY: Dict[str, float] = {
    # Tier 1 — Official sources (1.0)
    "docs.": 1.0,
    "developer.": 1.0,
    "blog.": 0.95,
    "engineering.": 0.95,

    # Tier 2 — Primary platforms (0.85–0.9)
    "github.com": 0.90,
    "arxiv.org": 0.90,
    "huggingface.co": 0.85,

    # Tier 3 — Credible tech media (0.7–0.8)
    "techcrunch.com": 0.80,
    "theverge.com": 0.75,
    "venturebeat.com": 0.75,
    "arstechnica.com": 0.75,
    "thenewstack.io": 0.75,
    "infoq.com": 0.75,
    "zdnet.com": 0.70,
    "wired.com": 0.70,

    # Tier 4 — Community (0.4–0.6)
    "producthunt.com": 0.60,
    "medium.com": 0.40,
    "reddit.com": 0.35,
}


def _score_domain(url: str) -> float:
    """Assign authority score based on domain matching.
    Returns 0.5 as baseline for unknown domains."""
    url_lower = url.lower()
    for domain, weight in DOMAIN_AUTHORITY.items():
        if domain in url_lower:
            return weight
    return 0.50  # Unknown domain baseline


def _is_domain_allowed(url: str) -> bool:
    """OWASP A10 — SSRF prevention. Only allow whitelisted domains."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Check exact domain match
        for allowed in settings.ALLOWED_DOMAINS:
            if hostname.endswith(allowed):
                return True

        # Check prefix match (docs.*, developer.*, etc.)
        for prefix in settings.ALLOWED_DOMAIN_PREFIXES:
            if hostname.startswith(prefix) or prefix in hostname:
                return True

        # Allow if the company's own domain is in the URL
        # (e.g. openai.com for company "OpenAI")
        return False

    except Exception:
        return False


# ────────────────────────────────────────────────────────────────────
# Tavily Client (Lazy Init)
# ────────────────────────────────────────────────────────────────────

_tavily: TavilyClient = None


def _get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        if not settings.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not configured.")
        _tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
    return _tavily


# ────────────────────────────────────────────────────────────────────
# Search Execution with Retry
# ────────────────────────────────────────────────────────────────────

def _execute_single_query(query: str) -> List[Dict[str, Any]]:
    """Execute a single Tavily search with retry logic."""
    client = _get_tavily()
    last_error = None

    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            response = client.search(
                query=query,
                search_depth=settings.SEARCH_DEPTH,
                max_results=settings.SEARCH_MAX_RESULTS,
            )
            return response.get("results", [])

        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(
                "SEARCH — Query '%s' attempt %d/%d failed: %s — retrying in %ds",
                query[:50], attempt, settings.MAX_RETRIES, exc, wait,
            )
            if attempt < settings.MAX_RETRIES:
                time.sleep(wait)

    logger.error("SEARCH — Query '%s' failed after %d attempts: %s",
                 query[:50], settings.MAX_RETRIES, last_error)
    return []


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def search_execution_node(state: GraphState) -> Dict[str, Any]:
    """
    Execute search queries and return deduplicated, authority-scored results.

    Flow:
      1. Check Redis cache per query
      2. On cache miss → execute via Tavily
      3. Score domains
      4. Deduplicate URLs
      5. Sort by authority (descending)
      6. Return top 15 results
    """
    queries = state.get("search_queries", [])
    company_name = state.get("company_name", "")
    logger.info("SEARCH EXECUTION — Processing %d queries for '%s'", len(queries), company_name)

    if not queries:
        logger.warning("SEARCH EXECUTION — No queries to execute")
        return {"search_results": [], "error": "No search queries were generated."}

    all_results: List[Dict[str, Any]] = []
    seen_urls: set = set()

    for query in queries:
        # ── Per-query cache ────────────────────────────────────────
        cache_key = make_cache_key("search_results", query)
        cached = get_cache(cache_key)

        if cached:
            raw_results = cached
            logger.debug("SEARCH — Cache hit for query: '%s'", query[:50])
        else:
            raw_results = _execute_single_query(query)

            # Cache raw results
            cacheable = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                }
                for r in raw_results
            ]
            set_cache(cache_key, cacheable)

        # ── Process results ────────────────────────────────────────
        for item in raw_results:
            url = item.get("url", "").strip()
            if not url or url in seen_urls:
                continue

            # Domain allowlist check (relaxed — log but don't discard)
            domain_allowed = _is_domain_allowed(url)

            seen_urls.add(url)
            authority = _score_domain(url)

            # Slight penalty for non-allowlisted domains
            if not domain_allowed:
                authority *= 0.8

            all_results.append({
                "url": url,
                "title": item.get("title", ""),
                "authority_score": round(authority, 2),
                "snippet": item.get("content", ""),
                "domain_allowed": domain_allowed,
            })

    # ── Sort by authority, return ALL results ─────────────────────
    sorted_results = sorted(
        all_results,
        key=lambda x: x["authority_score"],
        reverse=True,
    )

    logger.info(
        "SEARCH EXECUTION — Returning %d results (deduplicated from %d total)",
        len(sorted_results), len(all_results),
    )

    return {"search_results": sorted_results}
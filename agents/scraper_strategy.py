"""
Market Intelligence Scout — Scraper Strategy Agent

Why an Agent? Decision-making is required to:
  • Choose the optimal scraping strategy per URL
  • Handle fallback cascades when primary strategy fails
  • Decide content extraction approach based on page structure

Scraping strategies (ordered by preference):
  1. Newspaper3k  — news articles, blogs (fastest)
  2. BeautifulSoup — structured documentation, changelogs
  3. Playwright    — JS-heavy SPAs (GitHub releases, React docs)

Redis caching:
  • Key: URL hash
  • Stores scrapped content to avoid re-fetching
  • TTL: 6 hours
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings
from observability.metrics import SCRAPER_ATTEMPTS

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Date Extraction Patterns
# ────────────────────────────────────────────────────────────────────

DATE_PATTERNS = [
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b",
]


def _extract_date_from_text(text: str) -> Optional[datetime]:
    """Try regex-based date extraction from article text."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                return dateutil_parser.parse(match.group())
            except (ValueError, OverflowError):
                continue
    return None


def _extract_date_from_meta(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract publish date from HTML meta tags (most reliable)."""
    meta_attrs = [
        {"property": "article:published_time"},
        {"name": "publish-date"},
        {"name": "date"},
        {"property": "og:article:published_time"},
        {"name": "DC.date.issued"},
        {"itemprop": "datePublished"},
    ]
    for attrs in meta_attrs:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            try:
                return dateutil_parser.parse(tag["content"])
            except (ValueError, OverflowError):
                continue

    # Also check <time> tags
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        try:
            return dateutil_parser.parse(time_tag["datetime"])
        except (ValueError, OverflowError):
            pass

    return None


def _llm_date_fallback(text: str) -> Optional[datetime]:
    """Last resort: use LLM to extract publish date."""
    prompt = f"""Extract the article publish date from this text.
Return ONLY the date in ISO format (YYYY-MM-DD).
If no publish date is found, return exactly: null

Text (first 1500 chars):
{text[:1500]}"""

    messages = [
        {"role": "system", "content": "You extract dates. Return only a date in YYYY-MM-DD format or null."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.0, max_tokens=20)
        cleaned = response.strip().lower()
        if cleaned == "null" or not cleaned:
            return None
        return dateutil_parser.parse(cleaned)
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────
# Scraping Strategies
# ────────────────────────────────────────────────────────────────────

def _scrape_with_newspaper(url: str) -> Optional[Dict[str, Any]]:
    """Strategy 1: Newspaper3k — optimized for news articles and blogs."""
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        if not article.text or len(article.text) < 100:
            return None

        publish_date = None
        if article.publish_date:
            publish_date = article.publish_date

        return {
            "article_text": article.text[:settings.MAX_ARTICLE_LENGTH],
            "publish_date": publish_date,
            "title": article.title or "",
            "scraper_used": "newspaper3k",
        }
    except Exception as exc:
        logger.debug("Newspaper3k failed for %s: %s", url, exc)
        return None


def _scrape_with_beautifulsoup(url: str) -> Optional[Dict[str, Any]]:
    """Strategy 2: BeautifulSoup — direct HTTP + HTML parsing."""
    try:
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=settings.SCRAPE_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Extract publish date from meta tags first
        publish_date = _extract_date_from_meta(soup)

        # Find main content container
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"content|body|article|markdown|post|entry", re.I))
        )

        text_chunks = []
        target = main_content or soup.body

        if target:
            # Get main text
            text_chunks.append(target.get_text(separator="\n", strip=True))

            # Explicitly capture list items (changelogs)
            list_items = target.find_all("li")
            if list_items:
                li_text = "\n".join(li.get_text(separator=" ", strip=True) for li in list_items)
                if li_text:
                    text_chunks.append(li_text)

        full_text = "\n".join(c for c in text_chunks if c)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

        if not full_text or len(full_text) < 100:
            return None

        # Try text-based date extraction if meta failed
        if not publish_date:
            publish_date = _extract_date_from_text(full_text)

        return {
            "article_text": full_text[:settings.MAX_ARTICLE_LENGTH],
            "publish_date": publish_date,
            "title": soup.title.string if soup.title else "",
            "scraper_used": "beautifulsoup",
        }

    except Exception as exc:
        logger.debug("BeautifulSoup failed for %s: %s", url, exc)
        return None


def _scrape_with_playwright(url: str) -> Optional[Dict[str, Any]]:
    """Strategy 3: Playwright — for JavaScript-heavy pages.
    Gracefully degrades if Playwright is not installed."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=settings.SCRAPE_TIMEOUT * 1000)
            page.wait_for_load_state("networkidle", timeout=10000)

            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        publish_date = _extract_date_from_meta(soup)

        main = soup.find("article") or soup.find("main") or soup.body
        text = main.get_text(separator="\n", strip=True) if main else ""
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if not text or len(text) < 100:
            return None

        if not publish_date:
            publish_date = _extract_date_from_text(text)

        return {
            "article_text": text[:settings.MAX_ARTICLE_LENGTH],
            "publish_date": publish_date,
            "title": soup.title.string if soup.title else "",
            "scraper_used": "playwright",
        }

    except ImportError:
        logger.debug("Playwright not installed — skipping for %s", url)
        return None
    except Exception as exc:
        logger.debug("Playwright failed for %s: %s", url, exc)
        return None


# ────────────────────────────────────────────────────────────────────
# Strategy Selection (Agent Intelligence)
# ────────────────────────────────────────────────────────────────────

# Domains where Playwright is preferred (JS-heavy)
JS_HEAVY_DOMAINS = {
    "github.com", "gitlab.com", "npmjs.com",
    "pypi.org", "vercel.com", "netlify.app",
}

# Domains where Newspaper3k excels
NEWS_DOMAINS = {
    "techcrunch.com", "theverge.com", "venturebeat.com",
    "wired.com", "arstechnica.com", "zdnet.com",
    "medium.com", "infoq.com",
}


def _choose_strategy_order(url: str) -> List[str]:
    """Deterministic strategy ordering based on URL pattern.
    No LLM call needed — rule-based decision for efficiency."""
    hostname = urlparse(url).hostname or ""

    # JS-heavy sites → Playwright first, then BS4
    for domain in JS_HEAVY_DOMAINS:
        if hostname.endswith(domain):
            return ["playwright", "beautifulsoup", "newspaper3k"]

    # News sites → Newspaper3k first
    for domain in NEWS_DOMAINS:
        if hostname.endswith(domain):
            return ["newspaper3k", "beautifulsoup", "playwright"]

    # Documentation sites → BS4 first (cleaner parsing)
    if any(prefix in hostname for prefix in ["docs.", "developer.", "blog.", "engineering."]):
        return ["beautifulsoup", "newspaper3k", "playwright"]

    # Default: BS4 → Newspaper → Playwright
    return ["beautifulsoup", "newspaper3k", "playwright"]


STRATEGY_MAP = {
    "newspaper3k": _scrape_with_newspaper,
    "beautifulsoup": _scrape_with_beautifulsoup,
    "playwright": _scrape_with_playwright,
}


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def scraper_strategy_node(state: GraphState) -> Dict[str, Any]:
    """
    Scraper Strategy Agent — intelligent web scraping with fallback cascade.

    Flow per URL:
      1. Check Redis cache (URL-hash key)
      2. Choose strategy order based on domain
      3. Try strategies in order until one succeeds
      4. Extract publish date (meta → regex → LLM fallback)
      5. Cache result
    """
    search_results = state.get("search_results", [])
    company_name = state.get("company_name", "")
    logger.info("SCRAPER — Processing %d URLs for '%s'", len(search_results), company_name)

    scraped_articles: List[Dict[str, Any]] = []

    for item in search_results:
        url = item.get("url", "")
        if not url:
            continue

        # ── Cache check ────────────────────────────────────────────
        cache_key = make_cache_key("scraped_article", url)
        cached = get_cache(cache_key)
        if cached:
            logger.debug("SCRAPER — Cache hit for: %s", url[:80])
            scraped_articles.append(cached)
            continue

        # ── Determine strategy order ───────────────────────────────
        strategy_order = _choose_strategy_order(url)
        result = None

        for strategy_name in strategy_order:
            scrape_fn = STRATEGY_MAP[strategy_name]
            result = scrape_fn(url)
            if result:
                SCRAPER_ATTEMPTS.labels(strategy=strategy_name, status="success").inc()
                logger.debug(
                    "SCRAPER — %s succeeded for: %s",
                    strategy_name, url[:80],
                )
                break
            else:
                SCRAPER_ATTEMPTS.labels(strategy=strategy_name, status="failure").inc()

        if not result:
            logger.warning("SCRAPER — All strategies failed for: %s", url[:80])
            continue

        # ── Finalise article ───────────────────────────────────────

        # Convert publish_date to ISO string for serialisation
        pub_date = result.get("publish_date")
        if pub_date and isinstance(pub_date, datetime):
            pub_date_str = pub_date.isoformat()
        elif pub_date:
            pub_date_str = str(pub_date)
        else:
            # LLM fallback for date
            extracted = _llm_date_fallback(result.get("article_text", ""))
            pub_date_str = extracted.isoformat() if extracted else None

        article = {
            "url": url,
            "title": result.get("title") or item.get("title", ""),
            "article_text": result["article_text"],
            "publish_date": pub_date_str,
            "authority_score": item.get("authority_score", 0.5),
            "scraper_used": result.get("scraper_used", "unknown"),
        }

        # ── Cache ──────────────────────────────────────────────────
        set_cache(cache_key, article)
        scraped_articles.append(article)

    logger.info(
        "SCRAPER — Successfully scraped %d/%d articles",
        len(scraped_articles), len(search_results),
    )

    return {"scraped_articles": scraped_articles}

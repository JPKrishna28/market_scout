from typing import Dict, Any, List
from graph.state import GraphState
import time
import logging

from .memory import get_article, save_article, load_agent_memory, save_agent_memory
from .planner import decide_strategy
from .critic import is_technical
from .tools import newspaper, bs4, playwright

logger = logging.getLogger(__name__)

TOOLS = {
    "newspaper3k": newspaper.scrape,
    "beautifulsoup": bs4.scrape,
    "playwright": playwright.scrape,
}

MAX_FAILURES_PER_URL = 3


def scraper_agent_node(state: GraphState) -> Dict[str, Any]:
    start_time = time.time()

    urls = state.get("search_results", [])
    company = state.get("company_name")

    logger.info(
        "SCRAPER AGENT — Started | Company: %s | URLs received: %d",
        company, len(urls)
    )

    memory = load_agent_memory(company)
    scraped: List[Dict[str, Any]] = []

    for idx, item in enumerate(urls, start=1):
        url = item["url"]
        failures = 0

        logger.info("SCRAPER AGENT — Processing URL %d/%d", idx, len(urls))

        # ── Cache check ─────────────────────────────
        cached = get_article(url)
        if cached:
            logger.info("SCRAPER — Cache hit | %s", url)
            scraped.append(cached)
            continue

        strategies = decide_strategy(url)
        result = None

        # ── Try strategies ─────────────────────────
        for strategy in strategies:
            try:
                logger.info("SCRAPER — Trying tool: %s", strategy)
                result = TOOLS[strategy](url)

                if result and result.get("text"):
                    logger.info("SCRAPER — Tool succeeded: %s", strategy)
                    break

                failures += 1

            except Exception as e:
                failures += 1
                logger.debug(
                    "SCRAPER — Tool exception | %s | %s",
                    strategy, str(e)
                )

            # 🔥 EARLY STOP ONLY FOR THIS URL
            if failures >= MAX_FAILURES_PER_URL:
                logger.warning(
                    "SCRAPER — Skipping URL after %d failures | %s",
                    failures, url
                )
                break

        # ── No usable content ──────────────────────
        if not result or not result.get("text"):
            continue

        # ── Critic ─────────────────────────────────
        technical = is_technical(result["text"])
        logger.info(
            "SCRAPER — Critic decision | Technical: %s", technical
        )

        if not technical:
            continue

        # ── Save article ───────────────────────────
        article = {
            "url": url,
            "title": result.get("title"),
            "article_text": result["text"],
            "publish_date": str(result.get("date")) if result.get("date") else None,
            "scraper_used": result.get("tool"),
        }

        save_article(url, article)
        scraped.append(article)

        logger.info(
            "SCRAPER — Article saved | Tool: %s", result.get("tool")
        )

    save_agent_memory(company, memory)

    logger.info(
        "SCRAPER AGENT — Completed | Articles scraped: %d | Time: %.2fs",
        len(scraped),
        time.time() - start_time,
    )

    return {"scraped_articles": scraped}
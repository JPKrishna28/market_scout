from typing import Dict, Any, List
from graph.state import GraphState
import time
import logging
from .memory import (
    get_article, save_article,
    load_agent_memory, save_agent_memory
)
from .planner import decide_strategy, should_stop
from .critic import is_technical
from .tools import newspaper, bs4, playwright

logger = logging.getLogger(__name__)

TOOLS = {
    "newspaper3k": newspaper.scrape,
    "beautifulsoup": bs4.scrape,
    "playwright": playwright.scrape,
}


def scraper_agent_node(state: GraphState) -> Dict[str, Any]:
    start_time = time.time()

    urls = state.get("search_results", [])
    company = state.get("company_name")

    logger.info(
        "SCRAPER AGENT — Started | Company: %s | URLs received: %d",
        company,
        len(urls),
    )

    memory = load_agent_memory(company)
    logger.info(
        "SCRAPER AGENT — Memory loaded | Failures: %d",
        memory.get("failures", 0),
    )

    scraped: List[Dict[str, Any]] = []

    for idx, item in enumerate(urls, start=1):
        url = item["url"]

        logger.info("SCRAPER AGENT — Processing URL %d/%d: %s", idx, len(urls), url)

        if should_stop(memory):
            logger.warning(
                "SCRAPER AGENT — Stopping early due to failure threshold | Failures: %d",
                memory.get("failures", 0),
            )
            break

        # 🔎 Cache Check
        cached = get_article(url)
        if cached:
            logger.info("SCRAPER — Cache hit for %s", url)
            scraped.append(cached)
            continue

        strategies = decide_strategy(url)
        logger.info(
            "SCRAPER — Strategies decided for %s: %s",
            url,
            strategies,
        )

        result = None

        for s in strategies:
            logger.info("SCRAPER — Trying tool: %s | URL: %s", s, url)

            url_start = time.time()
            result = TOOLS[s](url)
            elapsed = round(time.time() - url_start, 2)

            if result and "text" in result:
                logger.info(
                    "SCRAPER — Tool %s succeeded | Time: %ss | Text length: %d",
                    s,
                    elapsed,
                    len(result["text"]),
                )
                break
            else:
                logger.warning(
                    "SCRAPER — Tool %s failed | Time: %ss",
                    s,
                    elapsed,
                )

        # No result
        if not result:
            memory["failures"] = memory.get("failures", 0) + 1
            logger.warning(
                "SCRAPER — No result for %s | Failures: %d",
                url,
                memory["failures"],
            )
            continue

        text = result.get("text")
        if not text:
            memory["failures"] = memory.get("failures", 0) + 1
            logger.warning(
                "SCRAPER — Empty text for %s | Failures: %d",
                url,
                memory["failures"],
            )
            continue

        # Critic Timing
        critic_start = time.time()
        technical = is_technical(text)
        critic_elapsed = round(time.time() - critic_start, 2)

        logger.info(
            "SCRAPER — Critic evaluated | URL: %s | Technical: %s | Time: %ss",
            url,
            technical,
            critic_elapsed,
        )

        if not technical:
            memory["failures"] = memory.get("failures", 0) + 1
            continue

        article = {
            "url": url,
            "title": result["title"],
            "article_text": result["text"],
            "publish_date": str(result["date"]) if result["date"] else None,
            "scraper_used": result["tool"],
        }

        save_article(url, article)
        scraped.append(article)

        logger.info(
            "SCRAPER — Article saved | URL: %s | Scraper: %s",
            url,
            result["tool"],
        )

    save_agent_memory(company, memory)

    total_elapsed = round(time.time() - start_time, 2)
    logger.info(
        "SCRAPER AGENT — Completed | Articles scraped: %d | Total time: %ss",
        len(scraped),
        total_elapsed,
    )

    return {"scraped_articles": scraped}
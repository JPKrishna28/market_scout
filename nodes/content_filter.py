"""
Market Intelligence Scout — Content Filter Node

Deterministic node with LLM-based semantic gating.

Responsibilities:
  • Classify articles as TECHNICAL or REJECT
  • Filter out: stock analysis, HR news, opinions, general news
  • Only pass through genuine technical feature updates
"""

import logging
from typing import Dict, Any, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)


def content_filter_node(state: GraphState) -> Dict[str, Any]:
    """
    Content Filter — semantic classification of article intent.

    Input:  state["filtered_results"] (from Date Validation)
    Output: state["filtered_results"] (overwritten with validated articles)
    """
    articles = state.get("filtered_results", [])
    logger.info("CONTENT FILTER — Evaluating %d articles", len(articles))

    if not articles:
        logger.warning("CONTENT FILTER — No articles to filter")
        return {"filtered_results": []}

    validated: List[Dict[str, Any]] = []

    for article in articles:
        title = article.get("title", "N/A")
        text_snippet = article.get("article_text", "")[:600]
        url = article.get("url", "")

        prompt = f"""You are an enterprise content classifier for a Market Intelligence system.

Classify this article's primary intent:

ACCEPT if it contains:
  - API changelogs or SDK updates
  - New model/product releases with technical specs
  - Architecture or infrastructure changes
  - Developer documentation updates
  - Performance benchmark results

REJECT if it is:
  - Stock/financial analysis
  - Corporate restructuring / HR news
  - Opinion articles or commentary
  - Marketing fluff without technical substance
  - Legal or regulatory news

Title: {title}
URL: {url}
Content excerpt:
{text_snippet}

Respond with ONLY one word: ACCEPT or REJECT"""

        messages = [
            {
                "role": "system",
                "content": "You are a strict binary classifier. Respond with exactly one word.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = invoke_llm(messages, temperature=0.0, max_tokens=10)
            decision = response.strip().upper()

            if "ACCEPT" in decision:
                validated.append(article)
                logger.debug("CONTENT FILTER — ACCEPT: %s", title[:60])
            else:
                logger.debug("CONTENT FILTER — REJECT: %s", title[:60])

        except Exception as exc:
            # On LLM failure, conservatively include the article
            logger.warning(
                "CONTENT FILTER — LLM error for '%s': %s — defaulting to ACCEPT",
                title[:40], exc,
            )
            validated.append(article)

    logger.info(
        "CONTENT FILTER — %d/%d articles passed",
        len(validated), len(articles),
    )

    return {"filtered_results": validated}
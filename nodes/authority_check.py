"""
Market Intelligence Scout — Authority Check Node

Deterministic node with LLM classification.

Responsibilities:
  • Verify if an article is an official or primary source
  • Filter out secondary news coverage and aggregated reports
  • Carry forward authority metadata
"""

import logging
from typing import Dict, Any, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)


def authority_check_node(state: GraphState) -> Dict[str, Any]:
    """
    Authority Check — classify article source credibility.

    Input:  state["filtered_results"] (from Content Filter)
    Output: state["filtered_results"] (overwritten with validated articles)
    """
    articles = state.get("filtered_results", [])
    company_name = state.get("company_name", "")
    logger.info("AUTHORITY CHECK — Evaluating %d articles for '%s'", len(articles), company_name)

    if not articles:
        return {"filtered_results": []}

    validated: List[Dict[str, Any]] = []

    for article in articles:
        title = article.get("title", "N/A")
        url = article.get("url", "")

        prompt = f"""You are an enterprise source-credibility classifier.

Determine if this article is an OFFICIAL or PRIMARY technical source for {company_name}.

PRIMARY sources include:
  - Official company blogs, docs, or changelogs
  - GitHub repositories owned by {company_name}
  - First-party developer documentation
  - Official press releases with technical detail

SECONDARY sources include:
  - News aggregation sites reporting about {company_name}
  - Third-party commentary or analysis
  - Community discussions

Title: {title}
URL: {url}

Respond with ONLY one word: PRIMARY or SECONDARY"""

        messages = [
            {"role": "system", "content": "You are a strict source classifier. Respond with one word."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = invoke_llm(messages, temperature=0.0, max_tokens=10)
            decision = response.strip().upper()

            if "PRIMARY" in decision:
                validated.append(article)
                logger.debug("AUTHORITY — PRIMARY: %s", url[:60])
            else:
                # Still include secondary sources but with reduced authority
                article_copy = dict(article)
                article_copy["authority_score"] = article_copy.get("authority_score", 0.5) * 0.7
                validated.append(article_copy)
                logger.debug("AUTHORITY — SECONDARY (reduced score): %s", url[:60])

        except Exception as exc:
            logger.warning("AUTHORITY — LLM error for '%s': %s — defaulting to include", url[:40], exc)
            validated.append(article)

    logger.info("AUTHORITY CHECK — %d articles passed", len(validated))
    return {"filtered_results": validated}
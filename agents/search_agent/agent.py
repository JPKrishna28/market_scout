import logging
import time
from typing import Dict, Any

from graph.state import GraphState
from agents.search_agent.planner import plan_queries
from agents.search_agent.executor import execute_queries
from agents.search_agent.critic import needs_retry
from agents.search_agent.memory import (
    load_agent_memory,
    save_agent_memory,
    remember_queries,
    remember_results,
)

logger = logging.getLogger(__name__)

MAX_AGENT_LOOPS = 2


def search_agent_node(state: GraphState) -> Dict[str, Any]:
    start_time = time.time()
    company = state["company_name"]

    logger.info("SEARCH AGENT — Start | company=%s", company)

    memory = load_agent_memory(company)
    last_results = []

    for iteration in range(1, MAX_AGENT_LOOPS + 1):
        logger.info("SEARCH AGENT — Iteration %d", iteration)

        queries = plan_queries(
            company,
            feedback=last_results,
            memory=memory,
        )

        logger.debug("SEARCH AGENT — Planned %d queries", len(queries))
        remember_queries(memory, queries)

        results = execute_queries(
            queries,
            seen_urls=set(memory.get("seen_urls", [])),
        )

        logger.info(
            "SEARCH AGENT — Retrieved %d results (iteration %d)",
            len(results),
            iteration,
        )

        remember_results(memory, results)

        if not needs_retry(results):
            logger.info("SEARCH AGENT — Stop condition met (no retry needed)")
            save_agent_memory(company, memory)
            return {"search_results": results}

        logger.warning("SEARCH AGENT — Retry required")
        last_results = results

    save_agent_memory(company, memory)
    elapsed = round(time.time() - start_time, 2)

    logger.warning(
        "SEARCH AGENT — Max iterations reached | company=%s | time=%ss",
        company,
        elapsed,
    )

    return {"search_results": last_results}
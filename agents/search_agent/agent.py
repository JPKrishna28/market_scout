import logging
from typing import Dict, Any
import time
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
    logger.info("SEARCH AGENT — Starting for company: %s", company)

    memory = load_agent_memory(company)
    last_results = []

    for iteration in range(1, MAX_AGENT_LOOPS + 1):
        logger.info("SEARCH AGENT — Iteration %d", iteration)

        queries = plan_queries(
            company,
            feedback=last_results,
            memory=memory,   # 🔥 agent context
        )

        remember_queries(memory, queries)

        results = execute_queries(
            queries,
            seen_urls=set(memory.get("seen_urls", [])),  # 🔥 avoid repeats
        )

        remember_results(memory, results)

        if not needs_retry(results):
            save_agent_memory(company, memory)
            return {"search_results": results}

        last_results = results

    save_agent_memory(company, memory)
    elapsed = round(time.time() - start_time, 2)
    logger.info(f"SEARCH AGENT — Completed in {elapsed}s")
    logger.warning("SEARCH AGENT — Max retries reached")
    
    return {"search_results": last_results}
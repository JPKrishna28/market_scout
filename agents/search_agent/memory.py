from typing import List, Dict
from cache.redis_client import get_cache, set_cache, make_cache_key

MEMORY_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def load_agent_memory(company: str) -> Dict[str, any]:
    """
    Load episodic memory for this agent run.
    """
    key = make_cache_key("search_agent_memory", company)
    data = get_cache(key)

    if not data:
        return {
            "attempted_queries": [],
            "seen_urls": [],
        }

    return data


def save_agent_memory(company: str, memory: Dict[str, any]) -> None:
    """
    Persist agent memory for future loops / runs.
    """
    key = make_cache_key("search_agent_memory", company)
    set_cache(key, memory, expire=MEMORY_TTL_SECONDS)


def remember_queries(memory: Dict[str, any], queries: List[str]) -> None:
    memory["attempted_queries"] = list(
        set(memory.get("attempted_queries", []) + queries)
    )


def remember_results(memory: Dict[str, any], results: List[Dict]) -> None:
    urls = [r.get("url") for r in results if r.get("url")]
    memory["seen_urls"] = list(
        set(memory.get("seen_urls", []) + urls)
    )
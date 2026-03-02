from typing import Dict, Any
from cache.redis_client import get_cache, set_cache, make_cache_key

ARTICLE_TTL = 6 * 60 * 60  # 6 hours
AGENT_TTL = 24 * 60 * 60   # 24 hours


def get_article(url: str):
    return get_cache(make_cache_key("article", url))


def save_article(url: str, article: Dict[str, Any]):
    set_cache(make_cache_key("article", url), article)


def load_agent_memory(company: str) -> Dict[str, Any]:
    return get_cache(make_cache_key("scraper_memory", company)) or {
        "attempted_urls": [],
        "failures": 0,
    }


def save_agent_memory(company: str, memory: Dict[str, Any]):
    set_cache(make_cache_key("scraper_memory", company), memory)
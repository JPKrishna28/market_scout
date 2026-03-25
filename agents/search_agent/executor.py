from typing import List, Dict, Set
from tavily import TavilyClient
from urllib.parse import urlparse

from app.config import settings

_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

MAX_RESULTS_RETURNED = 15

# domains we usually don't want to scrape
BLOCKED_DOMAINS = {
    "youtube.com",
    "github.com",
    "tesla.com",
    "developer.tesla.com",
}

# keywords that usually indicate documentation / product pages
LOW_VALUE_PATHS = [
    "/docs/",
    "/support/",
    "/manual/",
    "/statistics",
]


def is_valid_result(url: str) -> bool:
    """
    Filter obvious low-value sources before scraping.
    """
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    if any(d in domain for d in BLOCKED_DOMAINS):
        return False

    if any(p in path for p in LOW_VALUE_PATHS):
        return False

    return True


def execute_queries(
    queries: List[str],
    seen_urls: Set[str],
) -> List[Dict]:

    all_results: List[Dict] = []

    for query in queries:

        response = _client.search(
            query=query,
            search_depth=settings.SEARCH_DEPTH,
            max_results=settings.SEARCH_MAX_RESULTS,
        )

        for item in response.get("results", []):

            url = item.get("url")

            if not url:
                continue

            if url in seen_urls:
                continue

            if not is_valid_result(url):
                continue

            seen_urls.add(url)

            all_results.append({
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
            })

    # 🔥 LIMIT RESULTS
    return all_results[:MAX_RESULTS_RETURNED]
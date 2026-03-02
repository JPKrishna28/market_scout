from typing import List, Dict, Set
from tavily import TavilyClient
from app.config import settings

_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


def execute_queries(
    queries: List[str],
    seen_urls: Set[str],
) -> List[Dict]:
    """
    Deterministic tool used by Search Agent.

    - Executes queries via Tavily
    - Deduplicates against agent memory
    - Does NOT own state
    """
    all_results: List[Dict] = []

    for query in queries:
        response = _client.search(
            query=query,
            search_depth=settings.SEARCH_DEPTH,
            max_results=settings.SEARCH_MAX_RESULTS,
        )

        for item in response.get("results", []):
            url = item.get("url")
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            all_results.append({
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
            })

    return all_results
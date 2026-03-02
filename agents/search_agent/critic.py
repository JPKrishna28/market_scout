from typing import List, Dict


def needs_retry(results: List[Dict]) -> bool:
    """
    Agent self-evaluation:
    Decide if results are good enough
    """
    if not results:
        return True

    if len(results) < 5:
        return True

    # Simple quality heuristic
    technical_keywords = ["api", "sdk", "model", "release", "infrastructure"]
    hits = sum(
        any(k in r.get("snippet", "").lower() for k in technical_keywords)
        for r in results
    )

    return hits < 3
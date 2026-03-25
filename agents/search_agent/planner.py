import json
import logging
from typing import List, Optional, Dict, Any

from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)


def plan_queries(
    company: str,
    feedback: Optional[str] = None,
    memory: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Planning brain of the Search Agent.

    Responsibilities:
    - Generate NEW search queries
    - Respect memory (avoid repeats)
    - Return structured output
    - Fail safely if LLM misbehaves
    """

    attempted = memory.get("attempted_queries", []) if memory else []

    prompt = f"""
You are an autonomous technical search planning agent.

Company:
{company}

Previously attempted queries (DO NOT repeat):
{attempted}

Goal:
Generate NEW search queries that discover
technical feature updates released in the last 7 days.

Focus on:
- APIs
- SDKs
- Infrastructure
- Models
- Platform updates

Rules:
- Do NOT repeat previous queries
- Return exactly 4 queries
- Return ONLY valid JSON
- No markdown
- No explanations

Output format:
{{ "queries": ["...", "...", "...", "..."] }}
"""

    if feedback:
        prompt += f"\n\nFeedback from previous iteration:\n{feedback}\n"

    # 1️⃣ LLM call (always returns STRING)
    raw_response = invoke_llm(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300,
    )

    logger.debug("SEARCH PLANNER — Raw LLM output:\n%s", raw_response)

    # 2️⃣ Parse JSON
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.error("SEARCH PLANNER — Invalid JSON:\n%s", raw_response)
        raise RuntimeError("Search planner returned invalid JSON") from exc

    # 3️⃣ Validate schema
    queries = parsed.get("queries")

    if not isinstance(queries, list):
        raise RuntimeError("Search planner output missing 'queries' list")

    if len(queries) != 4:
        raise RuntimeError(f"Expected 4 queries, got {len(queries)}")

    # 4️⃣ Normalize + dedupe
    clean_queries = []
    for q in queries:
        if isinstance(q, str):
            q = q.strip()
            if q and q not in attempted:
                clean_queries.append(q)

    if not clean_queries:
        raise RuntimeError("Search planner produced no usable queries")

    logger.info(
        "SEARCH PLANNER — Generated %d queries for %s",
        len(clean_queries),
        company,
    )

    return clean_queries
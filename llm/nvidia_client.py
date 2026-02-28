"""
Market Intelligence Scout — LLM Client (NVIDIA NIM)

Enterprise-grade wrapper around the NVIDIA API with:
  • Retry logic (exponential back-off)
  • Structured logging
  • Token budget enforcement
  • Single client instance (connection reuse)
  • Prometheus metrics (latency, token usage, call counts)
"""

import logging
import time
from typing import List, Dict, Optional

from openai import OpenAI
from app.config import settings
from observability.metrics import LLM_CALL_COUNT, LLM_LATENCY, LLM_TOKEN_USAGE

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Singleton Client
# ────────────────────────────────────────────────────────────────────

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Lazy-initialise a single OpenAI-compatible client for NVIDIA NIM."""
    global _client
    if _client is None:
        if not settings.NVIDIA_API_KEY:
            raise RuntimeError("NVIDIA_API_KEY is not configured.")
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY,
        )
    return _client


def _infer_agent_name(messages: List[Dict[str, str]]) -> str:
    """Best-effort inference of calling agent from system prompt content."""
    if not messages:
        return "unknown"
    system_msg = messages[0].get("content", "").lower() if messages else ""
    if "security" in system_msg or "classify inputs" in system_msg:
        return "guardrails"
    if "search" in system_msg:
        return "search_planner"
    if "content classifier" in system_msg or "binary classifier" in system_msg:
        return "content_filter"
    if "source" in system_msg and "credibility" in system_msg:
        return "authority_check"
    if "extraction" in system_msg:
        return "feature_extraction"
    if "intelligence analyst" in system_msg:
        return "synthesis"
    if "date" in system_msg:
        return "scraper_date"
    return "unknown"


# ────────────────────────────────────────────────────────────────────
# Core LLM Invocation
# ────────────────────────────────────────────────────────────────────

def invoke_llm(
    messages: List[Dict[str, str]],
    temperature: float = settings.LLM_TEMPERATURE,
    max_tokens: int = settings.LLM_MAX_TOKENS,
    retries: int = settings.MAX_RETRIES,
) -> str:
    """Call the NVIDIA LLM with automatic retry on transient failures.

    Parameters
    ----------
    messages : list of {"role": ..., "content": ...}
    temperature : sampling temperature
    max_tokens : hard cap on response tokens
    retries : number of retry attempts

    Returns
    -------
    str — raw text response from the model
    """
    client = _get_client()
    last_error: Optional[Exception] = None
    agent_name = _infer_agent_name(messages)

    for attempt in range(1, retries + 1):
        start_time = time.time()
        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=settings.LLM_TOP_P,
            )
            duration = time.time() - start_time
            content = response.choices[0].message.content

            # ── Record Prometheus metrics ──────────────────────────
            LLM_CALL_COUNT.labels(agent_name=agent_name, status="success").inc()
            LLM_LATENCY.labels(agent_name=agent_name).observe(duration)
            if response.usage:
                LLM_TOKEN_USAGE.labels(
                    agent_name=agent_name, token_type="prompt"
                ).inc(response.usage.prompt_tokens)
                LLM_TOKEN_USAGE.labels(
                    agent_name=agent_name, token_type="completion"
                ).inc(response.usage.completion_tokens)

            logger.debug(
                "LLM OK  model=%s tokens=%s attempt=%d duration=%.2fs",
                settings.LLM_MODEL,
                response.usage.total_tokens if response.usage else "?",
                attempt,
                duration,
            )
            return content

        except Exception as exc:
            duration = time.time() - start_time
            last_error = exc
            LLM_CALL_COUNT.labels(agent_name=agent_name, status="retry").inc()
            LLM_LATENCY.labels(agent_name=agent_name).observe(duration)

            wait = 2 ** attempt  # 2s, 4s, 8s
            logger.warning(
                "LLM FAIL attempt=%d/%d error=%s — retrying in %ds",
                attempt, retries, exc, wait,
            )
            if attempt < retries:
                time.sleep(wait)

    # Exhausted retries
    LLM_CALL_COUNT.labels(agent_name=agent_name, status="failure").inc()
    raise RuntimeError(
        f"LLM invocation failed after {retries} attempts: {last_error}"
    ) from last_error
"""
Market Intelligence Scout — Prometheus Metrics

Enterprise observability with:
  • Request counters (total API calls, per endpoint)
  • Node latency histograms (per pipeline stage)
  • LLM token usage counters (per agent)
  • Pipeline success/failure rates
  • Feature extraction counts
  • Cache hit/miss ratios
"""

from prometheus_client import Counter, Histogram, Gauge, Info

# ────────────────────────────────────────────────────────────────────
# Application Info
# ────────────────────────────────────────────────────────────────────

APP_INFO = Info(
    "market_scout",
    "Market Intelligence Scout application metadata",
)
APP_INFO.info({
    "version": "2.0.0",
    "llm_model": "meta/llama-3.1-8b-instruct",
    "pipeline_nodes": "12",
})

# ────────────────────────────────────────────────────────────────────
# API Request Metrics
# ────────────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests received",
    ["endpoint", "method", "status"],
)

REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "Total time to process an API request",
    ["endpoint"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# ────────────────────────────────────────────────────────────────────
# Pipeline Node Metrics
# ────────────────────────────────────────────────────────────────────

NODE_LATENCY = Histogram(
    "node_latency_seconds",
    "Time spent in each pipeline node",
    ["node_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

NODE_SUCCESS = Counter(
    "node_executions_total",
    "Number of node executions",
    ["node_name", "status"],  # status: success | failure | skipped
)

PIPELINE_RUNS = Counter(
    "pipeline_runs_total",
    "Total pipeline executions",
    ["status"],  # status: completed | error | guardrail_blocked
)

# ────────────────────────────────────────────────────────────────────
# LLM Metrics
# ────────────────────────────────────────────────────────────────────

LLM_TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["agent_name", "token_type"],  # token_type: prompt | completion
)

LLM_CALL_COUNT = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["agent_name", "status"],  # status: success | failure | retry
)

LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "Time per LLM API call",
    ["agent_name"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30],
)

# ────────────────────────────────────────────────────────────────────
# Feature & Intelligence Metrics
# ────────────────────────────────────────────────────────────────────

FEATURES_EXTRACTED = Counter(
    "features_extracted_total",
    "Total features extracted across all runs",
    ["company", "category"],
)

FEATURES_VERIFIED = Counter(
    "features_verified_total",
    "Features that passed cross-source verification",
    ["company"],
)

CONFIDENCE_SCORE = Histogram(
    "feature_confidence_score",
    "Distribution of confidence scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

SOURCES_ANALYSED = Histogram(
    "sources_analysed_per_run",
    "Number of sources analysed per pipeline run",
    buckets=[1, 2, 3, 5, 8, 10, 15, 20],
)

# ────────────────────────────────────────────────────────────────────
# Cache Metrics
# ────────────────────────────────────────────────────────────────────

CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Redis cache operations",
    ["operation", "status"],  # operation: get|set, status: hit|miss|error
)

# ────────────────────────────────────────────────────────────────────
# Scraper Metrics
# ────────────────────────────────────────────────────────────────────

SCRAPER_ATTEMPTS = Counter(
    "scraper_attempts_total",
    "Scraping attempts by strategy",
    ["strategy", "status"],  # strategy: newspaper3k|beautifulsoup|playwright
)

URLS_DISCARDED = Counter(
    "urls_discarded_total",
    "URLs discarded by date validation",
    ["reason"],  # reason: expired | no_date
)

# ────────────────────────────────────────────────────────────────────
# Active Gauges
# ────────────────────────────────────────────────────────────────────

ACTIVE_PIPELINES = Gauge(
    "active_pipelines",
    "Number of pipeline runs currently in progress",
)

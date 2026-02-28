"""
Market Intelligence Scout — Graph State Definition

Enterprise-grade state schema for the LangGraph pipeline.
Every field is typed and annotated with its purpose for auditability.
"""

from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime


class ArticleResult(TypedDict, total=False):
    """Standardised shape for a single search result throughout the pipeline."""
    url: str
    title: str
    snippet: str
    authority_score: float
    article_text: str
    publish_date: Optional[str]              # ISO-8601 string after serialisation
    scraper_used: Optional[str]              # newspaper3k | beautifulsoup | playwright


class ExtractedFeature(TypedDict, total=False):
    """A single extracted technical feature with provenance."""
    feature_summary: str
    category: str                             # model_release | api_update | performance | capability
    metrics: List[str]
    confidence: float
    evidence: str
    source_authority: float
    url: str


class VerifiedFeature(TypedDict, total=False):
    """A feature after cross-source verification and clustering."""
    feature_summary: str
    category: str
    metrics: List[str]
    confidence_score: float
    source_count: int
    primary_url: str
    all_sources: List[str]
    publish_date: Optional[str]
    source_authority: float


class DiscardedURL(TypedDict, total=False):
    """Audit record for a URL discarded during date validation."""
    url: str
    reason: str
    timestamp: str                            # ISO-8601


class SynthesisReport(TypedDict, total=False):
    """Final executive-ready output."""
    company_name: str
    generated_at: str
    executive_summary: str
    features: List[Dict[str, Any]]
    total_sources_analysed: int
    total_features_verified: int
    metadata: Dict[str, Any]


# ────────────────────────────────────────────────────────────────────
# Primary Graph State — Single source of truth for the entire pipeline
# ────────────────────────────────────────────────────────────────────

class GraphState(TypedDict, total=False):
    """
    Immutable-by-convention state passed through LangGraph.

    Nodes MUST only write to the keys they own and documented below.
    Read access is unrestricted so downstream nodes can consume
    upstream outputs.
    """

    # ── Input ──────────────────────────────────────────────────────
    company_name: str                         # Sanitised company name (guardrails)

    # ── Search Planner Agent output ────────────────────────────────
    search_queries: List[str]                 # 3-4 semantic search queries

    # ── Search Execution Node output ───────────────────────────────
    search_results: List[Dict[str, Any]]      # Raw Tavily results with authority scores

    # ── Scraper Strategy Agent output ──────────────────────────────
    scraped_articles: List[Dict[str, Any]]    # Articles with full text + publish_date

    # ── Date Validation Node output ────────────────────────────────
    filtered_results: List[Dict[str, Any]]    # Articles passing the ≤ 7-day rule
    discarded_urls: List[Dict[str, Any]]      # Audit log of discarded URLs

    # ── Content Filter Node output ─────────────────────────────────
    # Reuses filtered_results (overwrite after semantic gating)

    # ── Feature Extraction Agent output ────────────────────────────
    extracted_features: List[Dict[str, Any]]  # Raw extracted features

    # ── Cross-Source Verification Node output ──────────────────────
    verified_features: List[Dict[str, Any]]   # Clustered & deduplicated features

    # ── Confidence Scoring Node output ─────────────────────────────
    scored_features: List[Dict[str, Any]]     # Features with final confidence scores

    # ── Synthesis Agent output ─────────────────────────────────────
    synthesis_report: Dict[str, Any]          # Executive-ready report

    # ── Control flow ───────────────────────────────────────────────
    error: str                                # Error message (triggers failure exit)
    retry_count: int                          # Retry counter for transient failures
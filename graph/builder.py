"""
Market Intelligence Scout — LangGraph Orchestration Builder

Enterprise-grade pipeline with:
  • Conditional edges (error branching, empty result handling)
  • Failure exits with descriptive error state
  • Full state tracking through every node

Pipeline:
  [Guardrails] → [Search Planner] → [Search Execution] → [Scraper Strategy]
  → [Date Validation] → [Content Filter] → [Authority Check]
  → [Feature Extraction] → [Verification (SBERT)] → [Confidence Scoring]
  → [Synthesis] → DONE

LangGraph controls FLOW, not intelligence.
MCP (NVIDIA) handles LLM calls — never orchestration.
"""

import logging
import time
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from graph.state import GraphState
from observability.metrics import NODE_LATENCY, NODE_SUCCESS

# ── Node Imports ───────────────────────────────────────────────────
from nodes.guardrails import guardrails_node
from agents.search_planner import search_planner_node
from nodes.search_execution import search_execution_node
from agents.scraper_strategy import scraper_strategy_node
from nodes.date_validation import date_validation_node
from nodes.content_filter import content_filter_node
from nodes.authority_check import authority_check_node
from nodes.feature_extraction import feature_extraction_node
from nodes.verification import verification_node
from nodes.scoring import confidence_scoring_node
from agents.synthesis import synthesis_node

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Node Instrumentation Wrapper
# ────────────────────────────────────────────────────────────────────

def _instrument_node(name: str, fn):
    """Wrap a node function with Prometheus latency and success metrics."""
    def wrapper(state: GraphState) -> Dict[str, Any]:
        start = time.time()
        try:
            result = fn(state)
            NODE_SUCCESS.labels(node_name=name, status="success").inc()
            return result
        except Exception as exc:
            NODE_SUCCESS.labels(node_name=name, status="failure").inc()
            raise
        finally:
            NODE_LATENCY.labels(node_name=name).observe(time.time() - start)
    wrapper.__name__ = fn.__name__
    return wrapper


# ────────────────────────────────────────────────────────────────────
# Error Exit Node
# ────────────────────────────────────────────────────────────────────

def error_exit_node(state: GraphState) -> Dict[str, Any]:
    """Terminal node for pipeline failures.
    Packages the error into the synthesis_report for consistent API response."""
    error_msg = state.get("error", "Unknown pipeline error")
    company = state.get("company_name", "N/A")

    logger.error("PIPELINE ERROR — Company: '%s' — Error: %s", company, error_msg)

    return {
        "synthesis_report": {
            "company_name": company,
            "generated_at": "",
            "executive_summary": f"Pipeline terminated: {error_msg}",
            "features": [],
            "total_sources_analysed": 0,
            "total_features_verified": 0,
            "metadata": {"error": error_msg, "pipeline_version": "2.0"},
        }
    }


# ────────────────────────────────────────────────────────────────────
# Conditional Edge Functions
# ────────────────────────────────────────────────────────────────────

def _check_guardrail(state: GraphState) -> str:
    """Route after guardrails: continue on success, exit on error."""
    if state.get("error"):
        return "error_exit"
    return "search_planner"


def _check_search_results(state: GraphState) -> str:
    """Route after search execution: exit if no results found."""
    results = state.get("search_results", [])
    if not results:
        return "no_results"
    return "scraper_strategy"


def _check_scraped_articles(state: GraphState) -> str:
    """Route after scraping: exit if all scraping failed."""
    articles = state.get("scraped_articles", [])
    if not articles:
        return "no_articles"
    return "date_validation"


def _check_filtered_after_date(state: GraphState) -> str:
    """Route after date validation: exit if all articles are too old."""
    filtered = state.get("filtered_results", [])
    if not filtered:
        return "all_expired"
    return "content_filter"


def _check_filtered_after_content(state: GraphState) -> str:
    """Route after content filter: exit if no technical articles remain."""
    filtered = state.get("filtered_results", [])
    if not filtered:
        return "no_technical"
    return "authority_check"


def _check_features(state: GraphState) -> str:
    """Route after feature extraction: exit if no features extracted."""
    features = state.get("extracted_features", [])
    if not features:
        return "no_features"
    return "verification"


# ────────────────────────────────────────────────────────────────────
# Early Exit Nodes (describe why the pipeline stopped)
# ────────────────────────────────────────────────────────────────────

def _no_results_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No search results found for '{state.get('company_name', 'N/A')}'. The company may not have recent public technical updates."}


def _no_articles_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"All URLs for '{state.get('company_name', 'N/A')}' failed to scrape. Sources may be behind paywalls or blocking automated access."}


def _all_expired_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"All articles for '{state.get('company_name', 'N/A')}' are older than 7 days. No recent technical updates found."}


def _no_technical_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No articles about '{state.get('company_name', 'N/A')}' contained technical feature updates. All content was classified as non-technical."}


def _no_features_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No extractable technical features were found in articles about '{state.get('company_name', 'N/A')}'. Content may be too generic."}


# ────────────────────────────────────────────────────────────────────
# Graph Builder
# ────────────────────────────────────────────────────────────────────

def build_graph():
    """Assemble and compile the LangGraph pipeline.

    This is called once at app startup. The compiled graph is
    thread-safe and can be invoked concurrently.
    """
    builder = StateGraph(GraphState)

    # ── Register all nodes (instrumented) ──────────────────────────
    builder.add_node("guardrails", _instrument_node("guardrails", guardrails_node))
    builder.add_node("search_planner", _instrument_node("search_planner", search_planner_node))
    builder.add_node("search_execution", _instrument_node("search_execution", search_execution_node))
    builder.add_node("scraper_strategy", _instrument_node("scraper_strategy", scraper_strategy_node))
    builder.add_node("date_validation", _instrument_node("date_validation", date_validation_node))
    builder.add_node("content_filter", _instrument_node("content_filter", content_filter_node))
    builder.add_node("authority_check", _instrument_node("authority_check", authority_check_node))
    builder.add_node("feature_extraction", _instrument_node("feature_extraction", feature_extraction_node))
    builder.add_node("verification", _instrument_node("verification", verification_node))
    builder.add_node("scoring", _instrument_node("scoring", confidence_scoring_node))
    builder.add_node("synthesis", _instrument_node("synthesis", synthesis_node))

    # Error / early-exit nodes
    builder.add_node("error_exit", error_exit_node)
    builder.add_node("no_results", _no_results_node)
    builder.add_node("no_articles", _no_articles_node)
    builder.add_node("all_expired", _all_expired_node)
    builder.add_node("no_technical", _no_technical_node)
    builder.add_node("no_features", _no_features_node)

    # ── Entry point ────────────────────────────────────────────────
    builder.set_entry_point("guardrails")

    # ── Conditional edges ──────────────────────────────────────────

    # Guardrails → pass/fail
    builder.add_conditional_edges("guardrails", _check_guardrail, {
        "search_planner": "search_planner",
        "error_exit": "error_exit",
    })

    # Search Planner → Search Execution (always)
    builder.add_edge("search_planner", "search_execution")

    # Search Execution → Scraper / empty exit
    builder.add_conditional_edges("search_execution", _check_search_results, {
        "scraper_strategy": "scraper_strategy",
        "no_results": "no_results",
    })

    # Scraper → Date Validation / scrape failure exit
    builder.add_conditional_edges("scraper_strategy", _check_scraped_articles, {
        "date_validation": "date_validation",
        "no_articles": "no_articles",
    })

    # Date Validation → Content Filter / all expired exit
    builder.add_conditional_edges("date_validation", _check_filtered_after_date, {
        "content_filter": "content_filter",
        "all_expired": "all_expired",
    })

    # Content Filter → Authority Check / no technical content exit
    builder.add_conditional_edges("content_filter", _check_filtered_after_content, {
        "authority_check": "authority_check",
        "no_technical": "no_technical",
    })

    # Authority Check → Feature Extraction (always continues)
    builder.add_edge("authority_check", "feature_extraction")

    # Feature Extraction → Verification / no features exit
    builder.add_conditional_edges("feature_extraction", _check_features, {
        "verification": "verification",
        "no_features": "no_features",
    })

    # Verification → Scoring (always)
    builder.add_edge("verification", "scoring")

    # Scoring → Synthesis (always)
    builder.add_edge("scoring", "synthesis")

    # ── Terminal edges ─────────────────────────────────────────────
    builder.add_edge("synthesis", END)

    # All error/early-exit nodes → error_exit → END
    builder.add_edge("no_results", "error_exit")
    builder.add_edge("no_articles", "error_exit")
    builder.add_edge("all_expired", "error_exit")
    builder.add_edge("no_technical", "error_exit")
    builder.add_edge("no_features", "error_exit")
    builder.add_edge("error_exit", END)

    # ── Compile ────────────────────────────────────────────────────
    compiled = builder.compile()
    logger.info("GRAPH — Pipeline compiled successfully with %d nodes", 17)

    return compiled
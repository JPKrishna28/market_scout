"""
Market Intelligence Scout — LangGraph Orchestration Builder

LangGraph controls FLOW, not intelligence.
Agents own planning, reasoning, retries, and memory.
"""

import logging
import time
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from graph.state import GraphState
from observability.metrics import NODE_LATENCY, NODE_SUCCESS

# ── Node Imports ───────────────────────────────────────────────────
from nodes.guardrails import guardrails_node
from agents.search_agent.agent import search_agent_node
from agents.scraper_agent.agent import scraper_agent_node
from nodes.date_validation import date_validation_node
from nodes.content_filter import content_filter_node
from nodes.authority_check import authority_check_node
from nodes.feature_extraction import feature_extraction_node
from nodes.verification import verification_node
from nodes.scoring import confidence_scoring_node
from nodes.synthesis import synthesis_node

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Node Instrumentation Wrapper
# ────────────────────────────────────────────────────────────────────

def _instrument_node(name: str, fn):
    def wrapper(state: GraphState) -> Dict[str, Any]:
        start = time.time()
        try:
            result = fn(state)
            NODE_SUCCESS.labels(node_name=name, status="success").inc()
            return result
        except Exception:
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
            "metadata": {"error": error_msg, "pipeline_version": "2.1"},
        }
    }


# ────────────────────────────────────────────────────────────────────
# Conditional Edge Functions
# ────────────────────────────────────────────────────────────────────

def _check_guardrail(state: GraphState) -> str:
    if state.get("error"):
        return "error_exit"
    return "search_agent"


def _check_search_results(state: GraphState) -> str:
    results = state.get("search_results", [])
    if not results:
        return "no_results"
    return "scraper_agent"


def _check_scraped_articles(state: GraphState) -> str:
    if not state.get("scraped_articles"):
        return "no_articles"
    return "date_validation"


def _check_filtered_after_date(state: GraphState) -> str:
    if not state.get("filtered_results"):
        return "all_expired"
    return "content_filter"


def _check_filtered_after_content(state: GraphState) -> str:
    if not state.get("filtered_results"):
        return "no_technical"
    return "authority_check"


def _check_features(state: GraphState) -> str:
    if not state.get("extracted_features"):
        return "no_features"
    return "verification"


# ────────────────────────────────────────────────────────────────────
# Early Exit Nodes
# ────────────────────────────────────────────────────────────────────

def _no_results_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No search results found for '{state.get('company_name')}'."}


def _no_articles_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"All URLs for '{state.get('company_name')}' failed to scrape."}


def _all_expired_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"All articles for '{state.get('company_name')}' are older than 7 days."}


def _no_technical_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No technical articles found for '{state.get('company_name')}'."}


def _no_features_node(state: GraphState) -> Dict[str, Any]:
    return {"error": f"No extractable features found for '{state.get('company_name')}'."}


# ────────────────────────────────────────────────────────────────────
# Graph Builder
# ────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(GraphState)

    # ── Core Nodes ────────────────────────────────────────────────
    builder.add_node("guardrails", _instrument_node("guardrails", guardrails_node))
    builder.add_node("search_agent", _instrument_node("search_agent", search_agent_node))
    builder.add_node("scraper_agent", _instrument_node("scraper_agent", scraper_agent_node))
    builder.add_node("date_validation", _instrument_node("date_validation", date_validation_node))
    builder.add_node("content_filter", _instrument_node("content_filter", content_filter_node))
    builder.add_node("authority_check", _instrument_node("authority_check", authority_check_node))
    builder.add_node("feature_extraction", _instrument_node("feature_extraction", feature_extraction_node))
    builder.add_node("verification", _instrument_node("verification", verification_node))
    builder.add_node("scoring", _instrument_node("scoring", confidence_scoring_node))
    builder.add_node("synthesis", _instrument_node("synthesis", synthesis_node))

    # ── Error Nodes ───────────────────────────────────────────────
    builder.add_node("error_exit", error_exit_node)
    builder.add_node("no_results", _no_results_node)
    builder.add_node("no_articles", _no_articles_node)
    builder.add_node("all_expired", _all_expired_node)
    builder.add_node("no_technical", _no_technical_node)
    builder.add_node("no_features", _no_features_node)

    # ── Entry Point ───────────────────────────────────────────────
    builder.set_entry_point("guardrails")

    # ── Conditional Routing ───────────────────────────────────────
    builder.add_conditional_edges("guardrails", _check_guardrail, {
        "search_agent": "search_agent",
        "error_exit": "error_exit",
    })

    builder.add_conditional_edges("search_agent", _check_search_results, {
        "scraper_agent": "scraper_agent",
        "no_results": "no_results",
    })

    builder.add_conditional_edges("scraper_agent", _check_scraped_articles, {
        "date_validation": "date_validation",
        "no_articles": "no_articles",
    })

    builder.add_conditional_edges("date_validation", _check_filtered_after_date, {
        "content_filter": "content_filter",
        "all_expired": "all_expired",
    })

    builder.add_conditional_edges("content_filter", _check_filtered_after_content, {
        "authority_check": "authority_check",
        "no_technical": "no_technical",
    })

    builder.add_conditional_edges("feature_extraction", _check_features, {
        "verification": "verification",
        "no_features": "no_features",
    })

    # ── Linear Continuation ───────────────────────────────────────
    builder.add_edge("authority_check", "feature_extraction")
    builder.add_edge("verification", "scoring")
    builder.add_edge("scoring", "synthesis")
    builder.add_edge("synthesis", END)

    # ── All Early Exit → Error Exit → END ─────────────────────────
    for node in [
        "no_results",
        "no_articles",
        "all_expired",
        "no_technical",
        "no_features",
        "error_exit",
    ]:
        builder.add_edge(node, "error_exit")

    builder.add_edge("error_exit", END)

    compiled = builder.compile()
    logger.info("GRAPH — Pipeline compiled successfully (agentic search enabled)")
    return compiled
"""
Market Intelligence Scout — FastAPI Application

Production-ready API with:
  • Structured request/response schemas
  • Prometheus metrics endpoint (/metrics)
  • OpenTelemetry tracing
  • Health check endpoint
  • CORS support
  • Startup/shutdown lifecycle hooks
"""

import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from prometheus_client import make_asgi_app

load_dotenv()

# ── Internal Imports ───────────────────────────────────────────────
from database.session import engine, get_db
from database.models import Base
from database import crud, schemas
from graph.builder import build_graph
from app.config import settings
from observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    PIPELINE_RUNS,
    ACTIVE_PIPELINES,
    FEATURES_EXTRACTED,
    FEATURES_VERIFIED,
    CONFIDENCE_SCORE,
    SOURCES_ANALYSED,
)

# ────────────────────────────────────────────────────────────────────
# Logging Configuration
# ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ────────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the company to analyse",
        examples=["OpenAI", "Google DeepMind", "Anthropic"],
    )


class FeatureItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    confidence_score: Optional[float] = None
    impact_assessment: Optional[str] = None
    source_url: Optional[str] = None
    source_count: Optional[int] = None
    key_metrics: Optional[List[str]] = None


def _safe_feature(f: dict, idx: int) -> FeatureItem:
    """Build a FeatureItem from a pipeline dict, mapping alternate key names."""
    return FeatureItem(
        rank=f.get("rank", idx + 1),
        title=f.get("title") or f.get("feature_title") or f.get("feature_summary", ""),
        description=f.get("description") or f.get("feature_summary") or f.get("feature_text", ""),
        category=f.get("category"),
        confidence_score=f.get("confidence_score") or f.get("confidence"),
        impact_assessment=f.get("impact_assessment"),
        source_url=f.get("source_url") or f.get("primary_url") or f.get("url"),
        source_count=f.get("source_count"),
        key_metrics=f.get("key_metrics") or f.get("metrics"),
    )


class AgentResponse(BaseModel):
    company_name: str
    generated_at: str
    executive_summary: str
    features: List[FeatureItem] = []
    total_sources_analysed: int = 0
    total_features_verified: int = 0
    all_sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# ────────────────────────────────────────────────────────────────────
# App Lifecycle
# ────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("Starting %s", settings.APP_NAME)
    Base.metadata.create_all(bind=engine)
    app.state.graph = build_graph()
    logger.info("LangGraph pipeline compiled and ready")

    # Initialise tracing (optional — only if OpenTelemetry deps are present)
    try:
        from observability.tracing import setup_tracing
        setup_tracing(app)
    except Exception as exc:
        logger.warning("Tracing setup skipped: %s", exc)

    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# ────────────────────────────────────────────────────────────────────
# FastAPI Application
# ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Market Intelligence Scout 🚀",
    description=(
        "Enterprise-grade Market Intelligence System that extracts, verifies, "
        "and scores technical features from public sources."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "https://api.market-scout.me",
    "https://market-scout.me",
    "https://www.market-scout.me",
]
if settings.DEBUG:
    allowed_origins.extend(["http://127.0.0.1:5173", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Mount Prometheus /metrics endpoint ─────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ────────────────────────────────────────────────────────────────────
# Middleware — Request Metrics
# ────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def track_request_metrics(request: Request, call_next):
    """Record request count and latency for every endpoint."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    endpoint = request.url.path
    if endpoint != "/metrics":  # Don't track metrics scraping itself
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)

    return response


# ────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "metrics": "/metrics",
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/run-agent",
    response_model=AgentResponse,
    tags=["Intelligence"],
    summary="Run Market Intelligence Pipeline",
)
def run_agent(request: AgentRequest):
    """Execute the full intelligence pipeline for a given company."""
    logger.info("API — Pipeline invoked for: '%s'", request.company_name)
    ACTIVE_PIPELINES.inc()

    try:
        graph = app.state.graph
        result = graph.invoke({"company_name": request.company_name})

        report = result.get("synthesis_report", {})
        if not report:
            PIPELINE_RUNS.labels(status="error").inc()
            raise HTTPException(status_code=500, detail="Pipeline produced no report.")

        # ── Record metrics ─────────────────────────────────────────
        error = result.get("error") or report.get("metadata", {}).get("error")
        features = report.get("features", [])

        if error and not features:
            PIPELINE_RUNS.labels(status="error").inc()
        else:
            PIPELINE_RUNS.labels(status="completed").inc()

        # Feature-level metrics
        for f in features:
            cat = f.get("category", "unknown") if isinstance(f, dict) else "unknown"
            FEATURES_EXTRACTED.labels(company=request.company_name, category=cat).inc()
            score = f.get("confidence_score", 0) if isinstance(f, dict) else 0
            CONFIDENCE_SCORE.observe(score)

        FEATURES_VERIFIED.labels(company=request.company_name).inc(
            report.get("total_features_verified", 0)
        )
        SOURCES_ANALYSED.observe(report.get("total_sources_analysed", 0))

        # ── Build response ─────────────────────────────────────────
        safe_features = []
        for i, f in enumerate(features):
            if isinstance(f, dict):
                try:
                    safe_features.append(_safe_feature(f, i))
                except Exception as feat_exc:
                    logger.warning("API — Skipping invalid feature #%d: %s — data: %s", i, feat_exc, f)
            else:
                logger.warning("API — Skipping non-dict feature #%d: %s", i, type(f))

        # Ensure all_sources is a list of strings
        raw_sources = report.get("all_sources") or []
        safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else None

        response = AgentResponse(
            company_name=report.get("company_name", request.company_name),
            generated_at=report.get("generated_at", datetime.now(timezone.utc).isoformat()),
            executive_summary=report.get("executive_summary", "No summary available."),
            features=safe_features,
            total_sources_analysed=report.get("total_sources_analysed", 0),
            total_features_verified=report.get("total_features_verified", 0),
            all_sources=safe_sources,
            metadata=report.get("metadata"),
        )

        # ── Persist to PostgreSQL ──────────────────────────────────
        try:
            db = next(get_db())
            crud.save_report(db, request.company_name, report)
            logger.info("API — Report saved to PostgreSQL for '%s'", request.company_name)
        except Exception as db_exc:
            logger.warning("API — DB persistence failed (non-fatal): %s", db_exc)

        logger.info(
            "API — Report: %d features, %d sources",
            len(response.features), response.total_sources_analysed,
        )
        return response

    except HTTPException:
        raise
    except ValueError as exc:
        PIPELINE_RUNS.labels(status="guardrail_blocked").inc()
        logger.error("API — ValueError during response build: %s", exc, exc_info=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        PIPELINE_RUNS.labels(status="error").inc()
        logger.error("API — Unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")
    finally:
        ACTIVE_PIPELINES.dec()


# ────────────────────────────────────────────────────────────────────
# History & CRUD Endpoints
# ────────────────────────────────────────────────────────────────────

@app.get(
    "/reports/{company_name}",
    response_model=list[schemas.ReportResponse],
    tags=["History"],
    summary="Get historical reports for a company",
)
def get_reports(company_name: str, limit: int = 10, db: Session = Depends(get_db)):
    """Retrieve past pipeline reports for a company."""
    return crud.get_reports_for_competitor(db, company_name, limit=limit)


@app.get(
    "/features/{company_name}",
    response_model=list[schemas.FeatureResponse],
    tags=["History"],
    summary="Get all features ever extracted for a company",
)
def get_features(company_name: str, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve all features extracted across all reports for a company."""
    return crud.get_all_features_for_competitor(db, company_name, limit=limit)


@app.post("/competitors", response_model=schemas.CompetitorResponse, tags=["Database"])
def create_competitor(competitor: schemas.CompetitorCreate, db: Session = Depends(get_db)):
    return crud.create_competitor(db, name=competitor.name, industry=competitor.industry)


@app.get("/competitors", response_model=list[schemas.CompetitorResponse], tags=["Database"])
def read_competitors(db: Session = Depends(get_db)):
    return crud.get_competitors(db)
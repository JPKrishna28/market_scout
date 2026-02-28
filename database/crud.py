"""
Market Intelligence Scout — Database CRUD Operations

Enterprise data access layer for PostgreSQL.
Handles: Competitor lookups, Feature saves, and Report persistence.
"""

from sqlalchemy.orm import Session
from .models import Competitor, Feature, Report


# ────────────────────────────────────────────────────────────────────
# Competitors
# ────────────────────────────────────────────────────────────────────

def create_competitor(db: Session, name: str, industry: str = "technology") -> Competitor:
    """Create a new competitor record."""
    competitor = Competitor(name=name, industry=industry)
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


def get_competitors(db: Session) -> list:
    """Retrieve all competitors."""
    return db.query(Competitor).all()


def get_or_create_competitor(db: Session, name: str) -> Competitor:
    """Find an existing competitor by name, or create a new one."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(name)
    ).first()

    if not competitor:
        competitor = Competitor(name=name, industry="technology")
        db.add(competitor)
        db.commit()
        db.refresh(competitor)

    return competitor


# ────────────────────────────────────────────────────────────────────
# Reports (Full Pipeline Run Persistence)
# ────────────────────────────────────────────────────────────────────

def save_report(db: Session, company_name: str, report_data: dict) -> Report:
    """Persist a complete pipeline run to PostgreSQL.

    Creates the competitor if it doesn't exist, saves the report,
    and saves each feature linked to both the report and competitor.
    """
    # Get or create competitor
    competitor = get_or_create_competitor(db, company_name)

    # Create the report
    report = Report(
        competitor_id=competitor.id,
        executive_summary=report_data.get("executive_summary", ""),
        total_sources=report_data.get("total_sources_analysed", 0),
        total_features=report_data.get("total_features_verified", 0),
        all_sources=report_data.get("all_sources", []),
        metadata_=report_data.get("metadata"),
    )
    db.add(report)
    db.flush()  # Get report.id without committing

    # Save each feature
    for f in report_data.get("features", []):
        if isinstance(f, dict):
            feature = Feature(
                competitor_id=competitor.id,
                report_id=report.id,
                feature_title=f.get("title", ""),
                feature_text=f.get("title") or f.get("description", ""),
                description=f.get("description", ""),
                category=f.get("category", ""),
                confidence_score=f.get("confidence_score", 0.0),
                source_count=f.get("source_count", 1),
                source_url=f.get("source_url", ""),
                evidence=f.get("impact_assessment", ""),
                metrics=f.get("key_metrics", []),
            )
            db.add(feature)

    db.commit()
    db.refresh(report)
    return report


def get_reports_for_competitor(db: Session, company_name: str, limit: int = 10) -> list:
    """Get the most recent reports for a company."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name)
    ).first()

    if not competitor:
        return []

    return (
        db.query(Report)
        .filter(Report.competitor_id == competitor.id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_features_for_competitor(db: Session, company_name: str, limit: int = 50) -> list:
    """Get all features ever extracted for a company (across all reports)."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name)
    ).first()

    if not competitor:
        return []

    return (
        db.query(Feature)
        .filter(Feature.competitor_id == competitor.id)
        .order_by(Feature.created_at.desc())
        .limit(limit)
        .all()
    )
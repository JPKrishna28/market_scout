from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .session import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    industry = Column(String, default="technology")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    features = relationship("Feature", back_populates="competitor", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="competitor", cascade="all, delete-orphan")


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"))
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    feature_title = Column(String, nullable=True)           # Short title (max 10 words)
    feature_text = Column(String)                            # Detailed 2-3 sentence summary
    description = Column(Text, nullable=True)                # Full description from synthesis
    category = Column(String)
    confidence_score = Column(Float)
    source_count = Column(Integer, default=1)
    source_url = Column(String, nullable=True)
    evidence = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    competitor = relationship("Competitor", back_populates="features")
    report = relationship("Report", back_populates="features")


class Report(Base):
    """Stores each pipeline run's full report for historical tracking."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"))
    executive_summary = Column(Text)
    total_sources = Column(Integer, default=0)
    total_features = Column(Integer, default=0)
    all_sources = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    competitor = relationship("Competitor", back_populates="reports")
    features = relationship("Feature", back_populates="report", cascade="all, delete-orphan")
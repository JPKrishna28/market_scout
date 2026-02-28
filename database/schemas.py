from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Feature Schemas ---
class FeatureCreate(BaseModel):
    feature_text: str
    category: str
    confidence_score: float
    source_count: int

class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competitor_id: int
    feature_title: Optional[str] = None
    feature_text: str
    description: Optional[str] = None
    category: str
    confidence_score: float
    source_count: int
    source_url: Optional[str] = None
    evidence: Optional[str] = None
    metrics: Optional[list] = None
    created_at: datetime

# --- Report Schemas ---
class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competitor_id: int
    executive_summary: str
    total_sources: int
    total_features: int
    all_sources: Optional[list] = None
    metadata_: Optional[dict] = None
    created_at: datetime
    features: List[FeatureResponse] = []

# --- Competitor Schemas ---
class CompetitorCreate(BaseModel):
    name: str
    industry: str = "technology"

class CompetitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str
    created_at: datetime
    features: List[FeatureResponse] = []
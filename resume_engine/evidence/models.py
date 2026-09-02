"""Data models for extracted evidence, claims, metrics, and line diagnostics."""
from __future__ import annotations

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class AcademicMetric(BaseModel):
    """Extracted academic benchmark (CPI, Board %, JEE rank, KVPY)."""
    name: str
    value: str
    numeric_value: Optional[float] = None
    scale: Optional[float] = 10.0


class CampusEntity(BaseModel):
    """Recognized IIT Kanpur entity (Council, Club, SURGE, Gymkhana, PoR)."""
    name: str
    category: str  # council, club, research, fest, hall, por_role
    context_snippet: str = ""


class AtomicClaim(BaseModel):
    """An atomic factual claim extracted from a resume bullet."""
    claim_id: str
    bullet_id: str
    section: str
    entry_id: Optional[str] = None
    page: int = 1
    text_snippet: str
    action_verb: Optional[str] = None
    verb_strength: str = "neutral"  # strong, neutral, weak
    metrics_detected: List[str] = Field(default_factory=list)
    has_quantifiable_impact: bool = False
    skills_matched: List[str] = Field(default_factory=list)
    entities_matched: List[str] = Field(default_factory=list)
    competencies_supported: List[str] = Field(default_factory=list)


class BulletDiagnostic(BaseModel):
    """Detailed line-by-line formatting & impact diagnostic."""
    claim_id: str
    bullet_id: str
    section: str
    entry_id: Optional[str] = None
    page: int = 1
    text_snippet: str
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    severity: str = "info"  # critical, warning, info


class EvidenceBundle(BaseModel):
    """Aggregated semantic evidence extracted from ResumeAST."""
    academic_metrics: List[AcademicMetric] = Field(default_factory=list)
    cpi: Optional[float] = None
    all_skills: List[str] = Field(default_factory=list)
    all_entities: List[str] = Field(default_factory=list)
    campus_entities: List[CampusEntity] = Field(default_factory=list)
    claims: List[AtomicClaim] = Field(default_factory=list)
    bullet_diagnostics: List[BulletDiagnostic] = Field(default_factory=list)

"""Evidence models v2 — typed evidence, structured metrics, confidence tracking."""
from __future__ import annotations
from pydantic import BaseModel, Field
from resume_engine.parser.models import BBox, EvidenceType, ProjectType, ImpactType


class EntityMention(BaseModel):
    canonical: str
    category: str
    surface: str
    competencies: dict[str, float] = Field(default_factory=dict)


class Metric(BaseModel):
    """A parsed numeric metric with semantic classification."""
    raw: str                         # original surface form, e.g. "10,000+"
    value: float | None = None       # normalized numeric value
    value_high: float | None = None  # upper bound for ranges
    unit: str | None = None          # %, x, k, M, B, L, Cr, users, ms, …
    kind: str = "quantity"           # see MetricKind enum values below
    # MetricKind values:
    #   percentage, multiplier, financial, count, duration, rank,
    #   accuracy, ratio, rate, year, model_param, event_id, unknown
    is_impact_relevant: bool = False  # True only when context implies outcome/scale
    direction: str | None = None     # "increase" | "decrease" | "neutral" | None


class AcademicMetric(BaseModel):
    """Typed CPI / SPI / percentage from education table."""
    metric_type: str      # "cpi" | "spi" | "percentage" | "rank"
    raw: str
    value: float
    scale: float | None = None    # e.g. 10.0 for "7.7/10"
    year_or_sem: str | None = None
    institution: str | None = None
    degree: str | None = None


class AtomicClaim(BaseModel):
    claim_id: str
    bullet_id: str
    entry_id: str | None = None
    text: str
    raw_text: str = ""
    section: str
    entry_type: str = "unknown"      # "experience"|"research"|"project"|"por"|"extracurricular"|…
    entry_context: str = ""          # Entry title and organization for context
    page: int
    bbox: BBox
    action_verb: str | None = None
    action_strength: float = 0.0
    action_confidence: float = 0.0   # confidence that first token is truly the action verb
    metrics: list[Metric] = Field(default_factory=list)
    impact_metrics: list[Metric] = Field(default_factory=list)  # only impact-relevant subset
    entities: list[EntityMention] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    hyperlinks: list[str] = Field(default_factory=list)
    subsection_label: str | None = None
    signals: dict[str, float] = Field(default_factory=dict)
    evidence_strength: float = 0.0
    extraction_confidence: float = 1.0  # 0-1, lower for ambiguous cases
    
    # NEW: Evidence Type Classification  
    evidence_types: list[EvidenceType] = Field(default_factory=list)
    project_types: list[ProjectType] = Field(default_factory=list)
    impact_types: list[ImpactType] = Field(default_factory=list)
    domain_relevance: dict[str, float] = Field(default_factory=dict)  # role -> relevance score
    presence_score: float = 0.0      # evidence exists
    role_relevance_score: dict[str, float] = Field(default_factory=dict)  # role -> relevance


class EvidenceDocument(BaseModel):
    source_file: str
    claims: list[AtomicClaim] = Field(default_factory=list)
    academic_metrics: list[AcademicMetric] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # Convenience: set of all skills detected anywhere in the resume
    all_skills: list[str] = Field(default_factory=list)
    # Convenience: set of all entity canonicals detected
    all_entities: list[str] = Field(default_factory=list)

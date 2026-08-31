"""Pipeline v2 — Richer analysis result with richer schema.

LOOP 6 fixes:
- AnalysisResult now includes document metadata, evidence, links, warnings.
- Passes link_objects from AST to scorer for accurate GitHub detection.
- Error handling for malformed PDFs, empty files, encrypted, bad roles.
- Temporary file cleanup in API layer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.scoring.scorer import RoleScorer, RoleScore
from resume_engine.advisory.advisor import CounterfactualAdvisor, AdvisoryReport
from resume_engine.evidence.models import AcademicMetric, AtomicClaim
from resume_engine.parser.models import LinkObject, Section


class DocumentSummary(BaseModel):
    source_file: str
    sections: list[str] = Field(default_factory=list)
    links: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    layout_diagnostics: dict = Field(default_factory=dict)


class EvidenceSummary(BaseModel):
    academic_metrics: list[AcademicMetric] = Field(default_factory=list)
    all_skills: list[str] = Field(default_factory=list)
    all_entities: list[str] = Field(default_factory=list)
    claim_count: int = 0


class AnalysisResult(BaseModel):
    """Richer analysis result schema (v2)."""
    role: str
    document: DocumentSummary
    evidence: EvidenceSummary
    score: RoleScore
    advisory: AdvisoryReport
    # Legacy flat fields for backward compatibility
    evidence_claims: int
    parser_warnings: list[str]

    def model_dump(self, **kwargs) -> dict:
        d = super().model_dump(**kwargs)
        return d


class ResumeEngine:
    def __init__(self, embedding_model: str | None = None):
        self.extractor = EvidenceExtractor()
        self.roles = load_role_graphs()
        self.matcher = HybridMatcher(embedding_model)
        self.scorer = RoleScorer()
        self.advisor = CounterfactualAdvisor()

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        rid = role_id.lower().strip()
        if rid not in self.roles:
            raise ValueError(
                f"Unknown role '{role_id}'. Choose one of: {', '.join(sorted(self.roles))}"
            )

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if path.stat().st_size == 0:
            raise ValueError(f"PDF file is empty: {pdf_path}")

        # Stage 1 — Parse
        ast = parse_pdf(path)

        # Stage 2 — Evidence extraction
        ev = self.extractor.extract(ast)

        # Stage 3 — Matching
        role = self.roles[rid]
        matches = self.matcher.match(ev, role)

        # Stage 4 — Scoring (pass link_objects for doc-level GitHub detection)
        score = self.scorer.score(ev, role, matches, link_objects=ast.link_objects)

        # Stage 5 — Advisory
        advisory = self.advisor.build(ev, score)

        # ── Build richer output schema ────────────────────────────────────
        doc_summary = DocumentSummary(
            source_file=ast.source_file,
            sections=[s.name for s in ast.sections],
            links=[
                {
                    "uri": lo.uri,
                    "type": lo.link_type,
                    "page": lo.page,
                    "section": lo.section,
                    "associated_text": lo.associated_text[:80],
                }
                for lo in ast.link_objects
            ],
            warnings=ast.warnings,
            layout_diagnostics=ast.layout_diagnostics,
        )

        ev_summary = EvidenceSummary(
            academic_metrics=ev.academic_metrics,
            all_skills=ev.all_skills,
            all_entities=ev.all_entities,
            claim_count=len(ev.claims),
        )

        return AnalysisResult(
            role=rid,
            document=doc_summary,
            evidence=ev_summary,
            score=score,
            advisory=advisory,
            evidence_claims=len(ev.claims),
            parser_warnings=ast.warnings,
        )

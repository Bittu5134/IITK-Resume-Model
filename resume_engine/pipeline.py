"""Main Resume Diagnostic Engine Pipeline.

Coordinates:
Spatial Parser -> IITK Evidence Extractor -> Role Ontology -> Scorer -> Counterfactual Advisor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.parser.models import ResumeAST
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.evidence.models import EvidenceBundle, AcademicMetric
from resume_engine.ontology.roles import ROLE_DEFINITIONS, get_role_requirement, RoleRequirement
from resume_engine.scoring.scorer import RoleScorer, RoleScore
from resume_engine.advisory.advisor import CounterfactualAdvisor, AdvisoryReport


class DocumentSummary(BaseModel):
    source_file: str
    sections: List[str] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    layout_diagnostics: Dict[str, Any] = Field(default_factory=dict)


class EvidenceSummary(BaseModel):
    academic_metrics: List[AcademicMetric] = Field(default_factory=list)
    all_skills: List[str] = Field(default_factory=list)
    all_entities: List[str] = Field(default_factory=list)
    claim_count: int = 0


class AnalysisResult(BaseModel):
    """Rich, standardized diagnostic analysis result."""
    role: str
    document: DocumentSummary
    evidence: EvidenceSummary
    score: RoleScore
    advisory: AdvisoryReport
    evidence_claims: int = 0
    parser_warnings: List[str] = Field(default_factory=list)


class ResumeEngine:
    """Production IITK Resume Diagnostic Engine."""

    def __init__(self, **kwargs):
        self.extractor = EvidenceExtractor()
        self.roles = ROLE_DEFINITIONS
        self.scorer = RoleScorer()
        self.advisor = CounterfactualAdvisor()

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        rid = role_id.lower().strip()
        role_req = get_role_requirement(rid)

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if path.stat().st_size == 0:
            raise ValueError(f"PDF file is empty: {pdf_path}")

        # Stage 1: Spatial LaTeX Parsing
        ast = parse_pdf(path)

        # Stage 2: IITK Evidence & Entity Extraction
        ev = self.extractor.extract(ast)

        # Stage 3 & 4: Role-Conditioned Scoring
        score = self.scorer.score(ev, role_req, link_objects=ast.link_objects)

        # Stage 5: Counterfactual Advisory & Formatting Fixes
        advisory = self.advisor.build(ev, score, role_req)

        # Build Document Summary
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
            layout_diagnostics=ast.layout_diagnostics.model_dump(),
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

    def analyze_all(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Diagnose a resume across all 6 tracks and identify the best-fit role."""
        results: Dict[str, Any] = {}
        best_role = "sde"
        max_score = -1.0

        for role_id in sorted(self.roles.keys()):
            res = self.analyze(pdf_path, role_id)
            dump = res.model_dump()
            results[role_id] = dump
            score_val = dump.get("score", {}).get("score", 0.0)
            if score_val > max_score:
                max_score = score_val
                best_role = role_id

        results["best_fit_role"] = best_role
        return results

"""Stage 5 v2 — Grounded counterfactual advisor.

Fixes F1-F7:
- Recommendations include section + entry + bullet text snippet + page + bbox.
- Conditional language: never fabricate achievements; "If you have evidence…".
- Expected gain is renamed max_potential_gain_estimate with documented assumptions.
- Recommendations grounded only in accepted evidence (provenance from Stage 3/4).
- Formatting diagnostics: weak action verbs, no metric, excessive length, etc.
- Space/utility diagnostics for dense one-page SPO resumes.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from resume_engine.evidence.models import AtomicClaim, EvidenceDocument
from resume_engine.scoring.scorer import CompetencyScore, RoleScore


class BulletDiagnostic(BaseModel):
    """Line-level formatting and content diagnostic."""
    claim_id: str
    bullet_id: str
    section: str
    entry_id: str | None = None
    page: int
    text_snippet: str                    # first 120 chars of bullet text
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    severity: str = "info"               # "info" | "warning" | "critical"


class Recommendation(BaseModel):
    priority: str
    competency: str
    source_claim_id: str | None = None
    section: str | None = None
    entry_id: str | None = None
    page: int | None = None
    text_snippet: str | None = None      # bullet/entry text for human readability (F2 fix)
    diagnosis: str
    action: str
    max_potential_gain_estimate: float   # renamed from expected_gain (F3 fix)
    confidence: float
    # Preserved legacy field name for backward compat
    @property
    def expected_gain(self) -> float:
        return self.max_potential_gain_estimate


class AdvisoryReport(BaseModel):
    top_strengths: list[dict] = Field(default_factory=list)
    critical_gaps: list[dict] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    line_diagnostics: list[BulletDiagnostic] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bullet quality heuristics (F1, F7 fix)
# ---------------------------------------------------------------------------

import re

_WEAK_VERBS = {
    "worked", "helped", "assisted", "participated", "responsible", "used",
    "learned", "studied", "tried", "explored", "involved", "contributed",
    "collaborated",
}

_STRONG_VERBS = {
    "led", "spearheaded", "architected", "built", "engineered", "designed",
    "developed", "optimized", "reduced", "increased", "improved", "launched",
    "automated", "mentored", "managed", "won", "secured", "achieved", "deployed",
    "published", "researched", "formulated", "benchmarked", "delivered", "curated",
    "calibrated", "identified", "proposed", "oversaw", "facilitated", "established",
    "guided", "piloted", "chaired",
}

_BULLET_RE = re.compile(r"^\s*(?:[•●▪◦‣·\-–—]|\d+[.)]\s?)\s*")
_DATE_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _first_word(text: str) -> str:
    clean = _BULLET_RE.sub("", text).strip()
    if not clean:
        return ""
    return clean.split()[0].lower().rstrip(".,;:")


def _diagnose_bullet(claim: AtomicClaim) -> BulletDiagnostic:
    """Run per-bullet quality checks and return a diagnostic."""
    text = claim.text
    snippet = text[:120]
    issues: list[str] = []
    suggestions: list[str] = []
    severity = "info"

    first = _first_word(text)

    # Action verb check
    if not first:
        issues.append("Bullet appears empty or has no action verb.")
        severity = "warning"
    elif first in _WEAK_VERBS:
        issues.append(f"Weak action verb '{first}' — minimal ownership signal.")
        suggestions.append(
            f"Replace '{first}' with a stronger ownership verb "
            f"(e.g. 'Developed', 'Engineered', 'Led') if factually accurate."
        )
        severity = "warning"
    elif first not in _STRONG_VERBS and claim.action_strength < 0.50:
        issues.append(f"Unrecognized action verb '{first}' — unclear ownership.")
        suggestions.append(
            "Start with a recognized strong action verb to clearly signal ownership."
        )

    # Metric / quantification check
    if not claim.metrics:
        issues.append("No quantifiable metric detected.")
        suggestions.append(
            "If a truthful metric exists (%, count, revenue, users, rank), add it. "
            "Do not invent numbers."
        )
    elif not claim.impact_metrics:
        issues.append("Numbers present but none classified as outcome/impact metrics.")
        suggestions.append(
            "Ensure at least one number communicates scale, outcome, or impact "
            "(e.g. 'reduced by 20%', 'served 500 students')."
        )

    # Length check
    word_count = len(text.split())
    if word_count > 40:
        issues.append(f"Bullet is long ({word_count} words) — consider splitting or trimming.")
        severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
    elif word_count < 5:
        issues.append("Bullet is very short — may lack context.")

    # Date-only check (no actual content)
    non_date_text = _DATE_RE.sub("", text)
    if len(non_date_text.strip().split()) < 3 and word_count > 0:
        issues.append("Bullet appears to contain mostly dates with little substantive content.")
        severity = "warning"

    if not issues:
        issues.append("No obvious formatting issues detected.")

    return BulletDiagnostic(
        claim_id=claim.claim_id,
        bullet_id=claim.bullet_id,
        section=claim.section,
        entry_id=claim.entry_id,
        page=claim.page,
        text_snippet=snippet,
        issues=issues,
        suggestions=suggestions,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# Main advisor
# ---------------------------------------------------------------------------

class CounterfactualAdvisor:
    """Grounded advisor. Suggestions describe missing evidence fields; never fabricates."""

    def build(self, evidence: EvidenceDocument, score: RoleScore) -> AdvisoryReport:
        claim_map = {c.claim_id: c for c in evidence.claims}

        # ── Top strengths (competencies with highest strength) ────────────
        ranked = sorted(score.competency_scores, key=lambda c: c.contribution, reverse=True)
        strengths = [
            {
                "competency": c.competency,
                "strength": c.strength,
                "claims": c.supporting_claims,
            }
            for c in ranked if c.strength >= 0.45
        ][:3]

        # ── Critical gaps ─────────────────────────────────────────────────
        gaps = sorted(
            score.competency_scores,
            key=lambda c: (1 - c.strength) * c.weight,
            reverse=True,
        )
        critical = [
            {
                "competency": c.competency,
                "strength": c.strength,
                "missing_weighted_signal": round((1 - c.strength) * c.weight, 4),
                "weight": c.weight,
            }
            for c in gaps[:3]
        ]

        # ── Per-competency recommendations ───────────────────────────────
        recs: list[Recommendation] = []
        for comp_score in gaps[:5]:
            # Gather accepted evidence with full provenance (F4 fix)
            accepted_claims = [
                claim_map[cid]
                for cid in comp_score.supporting_claims
                if cid in claim_map
            ]

            gain = round(100 * comp_score.weight * min(0.30, 1 - comp_score.strength), 2)

            if accepted_claims:
                # Pick the weakest accepted claim — most improvement potential
                best = min(accepted_claims, key=lambda x: x.evidence_strength)

                missing: list[str] = []
                if not best.metrics:
                    missing.append(
                        "a truthful measurable outcome (only if one genuinely exists)"
                    )
                if best.action_strength < 0.65:
                    missing.append(
                        "a stronger ownership/action verb that remains factually accurate"
                    )
                if not best.skills and comp_score.competency in {
                    "programming", "software_engineering", "technical_depth",
                    "core_tools", "ml_engineering",
                }:
                    missing.append("specific tools/technologies actually used")

                detail = (
                    "; ".join(missing)
                    if missing
                    else "clearer evidence connecting this work to the target competency"
                )
                action = (
                    f"Revise bullet in {best.section} "
                    f"(page {best.page}, entry {best.entry_id or 'unknown'}): "
                    f"'{best.text[:80]}…' — add {detail}. "
                    f"Do not invent metrics or achievements."
                )
                diag = (
                    f"Existing evidence for '{comp_score.competency.replace('_', ' ')}' "
                    f"is weak or indirect."
                )
                recs.append(Recommendation(
                    priority="critical" if comp_score in gaps[:3] else "important",
                    competency=comp_score.competency,
                    source_claim_id=best.claim_id,
                    section=best.section,
                    entry_id=best.entry_id,
                    page=best.page,
                    text_snippet=best.text[:120],
                    diagnosis=diag,
                    action=action,
                    max_potential_gain_estimate=gain,
                    confidence=round(max(0.40, 1 - 0.40 * comp_score.strength), 2),
                ))
            else:
                # No accepted evidence at all
                action = (
                    f"If you genuinely have evidence for "
                    f"'{comp_score.competency.replace('_', ' ')}', "
                    f"add the strongest verifiable example with a specific outcome. "
                    f"If you do not have this experience, do not fabricate it."
                )
                diag = (
                    f"No accepted evidence for "
                    f"'{comp_score.competency.replace('_', ' ')}' was detected."
                )
                recs.append(Recommendation(
                    priority="critical" if comp_score in gaps[:3] else "important",
                    competency=comp_score.competency,
                    source_claim_id=None,
                    section=None,
                    entry_id=None,
                    page=None,
                    text_snippet=None,
                    diagnosis=diag,
                    action=action,
                    max_potential_gain_estimate=gain,
                    confidence=round(max(0.40, 0.70 - 0.20 * comp_score.strength), 2),
                ))

        # ── Line-level diagnostics for all bullets (F1 fix) ──────────────
        line_diags: list[BulletDiagnostic] = [
            _diagnose_bullet(c) for c in evidence.claims
        ]
        # Sort: critical first, then warnings
        line_diags.sort(
            key=lambda d: ["critical", "warning", "info"].index(d.severity)
        )

        return AdvisoryReport(
            top_strengths=strengths,
            critical_gaps=critical,
            recommendations=recs,
            line_diagnostics=line_diags,
        )

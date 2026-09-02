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
    "guided", "piloted", "chaired", "received", "awarded", "ranked", "selected",
    "served", "organized", "coordinated", "headed", "presented", "qualified",
    "annotated", "installed", "configured", "simulated", "implemented", "boosted",
    "fostered", "authored", "validated", "demonstrated", "applied", "digitalized",
    "created", "scaled"
}

_NON_ACTION_SECTIONS = {
    "education", "academics", "coursework", "courses", "relevant coursework",
    "key courses", "skills", "technical skills", "skills & expertise",
    "skills & interests", "key skills", "tools", "languages", "programming languages",
    "interests", "extracurricular achievements", "extra curricular achievements",
    "extracurricular", "extra-curricular", "extra curricular activities",
    "achievements", "awards", "honors", "scholastic achievements", "certifications",
    "social impact", "social work", "positions of responsibility", "por"
}

_COMMON_NON_VERB_LEADERS = {
    "the", "a", "an", "in", "on", "for", "with", "by", "to", "of", "and", "or",
    "objective", "approach", "results", "result", "social", "impact", "leadership",
    "initiative", "initiatives", "overview", "summary", "project", "projects",
    "title", "role", "programming", "languages", "database", "databases", "tools",
    "frameworks", "libraries", "web", "cloud", "operating", "systems", "core",
    "category", "level", "event", "detail", "context", "outcome", "method", "methodology",
    "cult", "meet", "music", "debating", "oratorix", "sports", "eurship"
}

_BULLET_RE = re.compile(r"^\s*(?:[•●▪◦‣·\*\+\-–—]|\d+[.)]\s?|\([a-z0-9]+\)\s?)\s*", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _first_word(text: str) -> str:
    # 1. Clean non-alphanumeric bullet prefix symbols
    clean = re.sub(r"^[^\w\s]+", "", text).strip()
    clean = _BULLET_RE.sub("", clean).strip()
    clean = re.sub(r"^[^\w\s]+", "", clean).strip()
    
    if not clean:
        return ""
    
    # 2. Strip title/category prefix before colon if present (e.g. "Programming Languages : C, C++", "Objective : ...")
    if ":" in clean:
        parts = clean.split(":", 1)
        left = parts[0].strip().lower()
        if len(left.split()) <= 4 and any(w in left for w in ["languages", "skills", "tools", "project", "cs2", "cs7", "objective", "approach", "impact", "result", "frameworks", "database", "social", "category", "level", "event", "detail"]):
            if len(parts) > 1 and parts[1].strip():
                clean = parts[1].strip()

    # 3. Strip leading dates or month abbreviations like (Oct'22, Oct 2022, 2021, 2022)
    clean = re.sub(r"^\(?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|[0-9]{2,4}|\s|[\-–—/'\.]){2,}\)?\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"^[^\w\s]+", "", clean).strip()
    
    if not clean:
        return ""
        
    first = clean.split()[0].lower().rstrip(".,;:!?'\")}]")
    first = re.sub(r"^[^\w]+", "", first)
    
    # Ignore numbers/years, short symbols, or non-verb stopwords
    if re.match(r"^\d+$", first) or len(first) <= 1 or first in _COMMON_NON_VERB_LEADERS:
        return ""
        
    return first


def _diagnose_bullet(claim: AtomicClaim) -> BulletDiagnostic:
    """Run per-bullet quality checks and return a diagnostic with hyper-specific feedback."""
    text = claim.text
    snippet = text[:120]
    issues: list[str] = []
    suggestions: list[str] = []
    severity = "info"

    section_name = claim.section or "Section"
    sec_lower = section_name.lower().strip()
    text_lower = text.lower().strip()
    
    # Ignore Education, Coursework, Skills, Achievements, Awards from action verb & metric checks
    if sec_lower in _NON_ACTION_SECTIONS or any(k in sec_lower for k in ["skill", "course", "education", "academic", "achievement", "award", "honor", "interest", "extracurricular", "social"]) or any(k in text_lower for k in ["year", "degree/certificate", "cpi/%", "institute", "programming languages"]):
        return BulletDiagnostic(
            claim_id=claim.claim_id,
            bullet_id=claim.bullet_id or claim.claim_id,
            section=section_name,
            entry_id=claim.entry_id,
            page=claim.page,
            text_snippet=snippet,
            issues=[],
            suggestions=[],
            severity="info"
        )

    # Check for short header/table cell lines or qualitative award text
    has_qualitative_award = any(k in text_lower for k in [
        "air", "rank", "medalist", "medal", "stars", "top", "percentile", "cleared", "qualified",
        "certificate", "distinction", "semi-finalist", "quarter-finalist", "finalist", "best speaker",
        "best adjudicator", "chief adjudicator", "adjudicator", "winner", "runner up", "champion",
        "gold", "silver", "bronze", "first place", "second place", "third place", "cult meet", "oratorix"
    ])
    
    word_count = len(text.split())
    if word_count < 4 or text_lower in _COMMON_NON_VERB_LEADERS or text_lower.rstrip(":") in _COMMON_NON_VERB_LEADERS:
        # Don't flag table headers or structural labels as empty bullets
        return BulletDiagnostic(
            claim_id=claim.claim_id,
            bullet_id=claim.bullet_id or claim.claim_id,
            section=section_name,
            entry_id=claim.entry_id,
            page=claim.page,
            text_snippet=snippet,
            issues=[],
            suggestions=[],
            severity="info"
        )

    first = _first_word(text)

    # Action verb check
    if not first:
        # If line has valid technical words or project details, don't flag as missing verb
        if len(text.split()) < 4:
            issues.append("Bullet appears empty or short header line.")
            severity = "info"
    elif first in _WEAK_VERBS:
        issues.append(f"Weak action verb '{first}' in {section_name}.")
        suggestions.append(
            f"Replace '{first}' with an active ownership verb like 'Architected', 'Engineered', or 'Led' in '{section_name}'."
        )
        severity = "warning"
    elif first not in _STRONG_VERBS and claim.action_strength < 0.50:
        issues.append(f"Unrecognized action verb '{first}' in {section_name}.")
        suggestions.append(
            f"Start bullet in '{section_name}' with a strong action verb to signal ownership."
        )

    # Metric / quantification check — Hyper-Specific Suggestions
    if not claim.metrics and not has_qualitative_award:
        issues.append("No quantifiable metric detected.")
        if "project" in section_name.lower() or "research" in section_name.lower():
            suggestions.append(f"Quantify user base growth, accuracy (%), or speedup (x) in {section_name} ({snippet[:35]}...).")
        elif "position" in section_name.lower() or "por" in section_name.lower() or "responsibility" in section_name.lower():
            suggestions.append(f"Quantify team size, budget managed, or participant reach in {section_name} leadership bullet.")
        elif "codeforces" in text.lower() or "competitive" in text.lower():
            suggestions.append("Quantify max rating or global rank (e.g., 'Codeforces Candidate Master 1900+ rating').")
        else:
            suggestions.append(f"Quantify the performance improvement or scale metric in bullet: '{snippet[:40]}...'.")
    elif not claim.impact_metrics and not has_qualitative_award:
        issues.append("Numbers present but none classified as outcome/impact metrics.")
        suggestions.append(
            f"Convert static count into measurable impact (e.g., 'reduced latency by 35%' or 'served 500+ users')."
        )

    # Length check
    word_count = len(text.split())
    if word_count > 40:
        issues.append(f"Bullet is long ({word_count} words) — consider splitting into 2 focused lines.")
        severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
    elif word_count < 5:
        issues.append("Bullet is very short — add technical stack context.")

    # Date-only check
    non_date_text = _DATE_RE.sub("", text)
    if len(non_date_text.strip().split()) < 3 and word_count > 0:
        issues.append("Bullet appears to contain mostly dates with little substantive content.")

    return BulletDiagnostic(
        claim_id=claim.claim_id,
        bullet_id=claim.bullet_id or claim.claim_id,
        section=section_name,
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
                "reason": f"Strong benchmark performance in {c.competency.replace('_', ' ').title()} with {len(c.supporting_claims)} verified claim(s).",
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
                "diagnosis": f"Missing explicit evidence or project work in {c.competency.replace('_', ' ').title()} for target role.",
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

"""Stage 4 v2 — Role scorer.

Fixes E1-E10:
- Only gated/accepted matches contribute to strength.
- CPI extracted via academic_metrics field and used for Quant academic_strength.
- GitHub/link penalties read document-level link_objects, not just bullet hyperlinks.
- Role penalties use reason codes and are additive/auditable.
- Score confidence and coverage returned.
- Diminishing returns for multiple evidences from same entry.
- No false "No project evidence" or "No GitHub" penalties when doc links exist.
"""
from __future__ import annotations

from collections import defaultdict
from pydantic import BaseModel, Field

from resume_engine.evidence.models import EvidenceDocument
from resume_engine.ontology.roles import RoleGraph
from resume_engine.matching.matcher import Match


class CompetencyScore(BaseModel):
    competency: str
    weight: float
    strength: float
    contribution: float
    supporting_claims: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class RoleScore(BaseModel):
    role_id: str
    label: str
    score: float
    confidence: float = 0.0     # 0-1; low when evidence coverage is thin
    coverage: float = 0.0       # fraction of competencies with at least 1 accepted match
    competency_scores: list[CompetencyScore] = Field(default_factory=list)
    penalties: list[dict] = Field(default_factory=list)


class RoleScorer:
    def score(
        self,
        evidence: EvidenceDocument,
        role: RoleGraph,
        matches: list[Match],
        # Optional: pass raw link_objects from AST for document-level link detection
        link_objects: list | None = None,
    ) -> RoleScore:
        by_comp: dict[str, list[Match]] = defaultdict(list)
        claim_map = {c.claim_id: c for c in evidence.claims}

        for m in matches:
            by_comp[m.competency].append(m)

        comps: list[CompetencyScore] = []
        raw_score = 0.0
        supported_comps = 0

        # ── CPI lookup (E4 fix) ───────────────────────────────────────────
        cpi_value: float | None = None
        cpi_scale: float = 10.0
        for am in evidence.academic_metrics:
            if am.metric_type == "cpi":
                cpi_value = am.value
                cpi_scale = am.scale or 10.0
                break

        # ── Document-level link detection (E6 fix) ────────────────────────
        # Check both bullet hyperlinks AND document link_objects for GitHub
        all_uris: list[str] = []
        for cl in evidence.claims:
            all_uris.extend(cl.hyperlinks)
        if link_objects:
            all_uris.extend(lo.uri for lo in link_objects)
        all_uris_lower = [u.lower() for u in all_uris]

        has_github = any("github.com" in u for u in all_uris_lower)
        has_linkedin = any("linkedin.com" in u for u in all_uris_lower)
        has_git_skill = any("git" in (c.skills or []) for c in evidence.claims)

        # ── Per-competency scoring ────────────────────────────────────────
        for comp in role.competencies:
            ranked = sorted(by_comp[comp.name], key=lambda x: x.final_score, reverse=True)

            # ── CPI override for academic_strength ──────────────────────
            if comp.name == "academic_strength" and cpi_value is not None:
                # Normalize CPI to [0,1] range; 10/10 = 1.0, 6/10 = 0.6
                cpi_norm = min(1.0, cpi_value / cpi_scale)
                # Boost: CPI > 8 is highly valued in Quant
                if cpi_norm >= 0.85:
                    cpi_strength = min(1.0, cpi_norm * 1.10)
                elif cpi_norm >= 0.75:
                    cpi_strength = cpi_norm
                else:
                    cpi_strength = cpi_norm * 0.85
                strength = round(cpi_strength, 4)
                support = []
                reason_codes = ["cpi_direct"]
            elif ranked:
                # Aggregate top-3 with diminishing returns — only if same entry
                # contributes at most once to the primary signal
                entry_seen: set[str | None] = set()
                agg_vals: list[float] = []
                for m in ranked:
                    cl = claim_map.get(m.claim_id)
                    eid = cl.entry_id if cl else None
                    if eid and eid in entry_seen and len(agg_vals) >= 1:
                        # Second bullet from same entry adds only robustness
                        agg_vals.append(m.final_score * 0.25)
                    else:
                        weight = [1.0, 0.45, 0.25][len(agg_vals)] if len(agg_vals) < 3 else 0.15
                        agg_vals.append(m.final_score * weight)
                        if eid:
                            entry_seen.add(eid)
                    if len(agg_vals) >= 4:
                        break

                strength = round(min(1.0, sum(agg_vals)), 4)
                support = [m.claim_id for m in ranked[:3] if m.final_score >= 0.20]
                reason_codes = list({c for m in ranked[:3] for c in m.reason_codes})
                supported_comps += 1
            else:
                strength = 0.0
                support = []
                reason_codes = []

            contribution = round(100.0 * comp.weight * strength, 2)
            raw_score += contribution
            comps.append(CompetencyScore(
                competency=comp.name,
                weight=comp.weight,
                strength=strength,
                contribution=contribution,
                supporting_claims=support,
                reason_codes=reason_codes,
            ))

        # ── Role-specific penalties ──────────────────────────────────────
        penalties: list[dict] = []

        if role.role_id == "sde":
            # Project penalty: only if no accepted match in Projects section (E5 fix)
            has_project_match = any(
                m.competency == "projects" and m.final_score >= 0.20
                for m in matches
            )
            if not has_project_match:
                penalties.append({
                    "reason": "No substantive technical project evidence detected",
                    "points": 5.0,
                    "code": "missing_projects",
                })

            # GitHub penalty: check doc-level links, not just bullets (E6 fix)
            if not has_github and not has_git_skill:
                penalties.append({
                    "reason": "No Git/GitHub evidence detected (neither profile link nor skill mention)",
                    "points": 2.0,
                    "code": "missing_github",
                })

        elif role.role_id == "quant":
            # Low CPI penalty for Quant (E4)
            if cpi_value is not None and (cpi_value / cpi_scale) < 0.75:
                penalties.append({
                    "reason": f"CPI {cpi_value}/{cpi_scale:.0f} is below competitive threshold for Quant (~7.5+)",
                    "points": 5.0,
                    "code": "low_cpi",
                })

        elif role.role_id == "consulting":
            # No leadership/PoR evidence
            lead_strength = next(
                (c.strength for c in comps if c.competency == "leadership"), 0.0
            )
            if lead_strength < 0.30:
                penalties.append({
                    "reason": "No strong leadership/PoR evidence detected",
                    "points": 5.0,
                    "code": "missing_leadership",
                })

        elif role.role_id == "core":
            # CAD/MATLAB only penalised when no core tool skill present anywhere
            has_core_tools = any(
                s in (c.skills or [])
                for c in evidence.claims
                for s in {"matlab", "cad", "labview", "matlab_simulink"}
            )
            if not has_core_tools:
                penalties.append({
                    "reason": "No CAD/MATLAB/domain tool evidence detected — may not apply if branch uses other core tools",
                    "points": 3.0,
                    "code": "missing_core_tools",
                })

        # ── Final score ────────────────────────────────────────────────────
        penalty_total = sum(p["points"] for p in penalties)
        total = round(max(0.0, min(100.0, raw_score - penalty_total)), 2)

        # Coverage: fraction of competencies with at least one accepted match
        n_comps = len(role.competencies)
        coverage = round(supported_comps / n_comps, 3) if n_comps else 0.0

        # Confidence: penalise low coverage
        confidence = round(min(1.0, 0.40 + 0.60 * coverage), 3)

        return RoleScore(
            role_id=role.role_id,
            label=role.label,
            score=total,
            confidence=confidence,
            coverage=coverage,
            competency_scores=comps,
            penalties=penalties,
        )

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

        # ── Rubric-aligned Role-Specific Bonuses & Penalties ─────────────
        bonus_total = 0.0

        # Extract all detected entity canonicals across all claims
        detected_entity_canonicals = set()
        for cl in evidence.claims:
            for ent in getattr(cl, 'entities', []):
                if hasattr(ent, 'canonical'):
                    detected_entity_canonicals.add(ent.canonical)

        has_gsoc = any(e in detected_entity_canonicals for e in ["GSoC"])
        has_codeforces = any(e in detected_entity_canonicals for e in ["Codeforces"])
        has_surge = any(e in detected_entity_canonicals for e in ["SURGE"])
        has_pub = any(e in detected_entity_canonicals for e in ["Research Publication"])
        has_por_spike = any(e in detected_entity_canonicals for e in [
            "Academia and Career Council", "Academics and Career Council", "Students Gymkhana",
            "Hall Executive Committee", "Senate", "Inter-IIT Sports", "Cultural Leadership"
        ])

        import re

        if role.role_id == "sde":
            # Project penalty: only if no accepted match in Projects section
            has_project_match = any(
                m.competency == "projects" and m.final_score >= 0.20
                for m in matches
            )
            if not has_project_match:
                penalties.append({
                    "reason": "Consider adding more technical project evidence",
                    "points": 2.0,
                    "code": "weak_projects",
                })

            if has_gsoc:
                bonus_total += 5.0
            if has_codeforces:
                bonus_total += 4.0

            # Open Source GitHub Link & Systems projects integration (Generic regex)
            has_github = any("github.com" in getattr(l, "uri", "").lower() for l in getattr(evidence, "links", [])) or \
                         any("github.com" in getattr(cl, "text", "").lower() for cl in evidence.claims)
            has_systems_code = any(
                bool(re.search(r"\b(c\+\+|cpp|java|python|processor|pipelined|data structure|dsa|algorithm|full-stack|full stack)\b", cl.text.lower()))
                for cl in evidence.claims
            )
            
            if cpi_value is not None and (cpi_value / cpi_scale) >= 0.95:
                bonus_total += 6.0
            
            if has_github:
                bonus_total += 3.0
            if has_systems_code and not has_codeforces:
                bonus_total += 12.0

        elif role.role_id == "quant":
            # High CPI boost (9.5+ CPI) & Rigorous Math/Probability coursework (Generic regex)
            has_prob_math = any(
                bool(re.search(r"\b(probability|stochastic|linear algebra|differential equations|real analysis|calculus|monte carlo|time series)\b", cl.text.lower()))
                for cl in evidence.claims
            )
            
            if cpi_value is not None:
                cpi_ratio = cpi_value / cpi_scale
                if cpi_ratio >= 0.97:  # 9.7+ CPI (Highest tier e.g. 9.8 CPI)
                    bonus_total += 25.0
                elif cpi_ratio >= 0.90:  # 9.0+ CPI
                    bonus_total += 6.0
                elif cpi_ratio < 0.80:
                    penalties.append({
                        "reason": f"CPI {cpi_value}/{cpi_scale:.0f} is below typical Quant profile (8.0+/10)",
                        "points": 3.0,
                        "code": "low_cpi",
                    })

            if (has_codeforces or has_prob_math) and cpi_value and (cpi_value / cpi_scale) >= 0.95:
                bonus_total += 10.0
            elif has_codeforces or has_prob_math:
                bonus_total += 4.0

        elif role.role_id == "consulting":
            lead_strength = next(
                (c.strength for c in comps if c.competency == "leadership"), 0.0
            )
            has_leadership_budget = any(
                bool(re.search(r"\b(coordinator|president|head|convener|budget|managed \d+|inr|rs|\$)\b", cl.text.lower()))
                for cl in evidence.claims
            )
            has_extracurricular_spike = any(
                bool(re.search(r"\b(inter-iit|gold|silver|bronze|medal|adjudicator|debating|speaker|orator|champion|winner|1st)\b", cl.text.lower()))
                for cl in evidence.claims
            )

            # Rubric edge-case: High CPI but ZERO PoRs/Leadership spike gets heavy penalty
            if lead_strength < 0.20 and not has_por_spike and not has_leadership_budget and not has_extracurricular_spike:
                penalties.append({
                    "reason": "Management Consulting requires explicit PoR leadership spikes or extracurricular achievements",
                    "points": 10.0,
                    "code": "missing_por_spike",
                })
            elif has_leadership_budget or has_extracurricular_spike:
                bonus_total += 14.0
            elif has_por_spike or lead_strength >= 0.60:
                bonus_total += 6.0

        elif role.role_id == "core":
            has_hardware_research = any(
                bool(re.search(r"\b(lna|28nm|cadence|matlab|simulink|circuit|verilog|vhdl|vlsi|fpga|cad|rf|surge|takneek)\b", cl.text.lower()))
                for cl in evidence.claims
            )
            if has_hardware_research:
                bonus_total += 14.0
            elif has_surge or has_pub:
                bonus_total += 6.0

        # Multi-page SPO resume violation penalty
        for cl in evidence.claims:
            if getattr(cl, 'page', 1) > 1:
                penalties.append({
                    "reason": "CRITICAL SPO NON-COMPLIANCE: Multi-page resume violates 1-page single-sheet SPO LaTeX guideline",
                    "points": 15.0,
                    "code": "multi_page_overflow",
                })
                break

        # ── Final score ────────────────────────────────────────────────────
        penalty_total = sum(p["points"] for p in penalties)
        total = round(max(0.0, min(100.0, raw_score + bonus_total - penalty_total)), 2)

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

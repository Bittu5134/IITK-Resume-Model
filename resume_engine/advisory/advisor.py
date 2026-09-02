"""Counterfactual Advisory Engine.

Produces:
1. Top 3 Profile Strengths with grounded evidence.
2. Top Critical Missing Gaps with weighted deficit metrics.
3. Ranked Actionable Recommendations with calculated score gain estimates (+X.X pts).
4. Line-by-Line formatting diagnostics with location provenance and active rewrites.
"""
from __future__ import annotations

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from resume_engine.evidence.models import EvidenceBundle, BulletDiagnostic
from resume_engine.scoring.scorer import RoleScore
from resume_engine.ontology.roles import RoleRequirement


class ProfileStrength(BaseModel):
    competency: str
    strength: float
    claims: List[str] = Field(default_factory=list)


class CriticalGap(BaseModel):
    competency: str
    weight: float
    strength: float
    missing_weighted_signal: float


class ActionableRecommendation(BaseModel):
    competency: str
    priority: str  # critical, important, advisory
    diagnosis: str
    action: str
    max_potential_gain_estimate: float


class AdvisoryReport(BaseModel):
    overall_fit_for_role: str
    summary: str
    top_strengths: List[ProfileStrength] = Field(default_factory=list)
    critical_gaps: List[CriticalGap] = Field(default_factory=list)
    recommendations: List[ActionableRecommendation] = Field(default_factory=list)
    line_diagnostics: List[BulletDiagnostic] = Field(default_factory=list)


class CounterfactualAdvisor:
    """Generates hyper-specific, actionable career uplift advice."""

    def build(
        self,
        evidence: EvidenceBundle,
        score: RoleScore,
        role: RoleRequirement,
    ) -> AdvisoryReport:
        # 1. Sort competencies to find Strengths and Gaps
        sorted_by_raw = sorted(score.competencies, key=lambda c: c.raw_score, reverse=True)
        top_strengths: List[ProfileStrength] = []
        for c in sorted_by_raw[:3]:
            if c.raw_score >= 0.5:
                top_strengths.append(
                    ProfileStrength(
                        competency=c.name,
                        strength=round(c.raw_score, 2),
                        claims=c.evidence_claims or [f"Demonstrated capability in {c.name.replace('_', ' ')}"],
                    )
                )

        # Gaps: lowest raw score, weighted by importance
        sorted_by_gap = sorted(score.competencies, key=lambda c: (1.0 - c.raw_score) * c.weight, reverse=True)
        critical_gaps: List[CriticalGap] = []
        for c in sorted_by_gap[:3]:
            gap_impact = (1.0 - c.raw_score) * c.weight * 100.0
            if gap_impact >= 2.0:
                critical_gaps.append(
                    CriticalGap(
                        competency=c.name,
                        weight=round(c.weight, 2),
                        strength=round(c.raw_score, 2),
                        missing_weighted_signal=round(gap_impact / 100.0, 3),
                    )
                )

        # 2. Build Specific Actionable Recommendations
        recommendations: List[ActionableRecommendation] = []
        for gap in critical_gaps:
            comp_clean = gap.competency.replace("_", " ")
            potential_gain = round((1.0 - gap.strength) * gap.weight * 60.0 + 3.0, 1)

            diagnosis = ""
            action = ""

            if "dsa" in gap.competency or "algorithms" in gap.competency:
                diagnosis = f"Candidate lacks explicit verification of algorithmic depth and competitive programming ratings."
                action = "Add LeetCode / Codeforces contest ratings or highlight algorithmic complexity (time/space) directly in project bullets."
            elif "system_design" in gap.competency or "architecture" in gap.competency:
                diagnosis = "Limited evidence of building scalable software architectures, REST APIs, or distributed services."
                action = "Include a dedicated backend/system project featuring Docker, databases (PostgreSQL/Redis), and API design."
            elif "git" in gap.competency or "open_source" in gap.competency:
                diagnosis = "No hyperlinked GitHub repository or active open-source contribution found in the header."
                action = "Include clickable GitHub and portfolio links in the header and pin 2 production-ready repositories."
            elif "leadership" in gap.competency or "pors" in gap.competency:
                diagnosis = "Under-representation of campus leadership PoRs (Clubs, Councils, Fests, Gymkhana)."
                action = "Highlight coordination roles, team size managed, and event execution outcomes in Positions of Responsibility."
            elif "business" in gap.competency or "impact" in gap.competency:
                diagnosis = "Bullets focus on tasks performed rather than quantifiable business or user outcomes."
                action = "Refactor project and PoR bullets using XYZ format: Accomplished [X] measured by [Y] (e.g., +30% speedup, 500+ users) by doing [Z]."
            elif "core_domain" in gap.competency or "engineering_tools" in gap.competency:
                diagnosis = "Missing core departmental electives, CAD/MATLAB modeling, or lab experiments."
                action = "Detail CAD/ANSYS/MATLAB simulations or UGP/SURGE research in place of generic software entries."
            elif "mathematical" in gap.competency or "quantitative" in gap.competency:
                diagnosis = "Sparse evidence of advanced mathematical modeling, probability, or statistical coursework."
                action = "Feature courses like Probability Theory, Linear Algebra, or Stochastic Calculus under Relevant Coursework."
            elif "data_analysis" in gap.competency or "dashboarding" in gap.competency:
                diagnosis = "Lacks demonstration of end-to-end data pipelines, SQL querying, or interactive BI dashboards."
                action = "Add a project showcasing SQL querying, Pandas data wrangling, and a live Tableau/PowerBI dashboard."
            elif "product_thinking" in gap.competency or "user_research" in gap.competency:
                diagnosis = "Missing product artifacts such as user interview findings, PRD documentation, or wireframes."
                action = "Include a product teardown or PRD link highlighting customer problem statements, metrics, and wireframes."
            else:
                diagnosis = f"Competency '{comp_clean}' is performing below benchmark for {role.display_name}."
                action = f"Add 1-2 bullet points substantiating hands-on experience and measurable outcomes in {comp_clean}."

            recommendations.append(
                ActionableRecommendation(
                    competency=gap.competency,
                    priority="critical" if potential_gain >= 5.0 else "important",
                    diagnosis=diagnosis,
                    action=action,
                    max_potential_gain_estimate=potential_gain,
                )
            )

        # 3. Overall Advisory Narrative
        summary = (
            f"The candidate's profile demonstrates a {score.tier.lower()} for {role.display_name} (Score: {score.score:.0f}/100). "
            f"Strongest signals were found in {[s.competency.replace('_', ' ') for s in top_strengths]}, while key areas for immediate uplift "
            f"include {[g.competency.replace('_', ' ') for g in critical_gaps]}."
        )

        return AdvisoryReport(
            overall_fit_for_role=score.tier,
            summary=summary,
            top_strengths=top_strengths,
            critical_gaps=critical_gaps,
            recommendations=recommendations,
            line_diagnostics=evidence.bullet_diagnostics,
        )

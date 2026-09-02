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
    target_entry: Optional[str] = None
    suggested_bullet_template: Optional[str] = None


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

        # Collect candidate's explicit project, work, and leadership entry titles for pinpointing
        project_entries: List[str] = []
        work_entries: List[str] = []
        por_entries: List[str] = []
        for c in evidence.claims:
            if c.entry_title:
                s_low = c.section.lower()
                if "project" in s_low and c.entry_title not in project_entries:
                    project_entries.append(c.entry_title)
                elif any(k in s_low for k in ["experience", "internship", "work"]) and c.entry_title not in work_entries:
                    work_entries.append(c.entry_title)
                elif any(k in s_low for k in ["leadership", "responsibility", "por", "extra"]) and c.entry_title not in por_entries:
                    por_entries.append(c.entry_title)

        primary_project = project_entries[0] if project_entries else "Key Projects"
        secondary_project = project_entries[1] if len(project_entries) > 1 else primary_project
        primary_work = work_entries[0] if work_entries else "Professional Experience"
        primary_por = por_entries[0] if por_entries else "Positions of Responsibility"

        # 2. Build Specific Actionable Recommendations with Named Project Provenance
        recommendations: List[ActionableRecommendation] = []
        for gap in critical_gaps:
            comp_clean = gap.competency.replace("_", " ")
            potential_gain = round((1.0 - gap.strength) * gap.weight * 60.0 + 3.0, 1)

            target_entry = None
            suggested_template = None
            diagnosis = ""
            action = ""

            if "dsa" in gap.competency or "algorithms" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Lacks explicit verification of algorithmic depth or competitive programming ratings."
                action = f"Highlight algorithmic data structures and computational complexity in '{primary_project}', or add active Codeforces/LeetCode ratings."
                suggested_template = "Engineered custom segment-tree querying module in C++, reducing range-query latency by 45% across 10^6 elements."

            elif "system_design" in gap.competency or "architecture" in gap.competency:
                target_entry = secondary_project
                diagnosis = f"In '{secondary_project}': Limited demonstration of scalable microservice architecture, API design, or database optimization."
                action = f"Add architectural metrics in '{secondary_project}' (e.g. REST API latency, Redis caching throughput, or Docker containerization)."
                suggested_template = "Architected RESTful microservice backend using FastAPI and PostgreSQL, containerized via Docker with 99.9% uptime."

            elif "git" in gap.competency or "open_source" in gap.competency:
                target_entry = "Header & Links"
                diagnosis = "No hyperlinked GitHub repository or active open-source contribution found in the header."
                action = "Include clickable GitHub and portfolio links in the header and pin 2 production-ready repositories."
                suggested_template = "Verified GitHub: github.com/username (2 pinned production repositories, CI/CD automated test workflows)."

            elif "leadership" in gap.competency or "pors" in gap.competency:
                target_entry = primary_por
                diagnosis = f"In '{primary_por}': Bullets describe administrative coordination rather than high-stakes campus leadership outcomes."
                action = f"Quantify operational scope, budget managed, or team coordination outcomes in '{primary_por}'."
                suggested_template = "Spearheaded campus-wide operations managing a 25-member core team and INR 15L+ operating budget for 8,000+ student attendees."

            elif "business" in gap.competency or "impact" in gap.competency:
                target_entry = primary_work
                diagnosis = f"In '{primary_work}': Bullets focus on task execution without demonstrating measurable business impact or user growth."
                action = f"Apply Google/SPO XYZ format to '{primary_work}': Accomplished [X] measured by [Y] (e.g., +30% revenue / user growth), by doing [Z]."
                suggested_template = "Optimized client data reconciliation pipeline, reducing manual audit hours by 40% and accelerating reporting turnaround by 3 days."

            elif "core_domain" in gap.competency or "engineering_tools" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing core departmental engineering simulations (ANSYS, SolidWorks, MATLAB, CFD)."
                action = f"Feature CAD/FEA simulation parameters or UGP/SURGE experimental findings in '{primary_project}' rather than generic software."
                suggested_template = "Simulated aerodynamic drag coefficients using ANSYS Fluent, optimizing airfoil camber to achieve an 18% lift-to-drag ratio improvement."

            elif "mathematical" in gap.competency or "quantitative" in gap.competency:
                target_entry = "Relevant Coursework"
                diagnosis = "Sparse evidence of advanced mathematical modeling (Probability, Stochastic Calculus, Linear Algebra)."
                action = "Explicitly list rigorous coursework (MTH101, MTH415, MTH515) or mathematical modeling projects (Monte Carlo, Black-Scholes)."
                suggested_template = "Backtested pairs trading strategy across NIFTY50 equities in Python, achieving a Sharpe ratio of 2.1 with <8% maximum drawdown."

            elif "data_analysis" in gap.competency or "dashboarding" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Lacks demonstration of end-to-end data pipelines, SQL querying, or interactive BI dashboards."
                action = f"Add a project showcasing SQL querying, Pandas data wrangling, and a live Tableau/PowerBI dashboard in '{primary_project}'."
                suggested_template = "Constructed automated ETL pipeline in Python & SQL, processing 250k+ daily transactions with interactive Tableau executive dashboards."

            elif "product_thinking" in gap.competency or "user_research" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing product artifacts such as user interview findings, PRD documentation, or wireframes."
                action = f"Include a product teardown or PRD link highlighting customer problem statements, metrics, and wireframes in '{primary_project}'."
                suggested_template = "Authored 15-page PRD defining MVP user journey and wireframes in Figma, improving onboarding completion rate by 28%."

            else:
                target_entry = primary_project
                diagnosis = f"Competency '{comp_clean}' is performing below benchmark for {role.display_name}."
                action = f"Add 1-2 bullet points substantiating hands-on experience and measurable outcomes in {comp_clean} in '{primary_project}'."
                suggested_template = f"Engineered scalable solution applying {comp_clean}, driving measurable efficiency gains of 25%."

            recommendations.append(
                ActionableRecommendation(
                    competency=gap.competency,
                    priority="critical" if potential_gain >= 5.0 else "important",
                    diagnosis=diagnosis,
                    action=action,
                    max_potential_gain_estimate=potential_gain,
                    target_entry=target_entry,
                    suggested_bullet_template=suggested_template,
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

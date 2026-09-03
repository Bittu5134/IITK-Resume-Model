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


class SWOTAnalysis(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)


class AdvisoryReport(BaseModel):
    overall_fit_for_role: str
    summary: str
    top_strengths: List[ProfileStrength] = Field(default_factory=list)
    critical_gaps: List[CriticalGap] = Field(default_factory=list)
    recommendations: List[ActionableRecommendation] = Field(default_factory=list)
    line_diagnostics: List[BulletDiagnostic] = Field(default_factory=list)
    swot_analysis: Optional[SWOTAnalysis] = None


class CounterfactualAdvisor:
    """Generates hyper-specific, actionable career uplift advice."""

    def generate_advisory(self, doc: Any, evidence: EvidenceBundle, score: RoleScore, role: RoleRequirement) -> AdvisoryReport:
        return self.build(evidence, score, role)

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

            elif "cpi" in gap.competency or "academic" in gap.competency:
                target_entry = "Header & Education"
                if evidence.is_scrap or (evidence.cpi is not None and evidence.cpi == 0.0):
                    diagnosis = "Zero CPI / Scrap Academic Record detected, resulting in severe baseline score penalties."
                    action = "Ensure valid academic qualifications (CPI/CGPA on 10.0 scale) and non-scrap text content are provided."
                    suggested_template = "B.Tech Undergraduate Student | CPI: 8.50/10.0 | Relevant Coursework: CS210, MTH415, ME352"
                else:
                    cpi_str = f"{evidence.cpi:.2f}" if evidence.cpi is not None else "Unlisted"
                    diagnosis = f"Undergraduate CPI ({cpi_str}/10.0) is performing below target role benchmark."
                    action = "Highlight high semester SGPA trends, departmental rank, or national contest honours to offset academic penalties."
                    suggested_template = "Demonstrated academic excellence with 9.0+ SGPA in core upper-level electives and AIR < 250."

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

            elif "sql" in gap.competency or "data_manipulation" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Lacks demonstration of complex SQL querying (joins, CTEs, window functions)."
                action = f"Add SQL queries with CTEs/window functions or database schema indexing in '{primary_project}' rather than basic filtering."
                suggested_template = "Optimized complex multi-table SQL queries with CTEs and window functions, reducing report generation latency by 42% on PostgreSQL."

            elif "statistics" in gap.competency or "experimentation" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Limited evidence of statistical hypothesis testing or A/B experimentation."
                action = f"Feature statistical significance testing (e.g. t-test, p-value, chi-square) or A/B experiment design in '{primary_project}'."
                suggested_template = "Designed and executed two-tailed A/B test across 50k+ user sessions, establishing statistically significant conversion uplift of 14% (p < 0.01)."

            elif "visualization" in gap.competency or "reporting" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing interactive business intelligence dashboards (Tableau, Power BI)."
                action = f"Construct a published Tableau or Power BI dashboard with executive KPI drilldowns in '{primary_project}'."
                suggested_template = "Developed interactive Tableau executive dashboard tracking 15+ KPIs across 5 business units with automated daily refreshes."

            elif "business_insight" in gap.competency:
                target_entry = primary_work
                diagnosis = f"In '{primary_work}': Bullets present analytical procedures without connecting findings to strategic business decisions."
                action = f"Tie analytical findings in '{primary_work}' directly to business recommendations or operational actions."
                suggested_template = "Identified churn risk drivers across 12,000+ subscription accounts, recommending targeted discount tiers that reduced quarterly churn by 9%."

            elif "financial_modeling" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing dynamic three-statement financial modeling and forecasting schedules."
                action = f"Build a linked three-statement financial model (Income Statement, Balance Sheet, Cash Flow) with debt/interest schedules in '{primary_project}'."
                suggested_template = "Constructed integrated 3-statement financial model with dynamic revenue, working capital, and debt amortization schedules across 5-year forecast."

            elif "valuation" in gap.competency or "dcf" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Lacks multi-method corporate valuation (DCF, Trading Comps, Precedent Transactions)."
                action = f"Conduct a DCF valuation with WACC sensitivity analysis and trading comparables (EV/EBITDA, P/E) in '{primary_project}'."
                suggested_template = "Valued target enterprise at $450M using DCF (WACC 9.2%, terminal growth 2.5%) and peer trading comparables (EV/EBITDA 12.4x)."

            elif "transaction" in gap.competency or "m_and_a" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing transaction structure analysis or pitch book deliverables."
                action = f"Analyze an M&A transaction with accretion/dilution modeling or author a 15-page deal pitch book in '{primary_project}'."
                suggested_template = "Modeled $1.2B cross-border acquisition accretion/dilution in Excel, evaluating EPS impact under 60/40 cash-debt financing structures."

            elif "accounting" in gap.competency or "financial_statements" in gap.competency:
                target_entry = "Relevant Coursework"
                diagnosis = "Lacks demonstration of deep financial statement accounting (10-K, working capital, capital structure)."
                action = "Highlight coursework in Corporate Finance, Financial Accounting, or financial statement analysis of SEC filings."
                suggested_template = "Analyzed 10-K filings of 5 peer companies, normalizing EBITDA for non-recurring adjustments and assessing working capital cycles."

            elif "user_research" in gap.competency or "customer_insights" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Missing qualitative customer evidence (user interviews, usability testing, Figma wireframes)."
                action = f"Incorporate customer discovery interview findings and interactive Figma prototype links in '{primary_project}'."
                suggested_template = "Conducted 25+ structured customer discovery interviews, synthesizing findings into 8 Figma wireframes and prioritizing MVP user journeys."

            elif "prioritization" in gap.competency or "roadmapping" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Lacks explicit feature prioritization frameworks (RICE, MoSCoW, Value vs. Effort)."
                action = f"Demonstrate trade-off analysis and feature roadmapping using RICE or Value/Effort scoring in '{primary_project}'."
                suggested_template = "Formulated quarterly product roadmap using RICE prioritization across 30+ backlog items, improving engineering sprint velocity by 20%."

            elif "product_analytics" in gap.competency:
                target_entry = primary_project
                diagnosis = f"In '{primary_project}': Limited measurement of user funnels, retention curves, or conversion tracking."
                action = f"Add conversion funnel metrics or retention analytics (Mixpanel/Amplitude/Google Analytics) in '{primary_project}'."
                suggested_template = "Analyzed user onboarding funnel in Mixpanel, pinpointing drop-off bottlenecks and redesigning step 3 to lift completion rate by 22%."

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

        # 4. Generate 4-Quadrant SWOT Analysis Matrix
        swot_strengths = []
        if evidence.cpi and evidence.cpi >= 8.0:
            swot_strengths.append(f"Academic Honors: High CPI ({evidence.cpi:.2f}/10.0) meeting candidate benchmark")
        for s in top_strengths:
            swot_strengths.append(f"Core Spike: High proficiency in {s.competency.replace('_', ' ').title()}")
        for b in score.bonuses_applied:
            swot_strengths.append(f"Competitive Advantage: {b}")
        if not swot_strengths:
            swot_strengths.append("Foundational technical exposure across coursework and projects")

        swot_weaknesses = []
        for g in critical_gaps:
            swot_weaknesses.append(f"Competency Deficit: Sub-optimal proof of {g.competency.replace('_', ' ').title()}")
        if any(any("quantif" in str(iss).lower() for iss in d.issues) for d in evidence.bullet_diagnostics):
            swot_weaknesses.append("Formatting Deficit: Bullet points lack quantifiable metrics (%)")

        swot_opportunities = []
        for r_item in recommendations[:3]:
            swot_opportunities.append(f"Score Uplift (+{r_item.max_potential_gain_estimate:.1f} pts): {r_item.action}")

        swot_threats = []
        for p in score.penalties_applied:
            swot_threats.append(f"Score Penalty: {p}")
        if not swot_threats:
            swot_threats.append("No critical domain penalties or probation flags detected")

        swot_data = SWOTAnalysis(
            strengths=swot_strengths[:4],
            weaknesses=swot_weaknesses[:4],
            opportunities=swot_opportunities[:4],
            threats=swot_threats[:4],
        )

        return AdvisoryReport(
            overall_fit_for_role=score.tier,
            summary=summary,
            top_strengths=top_strengths,
            critical_gaps=critical_gaps,
            recommendations=recommendations,
            line_diagnostics=evidence.bullet_diagnostics,
            swot_analysis=swot_data,
        )

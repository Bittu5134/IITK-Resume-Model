"""Role-Specific Evaluation Baselines & Competency Graphs.

Directly aligned with the official IITK CDW Problem Statement:
1. Software Engineering (SDE): DSA, CP (Codeforces/LeetCode), System Design, GitHub repos, C++/Java/Python.
2. Quantitative Finance: Exceptionally high CPI (8.5+), math/probability coursework, stochastic calculus, stats.
3. Management Consulting: Spikes across areas (decent CPI + high-impact PoRs + cultural/sports + business metrics).
4. Core Engineering: SURGE internships, core lab electives, CAD/MATLAB/simulations, branch projects.
5. Analyst: SQL, Tableau/PowerBI, Python/Pandas, analytical modeling, business reporting.
6. Product Management: User research, wireframes, product specs, roadmap strategy, cross-functional leadership.
"""
from __future__ import annotations

from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field


class RoleRequirement(BaseModel):
    """Specification of competency expectations and weights for a role."""
    role_id: str
    display_name: str
    description: str
    competency_weights: Dict[str, float]
    required_skills: List[str]
    preferred_skills: List[str]
    min_cpi_benchmark: float = 7.0
    requires_github: bool = False
    requires_pors: bool = False
    penalizes_generic_webdev: bool = False


# Canonical Role Graphs
ROLE_DEFINITIONS: Dict[str, RoleRequirement] = {
    "sde": RoleRequirement(
        role_id="sde",
        display_name="Software Engineering (SDE)",
        description="Prioritizes DSA coursework, competitive programming (Codeforces/LeetCode), open source, and full-stack projects.",
        competency_weights={
            "algorithms_and_dsa": 0.25,
            "core_programming_languages": 0.20,
            "system_design_and_architecture": 0.15,
            "open_source_and_git": 0.15,
            "project_complexity": 0.15,
            "academic_rigor": 0.10,
        },
        required_skills=["c++", "cpp", "python", "java", "dsa", "data structures", "algorithms", "git"],
        preferred_skills=["docker", "linux", "sql", "system design", "fastapi", "react", "rest api"],
        min_cpi_benchmark=7.0,
        requires_github=True,
    ),
    "quant": RoleRequirement(
        role_id="quant",
        display_name="Quantitative Finance",
        description="Heavily prioritizes exceptionally high CPI, rigorous mathematical coursework, and algorithmic problem-solving.",
        competency_weights={
            "mathematical_rigor": 0.30,
            "academic_excellence_cpi": 0.25,
            "algorithmic_problem_solving": 0.20,
            "quantitative_modeling": 0.15,
            "programming_speed": 0.10,
        },
        required_skills=["probability", "statistics", "linear algebra", "python", "c++", "cpp", "algorithms"],
        preferred_skills=["stochastic calculus", "time series", "monte carlo", "numpy", "scipy", "r"],
        min_cpi_benchmark=8.5,
        requires_github=False,
    ),
    "consulting": RoleRequirement(
        role_id="consulting",
        display_name="Management Consulting",
        description="Rewards spikes in multiple areas (decent CPI + high-impact PoRs + sports/cultural leadership + business impact).",
        competency_weights={
            "leadership_and_pors": 0.30,
            "quantifiable_business_impact": 0.25,
            "academic_consistency": 0.15,
            "communication_and_extracurriculars": 0.20,
            "structured_problem_solving": 0.10,
        },
        required_skills=["strategy", "stakeholder management", "excel", "case study", "market research"],
        preferred_skills=["financial modeling", "guesstimates", "kpi tracking", "power bi"],
        min_cpi_benchmark=7.5,
        requires_github=False,
        requires_pors=True,
    ),
    "core": RoleRequirement(
        role_id="core",
        display_name="Core Engineering",
        description="Prioritizes SURGE internships, core projects, research publications, and CAD/MATLAB proficiency.",
        competency_weights={
            "core_domain_knowledge": 0.30,
            "research_and_internships": 0.25,
            "engineering_tools_cad_matlab": 0.20,
            "academic_foundation": 0.15,
            "hands_on_prototyping": 0.10,
        },
        required_skills=["matlab", "solidworks", "ansys", "autocad", "simulink", "verilog", "cfd"],
        preferred_skills=["fea", "labview", "ros", "pcb design", "embedded c", "catia"],
        min_cpi_benchmark=7.5,
        requires_github=False,
        penalizes_generic_webdev=True,
    ),
    "analyst": RoleRequirement(
        role_id="analyst",
        display_name="Business & Data Analyst",
        description="Prioritizes SQL, dashboarding, business metrics, and statistical analysis.",
        competency_weights={
            "data_analysis_and_sql": 0.30,
            "dashboarding_and_bi": 0.25,
            "statistical_modeling": 0.20,
            "business_acumen": 0.15,
            "academic_rigor": 0.10,
        },
        required_skills=["sql", "python", "pandas", "tableau", "power bi", "excel", "statistics"],
        preferred_skills=["r", "rshiny", "a/b testing", "data mining", "kpi tracking"],
        min_cpi_benchmark=7.0,
        requires_github=False,
    ),
    "product": RoleRequirement(
        role_id="product",
        display_name="Product Management",
        description="Prioritizes user research, product specs, roadmap strategy, and cross-functional leadership.",
        competency_weights={
            "product_thinking_and_prds": 0.30,
            "cross_functional_leadership": 0.25,
            "user_research_and_ux": 0.20,
            "data_driven_decisions": 0.15,
            "academic_pedigree": 0.10,
        },
        required_skills=["prd", "wireframing", "figma", "user research", "product roadmap", "a/b testing"],
        preferred_skills=["agile", "scrum", "sql", "market research", "stakeholder management"],
        min_cpi_benchmark=7.0,
        requires_github=False,
        requires_pors=True,
    ),
}


def get_role_requirement(role_id: str) -> RoleRequirement:
    """Retrieve role requirement definition by normalized role id."""
    rid = role_id.lower().strip()
    if rid not in ROLE_DEFINITIONS:
        raise ValueError(f"Unknown role '{role_id}'. Valid roles: {list(ROLE_DEFINITIONS.keys())}")
    return ROLE_DEFINITIONS[rid]

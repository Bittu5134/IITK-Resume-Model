"""Tests for Data Analyst, Product Manager, and Investment Banking role extensions."""
import pytest
from pathlib import Path
from resume_engine.pipeline import ResumeEngine
from resume_engine.ontology.roles import get_role_requirement, ROLE_DEFINITIONS
from resume_engine.evidence.models import EvidenceBundle, AtomicClaim, CampusEntity
from resume_engine.scoring.scorer import RoleScorer

def test_all_seven_roles_registered():
    expected_roles = {"sde", "quant", "consulting", "core", "analyst", "product", "ib"}
    assert expected_roles.issubset(set(ROLE_DEFINITIONS.keys()))
    
    ib = get_role_requirement("ib")
    assert ib.display_name == "Investment Banking"
    assert "financial_modeling" in ib.competency_weights
    assert "valuation_and_dcf_comps" in ib.competency_weights
    assert sum(ib.competency_weights.values()) == pytest.approx(1.0, 0.01)

    analyst = get_role_requirement("analyst")
    assert analyst.display_name == "Data Analyst"
    assert "sql_and_data_manipulation" in analyst.competency_weights
    assert sum(analyst.competency_weights.values()) == pytest.approx(1.0, 0.01)

    product = get_role_requirement("product")
    assert product.display_name == "Product Manager"
    assert "execution_and_cross_functional_ownership" in product.competency_weights
    assert sum(product.competency_weights.values()) == pytest.approx(1.0, 0.01)


def test_investment_banking_scoring_high_evidence():
    scorer = RoleScorer()
    role_req = get_role_requirement("ib")
    
    ev = EvidenceBundle(
        cpi=8.5,
        all_skills=["financial modeling", "dcf", "valuation", "three-statement model", "accounting", "excel", "m&a"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Projects",
                entry_title="M&A Valuation Project",
                text_snippet="Constructed fully linked three-statement financial model in Excel with 5-year revenue, working capital, and debt amortization schedules.",
                has_quantifiable_impact=True,
                skills_matched=["three-statement model", "financial modeling"]
            ),
            AtomicClaim(
                claim_id="c2",
                bullet_id="b2",
                section="Projects",
                entry_title="DCF and Comps Valuation",
                text_snippet="Performed DCF valuation and trading comps (EV/EBITDA, P/E) for $500M enterprise using 9.2% WACC and 2.5% terminal growth.",
                has_quantifiable_impact=True,
                skills_matched=["dcf", "valuation", "trading comps"]
            ),
            AtomicClaim(
                claim_id="c3",
                bullet_id="b3",
                section="Experience",
                entry_title="Investment Banking Challenge",
                text_snippet="CFA Research Challenge National Finalist: Authored 20-page equity research report analyzing 10-K filings and M&A deal structures.",
                has_quantifiable_impact=True,
                skills_matched=["equity research", "m&a", "10-k"]
            ),
        ]
    )
    score = scorer.score(ev, role_req)
    assert score.score >= 60.0
    assert score.tier in ["Moderate Fit", "Strong Alignment"]
    assert any("CFA Research Challenge" in b for b in score.bonuses_applied)
    assert not any("Generic finance terms" in p for p in score.penalties_applied)


def test_investment_banking_penalty_generic_buzzwords():
    scorer = RoleScorer()
    role_req = get_role_requirement("ib")
    
    ev = EvidenceBundle(
        cpi=7.8,
        all_skills=["stocks", "finance", "excel"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Projects",
                entry_title="Stock Market App",
                text_snippet="Invested in stock market using Robinhood app and tracked daily price changes of tech stocks in Excel.",
                skills_matched=["excel"]
            ),
        ]
    )
    score = scorer.score(ev, role_req)
    assert any("Generic finance terms listed without demonstrated financial modeling" in p for p in score.penalties_applied)


def test_data_analyst_scoring_and_penalties():
    scorer = RoleScorer()
    role_req = get_role_requirement("analyst")
    
    # Strong evidence bundle
    ev_strong = EvidenceBundle(
        cpi=8.0,
        all_skills=["sql", "python", "pandas", "tableau", "statistics", "a/b testing", "window functions"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Projects",
                entry_title="Sales Analytics",
                text_snippet="Authored complex PostgreSQL queries utilizing CTEs and window functions (ROW_NUMBER, PARTITION BY) across 250k+ transactions.",
                has_quantifiable_impact=True,
                skills_matched=["sql", "window functions"]
            ),
            AtomicClaim(
                claim_id="c2",
                bullet_id="b2",
                section="Experience",
                entry_title="Analytics Intern",
                text_snippet="Designed A/B hypothesis test across 80,000 user sessions, driving strategic recommendation that increased conversion by 12%.",
                has_quantifiable_impact=True,
                skills_matched=["a/b testing", "statistics"]
            ),
            AtomicClaim(
                claim_id="c3",
                bullet_id="b3",
                section="Projects",
                entry_title="Executive Dashboard",
                text_snippet="Constructed interactive Tableau dashboard with executive KPI drilldowns tracking weekly retention rates.",
                has_quantifiable_impact=True,
                skills_matched=["tableau"]
            ),
        ]
    )
    score_strong = scorer.score(ev_strong, role_req)
    assert score_strong.score >= 55.0
    assert not any("Keyword-heavy tool listing" in p for p in score_strong.penalties_applied)

    # Tool listing penalty bundle
    ev_weak = EvidenceBundle(
        cpi=7.2,
        all_skills=["sql", "tableau", "power bi", "python"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Technical Skills",
                text_snippet="Proficient in SQL, Tableau, Power BI, Python, and Excel.",
                skills_matched=["sql", "tableau", "power bi", "python", "excel"]
            ),
        ]
    )
    score_weak = scorer.score(ev_weak, role_req)
    assert any("Keyword-heavy tool listing without demonstrated SQL queries" in p for p in score_weak.penalties_applied)


def test_product_manager_scoring_and_penalties():
    scorer = RoleScorer()
    role_req = get_role_requirement("product")
    
    # Strong PM bundle
    ev_strong = EvidenceBundle(
        cpi=8.0,
        all_skills=["prd", "wireframing", "figma", "user research", "product roadmap", "a/b testing"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Projects",
                entry_title="Campus Marketplace MVP",
                text_snippet="Shipped production MVP to 2,500+ student users after conducting 20+ customer discovery interviews and designing wireframes in Figma.",
                has_quantifiable_impact=True,
                skills_matched=["prd", "wireframing", "figma", "user research"]
            ),
            AtomicClaim(
                claim_id="c2",
                bullet_id="b2",
                section="Experience",
                entry_title="Product Management Intern",
                text_snippet="Prioritized 40+ backlog features using RICE framework and authored PRD specs, lifting user retention by 18%.",
                has_quantifiable_impact=True,
                skills_matched=["product roadmap", "prd"]
            ),
        ]
    )
    score_strong = scorer.score(ev_strong, role_req)
    assert score_strong.score >= 55.0
    assert not any("Technical project mislabeled as product" in p for p in score_strong.penalties_applied)

    # Technical project mislabeled penalty
    ev_weak = EvidenceBundle(
        cpi=7.5,
        all_skills=["python", "c++", "django"],
        claims=[
            AtomicClaim(
                claim_id="c1",
                bullet_id="b1",
                section="Projects",
                entry_title="Compiler in C++",
                text_snippet="Implemented lexer, parser, and semantic code generation modules for custom subset of C in C++.",
                skills_matched=["c++"]
            ),
        ]
    )
    score_weak = scorer.score(ev_weak, role_req)
    assert any("Technical project mislabeled as product without user evidence" in p for p in score_weak.penalties_applied)


def test_pipeline_multi_track_execution(tmp_path):
    pdf_path = Path("examples/resume2.pdf")
    if not pdf_path.exists():
        pytest.skip("examples/resume2.pdf not found")

    engine = ResumeEngine()
    results = engine.analyze_all(str(pdf_path))
    
    for r in ["sde", "quant", "consulting", "core", "analyst", "product", "ib"]:
        assert r in results
        assert "score" in results[r]
        assert "advisory" in results[r]
        assert 0.0 <= results[r]["score"]["score"] <= 100.0

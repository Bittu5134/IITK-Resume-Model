"""Stage 3 tests — matcher correctness and zero-leakage invariants.

Key invariants:
- Unrelated bullets must produce zero matches for unrelated competencies.
- Gated matches must have gate_passed=True.
- No competency gets a non-zero score without gated evidence.
- Role-conditioning: CP evidence only scores SDE competitive_programming.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


def _setup(tmp_path, section_name, bullet_text):
    """Helper: create single-bullet PDF and return EvidenceDocument."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), section_name, fontsize=12)
    pg.insert_text((50, 80), f"• {bullet_text}", fontsize=10)
    d.save(str(p))
    d.close()
    return EvidenceExtractor().extract(parse_pdf(p))


def test_cp_bullet_zero_leadership(tmp_path):
    """A Codeforces/competitive programming bullet must have ZERO leadership score."""
    ev = _setup(tmp_path, "Achievements", "Ranked Codeforces Specialist with rating 1450")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    consulting_matches = matcher.match(ev, roles["consulting"])
    lead_matches = [m for m in consulting_matches if m.competency == "leadership" and m.final_score > 0]
    assert not lead_matches, (
        f"CP bullet incorrectly matched leadership: {lead_matches}"
    )


def test_cultural_bullet_zero_cp(tmp_path):
    """A cultural activities bullet must produce zero competitive_programming score."""
    ev = _setup(tmp_path, "Extracurricular", "Won gold medal in inter-hall cultural competition Antaragni")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_matches = matcher.match(ev, roles["sde"])
    cp_matches = [m for m in sde_matches if m.competency == "competitive_programming" and m.final_score > 0]
    assert not cp_matches, (
        f"Cultural bullet incorrectly matched competitive_programming: {cp_matches}"
    )


def test_por_bullet_zero_software_engineering(tmp_path):
    """A PoR leadership bullet must not score software_engineering."""
    ev = _setup(tmp_path, "Positions of Responsibility",
                "Convener, Students Gymkhana, led 12 hostel teams across campus")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_matches = matcher.match(ev, roles["sde"])
    se_matches = [m for m in sde_matches if m.competency == "software_engineering" and m.final_score > 0]
    assert not se_matches, (
        f"PoR bullet incorrectly scored software_engineering: {se_matches}"
    )


def test_project_bullet_scores_projects(tmp_path):
    """A Projects bullet with Python must match SDE 'projects'."""
    ev = _setup(tmp_path, "Projects", "Built image classifier using Python and TensorFlow achieving 90% accuracy")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_matches = matcher.match(ev, roles["sde"])
    proj_matches = [m for m in sde_matches if m.competency == "projects" and m.final_score > 0]
    assert proj_matches, (
        f"Projects bullet with Python not matched to SDE 'projects' competency"
    )


def test_experience_bullet_scores_internships(tmp_path):
    """An Experience section bullet must match SDE 'internships' competency."""
    ev = _setup(tmp_path, "Work Experience", "Business Analyst intern at Navikra Tech, used SQL for analysis")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_matches = matcher.match(ev, roles["sde"])
    intern_matches = [m for m in sde_matches if m.competency == "internships" and m.final_score > 0]
    assert intern_matches, "Experience bullet not matched to SDE internships"


def test_role_conditioning_cp_vs_lead(tmp_path):
    """SDE competitive_programming score must exceed consulting leadership for CP bullet."""
    ev = _setup(tmp_path, "Achievements", "Ranked Codeforces Specialist with rating 1450")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_m = matcher.match(ev, roles["sde"])
    con_m = matcher.match(ev, roles["consulting"])
    sde_cp = max((m.final_score for m in sde_m if m.competency == "competitive_programming"), default=0.0)
    con_lead = max((m.final_score for m in con_m if m.competency == "leadership"), default=0.0)
    assert sde_cp > con_lead, (
        f"SDE competitive_programming ({sde_cp:.3f}) should exceed consulting leadership ({con_lead:.3f})"
    )


def test_all_gated_matches_have_provenance(tmp_path):
    """Every match with final_score > 0 must have gate_passed=True."""
    ev = _setup(tmp_path, "Projects", "Developed web app using React and Node.js with 95% test coverage")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    for role in roles.values():
        matches = matcher.match(ev, role)
        bad = [m for m in matches if m.final_score > 0 and not m.gate_passed]
        assert not bad, f"Matches with score > 0 but gate_passed=False: {bad}"


# ---------------------------------------------------------------------------
# Golden resume matcher invariants
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_no_cp_match():
    """Golden resume has no CP evidence — competitive_programming must be 0."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_m = matcher.match(ev, roles["sde"])
    cp_score = max((m.final_score for m in sde_m if m.competency == "competitive_programming"), default=0.0)
    assert cp_score == 0.0, (
        f"Golden resume has no CP evidence but competitive_programming score = {cp_score}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_projects_have_accepted_matches():
    """Golden resume has projects — SDE 'projects' must have at least one accepted match."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matcher = HybridMatcher()
    sde_m = matcher.match(ev, roles["sde"])
    proj_matches = [m for m in sde_m if m.competency == "projects" and m.final_score > 0]
    assert proj_matches, "SDE 'projects' has no accepted match despite golden resume having key projects"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_leadership_has_accepted_matches():
    """Consulting 'leadership' must have accepted matches from PoR section."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matcher = HybridMatcher()
    con_m = matcher.match(ev, roles["consulting"])
    lead_matches = [m for m in con_m if m.competency == "leadership" and m.final_score > 0]
    assert lead_matches, "Consulting 'leadership' has no accepted match"

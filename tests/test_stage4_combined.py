"""Stage 4 tests — Scorer correctness and zero-leakage invariants.

Tests (per spec §4A):
 1. No evidence => zero for unrelated competencies
 2. Supporting claim invariant: strength>0 => non-empty supporting_claims
 3. Contribution formula sanity: 0 <= contribution <= weight*100
 4. Total score bounds: 0 <= score <= 100 for every role
 5. CP role specificity: CP bullet => SDE cp>0 but consulting must not turn it into leadership
 6. Projects penalty: genuine projects bullet => no "No project evidence" penalty
 7. Internship penalty: Experience bullet => no false internship penalty
 8. GitHub penalty: embedded link => no "No Git/GitHub" penalty
 9. Golden resume hard contract
10. Deterministic scoring: same evidence => same score
"""
from __future__ import annotations

from pathlib import Path
import pytest
import pymupdf

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.scoring.scorer import RoleScorer

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(tmp_path: Path, section: str, bullets: list[str],
              links: list[tuple[pymupdf.Rect, str]] | None = None) -> Path:
    """Create a single-page PDF with a named section and bullet lines."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page(width=600, height=800)
    pg.insert_text((50, 50), section, fontsize=12)
    y = 90
    for bullet in bullets:
        pg.insert_text((50, y), f"\u2022 {bullet}", fontsize=10)
        y += 25
    if links:
        for rect, uri in links:
            pg.insert_link({"from": rect, "kind": pymupdf.LINK_URI, "uri": uri})
    d.save(str(p))
    d.close()
    return p


def _score(tmp_path: Path, section: str, bullets: list[str],
           role_id: str, links=None):
    """Build evidence -> matches -> score for a synthetic resume."""
    p = _make_pdf(tmp_path, section, bullets, links)
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles[role_id])
    return RoleScorer().score(ev, roles[role_id], matches,
                              link_objects=ast.link_objects)


# ---------------------------------------------------------------------------
# TEST 1 — No evidence => zero for unrelated competencies
# ---------------------------------------------------------------------------

def test_no_evidence_zero_cp(tmp_path):
    """A 'Built React website' bullet must produce competitive_programming=0 for SDE."""
    score = _score(tmp_path, "Projects", ["Built React website using Node.js"], "sde")
    cp = next((c for c in score.competency_scores if c.competency == "competitive_programming"), None)
    assert cp is not None
    assert cp.strength == 0.0, f"competitive_programming strength should be 0, got {cp.strength}"


def test_no_evidence_zero_open_source(tmp_path):
    """A 'Built React website' bullet must produce open_source=0 for SDE."""
    score = _score(tmp_path, "Projects", ["Built React website using Node.js"], "sde")
    os_c = next((c for c in score.competency_scores if c.competency == "open_source"), None)
    assert os_c is not None
    assert os_c.strength == 0.0, f"open_source strength should be 0, got {os_c.strength}"


def test_no_evidence_zero_internships(tmp_path):
    """A 'Built React website' projects bullet must produce internships=0 for SDE."""
    score = _score(tmp_path, "Projects", ["Built React website using Node.js"], "sde")
    intern_c = next((c for c in score.competency_scores if c.competency == "internships"), None)
    assert intern_c is not None
    assert intern_c.strength == 0.0, f"internships strength should be 0 for Projects bullet, got {intern_c.strength}"


# ---------------------------------------------------------------------------
# TEST 2 — Supporting claim invariant
# ---------------------------------------------------------------------------

def test_supporting_claims_nonempty_when_nonzero(tmp_path):
    """For every competency with strength>0, supporting_claims must not be empty."""
    p = _make_pdf(tmp_path, "Projects", [
        "Built image classifier using Python and TensorFlow achieving 90% accuracy",
        "Developed REST API in Flask serving 50k requests/day",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches)
    for comp in score.competency_scores:
        if comp.strength > 0.0:
            assert comp.supporting_claims, (
                f"Competency '{comp.competency}' has strength={comp.strength} "
                f"but empty supporting_claims"
            )


def test_supporting_claims_nonempty_when_contribution_nonzero(tmp_path):
    """For every competency with contribution>0, supporting_claims must not be empty."""
    p = _make_pdf(tmp_path, "Experience", [
        "Business Analyst intern at Navikra Tech, built SQL dashboards for 5 KPIs",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["consulting"])
    score = RoleScorer().score(ev, roles["consulting"], matches)
    for comp in score.competency_scores:
        if comp.contribution > 0.0:
            assert comp.supporting_claims, (
                f"Competency '{comp.competency}' has contribution={comp.contribution} "
                f"but empty supporting_claims"
            )


# ---------------------------------------------------------------------------
# TEST 3 — Contribution formula sanity
# ---------------------------------------------------------------------------

def test_contribution_bounded_by_weight(tmp_path):
    """0 <= contribution <= weight*100 for every competency in every role."""
    p = _make_pdf(tmp_path, "Projects", [
        "Built distributed system in Go reducing latency by 40%",
        "Implemented ML pipeline using TensorFlow with 95% accuracy",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    scorer = RoleScorer()
    matcher = HybridMatcher()
    for role_id, role in roles.items():
        matches = matcher.match(ev, role)
        score = scorer.score(ev, role, matches)
        for comp in score.competency_scores:
            assert comp.contribution >= 0.0, (
                f"[{role_id}] {comp.competency}: contribution={comp.contribution} < 0"
            )
            max_possible = comp.weight * 100.0
            assert comp.contribution <= max_possible + 1e-6, (
                f"[{role_id}] {comp.competency}: contribution={comp.contribution} "
                f"> max allowed {max_possible}"
            )


# ---------------------------------------------------------------------------
# TEST 4 — Total score bounds
# ---------------------------------------------------------------------------

def test_score_in_0_100_all_roles(tmp_path):
    """Final score must be in [0, 100] for every role."""
    p = _make_pdf(tmp_path, "Projects", [
        "Built web app using React and Flask with 10k active users",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    scorer = RoleScorer()
    matcher = HybridMatcher()
    for role_id, role in roles.items():
        matches = matcher.match(ev, role)
        score = scorer.score(ev, role, matches)
        assert 0.0 <= score.score <= 100.0, (
            f"Score for '{role_id}' is {score.score}, out of [0, 100]"
        )


def test_empty_resume_low_scores(tmp_path):
    """A nearly empty resume must score low (<=20) for all roles."""
    # Just a heading line, no bullets
    p = tmp_path / "empty.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "John Doe", fontsize=12)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    scorer = RoleScorer()
    matcher = HybridMatcher()
    for role_id, role in roles.items():
        matches = matcher.match(ev, role)
        score = scorer.score(ev, role, matches)
        assert score.score <= 20.0, (
            f"Empty resume scored {score.score} for '{role_id}' — should be low"
        )


# ---------------------------------------------------------------------------
# TEST 5 — CP role specificity
# ---------------------------------------------------------------------------

def test_cp_bullet_sde_cp_positive(tmp_path):
    """Codeforces Specialist bullet must give SDE competitive_programming > 0."""
    score = _score(tmp_path, "Achievements", ["Codeforces Specialist, rating 1450"], "sde")
    cp = next((c for c in score.competency_scores if c.competency == "competitive_programming"), None)
    assert cp is not None
    assert cp.strength > 0.0, "SDE competitive_programming must be >0 for Codeforces bullet"


def test_cp_bullet_consulting_not_leadership(tmp_path):
    """Codeforces Specialist bullet must NOT convert to consulting leadership."""
    score = _score(tmp_path, "Achievements", ["Codeforces Specialist, rating 1450"], "consulting")
    lead = next((c for c in score.competency_scores if c.competency == "leadership"), None)
    assert lead is not None
    assert lead.strength == 0.0, (
        f"Consulting leadership must be 0 for a CP-only bullet, got {lead.strength}"
    )


# ---------------------------------------------------------------------------
# TEST 6 — Projects penalty
# ---------------------------------------------------------------------------

def test_genuine_project_no_penalty(tmp_path):
    """Resume with genuine Projects bullet must NOT receive 'No project evidence' penalty."""
    p = _make_pdf(tmp_path, "Projects", [
        "Built image classifier using Python and TensorFlow achieving 90% test accuracy",
        "Developed REST API with Flask serving 50k requests/day",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    project_penalties = [
        p for p in score.penalties
        if "project" in p.get("code", "").lower() or "project" in p.get("reason", "").lower()
    ]
    assert not project_penalties, (
        f"Project penalty fired despite genuine project evidence: {project_penalties}"
    )


# ---------------------------------------------------------------------------
# TEST 7 — Internship penalty
# ---------------------------------------------------------------------------

def test_genuine_internship_no_false_penalty(tmp_path):
    """Resume with an Experience/internship bullet must not lose internship-related points."""
    p = _make_pdf(tmp_path, "Work Experience", [
        "Business Analyst intern at Navikra Tech, used SQL and Python for analysis",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    # There is no explicit internship penalty in current scorer when match exists;
    # also verify internships strength > 0
    intern_comp = next(
        (c for c in score.competency_scores if c.competency == "internships"), None
    )
    assert intern_comp is not None
    assert intern_comp.strength > 0.0, (
        f"internships strength should be >0 when Experience bullet present, got {intern_comp.strength}"
    )


# ---------------------------------------------------------------------------
# TEST 8 — GitHub penalty
# ---------------------------------------------------------------------------

def test_github_embedded_link_no_penalty(tmp_path):
    """Embedded github.com link must suppress the 'No GitHub evidence' SDE penalty."""
    gh_rect = pymupdf.Rect(50, 50, 250, 65)
    p = _make_pdf(
        tmp_path,
        "Projects",
        ["Built open-source CLI tool in Python"],
        links=[(gh_rect, "https://github.com/jdoe/my-project")],
    )
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    github_penalties = [
        pen for pen in score.penalties
        if "github" in pen.get("code", "").lower() or "github" in pen.get("reason", "").lower()
    ]
    assert not github_penalties, (
        f"GitHub penalty fired despite embedded GitHub link: {github_penalties}"
    )


def test_github_word_alone_no_positive_os_score(tmp_path):
    """Mentioning 'GitHub' as plain text (no link, no PR keyword) must NOT trigger open_source strength."""
    p = _make_pdf(tmp_path, "Projects", [
        "See my GitHub for more details on this project",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches)
    os_c = next((c for c in score.competency_scores if c.competency == "open_source"), None)
    assert os_c is not None
    # A plain "GitHub" mention without PR/contribution keywords must not yield open_source > 0
    # (or at most a very small score — the gate requires open_source_keywords)
    assert os_c.strength == 0.0, (
        f"open_source strength should be 0 for plain GitHub mention, got {os_c.strength}"
    )


# ---------------------------------------------------------------------------
# TEST 9 — Golden resume hard contract
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sde_projects_strength_positive():
    """Golden resume SDE projects strength must be > 0."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    proj = next((c for c in score.competency_scores if c.competency == "projects"), None)
    assert proj is not None
    assert proj.strength > 0.0, f"SDE projects strength should be >0, got {proj.strength}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sde_internships_strength_positive():
    """Golden resume SDE internships strength must be > 0."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    intern_c = next((c for c in score.competency_scores if c.competency == "internships"), None)
    assert intern_c is not None
    assert intern_c.strength > 0.0, f"SDE internships strength should be >0, got {intern_c.strength}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sde_cp_strength_zero():
    """Golden resume has no CP evidence — SDE competitive_programming must be 0."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    cp = next((c for c in score.competency_scores if c.competency == "competitive_programming"), None)
    assert cp is not None
    assert cp.strength == 0.0, f"SDE CP strength should be 0, got {cp.strength}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_no_project_penalty():
    """Golden resume must NOT receive 'No project evidence' penalty for SDE."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    project_penalties = [
        p for p in score.penalties
        if "project" in p.get("code", "").lower()
    ]
    assert not project_penalties, (
        f"Golden resume incorrectly received project penalty: {project_penalties}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_no_fake_github_penalty():
    """Golden resume with GitHub links must NOT receive 'missing_github' penalty."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    # check links exist first
    uris = [lo.uri for lo in ast.link_objects]
    has_github = any("github.com" in u.lower() for u in uris)
    if not has_github:
        pytest.skip("Golden resume has no detected GitHub link — penalty test not applicable")
    roles = load_role_graphs()
    matches = HybridMatcher().match(ev, roles["sde"])
    score = RoleScorer().score(ev, roles["sde"], matches, link_objects=ast.link_objects)
    gh_penalties = [
        p for p in score.penalties
        if p.get("code") == "missing_github"
    ]
    assert not gh_penalties, (
        f"Golden resume has GitHub link but received missing_github penalty: {gh_penalties}"
    )


# ---------------------------------------------------------------------------
# TEST 10 — Deterministic scoring
# ---------------------------------------------------------------------------

def test_deterministic_scoring_identical_inputs(tmp_path):
    """Running identical evidence twice must produce identical scores."""
    p = _make_pdf(tmp_path, "Projects", [
        "Built image classifier using Python and TensorFlow achieving 90% accuracy",
        "Reduced inference latency by 32% using batched caching in Flask",
    ])
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    role = roles["sde"]
    scorer = RoleScorer()
    matcher = HybridMatcher()

    matches1 = matcher.match(ev, role)
    score1 = scorer.score(ev, role, matches1)

    matches2 = matcher.match(ev, role)
    score2 = scorer.score(ev, role, matches2)

    assert score1.score == score2.score, (
        f"Non-deterministic scoring: {score1.score} != {score2.score}"
    )
    for c1, c2 in zip(score1.competency_scores, score2.competency_scores):
        assert c1.strength == c2.strength, (
            f"Non-deterministic strength for '{c1.competency}': {c1.strength} != {c2.strength}"
        )


# ---------------------------------------------------------------------------
# Additional: role differentiation
# ---------------------------------------------------------------------------

def test_strong_sde_profile_ranks_above_consulting(tmp_path):
    """A strong SDE profile (DSA + projects + Python) should score higher for SDE than consulting."""
    bullets = [
        "Codeforces Specialist with max rating 1450, solved 500+ DSA problems",
        "Built full-stack web app using React and Node.js with REST API",
        "Contributed 14 merged PRs to open-source project on GitHub",
    ]
    p = _make_pdf(tmp_path, "Projects", bullets)
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    scorer = RoleScorer()
    matcher = HybridMatcher()

    sde_score = scorer.score(ev, roles["sde"], matcher.match(ev, roles["sde"])).score
    con_score = scorer.score(ev, roles["consulting"], matcher.match(ev, roles["consulting"])).score
    assert sde_score >= con_score, (
        f"Strong SDE profile should score at least as high for SDE ({sde_score}) "
        f"as consulting ({con_score})"
    )

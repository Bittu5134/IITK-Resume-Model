"""Stage 5 tests — Advisory engine correctness.

Tests (per spec §4B):
 1. Top strengths have actual supporting claims
 2. Recommendations pointing to evidence contain source_claim_id, section, page, text_snippet
 3. Advice must NOT fabricate metrics, technologies, or achievements
 4. Weak bullet gets specific diagnosis
 5. Strong (quantified) bullet must NOT get generic "quantify your impact"
 6. Missing competency recommendation uses conditional "if you genuinely have" language
 7. Expected gain is max_potential_gain_estimate (not guaranteed)
 8. Line diagnostics identify actual source bullet
 9. Golden resume produces useful line-specific recommendations
10. JSON serialization has no duplicate logical fields
"""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.scoring.scorer import RoleScorer
from resume_engine.advisory.advisor import CounterfactualAdvisor

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(tmp_path: Path, section: str, bullets: list[str]) -> Path:
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page(width=600, height=800)
    pg.insert_text((50, 50), section, fontsize=12)
    y = 90
    for bullet in bullets:
        pg.insert_text((50, y), f"\u2022 {bullet}", fontsize=10)
        y += 25
    d.save(str(p))
    d.close()
    return p


def _full_pipeline(tmp_path: Path, section: str, bullets: list[str], role_id: str = "sde"):
    p = _make_pdf(tmp_path, section, bullets)
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    role = roles[role_id]
    matches = HybridMatcher().match(ev, role)
    score = RoleScorer().score(ev, role, matches)
    advisory = CounterfactualAdvisor().build(ev, score)
    return ev, score, advisory


# ---------------------------------------------------------------------------
# TEST 1 — Top strengths have actual supporting claims
# ---------------------------------------------------------------------------

def test_top_strengths_have_claims(tmp_path):
    """Every top strength in the advisory must have a non-empty claims list."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built image classifier using Python and TensorFlow achieving 90% accuracy",
         "Developed REST API in Flask serving 50k requests/day with Docker"],
    )
    for strength in advisory.top_strengths:
        if strength.get("strength", 0) >= 0.45:
            assert strength.get("claims"), (
                f"Top strength '{strength.get('competency')}' has strength "
                f"{strength.get('strength')} but empty claims list"
            )


# ---------------------------------------------------------------------------
# TEST 2 — Recommendations with evidence have full provenance
# ---------------------------------------------------------------------------

def test_recommendations_with_claim_have_provenance(tmp_path):
    """Recommendations that reference a source claim must have section, page, text_snippet."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Worked on a model with Python"],
    )
    for rec in advisory.recommendations:
        if rec.source_claim_id is not None:
            assert rec.section is not None, (
                f"Rec for '{rec.competency}' has claim_id but no section"
            )
            assert rec.page is not None, (
                f"Rec for '{rec.competency}' has claim_id but no page"
            )
            assert rec.text_snippet is not None and len(rec.text_snippet) > 0, (
                f"Rec for '{rec.competency}' has claim_id but empty text_snippet"
            )


# ---------------------------------------------------------------------------
# TEST 3 — Advice must NOT fabricate metrics/technologies
# ---------------------------------------------------------------------------

# Known fabrication patterns: specific numbers, company names, technologies
# that were not in the original bullet
_FABRICATION_PATTERNS = [
    r"your codeforces rating",  # not in simple test resume
    r"add a gsoc",
    r"claim X",
    r"get a gsoc",
    r"add leetcode",
]

import re

def test_advice_no_fabrication(tmp_path):
    """Advisory must not suggest specific fake achievements not grounded in evidence."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Worked on latency optimization for a distributed system"],
    )
    all_text = " ".join(
        (rec.action or "") + " " + (rec.diagnosis or "")
        for rec in advisory.recommendations
    ).lower()
    for pat in _FABRICATION_PATTERNS:
        assert not re.search(pat, all_text), (
            f"Advisory fabrication pattern found: '{pat}' in text snippet: {all_text[:200]}"
        )


def test_advice_conditional_language_for_missing(tmp_path):
    """Advisory for missing evidence must use conditional language, not imperative claims."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built web application using JavaScript"],
    )
    # Find recommendations with no source_claim_id (zero evidence comps)
    zero_recs = [r for r in advisory.recommendations if r.source_claim_id is None]
    for rec in zero_recs:
        action_lower = rec.action.lower()
        # Must contain conditional language
        has_conditional = any(phrase in action_lower for phrase in [
            "if you genuinely", "if you have", "if you do not", "do not fabricate",
            "if you actually", "only if",
        ])
        assert has_conditional, (
            f"Zero-evidence rec for '{rec.competency}' lacks conditional language: "
            f"'{rec.action[:120]}'"
        )


# ---------------------------------------------------------------------------
# TEST 4 — Weak bullet gets specific diagnosis
# ---------------------------------------------------------------------------

def test_weak_bullet_gets_action_verb_diagnosis(tmp_path):
    """'Worked on latency' must get a weak action verb diagnosis."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Experience",
        ["Worked on latency improvement for the backend system"],
    )
    weak_diags = [
        d for d in advisory.line_diagnostics
        if any("weak" in issue.lower() or "action verb" in issue.lower() for issue in d.issues)
    ]
    assert weak_diags, (
        "Expected a weak-action-verb diagnostic for 'Worked on latency' bullet, got none"
    )


def test_weak_bullet_without_metric_gets_quantify_suggestion(tmp_path):
    """A bullet with no metric must get a 'add metric' suggestion (since none exists)."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Worked on backend system improvements"],
    )
    no_metric_diags = [
        d for d in advisory.line_diagnostics
        if any("metric" in issue.lower() or "quantif" in issue.lower() for issue in d.issues)
    ]
    assert no_metric_diags, (
        "Expected a 'no metric' diagnostic for an unquantified bullet, got none"
    )


# ---------------------------------------------------------------------------
# TEST 5 — Strong quantified bullet must NOT get generic "quantify your impact"
# ---------------------------------------------------------------------------

def test_strong_quantified_bullet_no_generic_quantify(tmp_path):
    """'Reduced inference latency by 32%...' must not receive 'quantify your impact' advice."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Reduced inference latency by 32% by introducing batched caching in Python"],
    )
    # Check line diagnostics for this bullet
    for diag in advisory.line_diagnostics:
        if "latency" in diag.text_snippet or "32" in diag.text_snippet:
            no_metric_issues = [
                issue for issue in diag.issues
                if "no quantifiable metric" in issue.lower()
            ]
            assert not no_metric_issues, (
                f"Quantified bullet incorrectly got 'no metric' issue: {diag.issues}"
            )


# ---------------------------------------------------------------------------
# TEST 6 — Missing competency recommendation uses conditional language
# ---------------------------------------------------------------------------

def test_missing_competency_no_imperative_claim(tmp_path):
    """'Add a Codeforces rating' must NOT appear in recommendations for a non-CP resume."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built web application using React and Node.js"],
    )
    for rec in advisory.recommendations:
        action_lower = rec.action.lower()
        # Must not command the user to "add codeforces" as if they have it
        assert "add a codeforces" not in action_lower, (
            f"Advisory commands 'add a codeforces': {rec.action[:150]}"
        )
        assert "get a gsoc" not in action_lower, (
            f"Advisory commands 'get a gsoc': {rec.action[:150]}"
        )


# ---------------------------------------------------------------------------
# TEST 7 — Expected gain uses max_potential_gain_estimate field
# ---------------------------------------------------------------------------

def test_gain_field_is_max_potential(tmp_path):
    """Recommendations must use max_potential_gain_estimate field, not guaranteed gain."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built image classifier using Python and TensorFlow"],
    )
    for rec in advisory.recommendations:
        # Field must exist and be a non-negative number
        assert hasattr(rec, "max_potential_gain_estimate"), (
            "Recommendation missing 'max_potential_gain_estimate' field"
        )
        assert rec.max_potential_gain_estimate >= 0.0, (
            f"max_potential_gain_estimate should be >= 0, got {rec.max_potential_gain_estimate}"
        )
        assert rec.max_potential_gain_estimate <= 100.0, (
            f"max_potential_gain_estimate should be <= 100, got {rec.max_potential_gain_estimate}"
        )


def test_gain_field_not_guaranteed_language(tmp_path):
    """The advisory output must not claim a 'guaranteed' score increase."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects", ["Built API with Python and Flask"],
    )
    # Check that the field is max_potential_gain_estimate, not 'guaranteed_gain'
    for rec in advisory.recommendations:
        d = rec.model_dump()
        assert "guaranteed_gain" not in d, (
            "Advisory output contains 'guaranteed_gain' field — must use max_potential_gain_estimate"
        )


# ---------------------------------------------------------------------------
# TEST 8 — Line diagnostics identify the actual source bullet
# ---------------------------------------------------------------------------

def test_line_diagnostics_identify_source_bullet(tmp_path):
    """Line diagnostics must carry text_snippet from the actual bullet."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Experience",
        ["Worked on data pipeline", "Built REST API reducing latency by 20%"],
    )
    snippets = [d.text_snippet for d in advisory.line_diagnostics]
    # Both bullets should appear in diagnostics
    assert any("data pipeline" in s for s in snippets), (
        "Bullet 'data pipeline' not found in line diagnostics snippets"
    )
    assert any("latency" in s or "API" in s for s in snippets), (
        "Bullet about REST API not found in line diagnostics snippets"
    )


def test_line_diagnostics_have_bullet_id(tmp_path):
    """Every line diagnostic must carry a bullet_id."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built ML pipeline using TensorFlow with 94% AUC"],
    )
    for diag in advisory.line_diagnostics:
        assert diag.bullet_id, (
            f"Line diagnostic missing bullet_id: {diag}"
        )
        assert diag.claim_id, (
            f"Line diagnostic missing claim_id: {diag}"
        )


# ---------------------------------------------------------------------------
# TEST 9 — Golden resume produces useful line-specific recommendations
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_line_diagnostics_nonempty():
    """Golden resume must produce non-empty line diagnostics."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    role = roles["sde"]
    matches = HybridMatcher().match(ev, role)
    score = RoleScorer().score(ev, role, matches, link_objects=ast.link_objects)
    advisory = CounterfactualAdvisor().build(ev, score)
    assert len(advisory.line_diagnostics) > 0, "No line diagnostics for golden resume"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_recommendations_have_provenance():
    """Golden resume recommendations that reference evidence must have full provenance."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    role = roles["sde"]
    matches = HybridMatcher().match(ev, role)
    score = RoleScorer().score(ev, role, matches, link_objects=ast.link_objects)
    advisory = CounterfactualAdvisor().build(ev, score)
    valid_claim_ids = {c.claim_id for c in ev.claims}
    for rec in advisory.recommendations:
        if rec.source_claim_id is not None:
            assert rec.source_claim_id in valid_claim_ids, (
                f"Rec references non-existent claim_id: {rec.source_claim_id}"
            )
            assert rec.section is not None
            assert rec.page is not None
            assert rec.text_snippet is not None and len(rec.text_snippet) > 3


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_line_specific_recommendations():
    """Golden resume should produce at least some recommendations referencing actual bullets."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    roles = load_role_graphs()
    role = roles["consulting"]
    matches = HybridMatcher().match(ev, role)
    score = RoleScorer().score(ev, role, matches, link_objects=ast.link_objects)
    advisory = CounterfactualAdvisor().build(ev, score)
    # At least half of recommendations should reference a specific bullet
    specific = [r for r in advisory.recommendations if r.source_claim_id is not None]
    total = len(advisory.recommendations)
    if total > 0:
        ratio = len(specific) / total
        assert ratio >= 0.5 or len(specific) >= 2, (
            f"Too few recommendations reference specific bullets: {len(specific)}/{total}"
        )


# ---------------------------------------------------------------------------
# TEST 10 — JSON serialization
# ---------------------------------------------------------------------------

def test_json_serializable(tmp_path):
    """Full advisory output must be JSON-serializable without errors."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built ML pipeline using TensorFlow reducing AUC error by 15%"],
    )
    d = advisory.model_dump()
    try:
        serialized = json.dumps(d)
    except TypeError as e:
        pytest.fail(f"Advisory output is not JSON-serializable: {e}")
    assert len(serialized) > 10


def test_no_duplicate_logical_fields(tmp_path):
    """Advisory model_dump must not have duplicate logical fields for gain."""
    _ev, score, advisory = _full_pipeline(
        tmp_path, "Projects",
        ["Built distributed system reducing p99 latency by 40%"],
    )
    for rec in advisory.recommendations:
        d = rec.model_dump()
        # 'expected_gain' may appear as a legacy alias but 'max_potential_gain_estimate' is canonical
        # They must NOT both appear with DIFFERENT values
        if "expected_gain" in d and "max_potential_gain_estimate" in d:
            assert d["expected_gain"] == d["max_potential_gain_estimate"], (
                f"Duplicate gain fields with different values: "
                f"expected_gain={d['expected_gain']}, "
                f"max_potential_gain_estimate={d['max_potential_gain_estimate']}"
            )


def test_full_pipeline_json_serializable_all_roles(tmp_path):
    """Full pipeline output must be JSON-serializable for all 4 roles."""
    from resume_engine.pipeline import ResumeEngine
    p = _make_pdf(tmp_path, "Projects", [
        "Reduced inference latency by 20% using Python batching",
        "Led team of 12 in Techkriti event managing 5000+ participants",
    ])
    eng = ResumeEngine()
    for role_id in ["sde", "quant", "consulting", "core"]:
        result = eng.analyze(p, role_id)
        try:
            serialized = json.dumps(result.model_dump())
        except TypeError as e:
            pytest.fail(f"Pipeline output for '{role_id}' not JSON-serializable: {e}")
        assert len(serialized) > 50

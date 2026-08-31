"""Stage 2 tests — evidence extraction correctness.

Includes:
- Metric parser edge cases (C3, C4, C5)
- Action verb normalization
- Skill recognition (scikit-learn, ML frameworks)
- IITK entity recognition
- CPI extraction from education table
- Golden resume evidence assertions
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor, parse_metrics
from resume_engine.evidence.models import EvidenceDocument

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


# ---------------------------------------------------------------------------
# Unit tests for metric parser
# ---------------------------------------------------------------------------

def test_metric_comma_number():
    """10,000+ should parse to value 10000, not split as 10 and 000."""
    metrics = parse_metrics("Mentored 10,000+ students across India")
    assert any(m.value is not None and m.value >= 10000 for m in metrics), (
        f"Expected value >= 10000, got: {[(m.raw, m.value) for m in metrics]}"
    )


def test_metric_percentage():
    metrics = parse_metrics("Reduced latency by 20% using caching")
    pct = [m for m in metrics if m.unit == "%"]
    assert pct, "No percentage metric found"
    assert pct[0].value == 20.0
    assert pct[0].is_impact_relevant is True


def test_metric_range():
    metrics = parse_metrics("Improved accuracy from 25% to 50%")
    # Should detect at least one metric around 25 or 50
    vals = [m.value for m in metrics if m.value is not None]
    assert any(20 <= v <= 55 for v in vals), f"Range not parsed: {vals}"


def test_metric_financial():
    metrics = parse_metrics("Company valued at $44.6B market cap")
    fin = [m for m in metrics if m.is_impact_relevant]
    assert fin, f"Financial metric not detected as impact: {[(m.raw, m.kind) for m in metrics]}"


def test_metric_year_not_impact():
    """Years like 2024 must NOT be classified as impact metrics."""
    metrics = parse_metrics("Worked at startup 2024, built API")
    impact = [m for m in metrics if m.is_impact_relevant]
    years = [m for m in metrics if m.kind == "year"]
    assert not impact or all(m.value != 2024 for m in impact), (
        f"Year 2024 incorrectly marked as impact: {impact}"
    )


def test_metric_model_param_not_impact():
    """Layer counts must NOT be impact metrics."""
    metrics = parse_metrics("Trained a 40-layer ResNet model")
    impact = [m for m in metrics if m.is_impact_relevant]
    assert not impact or all(m.value != 40 for m in impact), (
        f"Layer count 40 incorrectly marked as impact"
    )


def test_metric_accuracy():
    metrics = parse_metrics("Achieved ROC-AUC of 87% and recall of 73%")
    pcts = [m for m in metrics if m.unit == "%" and m.is_impact_relevant]
    assert len(pcts) >= 1, f"Accuracy metrics not found: {[(m.raw, m.is_impact_relevant) for m in metrics]}"


def test_metric_crore_lakh():
    metrics = parse_metrics("Managed budget of ₹75L and impacted 650 Cr market")
    vals = [m.value for m in metrics if m.value is not None]
    assert any(v >= 75 * 100_000 * 0.9 for v in vals), f"Lakh not parsed correctly: {vals}"


# ---------------------------------------------------------------------------
# Skill recognition
# ---------------------------------------------------------------------------

def test_skill_scikit_learn(tmp_path):
    """scikit-learn must be recognized (C11 fix)."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Research")
    pg.insert_text((50, 80), "• Used scikit-learn and TensorFlow for classification", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    all_skills = set(s for c in ev.claims for s in c.skills)
    assert "scikit_learn" in all_skills, f"scikit-learn not recognized; skills: {all_skills}"
    assert "tensorflow" in all_skills, f"TensorFlow not recognized; skills: {all_skills}"


def test_skill_ml_frameworks(tmp_path):
    """MobileNetV2 and deep_learning should be detected."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Research")
    pg.insert_text((50, 80), "• Trained MobileNetV2 with deep learning techniques", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    skills = set(s for c in ev.claims for s in c.skills)
    assert "MobileNetV2" in entities or "deep_learning" in skills, (
        f"MobileNetV2/deep_learning not detected; entities={entities}, skills={skills}"
    )


# ---------------------------------------------------------------------------
# Action verb tests
# ---------------------------------------------------------------------------

def test_action_weak_verb(tmp_path):
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Experience")
    pg.insert_text((50, 80), "• Worked on data pipeline using Python", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    assert ev.claims[0].action_strength < 0.50, "Weak verb 'worked' should have low strength"


def test_action_strong_verb(tmp_path):
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Experience")
    pg.insert_text((50, 80), "• Engineered ML pipeline reducing latency by 30%", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    claim = ev.claims[0]
    assert claim.action_strength >= 0.80, f"Expected strong verb strength >= 0.80, got {claim.action_strength}"


def test_unknown_verb_not_half(tmp_path):
    """Unknown action verbs must NOT default to 0.5 (C6 fix)."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Projects")
    pg.insert_text((50, 80), "• Xyxzed something with Python", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    assert ev.claims[0].action_strength != 0.5, "Unknown verb should not default to exactly 0.5"
    assert ev.claims[0].action_strength < 0.50, "Unknown verb should be low-confidence"


# ---------------------------------------------------------------------------
# IITK entity recognition
# ---------------------------------------------------------------------------

def test_entity_codeforces(tmp_path):
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Achievements")
    pg.insert_text((50, 80), "• Ranked Codeforces Specialist with rating 1450", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    assert "Codeforces" in entities


def test_entity_inter_iit(tmp_path):
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Extra-Curricular Activities")
    pg.insert_text((50, 80), "• Secured 2nd position in Inter IIT Tech Meet", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    assert "Inter IIT" in entities, f"Inter-IIT not detected; entities: {entities}"


def test_no_codeforces_without_text(tmp_path):
    """Codeforces must not appear when it's not in the resume."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((50, 50), "Projects")
    pg.insert_text((50, 80), "• Built web application using React and Node.js", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    assert "Codeforces" not in entities


# ---------------------------------------------------------------------------
# Golden resume evidence assertions
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_cpi_extracted():
    """CPI 7.7/10.0 must be extracted as an academic metric."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    cpi_metrics = [m for m in ev.academic_metrics if m.metric_type == "cpi"]
    assert cpi_metrics, f"No CPI academic metric found. Academic metrics: {ev.academic_metrics}"
    cpi_vals = [m.value for m in cpi_metrics]
    assert any(abs(v - 7.7) < 0.1 for v in cpi_vals), (
        f"Expected CPI ~7.7, got: {cpi_vals}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sql_detected():
    """SQL skill must be detected from Business Analyst internship bullet."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    all_skills = set(s for c in ev.claims for s in c.skills)
    assert "sql" in all_skills, f"SQL not detected. Skills: {sorted(all_skills)}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_tensorflow_scikit_detected():
    """TensorFlow and scikit-learn must both be detected."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    all_skills = set(s for c in ev.claims for s in c.skills)
    assert "tensorflow" in all_skills, f"TensorFlow not detected. Skills: {sorted(all_skills)}"
    assert "scikit_learn" in all_skills, f"scikit-learn not detected. Skills: {sorted(all_skills)}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_no_codeforces():
    """Codeforces must NOT appear in golden resume evidence (no CP in resume)."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    assert "Codeforces" not in entities, "Codeforces incorrectly detected in golden resume"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_leadership_from_por_not_projects():
    """Leadership signals must come from PoR section, not Projects/Research."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    non_por_high_lead = [
        c for c in ev.claims
        if c.section not in {"Positions of Responsibility", "Extracurricular", "Social Impact", "Experience"}
        and c.signals.get("leadership", 0) > 0.60
    ]
    assert not non_por_high_lead, (
        f"High leadership signal on non-PoR bullets (section contamination): "
        f"{[(c.section, c.text[:50], c.signals.get('leadership')) for c in non_por_high_lead]}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_inter_iit_snt_detected():
    """Inter-IIT and SnT Council must appear in golden resume entities."""
    ast = parse_pdf(GOLDEN)
    ev = EvidenceExtractor().extract(ast)
    entities = {e.canonical for c in ev.claims for e in c.entities}
    assert "Inter IIT" in entities or "Science and Technology Council" in entities, (
        f"Inter-IIT or SnT not detected. Entities: {sorted(entities)}"
    )

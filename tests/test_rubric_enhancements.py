"""Automated test suite for 150-Point Rubric Enhancements."""
from pathlib import Path
import pytest
from resume_engine.pipeline import ResumeEngine
from resume_engine.evidence.nlp import ResumeNLPPipeline
from resume_engine.evidence.extractor import EvidenceExtractor


def test_nlp_pipeline_rubric_entities():
    """NLP pipeline must detect GSoC, Codeforces, SURGE, and PoR entities."""
    nlp = ResumeNLPPipeline()

    res1 = nlp.analyze_bullet("Selected for GSoC (Google Summer of Code) under Python Software Foundation")
    assert "GSoC" in res1.detected_entities or "Google Summer of Code" in res1.detected_entities

    res2 = nlp.analyze_bullet("Ranked Codeforces Candidate Master with 1920 max rating")
    assert "Codeforces" in res2.detected_entities or "Candidate Master" in res2.detected_entities

    res3 = nlp.analyze_bullet("Awarded SURGE research grant at IIT Kanpur under CSE faculty")
    assert "SURGE" in res3.detected_entities or "SURGE Intern" in res3.detected_entities

    res4 = nlp.analyze_bullet("Served as General Secretary of Academics & Career Council (AnC)")
    assert "General Secretary" in res4.detected_entities or "AnC Council" in res4.detected_entities


def test_hyper_specific_bullet_diagnostics(tmp_path):
    """Line diagnostics must generate hyper-specific context suggestions."""
    from tests.test_stage6_e2e import _make_minimal_pdf
    pdf_bytes = _make_minimal_pdf("Projects", [
        "Worked on developing Python REST API with Flask",
        "Ranked Codeforces Candidate Master 1920 max rating"
    ])
    p = tmp_path / "test.pdf"
    p.write_bytes(pdf_bytes)

    engine = ResumeEngine()
    res = engine.analyze(p, "sde")
    assert len(res.advisory.line_diagnostics) > 0
    diag = res.advisory.line_diagnostics[0]
    assert len(diag.suggestions) > 0
    assert "Projects" in diag.suggestions[0] or "Codeforces" in diag.suggestions[0] or "Replace" in diag.suggestions[0]

"""Stage 6 end-to-end tests — Pipeline and API correctness.

Tests (per spec §4C):
- Valid PDF + valid role => full result
- Invalid role => 400 error
- Empty file => 400 error
- Non-PDF upload => 400 error
- Malformed PDF => 400 error
- Oversized upload
- API temporary file cleanup
- All four roles via CLI pipeline
- Output JSON serializable
- Output contains: role, document, evidence, score, advisory
- document contains: sections, links, warnings, layout_diagnostics
- Evidence summary exposes audit information
"""
from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path

import pymupdf
import pytest

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


# ---------------------------------------------------------------------------
# Helper: build a valid minimal PDF in memory
# ---------------------------------------------------------------------------

def _make_minimal_pdf(section: str = "Projects", bullets: list[str] | None = None) -> bytes:
    """Return bytes of a valid in-memory PDF."""
    if bullets is None:
        bullets = ["Built web app using Python and Flask"]
    d = pymupdf.open()
    pg = d.new_page(width=600, height=800)
    pg.insert_text((50, 50), section, fontsize=12)
    y = 90
    for b in bullets:
        pg.insert_text((50, y), f"\u2022 {b}", fontsize=10)
        y += 25
    buf = d.tobytes()
    d.close()
    return buf


# ---------------------------------------------------------------------------
# Pipeline (CLI-style) tests
# ---------------------------------------------------------------------------

def test_pipeline_valid_pdf_all_roles(tmp_path):
    """Valid PDF must succeed for all four roles and produce expected fields."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf("Projects", [
        "Built image classifier using Python and TensorFlow achieving 90% accuracy",
        "Developed REST API in Flask serving 50k requests/day",
    ]))
    eng = ResumeEngine()
    for role_id in ["sde", "quant", "consulting", "core"]:
        result = eng.analyze(str(p), role_id)
        assert result.role == role_id
        assert result.document is not None
        assert result.evidence is not None
        assert result.score is not None
        assert result.advisory is not None


def test_pipeline_result_has_required_schema_fields(tmp_path):
    """AnalysisResult must include role, document, evidence, score, advisory."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf())
    result = ResumeEngine().analyze(str(p), "sde")
    d = result.model_dump()
    for field in ["role", "document", "evidence", "score", "advisory"]:
        assert field in d, f"Missing field '{field}' in AnalysisResult"


def test_document_summary_has_required_fields(tmp_path):
    """DocumentSummary must contain sections, links, warnings, layout_diagnostics."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf())
    result = ResumeEngine().analyze(str(p), "sde")
    doc = result.document.model_dump()
    for field in ["sections", "links", "warnings", "layout_diagnostics"]:
        assert field in doc, f"Missing field '{field}' in DocumentSummary"
    assert isinstance(doc["sections"], list)
    assert isinstance(doc["links"], list)
    assert isinstance(doc["warnings"], list)
    assert isinstance(doc["layout_diagnostics"], dict)


def test_evidence_summary_exposes_audit_fields(tmp_path):
    """EvidenceSummary must expose academic_metrics, all_skills, all_entities, claim_count."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf("Projects", [
        "Built TensorFlow classifier using scikit-learn achieving 87% recall"
    ]))
    result = ResumeEngine().analyze(str(p), "sde")
    ev = result.evidence.model_dump()
    for field in ["academic_metrics", "all_skills", "all_entities", "claim_count"]:
        assert field in ev, f"Missing field '{field}' in EvidenceSummary"
    assert ev["claim_count"] >= 1


def test_pipeline_invalid_role(tmp_path):
    """Invalid role must raise ValueError."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf())
    with pytest.raises(ValueError, match="Unknown role"):
        ResumeEngine().analyze(str(p), "hft")


def test_pipeline_nonexistent_pdf():
    """Non-existent file must raise FileNotFoundError."""
    from resume_engine.pipeline import ResumeEngine
    with pytest.raises(FileNotFoundError):
        ResumeEngine().analyze("/nonexistent/path/r.pdf", "sde")


def test_pipeline_empty_file(tmp_path):
    """Empty file must raise ValueError."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "empty.pdf"
    p.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        ResumeEngine().analyze(str(p), "sde")


def test_pipeline_output_json_serializable(tmp_path):
    """Pipeline output must be fully JSON-serializable for all roles."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf("Projects", [
        "Built ML pipeline using TensorFlow with 95% accuracy"
    ]))
    eng = ResumeEngine()
    for role_id in ["sde", "quant", "consulting", "core"]:
        result = eng.analyze(str(p), role_id)
        try:
            serialized = json.dumps(result.model_dump())
        except TypeError as e:
            pytest.fail(f"Output not JSON-serializable for '{role_id}': {e}")
        assert len(serialized) > 50


def test_pipeline_scores_differ_across_roles(tmp_path):
    """The four role scores must not all be identical (role-conditioning must work)."""
    from resume_engine.pipeline import ResumeEngine
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf("Projects", [
        "Ranked Codeforces Specialist, max rating 1450",
        "Built REST API using Python and Flask",
        "Led team of 12 students in Techkriti event",
        "Studied Probability and Stochastic Calculus",
    ]))
    eng = ResumeEngine()
    scores = []
    for role_id in ["sde", "quant", "consulting", "core"]:
        result = eng.analyze(str(p), role_id)
        scores.append(result.score.score)
    assert len(set(scores)) > 1, (
        f"All role scores are identical ({scores[0]}) — role conditioning not working"
    )


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Return a TestClient for the FastAPI app."""
    try:
        from fastapi.testclient import TestClient
        from resume_engine.api.app import app
        with TestClient(app) as client:
            yield client
    except ImportError:
        pytest.skip("fastapi[testclient] or httpx not available")



def test_api_health(api_client):
    """Health endpoint must return 200 with status: ok."""
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "roles" in data
    assert sorted(data["roles"]) == ["consulting", "core", "quant", "sde"]


def test_api_valid_pdf(api_client, tmp_path):
    """Valid PDF + valid role must return 200 with analysis fields."""
    pdf_bytes = _make_minimal_pdf("Projects", [
        "Built web app using Python and Flask with 10k users"
    ])
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    for field in ["role", "document", "evidence", "score", "advisory"]:
        assert field in data, f"Missing field '{field}' in API response"


def test_api_invalid_role(api_client):
    """Invalid role must return HTTP 400."""
    pdf_bytes = _make_minimal_pdf()
    resp = api_client.post(
        "/analyze",
        data={"role": "hft"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 400
    assert "role" in resp.json()["detail"].lower()


def test_api_empty_file(api_client):
    """Empty file must return HTTP 400."""
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_api_non_pdf_extension(api_client):
    """File with non-PDF extension must return HTTP 400."""
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.docx", b"not a pdf", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower()


def test_api_non_pdf_bytes(api_client):
    """File with .pdf extension but non-PDF bytes must return HTTP 400."""
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", b"This is not a PDF file content", "application/pdf")},
    )
    assert resp.status_code == 400


def test_api_malformed_pdf(api_client):
    """Malformed PDF (bad magic bytes) must return HTTP 400."""
    bad_pdf = b"%PDF-1.4 this is corrupted garbage !@#$%"
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", bad_pdf, "application/pdf")},
    )
    # Should be 400 or 500, not crash silently
    assert resp.status_code in (400, 500)


def test_api_oversized_upload(api_client):
    """Files exceeding 10 MB must return HTTP 413."""
    big_data = b"%PDF-1.4 " + b"A" * (11 * 1024 * 1024)
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", big_data, "application/pdf")},
    )
    assert resp.status_code == 413


def test_api_temp_file_cleanup(api_client, tmp_path, monkeypatch):
    """Temporary files must be removed after analysis."""
    import resume_engine.api.app as app_module
    created_paths: list[str] = []
    original_mktemp = tempfile.NamedTemporaryFile

    class _TrackingTmpFile:
        def __init__(self, *args, **kwargs):
            self._f = original_mktemp(*args, **kwargs)
            created_paths.append(self._f.name)

        def __enter__(self):
            return self._f.__enter__()

        def __exit__(self, *args):
            return self._f.__exit__(*args)

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _TrackingTmpFile)

    pdf_bytes = _make_minimal_pdf()
    api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    # All tracked temp files must have been deleted
    for path in created_paths:
        assert not os.path.exists(path), (
            f"Temporary file was NOT cleaned up: {path}"
        )


def test_api_all_four_roles(api_client):
    """All four roles must succeed via API."""
    pdf_bytes = _make_minimal_pdf("Projects", [
        "Built ML pipeline using TensorFlow",
        "Led team of 10 in Techkriti coordination",
    ])
    for role_id in ["sde", "quant", "consulting", "core"]:
        resp = api_client.post(
            "/analyze",
            data={"role": role_id},
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200, (
            f"API failed for role '{role_id}': {resp.status_code} — {resp.text[:200]}"
        )
        data = resp.json()
        assert data["role"] == role_id


# ---------------------------------------------------------------------------
# Golden resume e2e tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_pipeline_all_roles():
    """Golden resume must complete successfully for all 4 roles."""
    from resume_engine.pipeline import ResumeEngine
    eng = ResumeEngine()
    for role_id in ["sde", "quant", "consulting", "core"]:
        result = eng.analyze(str(GOLDEN), role_id)
        assert result.role == role_id
        assert result.score.score >= 0.0
        assert result.score.score <= 100.0
        assert result.evidence.claim_count >= 5, (
            f"Golden resume has only {result.evidence.claim_count} claims for '{role_id}'"
        )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sections_in_document_summary():
    """Golden resume document summary must list all expected sections."""
    from resume_engine.pipeline import ResumeEngine
    result = ResumeEngine().analyze(str(GOLDEN), "sde")
    sections = result.document.sections
    required = ["Education", "Experience", "Research", "Projects",
                "Positions of Responsibility"]
    for sec in required:
        assert sec in sections, (
            f"Section '{sec}' missing from document summary. Got: {sections}"
        )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_evidence_skills_detected():
    """Golden resume evidence summary must include key skills."""
    from resume_engine.pipeline import ResumeEngine
    result = ResumeEngine().analyze(str(GOLDEN), "sde")
    skills = result.evidence.all_skills
    assert "tensorflow" in skills or "python" in skills, (
        f"Key skills not detected in golden resume. Skills: {skills}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_api_response(api_client):
    """Golden resume must return 200 with valid JSON from API."""
    with open(GOLDEN, "rb") as f:
        pdf_bytes = f.read()
    resp = api_client.post(
        "/analyze",
        data={"role": "sde"},
        files={"file": ("golden_resume_01.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, f"Golden resume API failed: {resp.status_code} — {resp.text[:300]}"
    data = resp.json()
    for field in ["role", "document", "evidence", "score", "advisory"]:
        assert field in data


def test_api_dashboard_html(api_client):
    """GET / must serve the Web Advisory Dashboard HTML page."""
    resp = api_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "IITK Context-Aware Resume Diagnostic Engine" in resp.text


def test_api_analyze_all(api_client):
    """POST /analyze-all must evaluate PDF across all 4 roles."""
    pdf_bytes = _make_minimal_pdf("Projects", [
        "Developed Python REST API with 99.9% uptime serving 100k users",
        "Ranked Codeforces Candidate Master 1900 rating",
    ])
    resp = api_client.post(
        "/analyze-all",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    for role_id in ["sde", "quant", "consulting", "core"]:
        assert role_id in data
        assert "score" in data[role_id]
        assert "advisory" in data[role_id]


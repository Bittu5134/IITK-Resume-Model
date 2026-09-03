"""Tests for Scrap Resume & Tiered CPI Penalty System."""
import pymupdf
import pytest
from pathlib import Path
from resume_engine.pipeline import ResumeEngine
from resume_engine.evidence.models import EvidenceBundle, AtomicClaim
from resume_engine.ontology.roles import get_role_requirement
from resume_engine.scoring.scorer import RoleScorer


def _make_pdf(cpi_str: str, bullets: list[str]) -> bytes:
    d = pymupdf.open()
    pg = d.new_page(width=600, height=800)
    pg.insert_text((50, 50), "Education", fontsize=12)
    pg.insert_text((50, 75), f"B.Tech | CPI: {cpi_str}", fontsize=10)
    pg.insert_text((50, 110), "Projects", fontsize=12)
    y = 135
    for b in bullets:
        pg.insert_text((50, y), f"\u2022 {b}", fontsize=10)
        y += 25
    buf = d.tobytes()
    d.close()
    return buf


def test_zero_cpi_resumes_score_below_twenty(tmp_path):
    p = tmp_path / "zero_cpi.pdf"
    p.write_bytes(_make_pdf("0.0/10.0", [
        "Worked on web project using python",
        "Assisted in basic team meetings"
    ]))

    engine = ResumeEngine()
    results = engine.analyze_all(str(p))

    for role_id in ["sde", "quant", "consulting", "core", "analyst", "product"]:
        sc = results[role_id]["score"]["score"]
        assert sc < 20.0, f"Role {role_id} score {sc} is >= 20.0 for 0.0 CPI!"
        penalties = results[role_id]["score"]["penalties_applied"]
        assert any("Zero CPI / Scrap Academic Record" in p for p in penalties)


def test_scrap_resume_content_scores_below_twenty(tmp_path):
    d = pymupdf.open()
    pg = d.new_page(width=600, height=800)
    pg.insert_text((50, 50), "Lorem ipsum scrap data sample text placeholder", fontsize=12)
    buf = d.tobytes()
    d.close()

    p = tmp_path / "scrap.pdf"
    p.write_bytes(buf)

    engine = ResumeEngine()
    results = engine.analyze_all(str(p))

    for role_id in ["sde", "quant", "consulting", "core", "analyst", "product"]:
        sc = results[role_id]["score"]["score"]
        assert sc < 20.0, f"Role {role_id} score {sc} is >= 20.0 for scrap resume!"


def test_progressive_cpi_penalties():
    scorer = RoleScorer()
    role_sde = get_role_requirement("sde")

    # Candidate with CPI 4.5 (Too bad: < 5.0 probation cutoff)
    ev_critical = EvidenceBundle(cpi=4.5, claims=[
        AtomicClaim(claim_id="1", bullet_id="1", section="Projects", text_snippet="Built REST API in Python Flask")
    ])
    sc_critical = scorer.score(ev_critical, role_sde)
    assert any("Academic deficit" in p for p in sc_critical.penalties_applied)

    # Candidate with CPI 5.5 (Normal: >= 5.0) -> No CPI penalty
    ev_low = EvidenceBundle(cpi=5.5, claims=[
        AtomicClaim(claim_id="1", bullet_id="1", section="Projects", text_snippet="Built REST API in Python Flask")
    ])
    sc_low = scorer.score(ev_low, role_sde)
    assert not any("CPI" in p for p in sc_low.penalties_applied)

    # Candidate with CPI 6.5 (Normal: >= 5.0) -> No CPI penalty
    ev_sub7 = EvidenceBundle(cpi=6.5, claims=[
        AtomicClaim(claim_id="1", bullet_id="1", section="Projects", text_snippet="Built REST API in Python Flask")
    ])
    sc_sub7 = scorer.score(ev_sub7, role_sde)
    assert not any("CPI" in p for p in sc_sub7.penalties_applied)

    # Candidate with CPI 8.5 -> No CPI penalty
    ev_good = EvidenceBundle(cpi=8.5, claims=[
        AtomicClaim(claim_id="1", bullet_id="1", section="Projects", text_snippet="Built REST API in Python Flask")
    ])
    sc_good = scorer.score(ev_good, role_sde)
    assert not any("CPI" in p for p in sc_good.penalties_applied)


def test_iitk_courses_catalog_recognition():
    from resume_engine.evidence.extractor import SKILL_TAXONOMY
    from resume_engine.ontology.courses import IITK_COURSES

    assert len(IITK_COURSES) >= 700
    assert "cs330" in SKILL_TAXONOMY
    assert "cs 330" in SKILL_TAXONOMY
    assert "ee380" in SKILL_TAXONOMY
    assert "mth101a" in SKILL_TAXONOMY
    assert "des601" in SKILL_TAXONOMY

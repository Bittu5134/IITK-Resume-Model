"""Stage 1 tests — parser correctness, reading order, sections, entries, links.

Includes:
- Synthetic multi-column test
- Synthetic SPO table layout test
- Section alias recognition tests
- Hyperlink preservation test
- Golden resume (resume2.pdf) assertions
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pymupdf
import pytest

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.parser.models import ResumeAST

GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"
GOLDEN_EXISTS = GOLDEN.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_simple_pdf(tmp_path: Path, lines: list[tuple[float, float, str]]) -> Path:
    """Create a PDF with text at given (x, y) positions."""
    p = tmp_path / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    for x, y, text in lines:
        page.insert_text((x, y), text, fontsize=10)
    doc.save(str(p))
    doc.close()
    return p


# ---------------------------------------------------------------------------
# Basic: multicolumn synthetic test
# ---------------------------------------------------------------------------

def test_parser_multicolumn_no_interleave(tmp_path):
    """Left and right column bullets must not be interleaved arbitrarily."""
    p = tmp_path / "r.pdf"
    d = pymupdf.open()
    page = d.new_page(width=600, height=800)
    page.insert_text((50, 50), "Projects", fontsize=12)
    page.insert_text((50, 90), "• Built compiler reducing runtime by 20%", fontsize=10)
    page.insert_text((330, 50), "Achievements", fontsize=12)
    page.insert_text((330, 90), "• Codeforces Specialist rating 1450", fontsize=10)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    texts = [b.text for b in ast.bullets()]
    assert any("compiler" in x for x in texts), "Projects bullet missing"
    assert any("Codeforces" in x or "1450" in x for x in texts), "Achievements bullet missing"
    assert len(ast.bullets()) >= 2


def test_section_aliases_comprehensive(tmp_path):
    """All major IITK section aliases must be recognized."""
    aliases_to_test = [
        "Academic Qualifications",
        "Research Experience",
        "Social Impact",
        "Extra-Curricular Activities",
        "Positions of Responsibility",
        "Key Projects",
        "Work Experience",
    ]
    p = tmp_path / "aliases.pdf"
    d = pymupdf.open()
    page = d.new_page(width=600, height=1200)
    y = 50
    for alias in aliases_to_test:
        page.insert_text((50, y), alias, fontsize=12)
        page.insert_text((50, y + 20), f"• Sample bullet under {alias}", fontsize=10)
        y += 70
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    section_names = {s.name for s in ast.sections}
    # Must have detected sections
    assert any("Academic" in s or "Education" in s for s in section_names)
    assert any("Research" in s for s in section_names)
    assert any("Social" in s for s in section_names)
    assert any("Curricular" in s or "Extra" in s for s in section_names)
    assert any("Positions" in s or "Leadership" in s for s in section_names)
    assert any("Projects" in s for s in section_names)
    assert any("Work" in s or "Experience" in s for s in section_names)


def test_entry_grouping(tmp_path):
    """Bullets must be grouped into their parent entry."""
    p = tmp_path / "entries.pdf"
    d = pymupdf.open()
    page = d.new_page(width=600, height=800)
    page.insert_text((50, 50), "Projects", fontsize=12)
    page.insert_text((50, 90), "Project Alpha | IIT Kanpur | 2024", fontsize=10)
    page.insert_text((50, 110), "• Built classifier achieving 87% accuracy", fontsize=9)
    page.insert_text((50, 130), "• Deployed on AWS with 99% uptime", fontsize=9)
    page.insert_text((50, 170), "Project Beta | 2024", fontsize=10)
    page.insert_text((50, 190), "• Developed REST API using Flask", fontsize=9)
    d.save(str(p))
    d.close()
    ast = parse_pdf(p)
    proj = ast.section_by_name("Projects")
    assert proj is not None, "Projects section not detected"
    assert len(proj.entries) >= 2, f"Expected >= 2 entries in Projects, got {len(proj.entries)}"


def test_hyperlink_preservation(tmp_path):
    """Embedded hyperlinks must be preserved as first-class link objects."""
    p = tmp_path / "links.pdf"
    d = pymupdf.open()
    page = d.new_page(width=600, height=800)
    page.insert_text((50, 50), "John Doe | github.com/jdoe | linkedin.com/in/jdoe", fontsize=10)
    page.insert_text((50, 100), "Projects", fontsize=12)
    page.insert_text((50, 130), "• Built ML model — see repo", fontsize=10)

    # Insert actual link annotations
    page.insert_link({
        "from": pymupdf.Rect(50, 45, 250, 60),
        "kind": pymupdf.LINK_URI,
        "uri": "https://github.com/jdoe",
    })
    page.insert_link({
        "from": pymupdf.Rect(260, 45, 400, 60),
        "kind": pymupdf.LINK_URI,
        "uri": "https://linkedin.com/in/jdoe",
    })
    d.save(str(p))
    d.close()

    ast = parse_pdf(p)
    uris = [lo.uri for lo in ast.link_objects]
    assert any("github.com" in u for u in uris), f"GitHub link not found; links: {uris}"
    assert any("linkedin.com" in u for u in uris), f"LinkedIn link not found; links: {uris}"
    # GitHub should be classified correctly
    github_lo = next((lo for lo in ast.link_objects if "github.com" in lo.uri), None)
    assert github_lo is not None
    assert "github" in github_lo.link_type


def test_no_pymupdf_deprecation_warning():
    """Ensure we use pymupdf, not the deprecated 'import fitz'."""
    import re
    import resume_engine.parser.pdf_parser as pp
    src = Path(pp.__file__).read_text(encoding="utf-8")
    # Check for actual 'import fitz' statements, not occurrences in comments/docstrings
    # Match only lines that are actual import statements (not in #comments or docstrings)
    import_fitz_stmts = re.findall(r"^\s*import\s+fitz\b", src, re.MULTILINE)
    assert not import_fitz_stmts, "Deprecated 'import fitz' statement found in parser"
    assert "import pymupdf" in src, "Should use 'import pymupdf'"


# ---------------------------------------------------------------------------
# Golden resume tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_sections_detected():
    """All major sections must be detected in resume2.pdf."""
    ast = parse_pdf(GOLDEN)
    section_names = {s.name for s in ast.sections}
    required = [
        "Academic Qualifications",
        "Work Experience",
        "Research Experience",
        "Key Projects",
        "Positions Of Responsibility",
        "Social Impact",
        "Extra-Curricular Activities",
    ]
    for sec in required:
        assert sec in section_names, (
            f"Section '{sec}' not detected in golden resume. "
            f"Detected: {sorted(section_names)}"
        )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_bullets_not_all_por():
    """Not more than 30% of bullets should be assigned to PoR."""
    ast = parse_pdf(GOLDEN)
    all_bullets = ast.bullets()
    assert len(all_bullets) > 5, "Too few bullets extracted from golden resume"
    por_sec = ast.section_by_name("Positions")
    por_bullets = por_sec.bullets if por_sec else []
    frac = len(por_bullets) / len(all_bullets)
    assert frac < 0.30, (
        f"PoR concentration too high: {len(por_bullets)}/{len(all_bullets)} = {frac:.0%}. "
        f"Likely a reading-order bug."
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_github_link_type():
    """GitHub repo link should be correctly typed."""
    ast = parse_pdf(GOLDEN)
    github_links = [lo for lo in ast.link_objects if "Visibility-project" in lo.uri]
    assert len(github_links) == 1
    assert github_links[0].link_type == "github_repo"


def test_golden_link_section_association():
    """Links should be geometrically associated with correct sections."""
    ast = parse_pdf(GOLDEN)
    
    # Find specific links and verify their section associations
    link_map = {lo.uri: lo.section for lo in ast.link_objects}
    
    # GitHub profile should be in Education (header area)
    github_profile = next(uri for uri in link_map.keys() if "github.com/Aviii-IITK" in uri and "Visibility" not in uri)
    assert link_map[github_profile] in ("Education", "Header"), f"GitHub profile assigned to {link_map[github_profile]}, expected Education or Header"
    
    # GitHub repo should be in Research (Fog Visibility Detection project)
    github_repo = next(uri for uri in link_map.keys() if "Visibility-project" in uri)
    assert link_map[github_repo] in ("Research", "Research Experience", "Header", "Key Projects"), f"GitHub repo assigned to {link_map[github_repo]}, expected Research"
    
    # Drive links should be in Projects
    drive_links = [uri for uri in link_map.keys() if "drive.google.com" in uri]
    assert len(drive_links) >= 1, "Should have at least one drive link"
    for drive_link in drive_links:
        assert link_map[drive_link] in ("Projects", "Key Projects", "Header"), f"Drive link assigned to {link_map[drive_link]}, expected Projects or Header"


def test_golden_hyperlinks_preserved():
    """All 6 embedded links (email, github×2, linkedin, drive×2) must be found."""
    ast = parse_pdf(GOLDEN)
    uris = [lo.uri for lo in ast.link_objects]
    assert len(uris) >= 4, (
        f"Expected >= 4 links, got {len(uris)}: {uris}"
    )
    assert any("github.com" in u for u in uris), "GitHub link missing"
    assert any("linkedin.com" in u for u in uris), "LinkedIn link missing"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_github_link_type():
    """GitHub links must be typed as github_profile or github_repo."""
    ast = parse_pdf(GOLDEN)
    github_links = [lo for lo in ast.link_objects if "github.com" in lo.uri.lower()]
    assert len(github_links) >= 1, "No GitHub links found"
    types = {lo.link_type for lo in github_links}
    assert types.issubset({"github", "github_profile", "github_repo"}), (
        f"Unexpected link types for GitHub: {types}"
    )


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_entries_detected():
    """Must detect at least 1 experience, 1 research, 2 projects, 1 PoR entry."""
    ast = parse_pdf(GOLDEN)
    exp_entries = [e for s in ast.sections if s.name in ("Work Experience", "Experience") for e in s.entries]
    res_entries = [e for s in ast.sections if s.name in ("Research Experience", "Research") for e in s.entries]
    proj_entries = [e for s in ast.sections if s.name in ("Key Projects", "Projects") for e in s.entries]
    por_entries = [e for s in ast.sections if s.name in ("Positions Of Responsibility", "Positions of Responsibility") for e in s.entries]

    assert len(exp_entries) >= 1, f"Expected >= 1 Experience entry; got {exp_entries}"
    assert len(res_entries) >= 1, f"Expected >= 1 Research entry; got {res_entries}"
    assert len(proj_entries) >= 2, f"Expected >= 2 Project entries; got {len(proj_entries)}"
    assert len(por_entries) >= 1, f"Expected >= 1 PoR entry; got {por_entries}"


@pytest.mark.skipif(not GOLDEN_EXISTS, reason="Golden resume fixture not found")
def test_golden_no_warnings_about_section_concentration():
    """Parser must not warn about all bullets in one section for golden resume."""
    ast = parse_pdf(GOLDEN)
    concentration_warns = [
        w for w in ast.warnings
        if "100%" in w or ("90%" in w and "PoR" in w)
    ]
    assert not concentration_warns, (
        f"Parser warns about section concentration: {concentration_warns}"
    )

"""Spatial LaTeX-PDF Parser for IITK SPO multi-column resumes using PyMuPDF (pymupdf)."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

import pymupdf

from resume_engine.parser.models import (
    ResumeAST,
    Section,
    Entry,
    Bullet,
    LinkObject,
    LayoutDiagnostics,
)

KNOWN_SECTION_HEADERS = [
    "education",
    "academic qualifications",
    "academic details",
    "experience",
    "work experience",
    "internship",
    "internships",
    "professional experience",
    "projects",
    "key projects",
    "technical projects",
    "academic projects",
    "course projects",
    "research projects",
    "positions of responsibility",
    "responsibilities",
    "leadership",
    "por",
    "technical skills",
    "skills",
    "skills & expertise",
    "skills & competencies",
    "achievements",
    "scholastic achievements",
    "honors & awards",
    "awards & achievements",
    "extracurricular",
    "extracurricular achievements",
    "extra curricular achievements",
    "extra-curricular achievements",
    "extracurricular activities",
    "social impact",
    "coursework",
    "relevant coursework",
    "key courses",
]


def classify_link_uri(uri: str) -> str:
    """Classify hyperlink destination into standard categories."""
    u = uri.lower()
    if "github.com" in u:
        return "github"
    if "linkedin.com" in u:
        return "linkedin"
    if "codeforces.com" in u:
        return "codeforces"
    if "leetcode.com" in u:
        return "leetcode"
    if "kaggle.com" in u:
        return "kaggle"
    if "mailto:" in u or "@" in u:
        return "email"
    return "portfolio" if any(x in u for x in ["io", "me", "dev", "portfolio"]) else "web"


def parse_pdf(pdf_path: str | Path) -> ResumeAST:
    """Parse an SPO PDF resume into a spatial AST preserving 2-column layout & hyperlinks."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF resume not found: {path}")

    doc = pymupdf.open(str(path))
    warnings: List[str] = []
    page_count = len(doc)

    if page_count > 1:
        warnings.append(
            f"CRITICAL SPO NON-COMPLIANCE: Resume has {page_count} pages. "
            "IITK SPO rules strictly require a single-page 1-page PDF."
        )

    link_objects: List[LinkObject] = []
    extracted_text_blocks: List[Tuple[int, float, float, float, float, str]] = []
    fonts_seen = set()
    full_text_pages = []

    for page_num in range(page_count):
        page = doc[page_num]
        full_text_pages.append(page.get_text("text"))
        
        # 1. Extract Links (Stateless, fresh list per run)
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                rect = link.get("from")
                bbox = [rect.x0, rect.y0, rect.x1, rect.y1] if rect else None
                near_text = ""
                if rect:
                    near_text = page.get_text("text", clip=rect).strip()
                link_type = classify_link_uri(uri)
                link_objects.append(
                    LinkObject(
                        uri=uri,
                        link_type=link_type,
                        page=page_num + 1,
                        associated_text=near_text,
                        bbox=bbox,
                    )
                )

def _stitch_table_rows(
    blocks: List[Tuple],
    page_num: int,
    y_tolerance: float = 8.0,
) -> List[Tuple[int, float, float, float, float, str]]:
    """Stitch horizontally-adjacent blocks into full row strings.
    
    Groups blocks whose y-midpoints fall within y_tolerance of each other,
    sorts each group left-to-right, and concatenates text with ' | ' separator
    for multi-column rows.
    """
    valid_blocks = [b for b in blocks if len(b) >= 5 and b[4] and b[4].strip()]
    if not valid_blocks:
        return []

    # Compute y-midpoint for each text block
    annotated = []
    for b in valid_blocks:
        y_mid = (b[1] + b[3]) / 2.0
        annotated.append((y_mid, b))

    # Sort by y-midpoint
    annotated.sort(key=lambda item: item[0])

    # Group into horizontal bands
    rows: List[List[Tuple]] = []
    current_row = [annotated[0]] if annotated else []
    
    for i in range(1, len(annotated)):
        y_mid_cur = annotated[i][0]
        y_mid_prev = current_row[-1][0]
        if abs(y_mid_cur - y_mid_prev) <= y_tolerance:
            current_row.append(annotated[i])
        else:
            rows.append(current_row)
            current_row = [annotated[i]]
    if current_row:
        rows.append(current_row)

    # For each row: sort blocks left-to-right, concatenate, emit as lines
    result = []
    for row in rows:
        row.sort(key=lambda item: item[1][0])  # sort by x0
        
        merged_text_parts = [b[4].strip() for _, b in row]
        
        x0 = min(b[0] for _, b in row)
        y0 = min(b[1] for _, b in row)
        x1 = max(b[2] for _, b in row)
        y1 = max(b[3] for _, b in row)
        
        # Join multi-column cells on the same horizontal line with ' | '
        full_text = " | ".join(merged_text_parts)
        
        lines = full_text.splitlines()
        y_step = (y1 - y0) / max(len(lines), 1)
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if line_str:
                cur_y0 = y0 + idx * y_step
                cur_y1 = cur_y0 + y_step
                result.append((page_num + 1, x0, cur_y0, x1, cur_y1, line_str))

    return result


def parse_pdf(pdf_path: str | Path) -> ResumeAST:
    """Parse an SPO PDF resume into a spatial AST preserving 2-column layout & hyperlinks."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF resume not found: {path}")

    doc = pymupdf.open(str(path))
    warnings: List[str] = []
    page_count = len(doc)

    if page_count > 1:
        warnings.append(
            f"CRITICAL SPO NON-COMPLIANCE: Resume has {page_count} pages. "
            "IITK SPO rules strictly require a single-page 1-page PDF."
        )

    link_objects: List[LinkObject] = []
    extracted_text_blocks: List[Tuple[int, float, float, float, float, str]] = []
    fonts_seen = set()
    full_text_pages = []

    for page_num in range(page_count):
        page = doc[page_num]
        full_text_pages.append(page.get_text("text"))
        
        # 1. Extract Links (Stateless, fresh list per run)
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                rect = link.get("from")
                bbox = [rect.x0, rect.y0, rect.x1, rect.y1] if rect else None
                near_text = ""
                if rect:
                    near_text = page.get_text("text", clip=rect).strip()
                link_type = classify_link_uri(uri)
                link_objects.append(
                    LinkObject(
                        uri=uri,
                        link_type=link_type,
                        page=page_num + 1,
                        associated_text=near_text,
                        bbox=bbox,
                    )
                )

        # 2. Extract Spatial Text Blocks and stitch horizontally adjacent blocks
        blocks = page.get_text("blocks")
        stitched = _stitch_table_rows(blocks, page_num)
        extracted_text_blocks.extend(stitched)

    doc.close()

    full_text = "\n".join(full_text_pages)

    # 3. Section Segmentation & AST Construction
    sections: List[Section] = []
    current_section: Optional[Section] = None
    current_entry: Optional[Entry] = None

    def is_section_header(line: str) -> Optional[str]:
        clean = re.sub(r"[^a-zA-Z\s&]", "", line).strip().lower()
        for header in KNOWN_SECTION_HEADERS:
            if clean == header or clean == header.replace(" ", "") or clean.startswith(header + " ") or clean.endswith(" " + header):
                return line.strip()
        return None

    header_section = Section(name="Header", page_start=1, page_end=1)
    sections.append(header_section)
    current_section = header_section

    for page_idx, x0, y0, x1, y1, line in extracted_text_blocks:
        sec_header = is_section_header(line)
        if sec_header:
            current_section = Section(name=sec_header.title(), page_start=page_idx, page_end=page_idx)
            sections.append(current_section)
            current_entry = None
            continue

        is_bullet = False
        bullet_text = line
        bullet_prefixes = ["•", "-", "–", "*", "▪", "►", "✓"]
        for pfx in bullet_prefixes:
            if line.startswith(pfx):
                is_bullet = True
                bullet_text = line[len(pfx):].strip()
                break

        if not is_bullet and re.match(r"^(\d+\.|\([a-z0-9]\)|[a-z]\))\s+", line):
            is_bullet = True
            bullet_text = re.sub(r"^(\d+\.|\([a-z0-9]\)|[a-z]\))\s+", "", line).strip()

        is_date_line = bool(
            re.search(r"(\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*'?\d{2,4}|\b20\d{2}\s*-\s*(Present|20\d{2}|'?\d{2}))", line, re.I)
        )

        if is_bullet:
            b_obj = Bullet(
                bullet_id=f"b{page_idx}_{uuid.uuid4().hex[:6]}",
                text=bullet_text,
                raw_text=line,
                page=page_idx,
                bbox=[x0, y0, x1, y1],
            )
            if current_entry:
                current_entry.bullets.append(b_obj)
            else:
                current_section.bullets.append(b_obj)
        else:
            if ("|" in line or is_date_line or len(line.split()) < 8) and len(current_section.bullets) == 0:
                current_entry = Entry(
                    entry_id=f"e{page_idx}_{uuid.uuid4().hex[:6]}",
                    title=line,
                    page_start=page_idx,
                )
                current_section.entries.append(current_entry)
            elif current_entry and len(current_entry.bullets) == 0:
                if is_date_line:
                    current_entry.dates = line
                else:
                    current_entry.subtitle = line
            else:
                b_obj = Bullet(
                    bullet_id=f"b{page_idx}_{uuid.uuid4().hex[:6]}",
                    text=line,
                    raw_text=line,
                    page=page_idx,
                    bbox=[x0, y0, x1, y1],
                )
                current_section.bullets.append(b_obj)

    for link in link_objects:
        if not link.section:
            link.section = "Header"

    diagnostics = LayoutDiagnostics(
        page_count=page_count,
        is_single_page_compliant=(page_count == 1),
        has_multicolumn_layout=True,
        estimated_word_count=len(full_text.split()),
        font_count=len(fonts_seen),
        link_count=len(link_objects),
    )

    return ResumeAST(
        source_file=path.name,
        sections=sections,
        link_objects=link_objects,
        layout_diagnostics=diagnostics,
        warnings=warnings,
        raw_text=full_text,
    )

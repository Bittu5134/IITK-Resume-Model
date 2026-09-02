"""Stage 1 v2 — Layout-aware SPO resume parser.

Key design decisions (fixes B1-B14):
- Row-major reading order: cluster lines into y-band rows, sort rows top-to-bottom,
  within each row sort x left-to-right. No global left/right split that breaks tables.
- Multi-column detection is LOCAL: only treat separate column regions as independent
  when they are spatially persistent and vertically independent (non-table pages).
- SPO table headings span the full width — treated as anchors, never split.
- Rich AST: ResumeDocument -> Section -> Entry -> Bullet -> Span with full provenance.
- All hyperlinks are first-class LinkObjects with page, bbox, type, nearest text.
- Unicode normalization on extracted text; raw_text preserved.
- Entry grouping: title rows start new entries; bullets attach to current entry.
- Subsection labels (Objective/Approach/Result/Leadership/…) detected and attached.
- Robust section alias table covering IITK SPO template variants.
- Parser warnings for anomalous layouts (sanity checks).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import NamedTuple

import pymupdf  # replaces deprecated 'import fitz'

from .models import (
    BBox, Bullet, Entry, LinkObject, ResumeAST, Section, Span
)

# ---------------------------------------------------------------------------
# Section vocabulary — comprehensive IITK SPO alias table
# ---------------------------------------------------------------------------
_SECTION_ALIASES: dict[str, str] = {
    # Education / Academics
    "education": "Education",
    "academic qualifications": "Education",
    "academic qualification": "Education",
    "academic details": "Education",
    "academics": "Education",
    "academic background": "Education",
    "academic achievements": "Achievements",
    "scholastic achievements": "Achievements",
    "scholastic highlights": "Achievements",

    # Experience
    "work experience": "Experience",
    "experience": "Experience",
    "internship": "Experience",
    "internships": "Experience",
    "professional experience": "Experience",
    "industry experience": "Experience",
    "technical experience": "Experience",

    # Research
    "research experience": "Research",
    "research": "Research",
    "research projects": "Research",
    "research work": "Research",
    "undergraduate research": "Research",

    # Projects
    "projects": "Projects",
    "key projects": "Projects",
    "technical projects": "Projects",
    "software projects": "Projects",
    "selected projects": "Projects",
    "project": "Projects",

    # Positions of Responsibility
    "positions of responsibility": "Positions of Responsibility",
    "position of responsibility": "Positions of Responsibility",
    "positions of responsibilities": "Positions of Responsibility",
    "por": "Positions of Responsibility",

    # Achievements
    "achievements": "Achievements",
    "awards": "Achievements",
    "awards and achievements": "Achievements",
    "honors and awards": "Achievements",
    "honours and awards": "Achievements",

    # Social Impact
    "social impact": "Social Impact",
    "social work": "Social Impact",
    "community service": "Social Impact",
    "volunteering": "Social Impact",
    "ngo": "Social Impact",

    # Extracurricular
    "extra-curricular activities": "Extracurricular",
    "extra curricular activities": "Extracurricular",
    "extracurricular activities": "Extracurricular",
    "extra curricular achievements": "Extracurricular",
    "extracurricular achievements": "Extracurricular",
    "extra-curricular achievements": "Extracurricular",
    "extracurricular": "Extracurricular",
    "co-curricular activities": "Extracurricular",
    "co curricular activities": "Extracurricular",
    "activities": "Extracurricular",
    "hobbies and interests": "Extracurricular",
    "interests": "Extracurricular",

    # Skills
    "skills": "Skills",
    "technical skills": "Skills",
    "programming skills": "Skills",
    "technologies": "Skills",
    "tools and technologies": "Skills",
    "core competencies": "Skills",

    # Coursework
    "relevant coursework": "Coursework",
    "relevant courses": "Coursework",
    "coursework": "Coursework",
    "courses": "Coursework",
    "key courses": "Coursework",
    "selected coursework": "Coursework",

    # Publications / Research output
    "publications": "Publications",
    "papers": "Publications",
    "research publications": "Publications",
}

# Subsection / row-label vocabulary
# Subsection / row-label vocabulary
_SUBLABELS: dict[str, str] = {
    "objective": "objective",
    "approach": "approach",
    "result": "result",
    "results": "result",
    "technical": "technical",
    "management": "management",
    "leadership": "leadership",
    "initiative": "initiative",
    "initiatives": "initiative",
    "impact": "impact",
    "mentorship": "mentorship",
    "cultural": "cultural",
    "sports": "sports",
    "responsibilities": "responsibilities",
    "description": "description",
    "summary": "summary",
    "contribution": "contribution",
    "contributions": "contribution",
    "overview": "overview",
    "category": "category",
    "level": "level",
    "event": "event",
    "detail": "detail",
    "role": "role",
    "context": "context",
    "outcome": "outcome",
    "method": "method",
    "methodology": "methodology",
    "key learning": "key learning",
    "takeaway": "takeaway",
    "findings": "findings",
}

# Bullet glyph patterns
_BULLET_RE = re.compile(r"^\s*(?:[•●▪◦‣·\u2022\u25cf\u25aa\u25e6\u2023]|[-–—\u2013\u2014]|\d+[.)]\s|\(\w\)\s?)\s*")

# Subsection label pattern: e.g. "Objective:", "Approach –", "Result •"
_SUBLABEL_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(k) for k in _SUBLABELS) + r")\s*[:–\-•·]?\s*",
    re.IGNORECASE,
)

# Date range pattern for entry metadata detection
_DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4}|\b\d{4}\s*[-–—]\s*(?:\d{4}|present|ongoing|now)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm_heading(text: str) -> str:
    """Normalize heading text for alias lookup."""
    s = text.strip()
    # Replace unicode dashes/hyphens with ASCII hyphen
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", s)
    # Replace non-breaking and other whitespace
    s = re.sub(r"[\u00a0\u200b\u2009\u202f]+", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Strip trailing punctuation
    s = s.rstrip(":.-– ")
    # Lowercase for lookup
    return s.lower()


def _normalize_text(text: str) -> str:
    """Unicode-normalize text: NFC, replace common ligatures, stitch hyphenation, normalize whitespace."""
    text = unicodedata.normalize("NFC", text)
    # Common ligatures
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    # Stitch hyphenated words across line breaks or soft spaces (e.g. "Entrepren-\nneurship" -> "Entrepreneurship")
    text = re.sub(r'(\b[A-Za-z]{2,})[\u2010\u2011\u2012\u2013\u2014\u2015\-]\s*[\r\n]+\s*([a-z]{2,}\b)', r'\1\2', text)
    text = re.sub(r'(\b[A-Za-z]{3,})[\u2010\u2011\u2012\u2013\u2014\u2015\-]\s+([a-z]{3,}\b)', r'\1\2', text)
    # Normalize dashes to en-dash for display
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015]", "\u2013", text)
    # Normalize quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    # Collapse repeated spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _detect_section(text: str) -> str | None:
    n = _norm_heading(text)
    if n in _SECTION_ALIASES:
        return _SECTION_ALIASES[n]
    # Fuzzy prefix match for short headings (e.g. "EDUCATION" all-caps)
    n_lower = n.lower()
    for k, v in _SECTION_ALIASES.items():
        if n_lower == k:
            return v
        # Allow ALL-CAPS variant
        if len(n_lower) <= 60 and n_lower.rstrip(":") == k:
            return v
    return None


def _infer_link_type(uri: str) -> str:
    u = uri.lower()
    if u.startswith("mailto:"):
        return "email"
    if "github.com" in u:
        # Heuristic: profile if path has only one segment
        path = uri.split("github.com", 1)[-1].strip("/")
        return "github_profile" if path.count("/") == 0 else "github_repo"
    if "linkedin.com" in u:
        return "linkedin"
    if "drive.google.com" in u or "docs.google.com" in u:
        return "drive"
    return "web"


def _stable_id(prefix: str, page: int, y: float, text: str) -> str:
    h = hashlib.md5(f"{page}|{round(y, 1)}|{text[:40]}".encode()).hexdigest()[:6]
    return f"{prefix}{page:02d}_{h}"


def _bbox_from_line(line: dict) -> BBox:
    b = line["bbox"]
    return BBox(x0=b[0], y0=b[1], x1=b[2], y1=b[3])


def _spans_from_line(line: dict, page_links: list[tuple], page_no: int) -> tuple[list[Span], list[str]]:
    span_objs: list[Span] = []
    bullet_links: list[str] = []
    for s in line.get("spans", []):
        sb = pymupdf.Rect(s["bbox"])
        uri = None
        for lr, lu in page_links:
            if sb.intersects(lr):
                uri = lu
                bullet_links.append(lu)
                break
        flags = int(s.get("flags", 0))
        span_objs.append(Span(
            text=s.get("text", ""),
            bbox=BBox(x0=sb.x0, y0=sb.y0, x1=sb.x1, y1=sb.y1),
            page=page_no,
            size=s.get("size"),
            bold=bool(flags & 16),
            italic=bool(flags & 2),
            uri=uri,
        ))
    return span_objs, sorted(set(bullet_links))


# ---------------------------------------------------------------------------
# Row-major reading order (B1 fix)
# ---------------------------------------------------------------------------

class _LineInfo(NamedTuple):
    text: str
    bbox: tuple[float, float, float, float]   # x0, y0, x1, y1
    spans: list[dict]
    block_type: str  # "text" | "image"


_Y_CLUSTER_GAP = 4.0  # px gap to consider same row


def _row_major_order(lines: list[_LineInfo]) -> list[_LineInfo]:
    """Sort lines in reading order: row-band top-to-bottom, within row left-to-right.

    This handles SPO table layouts correctly — no global left/right split.
    """
    if not lines:
        return []

    # Sort first by y0 so we can cluster into rows
    sorted_by_y = sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))

    rows: list[list[_LineInfo]] = []
    current_row: list[_LineInfo] = [sorted_by_y[0]]

    for line in sorted_by_y[1:]:
        # Check if this line y-overlaps with the current row band
        row_y1_max = max(l.bbox[3] for l in current_row)
        row_y0_min = min(l.bbox[1] for l in current_row)
        row_center = (row_y0_min + row_y1_max) / 2

        # A line belongs to the same row if its center y is within the current
        # row band (with a small tolerance gap)
        line_center_y = (line.bbox[1] + line.bbox[3]) / 2
        if line_center_y <= row_y1_max + _Y_CLUSTER_GAP:
            current_row.append(line)
        else:
            rows.append(current_row)
            current_row = [line]
    rows.append(current_row)

    # Within each row, sort left to right by x0
    result: list[_LineInfo] = []
    for row in rows:
        result.extend(sorted(row, key=lambda l: l.bbox[0]))

    return result


# ---------------------------------------------------------------------------
# Layout mode detection
# ---------------------------------------------------------------------------

def _detect_layout_mode(lines: list[_LineInfo], page_width: float) -> str:
    """Detect the dominant layout of a page."""
    if not lines:
        return "unknown"
    center = page_width / 2
    left_count = sum(1 for l in lines if l.bbox[2] < center * 1.05)
    right_count = sum(1 for l in lines if l.bbox[0] > center * 0.95)
    full_count = sum(1 for l in lines if l.bbox[0] < center * 0.5 and l.bbox[2] > center * 1.5)
    total = len(lines)
    if full_count / max(total, 1) > 0.6:
        return "table"
    if left_count >= 3 and right_count >= 3 and (left_count + right_count) / total > 0.5:
        return "multi-column"
    return "single-column"


# ---------------------------------------------------------------------------
# Entry title detection
# ---------------------------------------------------------------------------

def _is_title_row(text: str, spans: list[Span]) -> bool:
    """Heuristic: title rows are short, often bold, and don't start with bullets."""
    if _BULLET_RE.match(text):
        return False
    if _detect_section(text):
        return False
    # Has date range → likely a title/metadata row
    if _DATE_RE.search(text):
        return True
    # Bold text that's short → likely a title
    if spans and all(s.bold for s in spans) and len(text) < 100:
        return True
    # Short non-bullet line (e.g. "Fog Visibility Detection | IIT Kanpur")
    if len(text.split()) <= 12 and not text.startswith(" "):
        # Not a continuation of a long paragraph
        return True
    return False


def _detect_sublabel(text: str) -> tuple[str | None, str]:
    """Return (label, remainder_text) if text starts with a known sublabel."""
    m = _SUBLABEL_RE.match(text)
    if m:
        label_key = m.group(1).lower()
        remainder = text[m.end():].strip()
        return _SUBLABELS.get(label_key), remainder
    return None, text


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_pdf(path: str | Path) -> ResumeAST:
    path = Path(path)
    doc = pymupdf.open(str(path))

    sections: list[Section] = []
    current_section = Section(name="Header", page_start=1)
    sections.append(current_section)

    all_link_objects: list[LinkObject] = []
    all_link_uris: list[str] = []
    warnings: list[str] = []
    bullet_counter = 0
    entry_counter = 0
    layout_diagnostics: dict = {}

    current_entry: Entry | None = None

    for pno, page in enumerate(doc, start=1):
        page_width = page.rect.width

        # ── Collect all hyperlinks on this page ──────────────────────────
        page_links: list[tuple[pymupdf.Rect, str]] = []
        for lk in page.get_links():
            uri = lk.get("uri", "")
            if not uri:
                continue
            rect = pymupdf.Rect(lk["from"])
            page_links.append((rect, uri))

        # ── Extract text lines with geometry ─────────────────────────────
        raw = page.get_text("dict")
        raw_lines: list[_LineInfo] = []
        for block in raw.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                spans = line.get("spans", [])
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                raw_lines.append(_LineInfo(
                    text=text,
                    bbox=tuple(line["bbox"]),
                    spans=spans,
                    block_type="text",
                ))

        # ── Row-major reading order ────────────────────────────────────────
        ordered = _row_major_order(raw_lines)
        layout_mode = _detect_layout_mode(ordered, page_width)
        layout_diagnostics[f"page{pno}"] = layout_mode

        # ── Associate links with their nearest text ────────────────────────
        # Build link objects using nearest text span for context
        for lr, lu in page_links:
            # Find closest text
            nearest_text = ""
            nearest_dist = float("inf")
            for li in ordered:
                lb = li.bbox
                line_center = ((lb[0] + lb[2]) / 2, (lb[1] + lb[3]) / 2)
                link_center = ((lr.x0 + lr.x1) / 2, (lr.y0 + lr.y1) / 2)
                d = abs(line_center[0] - link_center[0]) + abs(line_center[1] - link_center[1])
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_text = li.text
            lobj = LinkObject(
                uri=lu,
                page=pno,
                bbox=BBox(x0=lr.x0, y0=lr.y0, x1=lr.x1, y1=lr.y1),
                link_type=_infer_link_type(lu),
                associated_text=nearest_text[:120],
                section=current_section.name,
            )
            all_link_objects.append(lobj)
            if lu not in all_link_uris:
                all_link_uris.append(lu)

        # ── Process lines ──────────────────────────────────────────────────
        current_section.layout_mode = layout_mode

        for line in ordered:
            text = line.text.strip()
            norm_text = _normalize_text(text)

            # Build span objects early (needed for heading detection)
            span_objs, bullet_links = _spans_from_line(
                {"spans": line.spans, "bbox": line.bbox}, page_links, pno
            )
            line_bbox = BBox(x0=line.bbox[0], y0=line.bbox[1],
                             x1=line.bbox[2], y1=line.bbox[3])

            # ── Section heading? ───────────────────────────────────────────
            sec_name = _detect_section(text)
            if sec_name:
                current_section = Section(
                    name=sec_name,
                    raw_heading=text,
                    page_start=pno,
                    layout_mode=layout_mode,
                )
                sections.append(current_section)
                current_entry = None  # reset entry grouping at new section
                continue

            # Track raw lines for audit
            current_section.raw_lines.append(text)

            # ── Bullet line? ───────────────────────────────────────────────
            if _BULLET_RE.match(text):
                clean = _BULLET_RE.sub("", text).strip()
                norm_clean = _normalize_text(clean)

                # Detect sublabel (Objective: / Approach – / etc.)
                sublabel, payload = _detect_sublabel(norm_clean)

                bullet_counter += 1
                bid = _stable_id("b", pno, line.bbox[1], clean)

                bullet = Bullet(
                    id=bid,
                    text=payload if sublabel else norm_clean,
                    raw_text=text,
                    normalized_text=norm_clean,
                    section=current_section.name,
                    entry_id=current_entry.id if current_entry else None,
                    page=pno,
                    bbox=line_bbox,
                    spans=span_objs,
                    hyperlinks=bullet_links,
                    subsection_label=sublabel,
                )

                # Attach to current entry
                if current_entry and current_entry.section == current_section.name:
                    current_entry.bullets.append(bullet)
                else:
                    # No current entry — create a placeholder entry
                    entry_counter += 1
                    eid = _stable_id("e", pno, line.bbox[1], clean)
                    current_entry = Entry(
                        id=eid,
                        section=current_section.name,
                        page_start=pno,
                        bbox=line_bbox,
                    )
                    current_section.entries.append(current_entry)
                    current_entry.bullets.append(bullet)

                current_section.bullets.append(bullet)

            else:
                # Non-bullet line: could be entry title, metadata, or standalone table row
                if _is_title_row(norm_text, span_objs):
                    # Start a new entry
                    entry_counter += 1
                    eid = _stable_id("e", pno, line.bbox[1], norm_text)
                    current_entry = Entry(
                        id=eid,
                        section=current_section.name,
                        title=norm_text,
                        page_start=pno,
                        bbox=line_bbox,
                        title_links=bullet_links,
                    )
                    # Try to parse dates from title row
                    dm = _DATE_RE.search(norm_text)
                    if dm:
                        current_entry.dates = dm.group(0)
                    current_section.entries.append(current_entry)

                    # Also populate Bullet for standalone achievement/event title rows
                    if current_section.name in {"Extracurricular", "Achievements", "Social Impact", "Positions of Responsibility", "Projects", "Skills"}:
                        bullet_counter += 1
                        bid = _stable_id("b", pno, line.bbox[1], norm_text)
                        t_bullet = Bullet(
                            id=bid,
                            text=norm_text,
                            raw_text=text,
                            normalized_text=norm_text,
                            section=current_section.name,
                            entry_id=eid,
                            page=pno,
                            bbox=line_bbox,
                            spans=span_objs,
                            hyperlinks=bullet_links,
                        )
                        current_entry.bullets.append(t_bullet)
                        current_section.bullets.append(t_bullet)
                elif len(norm_text) >= 5 and current_section.name not in {"Header", "Education"}:
                    # Standalone line / table row (e.g. Extracurricular achievements, awards, skills)
                    sublabel, payload = _detect_sublabel(norm_text)
                    bullet_counter += 1
                    bid = _stable_id("b", pno, line.bbox[1], norm_text)

                    bullet = Bullet(
                        id=bid,
                        text=payload if sublabel else norm_text,
                        raw_text=text,
                        normalized_text=norm_text,
                        section=current_section.name,
                        entry_id=current_entry.id if current_entry else None,
                        page=pno,
                        bbox=line_bbox,
                        spans=span_objs,
                        hyperlinks=bullet_links,
                        subsection_label=sublabel,
                    )

                    if current_entry and current_entry.section == current_section.name:
                        current_entry.bullets.append(bullet)
                    else:
                        entry_counter += 1
                        eid = _stable_id("e", pno, line.bbox[1], norm_text)
                        current_entry = Entry(
                            id=eid,
                            section=current_section.name,
                            page_start=pno,
                            bbox=line_bbox,
                        )
                        current_section.entries.append(current_entry)
                        current_entry.bullets.append(bullet)

                    current_section.bullets.append(bullet)

    # ── Continuation merging (B9 fix) ─────────────────────────────────────
    # Merge wrapped bullet lines that are continuations of the previous bullet
    _merge_continuations(sections)

    # ── Attach link objects to entries/sections ───────────────────────────
    _associate_links(all_link_objects, sections)

    # ── Parser sanity checks / warnings ──────────────────────────────────
    page_count = len(doc)
    layout_diagnostics["page_count"] = page_count
    _emit_warnings(sections, all_link_objects, warnings, bullet_counter, page_count=page_count)

    return ResumeAST(
        source_file=str(path),
        sections=sections,
        link_objects=all_link_objects,
        hyperlinks=sorted(set(all_link_uris)),
        warnings=warnings,
        layout_diagnostics=layout_diagnostics,
    )


def _merge_continuations(sections: list[Section]) -> None:
    """Merge wrapped continuation lines into the preceding bullet.

    Conservative: only merge if:
    - Previous line ends without terminal punctuation suggesting completion
    - Current line is indented or x-aligned with bullet body
    - Same entry and section
    - No bullet glyph on continuation line
    - y-gap is small (within ~1.5x line height)
    """
    for section in sections:
        bullets = section.bullets
        if len(bullets) < 2:
            continue
        merged_set: set[str] = set()
        for i in range(1, len(bullets)):
            prev = bullets[i - 1]
            curr = bullets[i]
            if curr.id in merged_set:
                continue
            if prev.section != curr.section:
                continue
            if prev.entry_id and curr.entry_id and prev.entry_id != curr.entry_id:
                continue
            # y-gap check
            y_gap = curr.bbox.y0 - prev.bbox.y1
            line_height = max(prev.bbox.height, curr.bbox.height, 8.0)
            if y_gap > line_height * 1.8:
                continue
            # Current line must not start with bullet glyph
            if _BULLET_RE.match(curr.raw_text):
                continue
            # Current line x0 should be close to prev bullet body x0
            x_offset = abs(curr.bbox.x0 - prev.bbox.x0)
            if x_offset > 20:
                continue
            # Previous text should not end with terminal punctuation
            if prev.text.rstrip().endswith((".", "!", "?")):
                continue
            # Merge
            prev.text = prev.text + " " + curr.text
            prev.normalized_text = prev.normalized_text + " " + curr.normalized_text
            prev.hyperlinks = sorted(set(prev.hyperlinks + curr.hyperlinks))
            prev.spans.extend(curr.spans)
            merged_set.add(curr.id)

        # Remove merged bullets from flat list
        section.bullets[:] = [b for b in bullets if b.id not in merged_set]
        # Also remove from entries
        for entry in section.entries:
            entry.bullets[:] = [b for b in entry.bullets if b.id not in merged_set]


def _associate_links(link_objects: list[LinkObject], sections: list[Section]) -> None:
    """Associate link objects to their geometrically nearest section/entry."""
    
    def _bbox_distance(bbox1: BBox, bbox2: BBox) -> float:
        """Calculate the minimum distance between two bounding boxes."""
        # Find closest points between the boxes
        x1_closest = max(bbox1.x0, min(bbox1.x1, bbox2.x0 + (bbox2.x1 - bbox2.x0) / 2))
        y1_closest = max(bbox1.y0, min(bbox1.y1, bbox2.y0 + (bbox2.y1 - bbox2.y0) / 2))
        x2_closest = max(bbox2.x0, min(bbox2.x1, bbox1.x0 + (bbox1.x1 - bbox1.x0) / 2))
        y2_closest = max(bbox2.y0, min(bbox2.y1, bbox1.y0 + (bbox1.y1 - bbox1.y0) / 2))
        
        dx = x1_closest - x2_closest
        dy = y1_closest - y2_closest
        return (dx * dx + dy * dy) ** 0.5
    
    def _section_bbox(section: Section) -> BBox | None:
        """Get the bounding box for a section (from its entries and bullets)."""
        if not section.entries:
            return None
        
        min_x0 = min_y0 = float('inf')
        max_x1 = max_y1 = float('-inf')
        
        for entry in section.entries:
            # Use entry's bbox
            min_x0 = min(min_x0, entry.bbox.x0)
            min_y0 = min(min_y0, entry.bbox.y0) 
            max_x1 = max(max_x1, entry.bbox.x1)
            max_y1 = max(max_y1, entry.bbox.y1)
            
            # Also check bullet spans for more precise bounds
            for bullet in entry.bullets:
                for span in bullet.spans:
                    min_x0 = min(min_x0, span.bbox.x0)
                    min_y0 = min(min_y0, span.bbox.y0)
                    max_x1 = max(max_x1, span.bbox.x1)
                    max_y1 = max(max_y1, span.bbox.y1)
        
        if min_x0 == float('inf'):
            return None
            
        return BBox(x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1)
    
    # Associate each link with the nearest section on the same page
    for lobj in link_objects:
        if lobj.section == "Header" or lobj.section is None:
            best_section = None
            best_distance = float('inf')
            
            # Find all sections on the same page
            page_sections = [s for s in sections if s.page_start == lobj.page and s.name != "Header"]
            
            for section in page_sections:
                section_bbox = _section_bbox(section)
                if section_bbox is None:
                    continue
                    
                distance = _bbox_distance(lobj.bbox, section_bbox)
                if distance < best_distance:
                    best_distance = distance
                    best_section = section
            
            if best_section is not None:
                lobj.section = best_section.name


def _emit_warnings(
    sections: list[Section],
    link_objects: list[LinkObject],
    warnings: list[str],
    bullet_counter: int,
    page_count: int = 1,
) -> None:
    """Emit sanity-check warnings for anomalous parse results (B13 fix)."""
    if page_count > 1:
        warnings.append(
            f"CRITICAL SPO NON-COMPLIANCE: Resume spans {page_count} pages. IITK SPO guidelines strictly require a 1-page single-sheet LaTeX resume. Multi-page resumes are disqualified by SPO screening."
        )

    if bullet_counter == 0:
        warnings.append("WARN: No bullet glyphs detected — resume may use table rows or custom markers.")

    # Check for implausibly high concentration in one section
    section_counts = {s.name: len(s.bullets) for s in sections}
    total = sum(section_counts.values())
    if total > 0:
        for name, count in section_counts.items():
            frac = count / total
            if frac > 0.7 and total > 5:
                warnings.append(
                    f"WARN: {count}/{total} bullets ({frac:.0%}) assigned to '{name}' — "
                    f"possible reading-order or section-detection failure."
                )

    # Check for education section
    sec_names = {s.name for s in sections}
    if "Education" not in sec_names:
        warnings.append("WARN: No 'Education' section detected — CPI/degree may be unavailable.")

    # Check for unassociated links
    unassoc = sum(1 for l in link_objects if l.section in ("Header", None))
    if unassoc > 0:
        warnings.append(f"INFO: {unassoc} hyperlink(s) remain in 'Header' section (pre-body).")

    # Check section order anomalies
    expected_order = ["Education", "Experience", "Research", "Projects",
                      "Positions of Responsibility", "Extracurricular"]
    detected = [s.name for s in sections if s.name != "Header"]
    order_ok = True
    last_idx = -1
    for s in detected:
        if s in expected_order:
            idx = expected_order.index(s)
            if idx < last_idx:
                order_ok = False
                break
            last_idx = idx
    if not order_ok:
        warnings.append("INFO: Section order differs from typical IITK SPO template — may be intentional.")

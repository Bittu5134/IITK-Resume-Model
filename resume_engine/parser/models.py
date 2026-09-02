"""Data models for LaTeX-PDF spatial parsing AST."""
from __future__ import annotations

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class LinkObject(BaseModel):
    """Hyperlink embedded within a PDF."""
    uri: str
    link_type: str = "web"  # github, linkedin, codeforces, leetcode, email, web, portfolio
    page: int = 1
    section: Optional[str] = None
    associated_text: str = ""
    bbox: Optional[List[float]] = None


class Bullet(BaseModel):
    """A single bullet point within a section or entry."""
    bullet_id: str
    text: str
    raw_text: str = ""
    page: int = 1
    bbox: Optional[List[float]] = None
    has_subbullets: bool = False
    subbullets: List[str] = Field(default_factory=list)


class Entry(BaseModel):
    """A structured entry (e.g. project, job, education item) containing bullets."""
    entry_id: str
    title: str = ""
    subtitle: str = ""
    organization: str = ""
    location: str = ""
    dates: str = ""
    page_start: int = 1
    bullets: List[Bullet] = Field(default_factory=list)


class Section(BaseModel):
    """A high-level resume section (e.g. Education, Experience, Projects)."""
    name: str
    page_start: int = 1
    page_end: int = 1
    entries: List[Entry] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)
    raw_text: str = ""


class LayoutDiagnostics(BaseModel):
    """Diagnostics about the PDF structure and SPO compliance."""
    page_count: int = 1
    is_single_page_compliant: bool = True
    has_multicolumn_layout: bool = True
    estimated_word_count: int = 0
    font_count: int = 0
    link_count: int = 0


class ResumeAST(BaseModel):
    """Abstract Syntax Tree representing parsed resume structure."""
    source_file: str
    parser_version: str = "2.0.0-spatial"
    sections: List[Section] = Field(default_factory=list)
    link_objects: List[LinkObject] = Field(default_factory=list)
    layout_diagnostics: LayoutDiagnostics = Field(default_factory=LayoutDiagnostics)
    warnings: List[str] = Field(default_factory=list)
    raw_text: str = ""

    def get_section(self, name_pattern: str) -> Optional[Section]:
        pat = name_pattern.lower()
        for s in self.sections:
            if pat in s.name.lower():
                return s
        return None

    def section_by_name(self, name_pattern: str) -> Optional[Section]:
        return self.get_section(name_pattern)

    def all_bullets(self) -> List[Bullet]:
        bullets = []
        for s in self.sections:
            for b in s.bullets:
                bullets.append(b)
            for e in s.entries:
                for b in e.bullets:
                    bullets.append(b)
        return bullets

    def bullets(self) -> List[Bullet]:
        return self.all_bullets()

"""Resume AST models — Stage 1 v2.
Hierarchy: ResumeDocument -> Section -> Entry -> Line/Bullet -> Span
Every object carries page + bbox provenance and a stable hash-derived ID.
"""
from __future__ import annotations
from typing import Literal
from enum import Enum
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Types of evidence that can be extracted from claims."""
    SOFTWARE_ENGINEERING = "software_engineering"
    PROGRAMMING = "programming"
    ML_ENGINEERING = "ml_engineering"
    TECHNICAL_RESEARCH = "technical_research"
    RESEARCH = "research"
    MATHEMATICAL = "mathematical"
    STATISTICAL = "statistical"
    QUANT_FINANCE = "quant_finance"
    BUSINESS_ANALYSIS = "business_analysis"
    BUSINESS_IMPACT = "business_impact"
    TECHNICAL_IMPACT = "technical_impact"
    RESEARCH_IMPACT = "research_impact"
    ORGANIZATIONAL_IMPACT = "organizational_impact"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"
    TEAMWORK = "teamwork"
    OPEN_SOURCE = "open_source"
    COMPETITIVE_PROGRAMMING = "competitive_programming"
    CORE_ENGINEERING = "core_engineering"
    COURSEWORK = "coursework"
    PUBLICATION = "publication"


class ProjectType(str, Enum):
    """Types of projects that can be classified."""
    SOFTWARE_PROJECT = "software_project"
    ML_PROJECT = "ml_project"
    RESEARCH_PROJECT = "research_project"
    CONSULTING_PROJECT = "consulting_project"
    QUANT_PROJECT = "quant_project"
    CORE_PROJECT = "core_project"
    GENERAL_PROJECT = "general_project"


class ImpactType(str, Enum):
    """Types of impact evidence."""
    TECHNICAL_IMPACT = "technical_impact"
    BUSINESS_IMPACT = "business_impact"
    RESEARCH_IMPACT = "research_impact"
    ORGANIZATIONAL_IMPACT = "organizational_impact"


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


class LinkObject(BaseModel):
    """First-class hyperlink with provenance."""
    uri: str
    page: int
    bbox: BBox
    link_type: Literal["email", "github_profile", "github_repo", "linkedin",
                       "drive", "web", "other"] = "other"
    associated_text: str = ""
    entry_id: str | None = None
    section: str | None = None


class Span(BaseModel):
    text: str
    bbox: BBox
    page: int
    size: float | None = None
    bold: bool = False
    italic: bool = False
    uri: str | None = None


class Bullet(BaseModel):
    """A single bullet / logical line within an entry."""
    id: str                          # stable: "b{page}_{rounded_y}_{hash4}"
    text: str                        # cleaned text (bullet glyph stripped)
    raw_text: str                    # original text as extracted
    normalized_text: str             # unicode-normalized
    section: str
    entry_id: str | None = None
    page: int
    bbox: BBox
    spans: list[Span] = Field(default_factory=list)
    hyperlinks: list[str] = Field(default_factory=list)
    subsection_label: str | None = None   # objective/approach/result/leadership/…
    is_continuation: bool = False


class Entry(BaseModel):
    """A grouped resume entry: one work/project/research/PoR item."""
    id: str                          # stable: "e{page}_{rounded_y}_{hash4}"
    section: str
    title: str = ""                  # role/project/company title row text
    organization: str = ""
    dates: str = ""
    mentor: str = ""
    location: str = ""
    page_start: int
    bbox: BBox
    bullets: list[Bullet] = Field(default_factory=list)
    title_links: list[str] = Field(default_factory=list)


class Section(BaseModel):
    name: str                        # canonical section name
    raw_heading: str = ""            # original heading text
    page_start: int
    entries: list[Entry] = Field(default_factory=list)
    # Flat bullets kept for backward-compat; identical to entries[*].bullets
    bullets: list[Bullet] = Field(default_factory=list)
    raw_lines: list[str] = Field(default_factory=list)
    layout_mode: str = "unknown"     # "single-column" | "table" | "multi-column" | "mixed"


class ResumeAST(BaseModel):
    source_file: str
    parser_version: str = "stage1-v2"
    sections: list[Section] = Field(default_factory=list)
    # Structured link objects (first-class)
    link_objects: list[LinkObject] = Field(default_factory=list)
    # Legacy convenience list of URIs
    hyperlinks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    layout_diagnostics: dict = Field(default_factory=dict)

    def bullets(self) -> list[Bullet]:
        """Flat list of all bullets across all sections (backward-compat)."""
        return [b for s in self.sections for b in s.bullets]

    def all_entries(self) -> list[Entry]:
        return [e for s in self.sections for e in s.entries]

    def section_by_name(self, name: str) -> Section | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

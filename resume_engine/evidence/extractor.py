"""Semantic Evidence & IITK NLP Extractor.

Extracts:
1. Academic metrics (CPI, JEE ranks, Board %, KVPY, IISER, NTSE, Olympiads).
2. IITK campus entities (SURGE, AnC Council, Gymkhana, PoRs, Halls, Clubs, Takneek).
3. Technical & domain skills (including C++, Open Source, Linux, Git, etc.).
4. Action verb strength and quantifiable impact detection per bullet.
5. Sub-header bypass filter for layout terms (< 4 words or structural labels).
"""
from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional, Set

from resume_engine.parser.models import ResumeAST, Section, Entry, Bullet
from resume_engine.evidence.models import (
    EvidenceBundle,
    AcademicMetric,
    CampusEntity,
    AtomicClaim,
    BulletDiagnostic,
)

# IITK Jargon & Campus Entity Ontology
IITK_ENTITIES_MAP = {
    # Councils & Administration
    "AnC Council": "council",
    "Academics and Career Council": "council",
    "Academics & Career Council": "council",
    "Career Development Wing": "council",
    "CDW": "council",
    "Science and Technology Council": "council",
    "SnT Council": "council",
    "Media and Culture Council": "council",
    "MnC Council": "council",
    "Games and Sports Council": "council",
    "GnS Council": "council",
    "Students' Gymkhana": "council",
    "Students Gymkhana": "council",
    "Gymkhana": "council",
    "SPO": "council",
    "Student Placement Office": "council",
    "Senate": "council",
    "SSAC": "council",
    
    # Clubs & Cells
    "Programming Club": "club",
    "PClub": "club",
    "P-Club": "club",
    "Electronics Club": "club",
    "E-Club": "club",
    "Robotics Club": "club",
    "Aeromodelling Club": "club",
    "Astronomy Club": "club",
    "Finance and Analytics Club": "club",
    "Consulting Club": "club",
    "Debating Society": "club",
    "DebSoc": "club",
    "Quiz Club": "club",
    "Literary Society": "club",
    "Dramatics Club": "club",
    "Dance Club": "club",
    "Music Club": "club",
    "Fine Arts Club": "club",
    "E-Cell": "club",
    "Entrepreneurship Cell": "club",
    "NSS": "club",
    "NSS, IIT Kanpur": "club",
    "BCS IITK": "club",
    "Brain and Cognitive Society": "club",
    "Association for Computing Activities": "club",
    "ACA": "club",

    # Fests & Major Events
    "Techkriti": "fest",
    "Antaragni": "fest",
    "Udghosh": "fest",
    "E-Summit": "fest",
    "ESummit": "fest",
    "Galaxy": "fest",
    "Takneek": "fest",
    "Takneek'23": "fest",
    "Spectrum": "fest",
    "Inferno": "fest",
    "Inter-IIT": "fest",
    "Inter-IIT Tech Meet": "fest",
    "Inter-IIT Cult Meet": "fest",
    "Inter-IIT Sports Meet": "fest",

    # Research & Academics / Open Source / Olympiads
    "SURGE": "research",
    "SURGE, IIT Kanpur": "research",
    "SURGE Internship": "research",
    "Summer Undergraduate Research Grant for Excellence": "research",
    "Undergraduate Project": "research",
    "UGP": "research",
    "B.Tech Project": "research",
    "BTP": "research",
    "M.Tech Project": "research",
    "MTP": "research",
    "TenSixty Bio": "research",
    "Stanford University": "research",
    "Linux Foundation": "open_source",
    "OpenPrinting": "open_source",
    "Zephyr Project": "open_source",
    "Academic Excellence Award": "award",
    "INMO": "award",
    "RMO": "award",
    "IOQM": "award",
    "INPhO": "award",
    "INChO": "award",
    "ISI": "award",
    "KVPY": "award",

    # PoR Titles
    "General Secretary": "por_role",
    "Overall Coordinator": "por_role",
    "Manager": "por_role",
    "Head": "por_role",
    "Coordinator": "por_role",
    "Secretary": "por_role",
    "Events Organizer": "por_role",
    "Organizer": "por_role",
    "Junior Executive": "por_role",
    "Senior Executive": "por_role",
    "Academic Mentor": "por_role",
    "Student Guide": "por_role",
}

# Skill Lexicon
SKILL_TAXONOMY = {
    # Software & Tech
    "python": "software", "c++": "software", "cpp": "software", "c": "software",
    "java": "software", "rust": "software", "golang": "software", "go": "software",
    "javascript": "software", "typescript": "software", "react": "software", "node.js": "software",
    "nodejs": "software", "express": "software", "django": "software", "flask": "software", "fastapi": "software",
    "sql": "software", "postgresql": "software", "mysql": "software", "mongodb": "software",
    "redis": "software", "docker": "software", "kubernetes": "software", "aws": "software",
    "git": "software", "open source": "software", "open-source": "software", "linux": "software", "bash": "software",
    "graphql": "software", "rest api": "software", "api": "software",
    "data structures": "software", "algorithms": "software", "dsa": "software",
    "system design": "software", "oop": "software", "operating systems": "software",
    "computer networks": "software", "dbms": "software", "mips": "software", "assembly": "software",
    "dijkstra": "software", "huffman": "software", "sorting": "software", "insertion sort": "software", "graphs": "software",
    "bfs": "software", "dfs": "software", "bellman-ford": "software", "floyd-warshall": "software",
    "prims": "software", "kruskal": "software", "image processing": "software", "opencv": "software",
    "interpolation": "software", "convolution": "software", "edge detection": "software", "canny": "software",

    # AI / ML / Quant
    "machine learning": "ai_quant", "deep learning": "ai_quant", "neural networks": "ai_quant",
    "pytorch": "ai_quant", "tensorflow": "ai_quant", "keras": "ai_quant", "scikit-learn": "ai_quant", "sklearn": "ai_quant",
    "computer vision": "ai_quant", "nlp": "ai_quant", "transformers": "ai_quant", "gan": "ai_quant",
    "cnn": "ai_quant", "rnn": "ai_quant", "lstm": "ai_quant", "bert": "ai_quant", "llm": "ai_quant",
    "ann": "ai_quant", "backpropagation": "ai_quant", "artificial neural network": "ai_quant",
    "cyclegan": "ai_quant", "probability": "quant", "statistics": "quant", "stochastic calculus": "quant",
    "pairs trading": "quant", "backtesting": "quant", "adf test": "quant", "blueshift": "quant", "co-integration": "quant",
    "linear algebra": "quant", "discrete mathematics": "quant", "time series": "quant", "monte carlo": "quant",
    "black scholes": "quant", "backtesting": "quant", "numpy": "quant", "pandas": "quant",
    "scipy": "quant", "r": "quant", "rshiny": "quant", "matlab": "quant",

    # Core Engineering
    "autocad": "core", "solidworks": "core", "catia": "core", "ansys": "core",
    "cfd": "core", "fem": "core", "fea": "core", "matlab/simulink": "core",
    "simulink": "core", "labview": "core", "verilog": "core", "vhdl": "core",
    "embedded c": "core", "microcontroller": "core", "pcb design": "core",
    "altium": "core", "fpga": "core", "arduino": "core", "raspberry pi": "core",
    "ros": "core", "robot operating system": "core",

    # Consulting & Analytics
    "tableau": "analyst", "power bi": "analyst", "powerbi": "analyst", "excel": "analyst",
    "market research": "consulting", "financial modeling": "consulting", "guesstimates": "consulting",
    "case study": "consulting", "cost optimization": "consulting", "strategy": "consulting",
    "stakeholder management": "consulting", "kpi tracking": "consulting", "business development": "consulting",

    # Product Management
    "product roadmap": "product", "wireframing": "product", "figma": "product",
    "a/b testing": "product", "user research": "product", "prd": "product",
    "product analytics": "product", "agile": "product", "scrum": "product",
}

STRONG_VERBS = {
    "architected", "spearheaded", "engineered", "designed", "developed", "built", "implemented",
    "optimized", "accelerated", "orchestrated", "automated", "formulated", "deployed", "scaled",
    "streamlined", "modeled", "devised", "pioneered", "championed", "directed", "managed",
    "founded", "overhauled", "boosted", "maximized", "curated", "published", "secured", "won",
    "trained", "authored", "created", "validated", "digitalized", "achieved", "rated", "qualified",
}

WEAK_VERBS = {
    "worked on", "worked with", "assisted in", "assisted with", "helped", "helped with",
    "responsible for", "participated in", "involved in", "tried to", "handled", "looked after",
    "contributed to", "supported", "tasked with",
}

# Known Sub-Headers & Structural labels to bypass from action-verb diagnostics
STRUCTURAL_SUBHEADERS = {
    "objective", "approach", "impact", "initiatives", "leadership", "overview",
    "background", "results", "technologies", "key courses", "tools", "skills",
    "awards", "details", "summary", "experience", "projects", "timeline", "dates",
    "programming languages", "libraries", "relevant courses", "sports", "mentoring",
    "project", "mentor", "national", "international", "debating", "music",
    "london", "delhi", "mumbai", "chennai", "kolkata", "cultural", "technical",
}


def _has_substantive_skill(text: str, skills: set[str]) -> bool:
    """Check if text contains a real skill match (word-boundary), not a substring accident."""
    text_lower = text.lower()
    for s in skills:
        if len(s) <= 2:
            if re.search(r"\b" + re.escape(s) + r"\b", text_lower):
                return True
        else:
            if s in text_lower:
                return True
    return False


class EvidenceExtractor:
    """Extracts semantic evidence, campus entities, academic marks, and line issues."""

    def extract(self, ast: ResumeAST) -> EvidenceBundle:
        academic_metrics: List[AcademicMetric] = []
        cpi_val: Optional[float] = None
        recognized_entities: Set[str] = set()
        campus_entities: List[CampusEntity] = []
        matched_skills: Set[str] = set()
        claims: List[AtomicClaim] = []
        bullet_diagnostics: List[BulletDiagnostic] = []

        raw_text = ast.raw_text

        # 1. CPI detection
        cpi_match = re.search(r"(\b[0-9]\.[0-9]{1,2})\s*/\s*10(?:\.0)?", raw_text, re.I)
        if not cpi_match:
            cpi_match = re.search(r"(?:CPI|CGPA|GPA)[\s:]*([0-9]\.[0-9]{1,2})", raw_text, re.I)

        if cpi_match:
            try:
                cpi_val = float(cpi_match.group(1))
                academic_metrics.append(
                    AcademicMetric(
                        name="Undergraduate CPI",
                        value=f"{cpi_val:.2f}/10.0",
                        numeric_value=cpi_val,
                        scale=10.0,
                    )
                )
            except ValueError:
                pass

        # Class XII / Class X percentages
        xii_match = re.search(r"(?:Class\s*(?:XII|12th?)|CBSE\s*(?:\(XII\)|XII)|ISC)[^\n%]*?([0-9]{2}(?:\.[0-9]{1,2})?)\s*%", raw_text, re.I)
        if xii_match:
            academic_metrics.append(
                AcademicMetric(name="Class XII Percentage", value=f"{xii_match.group(1)}%")
            )

        x_match = re.search(r"(?:Class\s*(?:X|10th?)|CBSE\s*(?:\(X\)|X)|ICSE\s*(?:\(X\)|X)?)[^\n%]*?([0-9]{2}(?:\.[0-9]{1,2})?)\s*%", raw_text, re.I)
        if x_match:
            academic_metrics.append(
                AcademicMetric(name="Class X Percentage", value=f"{x_match.group(1)}%")
            )

        # JEE Advanced Rank
        jee_adv = re.search(r"(?:(?:All\s*India\s*)?(?:Rank|AIR)\s*([0-9]{1,5})\s*in\s*JEE\s*(?:Advanced|Adv\.?)|JEE\s*(?:Advanced|Adv\.?)[^\n\d]*?(?:Rank|AIR)\s*([0-9]{1,5}))", raw_text, re.I)
        if jee_adv:
            rank_val = jee_adv.group(1) or jee_adv.group(2)
            if rank_val:
                academic_metrics.append(
                    AcademicMetric(name="JEE Advanced Rank", value=f"AIR {rank_val}")
                )

        # JEE Mains Rank
        jee_main = re.search(r"(?:(?:All\s*India\s*)?(?:Rank|AIR)\s*([0-9]{1,5})\s*in\s*(?:the\s*)?JEE\s*(?:Main|Mains)|JEE\s*(?:Main|Mains)[^\n\d]*?(?:Rank|AIR)\s*([0-9]{1,5}))", raw_text, re.I)
        if jee_main:
            rank_val = jee_main.group(1) or jee_main.group(2)
            if rank_val:
                academic_metrics.append(
                    AcademicMetric(name="JEE Mains Rank", value=f"AIR {rank_val}")
                )

        # KVPY Rank
        kvpy_match = re.search(r"(?:(?:All\s*India\s*)?(?:Rank|AIR)\s*([0-9]{1,4})[^\n\d]*?in\s*KVPY|KVPY[^\n\d]*?(?:Rank|AIR)\s*([0-9]{1,4}))", raw_text, re.I)
        if kvpy_match:
            rank_val = kvpy_match.group(1) or kvpy_match.group(2)
            if rank_val:
                academic_metrics.append(
                    AcademicMetric(name="KVPY National Rank", value=f"AIR {rank_val}")
                )

        # IISER Rank
        iiser_match = re.search(r"(?:(?:All\s*India\s*)?(?:Rank|AIR)\s*([0-9]{1,4})\s*in\s*IISER|IISER[^\n\d]*?(?:Rank|AIR)\s*([0-9]{1,4}))", raw_text, re.I)
        if iiser_match:
            rank_val = iiser_match.group(1) or iiser_match.group(2)
            if rank_val:
                academic_metrics.append(
                    AcademicMetric(name="IISER Aptitude Rank", value=f"AIR {rank_val}")
                )

        # 2. Extract IITK Entities across text
        for ent_name, cat in IITK_ENTITIES_MAP.items():
            if re.search(r"\b" + re.escape(ent_name) + r"\b", raw_text, re.I):
                recognized_entities.add(ent_name)
                campus_entities.append(CampusEntity(name=ent_name, category=cat))

        # 3. Extract Skills
        for skill_term, _ in SKILL_TAXONOMY.items():
            if "+" in skill_term:
                pat = re.escape(skill_term)
            else:
                pat = r"\b" + re.escape(skill_term) + r"\b"
            if re.search(pat, raw_text, re.I):
                matched_skills.add(skill_term)

        # 4. Sub-Header Bypass Filter & Bullet Diagnostics
        claim_counter = 1
        for section in ast.sections:
            all_sec_bullets: List[Tuple[Optional[str], Bullet]] = []
            for b in section.bullets:
                all_sec_bullets.append((None, b))
            for entry in section.entries:
                for b in entry.bullets:
                    all_sec_bullets.append((entry.entry_id, b))

            for entry_id, bullet in all_sec_bullets:
                b_text = bullet.text.strip()
                if not b_text:
                    continue

                words = b_text.split()
                clean_single = re.sub(r"[^a-zA-Z\s]", "", b_text).strip().lower()

                # Robust Sub-Header & Fragment Bypass Rules
                is_sub_header = (
                    (len(words) < 4 and not _has_substantive_skill(b_text, matched_skills))
                    or clean_single in STRUCTURAL_SUBHEADERS
                    or bool(re.match(r"^[\(\[]?(?:19|20)\d{2}(?:\s*[-–]\s*(?:19|20)\d{2}|Present)?[\)\]]?$", b_text.strip()))
                    or (b_text.rstrip().endswith("-") and len(words) == 1)
                    or (len(words) <= 3 and bool(re.search(r"['']?\d{2,4}", b_text)))
                )

                if is_sub_header:
                    continue

                claim_id = f"c{claim_counter:04d}"
                claim_counter += 1

                first_words = words[:3]
                start_phrase = " ".join(first_words).lower()
                action_verb = first_words[0].lower().rstrip(":,.") if first_words else None

                verb_strength = "neutral"
                issues: List[str] = []
                suggestions: List[str] = []
                severity = "info"

                # Check for weak verbs
                for wv in WEAK_VERBS:
                    if start_phrase.startswith(wv) or b_text.lower().startswith(wv):
                        verb_strength = "weak"
                        severity = "warning"
                        issues.append(f"Weak action verb detected ('{wv}'). Lacks authoritative leadership signal.")
                        suggestions.append(
                            f"Replace '{wv}' with a strong active verb like 'Architected', 'Spearheaded', 'Optimized', or 'Engineered'."
                        )
                        break

                if verb_strength != "weak":
                    for sv in STRONG_VERBS:
                        if action_verb == sv or b_text.lower().startswith(sv):
                            verb_strength = "strong"
                            break

                # Quantifiable metric detection
                metrics_found = re.findall(
                    r"(\d+(?:\.\d+)?%|\b(?:INR|Rs\.?|\$)\s*\d+[\d,]*(?:\s*(?:lakh|cr|k|m))?|\b\d+(?:\.\d+)?x\b|\b\d{2,}\+?\s*(?:users|clients|students|teams|freshers|participants|requests|lines|ms|fps|gb|mb|talks|workshops|colleges|companies|hours|weeks|months)\b)",
                    b_text,
                    re.I,
                )
                has_metric = len(metrics_found) > 0

                if not has_metric and section.name.lower() in ["projects", "key projects", "experience", "work experience", "positions of responsibility"]:
                    if severity == "info":
                        severity = "warning"
                    issues.append("Missing quantifiable impact metric (e.g. latency reduced by X%, handled Y users, or Z budget).")
                    suggestions.append(
                        "Apply XYZ Formula: 'Accomplished [X] as measured by [Y] (e.g., +25% speedup, 500+ users), by doing [Z]'."
                    )

                word_count = len(words)
                if word_count > 38:
                    severity = "warning"
                    issues.append(f"Bullet is overly long ({word_count} words). May exceed single-line SPO LaTeX margin.")
                    suggestions.append("Trim filler words and split into two focused, high-impact bullet points.")

                b_skills = [s for s in matched_skills if (re.escape(s) in b_text if "+" in s else re.search(r"\b" + re.escape(s) + r"\b", b_text, re.I))]
                b_entities = [e for e in recognized_entities if re.search(r"\b" + re.escape(e) + r"\b", b_text, re.I)]

                claim_obj = AtomicClaim(
                    claim_id=claim_id,
                    bullet_id=bullet.bullet_id,
                    section=section.name,
                    entry_id=entry_id,
                    page=bullet.page,
                    text_snippet=b_text[:120],
                    action_verb=action_verb,
                    verb_strength=verb_strength,
                    metrics_detected=metrics_found,
                    has_quantifiable_impact=has_metric,
                    skills_matched=b_skills,
                    entities_matched=b_entities,
                )
                claims.append(claim_obj)

                diag_obj = BulletDiagnostic(
                    claim_id=claim_id,
                    bullet_id=bullet.bullet_id,
                    section=section.name,
                    entry_id=entry_id,
                    page=bullet.page,
                    text_snippet=b_text,
                    issues=issues,
                    suggestions=suggestions,
                    severity=severity,
                )
                bullet_diagnostics.append(diag_obj)

        return EvidenceBundle(
            academic_metrics=academic_metrics,
            cpi=cpi_val,
            all_skills=sorted(list(matched_skills)),
            all_entities=sorted(list(recognized_entities)),
            campus_entities=campus_entities,
            claims=claims,
            bullet_diagnostics=bullet_diagnostics,
        )

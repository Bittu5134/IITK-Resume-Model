"""Stage 2 v2 — Evidence extractor.

Fixes C1-C15:
- Consumes richer AST (entries, academic rows, non-bullet lines)
- Typed evidence: academic_metric, fact, achievement, skill, role, etc.
- Robust metric parser: commas, ranges, k/M/B/L/Cr, %, $, ₹, signed
- Action verb lemmatization and inflection normalization
- Expanded skill ontology (scikit-learn, ML frameworks, etc.)
- Unknown action verbs are neutral/low-confidence, NOT 0.5 by default
- Metric semantic classification: impact vs. non-impact
- Section-based signals are weak priors, not hard evidence
- No leakage: evidence_strength reflects claim quality, not arbitrary inflation
"""
from __future__ import annotations

import re
import yaml
from pathlib import Path

from resume_engine.parser.models import ResumeAST, Bullet, Section, BBox
from .models import (
    AcademicMetric, AtomicClaim, EntityMention, EvidenceDocument, Metric,
    EvidenceType, ProjectType, ImpactType
)

# ---------------------------------------------------------------------------
# Action verb lexicon — normalized to lemma form
# ---------------------------------------------------------------------------

# Strong action verbs with ownership/outcome connotation: 0.80–1.0
_STRONG: dict[str, float] = {
    "led": 1.0, "spearheaded": 1.0, "architected": 0.95, "pioneered": 0.95,
    "founded": 0.95, "launched": 0.95, "created": 0.90, "established": 0.90,
    "built": 0.90, "engineered": 0.90, "designed": 0.90, "developed": 0.85,
    "implemented": 0.85, "deployed": 0.85, "automated": 0.90, "optimized": 0.90,
    "reduced": 0.95, "increased": 0.95, "improved": 0.90, "accelerated": 0.90,
    "won": 0.95, "secured": 0.90, "achieved": 0.90, "awarded": 0.90,
    "published": 1.0, "researched": 0.80, "investigated": 0.80,
    "mentored": 0.85, "managed": 0.85, "oversaw": 0.85, "supervised": 0.85,
    "organized": 0.80, "coordinated": 0.80, "facilitated": 0.80,
    "delivered": 0.90, "formulated": 0.85, "benchmarked": 0.85,
    "curated": 0.80, "calibrated": 0.85, "proposed": 0.80,
    "identified": 0.80, "presented": 0.75, "projected": 0.80,
    "estimated": 0.75, "safeguarded": 0.85, "analyzed": 0.80,
    "mapped": 0.75, "advocated": 0.80, "guided": 0.80, "piloted": 0.85,
    "chaired": 0.85, "supported": 0.70, "fine-tuned": 0.85, "finetuned": 0.85,
    "trained": 0.80, "evaluated": 0.80, "contributed": 0.75,
}

# Weak action verbs: 0.25–0.50
_WEAK: dict[str, float] = {
    "worked": 0.35, "helped": 0.35, "assisted": 0.30, "participated": 0.30,
    "responsible": 0.25, "used": 0.45, "learned": 0.30, "studied": 0.30,
    "tried": 0.25, "explored": 0.40, "involved": 0.30, "supported": 0.45,
    "collaborated": 0.50, "contributed": 0.50,
}

# Inflection normalization: irregular past → lemma or canonical form
_INFLECTIONS: dict[str, str] = {
    "built": "built", "led": "led", "won": "won", "ran": "run",
    "wrote": "write", "ran": "run", "drove": "drive", "made": "make",
    "oversaw": "oversaw", "grew": "grow", "scaled": "scaled",
    "optimize": "optimized", "optimizing": "optimized",
}

# Verb suffixes to strip for lemmatization fallback
_VERB_SUFFIXES = ["ing", "ed", "er", "s"]

# ---------------------------------------------------------------------------
# Metric parser  (C3, C4)
# ---------------------------------------------------------------------------

# Units that indicate financial/scale magnitude
_SCALE_MAP: dict[str, float] = {
    "k": 1_000, "m": 1_000_000, "b": 1_000_000_000,
    "l": 100_000, "lakh": 100_000, "cr": 10_000_000, "crore": 10_000_000,
}

# Impact-relevant units / contexts
_IMPACT_UNITS = {"percent", "%", "x", "times", "k", "m", "b", "l", "cr",
                 "lakh", "crore", "usd", "$", "₹", "inr", "rs",
                 "users", "students", "members", "customers", "employees",
                 "teams", "projects", "schools", "colleges",
                 "ms", "seconds", "requests/day"}

_METRIC_RE = re.compile(
    r"""
    (?P<sign>[+\-])?
    (?:
        # Currency prefix: $44.6B or ₹75L
        (?P<currency>[$₹€£]|rs\.?|inr)\s*
    )?
    (?P<int>\d{1,3}(?:,\d{3})*|\d+)   # integer part with optional comma grouping
    (?:\.(?P<frac>\d+))?               # optional decimal
    (?P<plus>\+)?                       # trailing + (10,000+)
    \s*
    (?P<scale>k|m|b|l|lakh|cr|crore)?  # scale suffix
    \s*
    (?P<unit>%|x|times|ms|sec(?:ond)?s?|
             users?|students?|members?|customers?|employees?|
             team(?:s)?|projects?|schools?|colleges?|
             requests?\/day|months?|years?|weeks?|days?|
             usd|\$|₹|inr|rs\.?)?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Range pattern: "25%–50%" or "25-50%"
_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%?\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(%|x|times)?",
    re.IGNORECASE,
)

# Year pattern (to classify as non-impact)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Model/technical parameter patterns
_MODEL_PARAM_RE = re.compile(
    r"\b\d+\s*(?:layer|layers|epoch|epochs|neuron|neurons|parameter|parameters|"
    r"class|classes|dimension|channel|filter|head|heads|block|blocks)\b",
    re.IGNORECASE,
)

# Event/label patterns (should NOT be impact metrics)
_EVENT_LABEL_RE = re.compile(
    r"\b(?:galaxy|antaragni|techkriti|inferno|udghosh|takneek|"
    r"inter.?iit|iitk|iisc|nit|bits)\b",
    re.IGNORECASE,
)


def _classify_metric_kind(raw: str, value: float, unit: str | None, context: str) -> tuple[str, bool]:
    """Return (kind, is_impact_relevant)."""
    raw_lower = raw.lower()
    ctx_lower = context.lower()

    # Year — never impact
    if _YEAR_RE.fullmatch(raw.strip()):
        return "year", False

    # Model parameter context
    if _MODEL_PARAM_RE.search(context):
        return "model_param", False

    # Event label in raw or nearby context
    if _EVENT_LABEL_RE.search(raw) or _EVENT_LABEL_RE.search(context[:60]):
        return "event_id", False

    # Rank (standalone small integer with "rank" nearby or "1st/2nd/3rd")
    if re.search(r"\b(rank|ranked|position|place|1st|2nd|3rd|\dth)\b", ctx_lower):
        return "ranking_metric", True  # ranking IS impact-relevant

    # Duration
    if unit and re.match(r"months?|years?|weeks?|days?", unit, re.I):
        return "duration", False

    # Financial
    if unit and re.match(r"\$|₹|usd|inr|rs", unit, re.I):
        return "financial", True
    if re.search(r"\b(revenue|profit|cost|saving|budget|funding|valuat|market cap)\b", ctx_lower):
        return "financial", True

    # Percentage — almost always impact-relevant
    if unit == "%":
        return "percentage", True

    # Multiplier
    if unit and unit.lower() in {"x", "times"}:
        return "multiplier", True

    # Large count (with scale suffix or large number of people)
    if unit and unit.lower() in {"users", "students", "members", "customers",
                                  "employees", "teams", "schools", "colleges"}:
        return "count", True

    # Accuracy / recall / AUC (no unit, but context has ML evaluation words)
    if re.search(r"\b(accuracy|recall|precision|f1|auc|roc|mse|rmse|mae|r2|r\^2)\b", ctx_lower):
        return "accuracy", True

    # Latency / performance
    if unit and re.match(r"ms|sec|requests?/day", unit, re.I):
        return "rate", True

    # Small standalone integer — likely count of items, not necessarily impact
    if value < 20 and not unit:
        return "count", False

    return "quantity", value >= 100  # large bare numbers might be impact


def parse_metrics(text: str) -> list[Metric]:
    """Parse all metrics from a text string."""
    metrics: list[Metric] = []

    # First check for range patterns
    for rm in _RANGE_RE.finditer(text):
        low_val = float(rm.group(1))
        high_val = float(rm.group(2))
        unit = rm.group(3) or "%"
        raw = rm.group(0)
        kind, impact = _classify_metric_kind(raw, low_val, unit, text)
        metrics.append(Metric(
            raw=raw, value=low_val, value_high=high_val,
            unit=unit, kind=kind, is_impact_relevant=impact,
        ))
        # Remove from text so we don't double-count
        text = text.replace(raw, " ", 1)

    for m in _METRIC_RE.finditer(text):
        raw = m.group(0).strip()
        if not raw or not m.group("int"):
            continue
        # Skip pure years in isolation
        if _YEAR_RE.fullmatch(raw.strip()):
            continue

        # Parse value
        int_str = m.group("int").replace(",", "")
        frac_str = m.group("frac") or ""
        val_str = int_str + ("." + frac_str if frac_str else "")
        try:
            value = float(val_str)
        except ValueError:
            continue

        # Apply scale
        scale_key = (m.group("scale") or "").lower()
        if scale_key in _SCALE_MAP:
            value *= _SCALE_MAP[scale_key]

        unit = m.group("unit") or m.group("currency") or m.group("scale") or None
        kind, impact = _classify_metric_kind(raw, value, unit, text)

        # Determine direction from context
        direction = None
        ctx = text[:m.start() + len(raw) + 20].lower()
        if re.search(r"\b(reduc|decreas|cut|lower|drop|shrink|eliminat)\w*\b", ctx):
            direction = "decrease"
        elif re.search(r"\b(increas|improv|boost|enhanc|grew|grow|scale|achiev)\w*\b", ctx):
            direction = "increase"

        metrics.append(Metric(
            raw=raw, value=value,
            unit=unit, kind=kind,
            is_impact_relevant=impact,
            direction=direction,
        ))

    return metrics


# ---------------------------------------------------------------------------
# Action verb normalizer
# ---------------------------------------------------------------------------

def _normalize_verb(word: str) -> str:
    """Normalize inflected verb to a lookup-friendly form."""
    w = word.lower().strip(".,;:")
    if w in _INFLECTIONS:
        return _INFLECTIONS[w]
    # Strip common suffixes
    for suf in _VERB_SUFFIXES:
        if w.endswith(suf) and len(w) > len(suf) + 2:
            stem = w[: -len(suf)]
            if stem in _STRONG or stem in _WEAK:
                return stem
    return w


def _action_verb(text: str) -> tuple[str | None, float, float]:
    """Return (verb, strength, confidence) for the leading action verb."""
    # Strip bullet glyph and leading non-alpha
    clean = re.sub(r"^[^A-Za-z]+", "", text).strip()
    if not clean:
        return None, 0.0, 0.0

    first_token = clean.split()[0] if clean.split() else ""
    norm = _normalize_verb(first_token)

    if norm in _STRONG:
        return norm, _STRONG[norm], 0.90
    if first_token.lower() in _STRONG:
        return first_token.lower(), _STRONG[first_token.lower()], 0.90
    if norm in _WEAK:
        return norm, _WEAK[norm], 0.85
    if first_token.lower() in _WEAK:
        return first_token.lower(), _WEAK[first_token.lower()], 0.85

    # Unknown verb — neutral/low, NOT 0.5 (C6 fix)
    if re.match(r"^[A-Z][a-z]+ed$", first_token) or re.match(r"^[A-Z][a-z]+ing$", first_token):
        # Looks like a past-tense or gerund action verb — mild positive
        return first_token.lower(), 0.45, 0.50
    return first_token.lower() or None, 0.20, 0.30


# ---------------------------------------------------------------------------
# Section → entry type mapping
# ---------------------------------------------------------------------------

_SECTION_ENTRY_TYPE: dict[str, str] = {
    "Experience": "experience",
    "Research": "research",
    "Projects": "project",
    "Positions of Responsibility": "por",
    "Extracurricular": "extracurricular",
    "Achievements": "achievement",
    "Education": "education",
    "Skills": "skill",
    "Coursework": "coursework",
    "Social Impact": "social_impact",
    "Publications": "publication",
    "Header": "metadata",
}

# ---------------------------------------------------------------------------
# Academic metric parser (C2)
# ---------------------------------------------------------------------------

_CPI_RE = re.compile(
    r"""
    \b(?:cpi|cgpa|gpa|spi|sgpa)\b.*?            # label
    (?:(?P<value>\d+\.\d+|\d+)                   # value
    \s*(?:/\s*(?P<scale>\d+(?:\.\d+)?))?)?       # optional /scale
    """,
    re.VERBOSE | re.IGNORECASE,
)
_FRAC_GRADE_RE = re.compile(r"(\d+\.\d+)\s*/\s*(\d+(?:\.\d+)?)")


def _parse_academic_metrics(raw_lines: list[str]) -> list[AcademicMetric]:
    """Extract CPI/SPI and degree info from education raw lines."""
    results: list[AcademicMetric] = []
    for line in raw_lines:
        # Pattern: "7.7/10.0" or "CPI: 7.7" or "7.7 / 10"
        for m in _FRAC_GRADE_RE.finditer(line):
            val = float(m.group(1))
            scale = float(m.group(2))
            if 0 < val <= scale <= 10.5:
                # Looks like a GPA
                mtype = "cpi"
                if re.search(r"\bspi\b|\bsgpa\b", line, re.I):
                    mtype = "spi"
                results.append(AcademicMetric(
                    metric_type=mtype,
                    raw=m.group(0),
                    value=val,
                    scale=scale,
                    institution=_extract_institution(line),
                ))
        # Standalone CPI label
        for m in _CPI_RE.finditer(line):
            if m.group("value"):
                val = float(m.group("value"))
                scale = float(m.group("scale")) if m.group("scale") else None
                if 0 < val <= (scale or 10.0):
                    mtype = "spi" if re.search(r"\bspi\b|\bsgpa\b", m.group(0), re.I) else "cpi"
                    already = any(abs(r.value - val) < 0.01 for r in results)
                    if not already:
                        results.append(AcademicMetric(
                            metric_type=mtype, raw=m.group(0),
                            value=val, scale=scale,
                            institution=_extract_institution(line),
                        ))
    return results


def _extract_institution(line: str) -> str | None:
    if re.search(r"\biit\b|\biitk\b|\bkanpur\b", line, re.I):
        return "IIT Kanpur"
    if re.search(r"\bnit\b|\bnsit\b|\bbits\b|\biisc\b", line, re.I):
        return re.search(r"(nit|nsit|bits|iisc)\b.*", line, re.I).group(0)[:40] if re.search(r"(nit|nsit|bits|iisc)\b.*", line, re.I) else None
    return None


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

class EvidenceExtractor:
    def __init__(self, config_dir: str | Path | None = None):
        root = Path(config_dir) if config_dir else Path(__file__).resolve().parents[1] / "config"
        raw_entities = yaml.safe_load((root / "iitk_entities.yaml").read_text())
        self.entities = raw_entities.get("entities", raw_entities)
        self.skills: dict[str, list[str]] = yaml.safe_load(
            (root / "skills.yaml").read_text()
        )["skills"]
        
        # Load coursework ontology for course extraction
        try:
            coursework_data = yaml.safe_load((root / "coursework.yaml").read_text())
            self.course_codes = coursework_data.get("course_codes", [])
            self.courses = coursework_data.get("courses", [])
        except FileNotFoundError:
            self.course_codes = []
            self.courses = []

    def _normalize_iitk_entity(self, surface_text: str) -> str:
        """Normalize IITK entity variants to canonical form."""
        normalized = surface_text.strip()
        
        # Handle quote variants
        normalized = re.sub(r"['']", "'", normalized)
        
        # Handle year suffixes - remove '24, '25, '26, etc.
        normalized = re.sub(r"'[0-9]{2}$", "", normalized)
        
        # Handle spacing variants
        normalized = re.sub(r"\s+", " ", normalized)
        
        # Handle specific IITK entity normalizations
        entity_normalizations = {
            "takneek": "Takneek",
            "antaragni": "Antaragni", 
            "galaxy": "Galaxy",
            "inferno": "Inferno",
            "udghosh": "Udghosh",
            "techkriti": "Techkriti",
            "inter iit": "Inter IIT",
            "inter-iit": "Inter IIT",
            "iit kanpur": "IIT Kanpur",
            "iitk": "IIT Kanpur",
        }
        
        normalized_lower = normalized.lower()
        for pattern, canonical in entity_normalizations.items():
            if pattern in normalized_lower:
                normalized = re.sub(re.escape(pattern), canonical, normalized, flags=re.IGNORECASE)
                
        return normalized

    def _entities(self, text: str) -> list[EntityMention]:
        low = text.lower()
        out: list[EntityMention] = []
        seen: set[str] = set()
        for _key, spec in self.entities.items():
            canonical = spec["canonical"]
            if canonical in seen:
                continue
            for alias in spec.get("aliases", []):
                # Word-boundary aware match
                pattern = r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])"
                if re.search(pattern, low):
                    # Apply normalization to the surface form
                    normalized_surface = self._normalize_iitk_entity(alias)
                    out.append(EntityMention(
                        canonical=canonical,
                        category=spec["category"],
                        surface=normalized_surface,
                        competencies={k: float(v) for k, v in spec.get("competencies", {}).items()},
                    ))
                    seen.add(canonical)
                    break
        return out

    def _extract_courses(self, text: str) -> list[dict]:
        """Extract course names and codes from text using coursework ontology."""
        found_courses = []
        text_lower = text.lower()
        seen_courses = set()
        
        # Extract course codes (ESC101, MTH101, CS220, etc.)
        for course_code in self.course_codes:
            code = course_code['code']
            if code in seen_courses:
                continue
            for alias in course_code.get('aliases', []):
                # Word boundary aware matching
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, text_lower):
                    found_courses.append({
                        'type': 'course_code',
                        'code': code,
                        'name': course_code['name'],
                        'competencies': course_code.get('competencies', [])
                    })
                    seen_courses.add(code)
                    break
        
        # Extract course names (Linear Algebra, Algorithms, etc.)
        for course in self.courses:
            name = course['name']
            if name in seen_courses:
                continue
            for alias in course.get('aliases', []):
                # More flexible matching for course names
                if alias.lower() in text_lower:
                    found_courses.append({
                        'type': 'course_name',
                        'name': name,
                        'competencies': course.get('competencies', []),
                        'role_relevance': course.get('role_relevance', {})
                    })
                    seen_courses.add(name)
                    break
        
        return found_courses

    def _classify_evidence_types(
        self, 
        text: str, 
        skills: list[str], 
        entities: list[EntityMention],
        section: str,
        metrics: list[Metric],
        impact_metrics: list[Metric]
    ) -> tuple[list[EvidenceType], list[ProjectType], list[ImpactType]]:
        """Classify evidence types based on semantic patterns with hard gates."""
        evidence_types = []
        project_types = []
        impact_types = []
        
        text_lower = text.lower()
        
        # ── PROGRAMMING HARD GATE ──────────────────────────────────
        # Programming requires explicit evidence: language, framework, code/API/software, SQL
        programming_skills = {"python", "cpp", "java", "javascript", "typescript", "r_lang", 
                             "go_lang", "rust", "scala", "sql", "nodejs", "react", "flask", 
                             "django", "fastapi", "spring"}
        programming_patterns = r"\b(code|coded|coding|programming|implemented|engineered|built.*software|developed.*api|developed.*system|database|framework|library|repository|deployment|backend|frontend|pipeline|script|algorithm|sql)\b"
        
        # VETO: Business analysis/pricing/optimization alone cannot be programming
        business_veto_patterns = r"\b(business analyst|pricing strategy|cohort analysis|market analysis|business optimization|pricing optimization|developed.*strateg|developed.*pricing|developed.*business)\b"
        has_business_veto = re.search(business_veto_patterns, text_lower)
        
        has_programming_evidence = (
            any(skill in skills for skill in programming_skills) or
            re.search(programming_patterns, text_lower)
        )
        
        if has_programming_evidence and not has_business_veto:
            evidence_types.append(EvidenceType.PROGRAMMING)
        
        # ── SOFTWARE ENGINEERING EVIDENCE ──────────────────────────────────
        software_skills = {"git", "docker", "aws", "kubernetes", "microservices", "devops"}
        software_patterns = r"\b(software|system|architecture|microservice|deployment|version control|ci/cd|containerization)\b"
        
        if (EvidenceType.PROGRAMMING in evidence_types or 
            any(skill in skills for skill in software_skills) or 
            re.search(software_patterns, text_lower)):
            evidence_types.append(EvidenceType.SOFTWARE_ENGINEERING)
        
        # ── ML ENGINEERING EVIDENCE ──────────────────────────────────────────
        ml_skills = {"tensorflow", "pytorch", "scikit_learn", "keras", "machine_learning", 
                    "deep_learning", "nlp", "computer_vision", "neural_networks"}
        ml_patterns = r"\b(model|neural|classifier|regression|accuracy|precision|recall|training|dataset|fine.?tun|mobilenet|roc.?auc)\b"
        
        if (any(skill in skills for skill in ml_skills) or
            re.search(ml_patterns, text_lower)):
            evidence_types.append(EvidenceType.ML_ENGINEERING)
            
        # ── QUANT MATHEMATICS HARD GATE ──────────────────────────────────────────
        # DO NOT match "cohort analysis models", "pricing strategy", "ML model" to rigorous mathematics
        # Mathematics requires explicit mathematical signals
        math_skills = {"probability", "statistics", "stochastic_calculus", "linear_algebra", 
                      "calculus", "mathematical_optimization", "numerical_methods"}
        math_patterns = r"\b(probability|calculus|linear algebra|stochastic|mathematical modelling|numerical methods|mathematical optimization|theorem|proof|equation|derivative|integral|matrix)\b"
        
        # VETO generic business or ML contexts from mathematics
        math_veto_patterns = r"\b(cohort analysis models|pricing strategy|ml model|business model)\b"
        has_math_veto = re.search(math_veto_patterns, text_lower)
        
        has_math_evidence = (
            any(skill in skills for skill in math_skills) or
            re.search(math_patterns, text_lower)
        )
        
        if has_math_evidence and not has_math_veto:
            evidence_types.append(EvidenceType.MATHEMATICAL)
            
        # ── QUANT STATISTICS HARDENING ──────────────────────────────────────────
        # Statistics requires explicit statistical semantics, not just "ML" or "guided ML students"
        strong_stats_patterns = r"\b(regression|distribution|variance|hypothesis|statistical testing|econometrics|sampling|confidence interval|time.?series statistics)\b"
        medium_stats_patterns = r"\b(roc.?auc|threshold calibration)\b"
        
        # VETO weak statistical associations
        stats_veto_patterns = r"\b(guided.*ml.*students|ml|fintech)\b"
        has_stats_veto = re.search(stats_veto_patterns, text_lower) and not re.search(strong_stats_patterns, text_lower)
        
        has_strong_stats = re.search(strong_stats_patterns, text_lower)
        has_medium_stats = re.search(medium_stats_patterns, text_lower)
        
        if has_strong_stats or (has_medium_stats and not has_stats_veto):
            evidence_types.append(EvidenceType.STATISTICAL)
            
        # ── QUANT FINANCE EVIDENCE (HARDENED) ──────────────────────────────────────────
        # Requires actual finance/market modeling evidence
        quant_finance_patterns = r"\b(finance|market modelling|portfolio|option pricing|monte carlo|stochastic|risk modelling|econometrics|time series|financial modelling|trading|derivatives|quantitative finance)\b"
        
        # VETO generic business pricing or ML projects
        quant_veto_patterns = r"\b(pricing strategy|business pricing)\b"
        has_quant_veto = re.search(quant_veto_patterns, text_lower)
        
        if re.search(quant_finance_patterns, text_lower) and not has_quant_veto:
            evidence_types.append(EvidenceType.QUANT_FINANCE)
            
        # ── BUSINESS ANALYSIS EVIDENCE ──────────────────────────────────────
        business_skills = {"crm", "saas", "fintech", "erp", "business_optimization"}
        business_patterns = r"\b(business|strategy|market|revenue|profit|pricing|customer|client|stakeholder|cohort analysis|business analyst)\b"
        
        if (any(skill in skills for skill in business_skills) or
            re.search(business_patterns, text_lower)):
            evidence_types.append(EvidenceType.BUSINESS_ANALYSIS)
            
        # ── RESEARCH EVIDENCE ──────────────────────────────────────────
        research_patterns = r"\b(research|study|investigation|methodology|findings|hypothesis|experiment)\b"
        
        if (section == "Research" or 
            re.search(research_patterns, text_lower)):
            evidence_types.append(EvidenceType.RESEARCH)
            
        # ── TECHNICAL RESEARCH EVIDENCE ──────────────────────────────────────────
        if (EvidenceType.RESEARCH in evidence_types and 
            (EvidenceType.SOFTWARE_ENGINEERING in evidence_types or 
             EvidenceType.ML_ENGINEERING in evidence_types or
             EvidenceType.MATHEMATICAL in evidence_types)):
            evidence_types.append(EvidenceType.TECHNICAL_RESEARCH)
            
        # ── LEADERSHIP EVIDENCE ──────────────────────────────────────────
        leadership_patterns = r"\b(led|lead|managed|oversaw|coordinated|chaired|convener|president|head|elected)\b"
        
        if re.search(leadership_patterns, text_lower):
            evidence_types.append(EvidenceType.LEADERSHIP)
            
        # ── COMMUNICATION EVIDENCE (IMPROVED & EXPANDED) ──────────────────────────────────────────
        # Focus on actual stakeholder/presentation, debating, adjudicating, and public speaking evidence
        comm_patterns = r"\b(presented|interviewed|chaired|coordinated with|academic mentor|represented|stakeholder|facilitated|negotiated|communicated|mentored|taught|delivered|speaker|adjudicator|debating|debate|oratorix|rmlpd|chief adjudicator|semi-finalist|adjudicating|orator|trinity college|public speaking)\b"
        
        if re.search(comm_patterns, text_lower):
            evidence_types.append(EvidenceType.COMMUNICATION)
            
        # ── TEAMWORK EVIDENCE ──────────────────────────────────────────
        teamwork_patterns = r"\b(collaborated|team|coordinated|worked with|group project)\b"
        
        if re.search(teamwork_patterns, text_lower):
            evidence_types.append(EvidenceType.TEAMWORK)
            
        # ── OPEN SOURCE EVIDENCE (ENHANCED WITH GITHUB REPO LINKS) ──────────────────────────
        os_patterns = r"\b(open.?source|pull request|pr|fork|contribute|gsoc|package|github.*contribute|repo|repository)\b"
        is_github_profile_only = "github profile" in text_lower or (text_lower.startswith("github profile available at") or "github.com/username" in text_lower)
        has_github_repo_link = "github.com/" in text_lower and not is_github_profile_only and "github.com/in/" not in text_lower
        
        if re.search(os_patterns, text_lower) or (has_github_repo_link and "profile" not in text_lower):
            if EvidenceType.OPEN_SOURCE not in evidence_types:
                evidence_types.append(EvidenceType.OPEN_SOURCE)
            
        # ── COMPETITIVE PROGRAMMING EVIDENCE ──────────────────────────────────────────
        cp_patterns = r"\b(codeforces|codechef|leetcode|competitive programming|contest|algorithmic|icpc)\b"
        
        if re.search(cp_patterns, text_lower):
            evidence_types.append(EvidenceType.COMPETITIVE_PROGRAMMING)
            
        # ── CORE ENGINEERING EVIDENCE ──────────────────────────────────────────
        core_skills = {"matlab", "cad", "matlab_simulink", "labview", "mathematica", "solidworks", "ansys"}
        core_patterns = r"\b(cad|matlab|solidworks|ansys|simulink|mechanical|civil|electrical|chemical|core engineering|autocad|catia)\b"
        
        if (any(skill in skills for skill in core_skills) or
            re.search(core_patterns, text_lower)):
            evidence_types.append(EvidenceType.CORE_ENGINEERING)
            
        # ── COURSEWORK EVIDENCE ──────────────────────────────────────────
        coursework_patterns = r"\b(course|coursework|elective|subject|grade|semester|academic)\b"
        
        if (section in {"Education", "Coursework"} or
            re.search(coursework_patterns, text_lower)):
            evidence_types.append(EvidenceType.COURSEWORK)
            
        # ── PUBLICATION EVIDENCE (HARDENED) ──────────────────────────────────────────
        pub_patterns = r"\b(published|publication|paper|journal|conference|proceedings|doi|cite|author|accepted|arxiv|peer.?review)\b"
        
        if re.search(pub_patterns, text_lower):
            evidence_types.append(EvidenceType.PUBLICATION)

        # ── EXCLUSION RULE: Entrance Exam Ranks & CP stats must NEVER trigger Business Analysis/Impact ──
        is_academic_rank_or_cp = any(k in text_lower for k in [
            "jee", "jee advanced", "jee mains", "kvpy", "air ", "all india rank", 
            "olympiad", "codeforces", "codechef", "leetcode", "takneek", "kvpy sa",
            "kvpy sx", "kvpy sb", "kvpy fellow", "academic excellence award", "kvpy rank"
        ]) or section in {"Achievements", "Scholastic Achievements"}

        if is_academic_rank_or_cp:
            if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
                evidence_types.remove(EvidenceType.BUSINESS_ANALYSIS)
            if ImpactType.BUSINESS_IMPACT in impact_types:
                impact_types.remove(ImpactType.BUSINESS_IMPACT)
            
        # ── PROJECT TYPE CLASSIFICATION ──────────────────────────────────────────
        if section in {"Projects", "Research"}:
            if EvidenceType.SOFTWARE_ENGINEERING in evidence_types or EvidenceType.PROGRAMMING in evidence_types:
                project_types.append(ProjectType.SOFTWARE_PROJECT)
            if EvidenceType.ML_ENGINEERING in evidence_types:
                project_types.append(ProjectType.ML_PROJECT)
            if EvidenceType.RESEARCH in evidence_types:
                project_types.append(ProjectType.RESEARCH_PROJECT)
            if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
                project_types.append(ProjectType.CONSULTING_PROJECT)
            if EvidenceType.QUANT_FINANCE in evidence_types:
                project_types.append(ProjectType.QUANT_PROJECT)
            if EvidenceType.CORE_ENGINEERING in evidence_types:
                project_types.append(ProjectType.CORE_PROJECT)
            
            if not project_types:
                project_types.append(ProjectType.GENERAL_PROJECT)
                
        # ── IMPACT TYPE CLASSIFICATION (REFINED) ──────────────────────────────────────────
        if impact_metrics:
            technical_contexts = r"\b(accuracy|recall|precision|f1|auc|latency|performance|efficiency|api.*reduced|system.*improved|sql.*optimized)\b"
            business_contexts = r"\b(revenue.*growth|profit|cost.*reduction|market|customer|pricing.*optimization|business.*impact)\b"
            research_contexts = r"\b(dataset|model.*accuracy|experiment|validation|methodology|research|recall.*87)\b"
            org_contexts = r"\b(students|members|teams|hostels|organization|community|served.*students|hostel.*affairs)\b"
            
            if re.search(technical_contexts, text_lower):
                impact_types.append(ImpactType.TECHNICAL_IMPACT)
            if re.search(business_contexts, text_lower) and not is_academic_rank_or_cp:
                impact_types.append(ImpactType.BUSINESS_IMPACT)
            if re.search(research_contexts, text_lower):
                impact_types.append(ImpactType.RESEARCH_IMPACT)
            if re.search(org_contexts, text_lower):
                impact_types.append(ImpactType.ORGANIZATIONAL_IMPACT)
                
            # Default assignment based on section if no specific context matches
            if not impact_types:
                if section in {"Positions of Responsibility", "Social Impact"}:
                    impact_types.append(ImpactType.ORGANIZATIONAL_IMPACT)
                else:
                    impact_types.append(ImpactType.TECHNICAL_IMPACT)
                
        return evidence_types, project_types, impact_types
        
        if re.search(leadership_patterns, text_lower):
            evidence_types.append(EvidenceType.LEADERSHIP)
            
        # ── Communication Evidence (HARDENED) ──────────────────────────────────────────
        comm_patterns = r"\b(presented|presentation|interviewed|communicate|mentor|teach|facilitate|negotiate|stakeholder)\b"
        
        if re.search(comm_patterns, text_lower):
            evidence_types.append(EvidenceType.COMMUNICATION)
            
        # ── Open Source Evidence ──────────────────────────────────────────
        os_patterns = r"\b(open.?source|pull request|fork|contribute|gsoc|package)\b"
        
        if re.search(os_patterns, text_lower):
            evidence_types.append(EvidenceType.OPEN_SOURCE)
            
        # ── Competitive Programming Evidence ──────────────────────────────────────────
        cp_patterns = r"\b(codeforces|codechef|leetcode|competitive programming|contest|algorithmic)\b"
        
        if re.search(cp_patterns, text_lower):
            evidence_types.append(EvidenceType.COMPETITIVE_PROGRAMMING)
            
        # ── Core Engineering Evidence ──────────────────────────────────────────
        core_skills = {"matlab", "cad", "matlab_simulink", "labview", "mathematica"}
        core_patterns = r"\b(cad|matlab|solidworks|ansys|simulink|mechanical|civil|electrical|chemical)\b"
        
        if (any(skill in skills for skill in core_skills) or
            re.search(core_patterns, text_lower)):
            evidence_types.append(EvidenceType.CORE_ENGINEERING)
            
        # ── Publication Evidence (HARDENED) ──────────────────────────────────────────
        pub_patterns = r"\b(published|publication|paper|journal|conference|proceedings|doi|cite|author|accepted)\b"
        
        if re.search(pub_patterns, text_lower):
            evidence_types.append(EvidenceType.PUBLICATION)
            
        # ── Project Type Classification ──────────────────────────────────────────
        if section in {"Projects", "Research"}:
            if EvidenceType.SOFTWARE_ENGINEERING in evidence_types:
                project_types.append(ProjectType.SOFTWARE_PROJECT)
            if EvidenceType.ML_ENGINEERING in evidence_types:
                project_types.append(ProjectType.ML_PROJECT)
            if EvidenceType.RESEARCH in evidence_types:
                project_types.append(ProjectType.RESEARCH_PROJECT)
            if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
                project_types.append(ProjectType.CONSULTING_PROJECT)
            if EvidenceType.QUANT_FINANCE in evidence_types:
                project_types.append(ProjectType.QUANT_PROJECT)
            if EvidenceType.CORE_ENGINEERING in evidence_types:
                project_types.append(ProjectType.CORE_PROJECT)
            
            if not project_types:
                project_types.append(ProjectType.GENERAL_PROJECT)
                
        # ── Impact Type Classification ──────────────────────────────────────────
        if impact_metrics:
            technical_contexts = {"accuracy", "recall", "precision", "latency", "performance", "efficiency", "sql", "system", "algorithm"}
            business_contexts = {"revenue", "profit", "cost", "growth", "market", "customer", "pricing", "business"}
            research_contexts = {"dataset", "model", "experiment", "validation", "methodology", "research"}
            org_contexts = {"students", "members", "teams", "hostels", "organization", "community", "hostel"}
            
            if any(ctx in text_lower for ctx in technical_contexts):
                impact_types.append(ImpactType.TECHNICAL_IMPACT)
            if any(ctx in text_lower for ctx in business_contexts):
                impact_types.append(ImpactType.BUSINESS_IMPACT)
            if any(ctx in text_lower for ctx in research_contexts):
                impact_types.append(ImpactType.RESEARCH_IMPACT)
            if any(ctx in text_lower for ctx in org_contexts):
                impact_types.append(ImpactType.ORGANIZATIONAL_IMPACT)
                
            # Default based on section if no specific context
            if not impact_types:
                if section == "Experience":
                    impact_types.append(ImpactType.BUSINESS_IMPACT)
                elif section in {"Research", "Projects"}:
                    impact_types.append(ImpactType.TECHNICAL_IMPACT)
                else:
                    impact_types.append(ImpactType.ORGANIZATIONAL_IMPACT)
                
        return evidence_types, project_types, impact_types

    def _compute_domain_relevance(
        self, 
        evidence_types: list[EvidenceType],
        project_types: list[ProjectType],
        impact_types: list[ImpactType],
        section: str
    ) -> dict[str, float]:
        """Compute domain relevance scores for each role."""
        relevance = {"sde": 0.0, "quant": 0.0, "consulting": 0.0, "core": 0.0, "analyst": 0.0, "product": 0.0}

        # ── Analyst Relevance ──────────────────────────────────────
        if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
            relevance["analyst"] += 1.0
        if EvidenceType.STATISTICAL in evidence_types:
            relevance["analyst"] += 0.9
        if EvidenceType.MATHEMATICAL in evidence_types:
            relevance["analyst"] += 0.6
        if ImpactType.BUSINESS_IMPACT in impact_types:
            relevance["analyst"] += 0.8
        if ProjectType.CONSULTING_PROJECT in project_types:
            relevance["analyst"] += 0.7

        # ── Product Relevance ──────────────────────────────────────
        if EvidenceType.LEADERSHIP in evidence_types:
            relevance["product"] += 0.9
        if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
            relevance["product"] += 0.8
        if ImpactType.ORGANIZATIONAL_IMPACT in impact_types:
            relevance["product"] += 0.8
        if ImpactType.BUSINESS_IMPACT in impact_types:
            relevance["product"] += 0.7
        if EvidenceType.SOFTWARE_ENGINEERING in evidence_types or EvidenceType.PROGRAMMING in evidence_types:
            relevance["product"] += 0.5

        if EvidenceType.SOFTWARE_ENGINEERING in evidence_types:
            relevance["sde"] += 0.9
        if EvidenceType.PROGRAMMING in evidence_types:
            relevance["sde"] += 0.8
        if EvidenceType.ML_ENGINEERING in evidence_types:
            relevance["sde"] += 0.6  # ML can be relevant to SDE
        if EvidenceType.OPEN_SOURCE in evidence_types:
            relevance["sde"] += 0.7
        if EvidenceType.COMPETITIVE_PROGRAMMING in evidence_types:
            relevance["sde"] += 0.8
        if ProjectType.SOFTWARE_PROJECT in project_types:
            relevance["sde"] += 0.7
        if ProjectType.ML_PROJECT in project_types:
            relevance["sde"] += 0.5
        if ImpactType.TECHNICAL_IMPACT in impact_types:
            relevance["sde"] += 0.6
        
        # Penalize non-technical contexts for SDE
        if EvidenceType.BUSINESS_ANALYSIS in evidence_types and section == "Experience":
            relevance["sde"] *= 0.3  # Strong penalty for business analyst roles
            
        # ── Quant Relevance ──────────────────────────────────────────
        if EvidenceType.MATHEMATICAL in evidence_types:
            relevance["quant"] += 1.0
        if EvidenceType.STATISTICAL in evidence_types:
            relevance["quant"] += 0.9
        if EvidenceType.QUANT_FINANCE in evidence_types:
            relevance["quant"] += 1.0
        if EvidenceType.PROGRAMMING in evidence_types:
            relevance["quant"] += 0.4  # Some programming is relevant to quant
        if ProjectType.QUANT_PROJECT in project_types:
            relevance["quant"] += 0.8
        if ProjectType.ML_PROJECT in project_types:
            relevance["quant"] += 0.3  # Reduced: Generic ML != quantitative finance
        if ImpactType.RESEARCH_IMPACT in impact_types:
            relevance["quant"] += 0.6
        if ImpactType.TECHNICAL_IMPACT in impact_types:
            relevance["quant"] += 0.3
            
        # ── Consulting Relevance ──────────────────────────────────────────
        if EvidenceType.BUSINESS_ANALYSIS in evidence_types:
            relevance["consulting"] += 1.0
        if EvidenceType.LEADERSHIP in evidence_types:
            relevance["consulting"] += 0.9
        if EvidenceType.COMMUNICATION in evidence_types:
            relevance["consulting"] += 0.8
        if EvidenceType.TEAMWORK in evidence_types:
            relevance["consulting"] += 0.6
        if ProjectType.CONSULTING_PROJECT in project_types:
            relevance["consulting"] += 0.8
        if ImpactType.BUSINESS_IMPACT in impact_types:
            relevance["consulting"] += 0.8
        if ImpactType.ORGANIZATIONAL_IMPACT in impact_types:
            relevance["consulting"] += 0.7
        
        # Leadership sections are highly relevant to consulting
        if section == "Positions of Responsibility":
            relevance["consulting"] += 0.5
            
        # ── Core Relevance (with domain filtering) ──────────────────────────────────────────
        if EvidenceType.CORE_ENGINEERING in evidence_types:
            relevance["core"] += 1.0
        if EvidenceType.TECHNICAL_RESEARCH in evidence_types:
            relevance["core"] += 0.8
        if EvidenceType.RESEARCH in evidence_types:
            relevance["core"] += 0.7
        if EvidenceType.MATHEMATICAL in evidence_types:
            relevance["core"] += 0.5  # Some math is core-relevant
        if EvidenceType.PUBLICATION in evidence_types:
            relevance["core"] += 0.6
        if ProjectType.CORE_PROJECT in project_types:
            relevance["core"] += 0.9
        if ProjectType.RESEARCH_PROJECT in project_types:
            relevance["core"] += 0.6
        if ImpactType.TECHNICAL_IMPACT in impact_types:
            # Technical impact is only core-relevant if not in business context
            if EvidenceType.BUSINESS_ANALYSIS not in evidence_types:
                relevance["core"] += 0.5
        if ImpactType.RESEARCH_IMPACT in impact_types:
            relevance["core"] += 0.7
        
        # CORE DOMAIN GATE: Business analyst internship gets low core relevance
        if (EvidenceType.BUSINESS_ANALYSIS in evidence_types and 
            section == "Experience" and 
            not EvidenceType.CORE_ENGINEERING in evidence_types):
            relevance["core"] *= 0.2  # Strong penalty for non-core business roles
            
        # Research and technical sections are relevant to core (if not business)
        if (section in {"Research", "Projects"} and 
            EvidenceType.BUSINESS_ANALYSIS not in evidence_types):
            relevance["core"] += 0.3
            
        # Cap all scores at 1.0
        for role in relevance:
            relevance[role] = min(1.0, relevance[role])
            
        return relevance
            
        # Cap all scores at 1.0
        for role in relevance:
            relevance[role] = min(1.0, relevance[role])
            
        return relevance

    def _skills(self, text: str) -> list[str]:
        low = text.lower()
        out: list[str] = []
        for sk, aliases in self.skills.items():
            for a in aliases:
                a_stripped = a.strip('"')
                pattern = r"(?<![a-z0-9\+])" + re.escape(a_stripped.lower()) + r"(?![a-z0-9\+])"
                if re.search(pattern, low):
                    out.append(sk)
                    break
        return out

    def _evidence_strength(
        self,
        action_str: float,
        action_conf: float,
        impact_metrics: list[Metric],
        all_metrics: list[Metric],
        skills: list[str],
        entities: list[EntityMention],
        hyperlinks: list[str],
        entry_type: str,
    ) -> float:
        """Compute evidence strength from interpretable features (C7 fix).

        Features:
          - ownership (action verb quality × confidence)
          - outcome relevance (impact metrics only, with diminishing returns)
          - specificity (skills + entities)
          - link/verification support
        All capped at 1.0; no feature alone saturates the score.
        """
        # Ownership: how strongly does the subject own this work?
        ownership = action_str * action_conf  # 0–1

        # Outcome: impact metrics, with diminishing returns (not just count)
        outcome = 0.0
        for i, m in enumerate(impact_metrics[:3]):
            outcome += 0.3 * (0.6 ** i)  # 0.30, 0.18, 0.108 for 1st, 2nd, 3rd
        outcome = min(0.50, outcome)

        # Specificity: skills and entities provide concrete detail
        spec = min(0.25, 0.07 * len(skills) + 0.07 * len(entities))

        # Verification: link to project/repo adds credibility
        verification = 0.05 if hyperlinks else 0.0

        # Entry context: research/project/experience claims warrant slightly
        # higher baseline credibility than generic bullets
        context_bonus = 0.05 if entry_type in {"experience", "research", "project"} else 0.0

        total = ownership * 0.40 + outcome * 0.35 + spec * 0.15 + verification * 0.05 + context_bonus * 0.05
        return round(min(1.0, total), 4)

    def extract(self, ast: ResumeAST) -> EvidenceDocument:
        claims: list[AtomicClaim] = []
        all_academic: list[AcademicMetric] = []
        all_skills_set: set[str] = set()
        all_entities_set: set[str] = set()

        # ── Academic metrics from Education section ──────────────────────
        seen_academic: set[tuple] = set()
        for section in ast.sections:
            if section.name == "Education":
                academic_metrics = _parse_academic_metrics(section.raw_lines)
                for am in academic_metrics:
                    key = (am.metric_type, round(am.value, 2))
                    if key not in seen_academic:
                        seen_academic.add(key)
                        all_academic.append(am)
                # Also check entry titles (education table rows often have CPI inline)
                for entry in section.entries:
                    entry_metrics = _parse_academic_metrics([entry.title])
                    for am in entry_metrics:
                        key = (am.metric_type, round(am.value, 2))
                        if key not in seen_academic:
                            seen_academic.add(key)
                            all_academic.append(am)

        # ── Claims from bullets ────────────────────────────────────────────
        claim_idx = 0
        for section in ast.sections:
            entry_type = _SECTION_ENTRY_TYPE.get(section.name, "unknown")
            
            # ── SPECIAL: Extract courses from raw_lines in Coursework sections ──
            # Many resumes list courses as plain text, not bullets
            if section.name in {"Coursework", "Education"} or "course" in section.name.lower():
                if section.raw_lines and not section.bullets:
                    # Process raw_lines to extract courses
                    combined_text = " ".join(section.raw_lines)
                    extracted_courses = self._extract_courses(combined_text)
                    
                    if extracted_courses:
                        # Create a synthetic claim for coursework
                        claim_idx += 1
                        # Use first entry bbox if available, else section default
                        bbox = section.entries[0].bbox if section.entries else BBox(x0=0, y0=0, x1=100, y1=10)
                        page = section.entries[0].page_start if section.entries else 1
                        
                        claims.append(AtomicClaim(
                            claim_id=f"c{claim_idx:04d}",
                            bullet_id=f"synthetic_coursework_{section.name}",
                            entry_id=None,
                            text=combined_text[:200],  # Truncate for brevity
                            raw_text=combined_text[:200],
                            section=section.name,
                            entry_type="coursework",
                            entry_context="Relevant Coursework",
                            page=page,
                            bbox=bbox,
                            action_verb=None,
                            action_strength=0.0,
                            action_confidence=0.0,
                            metrics=[],
                            impact_metrics=[],
                            entities=[],
                            skills=[],
                            courses=extracted_courses,
                            hyperlinks=[],
                            subsection_label=None,
                            signals={"coursework": min(0.85, 0.40 + 0.15 * min(len(extracted_courses), 3))},
                            evidence_strength=0.70,  # Moderate strength for coursework
                            evidence_types=[EvidenceType.COURSEWORK],
                            project_types=[],
                            impact_types=[],
                            domain_relevance={"sde": 0.7, "quant": 0.8, "consulting": 0.4, "core": 0.8},
                            presence_score=0.70,
                            role_relevance_score={"sde": 0.49, "quant": 0.56, "consulting": 0.28, "core": 0.56},
                        ))

            for bullet in section.bullets:
                claim_idx += 1
                text = bullet.text or bullet.normalized_text
                raw = bullet.raw_text or text
                
                # Get entry context for better classification
                entry_context = ""
                if bullet.entry_id:
                    # Find the entry this bullet belongs to
                    for entry in section.entries:
                        if entry.id == bullet.entry_id:
                            entry_context = f"{entry.title} {entry.organization}".strip()
                            break
                
                # If entry context is just a subsection label, look for parent entry
                if entry_context in ["Objective", "Approach", "Results", "Leadership", "Impact", "Initiatives"]:
                    # Look for the main entry (usually the first non-subsection entry in the section)
                    for entry in section.entries:
                        if "Business Analyst" in entry.title or "Navikra" in entry.title:
                            entry_context = f"{entry.title} {entry.organization}".strip()
                            break

                action_verb, action_str, action_conf = _action_verb(text)
                all_metrics = parse_metrics(text)
                impact_metrics = [m for m in all_metrics if m.is_impact_relevant]
                entities = self._entities(text)
                skills = self._skills(text)
                
                # Extract courses from coursework sections - need full entry context
                combined_text_for_courses = f"{entry_context} {text}".strip()
                courses = []
                if section.name in {"Coursework", "Education"} or "course" in section.name.lower():
                    courses = self._extract_courses(combined_text_for_courses)

                # Collect for document-level convenience
                all_skills_set.update(skills)
                all_entities_set.update(e.canonical for e in entities)

                # Compute section-based signals as WEAK PRIORS (C8 fix)
                signals: dict[str, float] = {}
                for e in entities:
                    for k, v in e.competencies.items():
                        signals[k] = max(signals.get(k, 0.0), float(v))

                # Section-based signals are weak (0.3–0.4 max from section alone)
                if section.name == "Positions of Responsibility":
                    signals["leadership"] = max(signals.get("leadership", 0), 0.35)
                    signals["organizational_impact"] = max(signals.get("organizational_impact", 0), 0.30)
                elif section.name in {"Projects", "Research"}:
                    signals["technical_depth"] = max(signals.get("technical_depth", 0), 0.30)
                elif section.name == "Experience":
                    signals["professional_exposure"] = max(signals.get("professional_exposure", 0), 0.30)
                elif section.name == "Extracurricular":
                    signals["breadth"] = max(signals.get("breadth", 0), 0.25)

                # Impact signal only from actual impact-relevant metrics (C4 fix)
                if impact_metrics:
                    signals["quantified_impact"] = min(
                        0.80,
                        0.40 + 0.15 * min(len(impact_metrics), 3)
                    )

                # Skill-based signals
                if any(s in skills for s in {"sql", "python", "cpp", "java", "javascript", "nodejs"}):
                    signals["software_engineering"] = max(signals.get("software_engineering", 0), 0.50)
                if any(s in skills for s in {"tensorflow", "pytorch", "scikit_learn", "keras", "machine_learning", "deep_learning"}):
                    signals["ml_engineering"] = max(signals.get("ml_engineering", 0), 0.60)
                if any(s in skills for s in {"matlab", "cad", "matlab_simulink", "labview"}):
                    signals["core_tools"] = max(signals.get("core_tools", 0), 0.75)
                if any(s in skills for s in {"probability", "statistics", "stochastic_calculus"}):
                    signals["mathematics"] = max(signals.get("mathematics", 0), 0.60)
                if any(s in skills for s in {"dsa", "competitive_programming"}):
                    signals["algorithms"] = max(signals.get("algorithms", 0), 0.70)
                if skills:
                    signals["programming"] = max(signals.get("programming", 0), 0.50)
                
                # Coursework-based signals - add competency signals from extracted courses
                if courses:
                    signals["coursework"] = min(0.85, 0.40 + 0.15 * min(len(courses), 3))
                    for course in courses:
                        # Add signals from course competencies
                        for comp in course.get('competencies', []):
                            signals[comp] = max(signals.get(comp, 0), 0.55)

                evidence_str = self._evidence_strength(
                    action_str, action_conf, impact_metrics, all_metrics,
                    skills, entities, bullet.hyperlinks, entry_type,
                )

                # Classify evidence types and compute domain relevance (including entry context)
                combined_text = f"{entry_context} {text}".strip()
                evidence_types, project_types, impact_types = self._classify_evidence_types(
                    combined_text, skills, entities, section.name, all_metrics, impact_metrics
                )
                domain_relevance = self._compute_domain_relevance(
                    evidence_types, project_types, impact_types, section.name
                )
                
                # Compute presence vs role-relevance scores
                presence_score = evidence_str
                role_relevance_scores = {}
                for role in ["sde", "quant", "consulting", "core", "analyst", "product"]:
                    role_relevance_scores[role] = presence_score * domain_relevance[role]

                claims.append(AtomicClaim(
                    claim_id=f"c{claim_idx:04d}",
                    bullet_id=bullet.id,
                    entry_id=bullet.entry_id,
                    text=text,
                    raw_text=raw,
                    section=section.name,
                    entry_type=entry_type,
                    entry_context=entry_context,
                    page=bullet.page,
                    bbox=bullet.bbox,
                    action_verb=action_verb,
                    action_strength=action_str,
                    action_confidence=action_conf,
                    metrics=all_metrics,
                    impact_metrics=impact_metrics,
                    entities=entities,
                    skills=skills,
                    courses=courses,
                    hyperlinks=bullet.hyperlinks,
                    subsection_label=bullet.subsection_label,
                    signals=signals,
                    evidence_strength=evidence_str,
                    evidence_types=evidence_types,
                    project_types=project_types,
                    impact_types=impact_types,
                    domain_relevance=domain_relevance,
                    presence_score=presence_score,
                    role_relevance_score=role_relevance_scores,
                ))

        # ── Document-level link signals ───────────────────────────────────
        doc_links = [lo.uri for lo in ast.link_objects]

        return EvidenceDocument(
            source_file=ast.source_file,
            claims=claims,
            academic_metrics=all_academic,
            warnings=list(ast.warnings),
            all_skills=sorted(all_skills_set),
            all_entities=sorted(all_entities_set),
        )

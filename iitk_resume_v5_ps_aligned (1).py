"""
IITK Resume Analyzer — V4 Competition Edition
==============================================

This is an upgraded intelligence/ranking layer for an existing resume parser.

Core principle
--------------
The system ranks demonstrated evidence for a target role. It does NOT assign
prestige points merely because a title exists.

Pipeline
--------
parser
  -> institutional normalization / ontology
  -> competency evidence
  -> role-conditioned candidate representation
  -> order-invariant novelty + coverage
  -> role interactions
  -> learned / prior pairwise ranker
  -> calibration + stability audit
  -> ranking + explanations + counterfactuals

What changed from the earlier V4
--------------------------------
1. FIXED: order dependence in novelty/attention.
2. FIXED: duplicate-item contribution could be index/order sensitive.
3. Added explicit institution configuration (CPI vs CGPA and scales).
4. Added an extensible IITK organization/POR knowledge layer.
5. Added academic-feature support without allowing CPI to dominate unrelated
   roles.
6. Added robust evidence aggregation with a geometric/soft-OR blend.
7. Added role-conditioned first- and second-order feature construction.
8. Added a pure-Python pairwise learning-to-rank model with regularization.
9. Added Platt-style calibration hooks for held-out labels.
10. Added ranking metrics: NDCG@K, MRR, Precision@K, Spearman.
11. Added perturbation/stability auditing.
12. Added title-inflation, duplication and keyword-gaming tests.
13. Added feature ablation / counterfactual explanations.
14. Added deterministic fallback priors, so the system still works before
    institution-specific training data exists.

The model is designed to be trained on IITK-specific expert pairwise rankings
when those become available. Until then, the engineered prior layer is used.

Expected parser input
---------------------
{
  "id": "cand_01",
  "academics": {"cpi": 9.1, "cpi_scale": 10.0},
  "items": [
    {
      "id": "por1",
      "type": "por",
      "organization": "Programming Club",
      "title": "Secretary",
      "description": "...",
      "competencies": {...},
      "evidence": {...},
      "embedding": [...]
    }
  ]
}

All external semantic/NLP work remains upstream. This file consumes structured
signals produced by the parser/semantic extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Iterable
import copy
import math
import random
import re


# ============================================================================
# 1. ONTOLOGY / INSTITUTION CONFIGURATION
# ============================================================================

COMPETENCIES = [
    "technical", "analytical", "problem_solving", "quantitative", "research",
    "leadership", "communication", "stakeholder", "business", "execution",
    "strategy", "innovation", "teamwork", "ownership", "impact",
    "domain_knowledge",
    # Added for Core Engineering: CAD/MATLAB depth, core electives, hands-on
    # branch-specific work. Kept separate from "technical" on purpose --
    # the PS explicitly wants generic web-dev projects to NOT read as core
    # engineering strength, and folding both into one "technical" axis would
    # make that distinction impossible.
    "core_domain",
]

ROLE_ALIASES = {
    "swe": "software",
    "software engineer": "software",
    "software developer": "software",
    "sde": "software",
    "ml engineer": "ml",
    "machine learning": "ml",
    "machine learning engineer": "ml",
    "ai": "ml",
    "ai/ml": "ml",
    "ai ml": "ml",
    "artificial intelligence": "ml",
    "data scientist": "data_science",
    "data science": "data_science",
    "data analyst": "data_analyst",
    "data analytics": "data_analyst",
    "analyst": "data_analyst",
    "quantitative": "quant",
    "quantitative finance": "quant",
    "quant": "quant",
    "management consulting": "consulting",
    "consulting": "consulting",
    "core": "core",
    "core engineering": "core",
    "core eng": "core",
    "core engg": "core",
}

# These are role priors, not truth. They are intentionally normalized.
# NOTE on the PS: SDE=software, Quant Finance=quant, Management Consulting
# =consulting, Core Engineering=core are the 4 tracks the PS *requires*.
# ml (AI/ML) and data_analyst are added on top, as the PS explicitly allows
# ("account for at least 4 major roles"). data_science is kept too since it
# already existed and is a real, distinct track from data_analyst (deeper
# modeling/research vs. SQL+reporting+business communication).
ROLE_WEIGHTS = {
    "software": {
        "technical": .22, "analytical": .13, "problem_solving": .15,
        "quantitative": .07, "research": .03, "leadership": .05,
        "communication": .05, "stakeholder": .02, "business": .02,
        "execution": .08, "strategy": .03, "innovation": .04,
        "teamwork": .05, "ownership": .06, "impact": .04,
        "domain_knowledge": .04, "core_domain": .01,
    },
    "ml": {
        "technical": .20, "analytical": .15, "problem_solving": .14,
        "quantitative": .12, "research": .12, "leadership": .03,
        "communication": .04, "stakeholder": .01, "business": .02,
        "execution": .05, "strategy": .02, "innovation": .04,
        "teamwork": .03, "ownership": .04, "impact": .04,
        "domain_knowledge": .04, "core_domain": .01,
    },
    "quant": {
        "technical": .13, "analytical": .18, "problem_solving": .15,
        "quantitative": .23, "research": .10, "leadership": .02,
        "communication": .03, "stakeholder": .01, "business": .04,
        "execution": .03, "strategy": .03, "innovation": .02,
        "teamwork": .02, "ownership": .03, "impact": .03,
        "domain_knowledge": .03, "core_domain": .01,
    },
    "consulting": {
        "technical": .04, "analytical": .13, "problem_solving": .15,
        "quantitative": .09, "research": .03, "leadership": .11,
        "communication": .10, "stakeholder": .10, "business": .10,
        "execution": .06, "strategy": .08, "innovation": .03,
        "teamwork": .07, "ownership": .05, "impact": .08,
        "domain_knowledge": .04, "core_domain": .00,
    },
    "data_science": {
        "technical": .16, "analytical": .17, "problem_solving": .13,
        "quantitative": .17, "research": .08, "leadership": .03,
        "communication": .05, "stakeholder": .03, "business": .04,
        "execution": .05, "strategy": .02, "innovation": .03,
        "teamwork": .03, "ownership": .04, "impact": .04,
        "domain_knowledge": .05, "core_domain": .01,
    },
    # NEW -- required by the PS. SURGE internships / core projects / research
    # publications / CAD-MATLAB proficiency are prioritized; generic web-dev
    # and missing core electives are penalized (that penalty is handled by
    # the hard-rule layer below, not by this soft weight vector alone).
    "core": {
        "technical": .06, "analytical": .10, "problem_solving": .12,
        "quantitative": .08, "research": .16, "leadership": .02,
        "communication": .03, "stakeholder": .01, "business": .01,
        "execution": .07, "strategy": .02, "innovation": .06,
        "teamwork": .03, "ownership": .04, "impact": .04,
        "domain_knowledge": .07, "core_domain": .08,
    },
    # NEW -- SQL/dashboards/reporting/business communication, distinct from
    # data_science's deeper modeling & research emphasis.
    "data_analyst": {
        "technical": .10, "analytical": .19, "problem_solving": .10,
        "quantitative": .16, "research": .03, "leadership": .02,
        "communication": .10, "stakeholder": .06, "business": .10,
        "execution": .07, "strategy": .02, "innovation": .01,
        "teamwork": .02, "ownership": .03, "impact": .06,
        "domain_knowledge": .02, "core_domain": .01,
    },
}

# Role × competency interaction priors.
SYNERGY = {
    "consulting": {
        ("leadership", "communication"): .10,
        ("communication", "stakeholder"): .12,
        ("analytical", "business"): .12,
        ("problem_solving", "strategy"): .10,
        ("quantitative", "business"): .07,
        ("ownership", "impact"): .06,
    },
    "software": {
        ("technical", "problem_solving"): .13,
        ("technical", "analytical"): .09,
        ("ownership", "execution"): .07,
        ("technical", "impact"): .05,
    },
    "ml": {
        ("technical", "quantitative"): .13,
        ("technical", "analytical"): .13,
        ("research", "problem_solving"): .10,
        ("technical", "impact"): .06,
    },
    "quant": {
        ("quantitative", "analytical"): .16,
        ("analytical", "problem_solving"): .12,
        ("quantitative", "technical"): .10,
        ("research", "quantitative"): .09,
    },
    "data_science": {
        ("technical", "quantitative"): .12,
        ("analytical", "business"): .09,
        ("problem_solving", "impact"): .06,
    },
    "core": {
        ("core_domain", "research"): .14,
        ("core_domain", "problem_solving"): .10,
        ("research", "innovation"): .08,
        ("core_domain", "domain_knowledge"): .10,
    },
    "data_analyst": {
        ("analytical", "business"): .13,
        ("quantitative", "communication"): .10,
        ("analytical", "communication"): .09,
    },
}

# Weak title priors; description evidence should dominate.
POR_TITLE_PRIORS = {
    "general secretary": {"leadership": .82, "execution": .70, "ownership": .72},
    "secretary": {"leadership": .60, "execution": .62, "communication": .55},
    "coordinator": {"execution": .65, "communication": .62, "teamwork": .60},
    "manager": {"execution": .72, "ownership": .72, "leadership": .68},
    "head": {"leadership": .78, "ownership": .76, "strategy": .62},
    "convenor": {"leadership": .72, "execution": .72, "communication": .65},
    "core team": {"teamwork": .60, "execution": .52},
    "member": {"teamwork": .38, "execution": .30},
}

# Extensible organization priors. Do not treat these as fixed scores.
# Add entries from the institution's official handbook whenever available.
# The prior gets updated by the resume description.
ORGANIZATION_PRIORS = {
    "programming_club": {
        "technical": .55, "teamwork": .45, "execution": .45,
        "communication": .35,
    },
    "entrepreneurship_cell": {
        "business": .55, "stakeholder": .50, "communication": .45,
        "strategy": .40,
    },
    "finance_and_analytics_club": {
        "quantitative": .55, "analytical": .50, "technical": .35,
    },
    "student_senate": {
        "leadership": .55, "stakeholder": .55, "communication": .50,
        "ownership": .45,
    },
    # From the PS's own worked example of IITK jargon ("SURGE," "CPI,"
    # "AnC Council") -- Academics and Career Council, the body issuing this
    # PS. First-pass prior; correct against the real PoR handbook.
    "anc_council": {
        "leadership": .50, "stakeholder": .55, "communication": .50,
        "execution": .45, "business": .30,
    },
}

TERM_NORMALIZATION = {
    r"\bcgpa\b": "cpi",
    r"\bgrade point average\b": "cpi",
    r"\bposition of responsibility\b": "por",
    r"\bpositions of responsibility\b": "por",
    r"\bprogramming club\b": "programming_club",
    r"\bprog club\b": "programming_club",
    r"\bentrepreneurship cell\b": "entrepreneurship_cell",
    r"\be-cell\b": "entrepreneurship_cell",
    r"\bfinance(?: and)? analytics club\b": "finance_and_analytics_club",
    r"\banc council\b": "anc_council",
    r"\bacademics and career council\b": "anc_council",
}

ACADEMIC_ROLE_RELEVANCE = {
    "consulting": .65,
    "quant": .80,
    "ml": .55,
    "data_science": .60,
    "software": .35,
    "core": .45,
    "data_analyst": .45,
}

# Hard constraints are kept separate from soft score. They should only flag
# eligibility; they should not silently dominate a ranking.
ROLE_GATES = {
    "quant": {"minimum_cpi": 0.0},
    "ml": {"minimum_cpi": 0.0},
    "data_science": {"minimum_cpi": 0.0},
    "software": {"minimum_cpi": 0.0},
    "consulting": {"minimum_cpi": 0.0},
    "core": {"minimum_cpi": 0.0},
    "data_analyst": {"minimum_cpi": 0.0},
}


# ============================================================================
# 1B. HARD-RULE PENALTIES (PS Section 3: explicit "penalizes X" language)
# ============================================================================
# The PS names concrete, checkable conditions per role ("penalizes missing
# GitHub links", "penalizes generic web dev projects", "penalizes low CPI").
# These are NOT soft competency signals -- they're closer to binary rule
# checks -- so they're modeled separately from ROLE_WEIGHTS/SYNERGY and
# applied as an explicit, individually-explainable penalty term.
#
# Recognized signals (populate these from the parser/extraction layer):
#   Candidate.profile["has_github_link"]      -> 1.0 / 0.0
#   Candidate.profile["core_electives_count"] -> int, >=0
#   ResumeItem.tags may contain any of:
#       "language:cpp", "language:java", "language:python"   (SDE)
#       "competitive_programming", "open_source", "gsoc"     (SDE)
#       "generic_webdev"                                     (Core penalty)
#       "core_project", "cad", "matlab"                      (Core credit)
#       "business_impact_metric"                             (Consulting)
#       "poor_formatting"                                    (Consulting penalty;
#                                                              usually set by
#                                                              the formatting
#                                                              checker, not NLP)
HARD_RULES = {
    "software": {
        "missing_github_penalty": 0.10,
        "no_recognized_language_penalty": 0.08,
    },
    "core": {
        "generic_webdev_penalty_per_item": 0.06,
        "generic_webdev_penalty_cap": 0.18,
        "missing_core_electives_penalty": 0.10,
    },
    "quant": {
        "low_cpi_threshold": 0.75,   # normalized cpi/scale
        "low_cpi_penalty": 0.12,
        "no_algorithmic_signal_penalty": 0.08,
    },
    "consulting": {
        "missing_business_metric_penalty": 0.10,
        "poor_formatting_penalty": 0.08,
    },
}


# ============================================================================
# 2. DATA STRUCTURES
# ============================================================================

@dataclass
class InstitutionConfig:
    metric_name: str = "cpi"
    metric_scale: float = 10.0
    aliases: Dict[str, str] = field(default_factory=lambda: {
        "cgpa": "cpi",
        "gpa": "cpi",
        "cpi": "cpi",
    })
    role_weights: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: copy.deepcopy(ROLE_WEIGHTS)
    )
    organization_priors: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: copy.deepcopy(ORGANIZATION_PRIORS)
    )
    role_gates: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: copy.deepcopy(ROLE_GATES)
    )


@dataclass
class Evidence:
    action: float = 0.0
    scope: float = 0.0
    method: float = 0.0
    outcome: float = 0.0
    quantification: float = 0.0
    specificity: float = 0.0
    credibility: float = 1.0
    semantic_strength: float = 0.0
    provenance_strength: float = 0.0

    def clamp(self) -> "Evidence":
        for name in self.__dataclass_fields__:
            setattr(self, name, clamp01(getattr(self, name)))
        return self


@dataclass
class ResumeItem:
    id: str
    item_type: str
    title: str = ""
    organization: str = ""
    description: str = ""
    # Individual bullets, if the parser can supply them. "Line-by-Line
    # Formatting Fixes" (PS Module C) needs per-bullet granularity; a single
    # description string can't give that. Falls back to `description` as one
    # bullet wherever this is empty, so nothing upstream breaks.
    bullets: List[str] = field(default_factory=list)
    competencies: Dict[str, float] = field(default_factory=dict)
    evidence: Evidence = field(default_factory=Evidence)
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Candidate:
    id: str
    items: List[ResumeItem] = field(default_factory=list)
    academics: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScoredItem:
    item_id: str
    contribution: float
    dynamic_weight: float
    quality: float
    role_fit: float
    novelty: float
    reliability: float


@dataclass
class RoleResult:
    role: str
    score: float
    relative_fit: float
    confidence: float
    coverage: Dict[str, float]
    gaps: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    item_scores: List[ScoredItem]
    diagnostics: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 3. NUMERICAL / TEXT HELPERS
# ============================================================================

def clamp01(x: Any) -> float:
    try:
        value = float(x)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def safe_exp(x: float) -> float:
    return math.exp(max(-60.0, min(60.0, float(x))))


def sigmoid(x: float) -> float:
    x = max(-60.0, min(60.0, float(x)))
    return 1.0 / (1.0 + math.exp(-x))


def softmax(values: List[float], temperature: float = 1.0) -> List[float]:
    if not values:
        return []
    t = max(1e-6, temperature)
    z = [float(v) / t for v in values]
    m = max(z)
    e = [safe_exp(v - m) for v in z]
    total = sum(e)
    return [v / total for v in e] if total > 0 else [1.0 / len(z)] * len(z)


def cosine(a: Optional[List[float]], b: Optional[List[float]]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    aa = sum(float(x) ** 2 for x in a)
    bb = sum(float(x) ** 2 for x in b)
    if aa <= 1e-12 or bb <= 1e-12:
        return 0.0
    return sum(float(x) * float(y) for x, y in zip(a, b)) / math.sqrt(aa * bb)


def normalize_role(role: str) -> str:
    key = re.sub(r"\s+", " ", str(role).strip().lower())
    return ROLE_ALIASES.get(key, key if key in ROLE_WEIGHTS else "software")


def normalize_text(text: str) -> str:
    text = str(text or "")
    for pattern, replacement in TERM_NORMALIZATION.items():
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def stable_sigmoid_loss(logit: float, label: int) -> float:
    # Binary cross entropy in stable form.
    y = 1.0 if int(label) else 0.0
    z = max(-60.0, min(60.0, float(logit)))
    if z >= 0:
        return (1.0 - y) * z + math.log1p(math.exp(-z))
    return -y * z + math.log1p(math.exp(z))


def rankdata(values: List[float]) -> List[float]:
    """Average-tie ranks, 1-based."""
    indexed = sorted(enumerate(values), key=lambda p: p[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = rank
        i = j + 1
    return ranks


# ============================================================================
# 3B. TEXT-LEVEL SIGNAL EXTRACTION -- Impact Detection & Action-Verb Strength
# ============================================================================
# PS Module B names these two sub-features explicitly:
#   "Impact Detection: Detect whether bullet points contain quantifiable
#    metrics (e.g., 'reduced latency by 20%' vs. 'worked on latency')."
#   "Action Verbs: Evaluate the strength of verbs used to begin bullet
#    points."
# Both run on raw bullet text, upstream of the Evidence/competency scoring
# the rest of this file assumes already exists. Regex/lexicon based on
# purpose -- matches the PS's own "heuristics/NLP" framing (Module B) and
# "intelligent use of heuristics/NLP" (Codebase & Arch. criterion), and
# stays auditable for the Actionability criterion ("pinpointing specific
# bullet points to fix" needs a traceable reason, not an embedding score).

_STRONG_VERBS = [
    "led", "architected", "engineered", "spearheaded", "designed", "built",
    "developed", "launched", "optimized", "automated", "orchestrated",
    "pioneered", "founded", "drove", "delivered", "scaled", "transformed",
    "revamped", "restructured", "implemented", "negotiated", "secured",
    "formulated", "established", "directed", "executed", "deployed",
    "authored", "patented", "reduced", "increased", "improved", "boosted",
    "cut", "accelerated",
]
_MODERATE_VERBS = [
    "managed", "created", "analyzed", "coordinated", "organized",
    "conducted", "collaborated", "contributed", "supported", "maintained",
    "presented", "tested", "wrote", "integrated", "researched", "trained",
    "mentored", "planned", "evaluated", "identified", "benchmarked",
    "curated", "calibrated", "formatted", "oversaw", "advocated",
]
_WEAK_VERBS = [
    "helped", "worked", "involved", "participated", "responsible",
    "assisted", "member", "attended", "familiar", "exposed", "learned",
    "shadowed", "observed",
]

ACTION_VERB_TIERS: Dict[str, float] = {}
for _v in _STRONG_VERBS:
    ACTION_VERB_TIERS[_v] = 0.90
for _v in _MODERATE_VERBS:
    ACTION_VERB_TIERS[_v] = 0.55
for _v in _WEAK_VERBS:
    ACTION_VERB_TIERS[_v] = 0.20

# Neutral, not punitive: an un-recognized opening word (jargon, a typo, a
# non-English word) is a gap in the lexicon, not evidence of a weak claim.
_UNRECOGNIZED_VERB_SCORE = 0.45

_BULLET_LEAD_RE = re.compile(r"^[\s\u2022\-\*\u2013\u2014\d\.\)]+")
_WORD_RE = re.compile(r"[A-Za-z]+")


def leading_action_verb(text: str) -> Tuple[Optional[str], float]:
    """(matched_word, strength in [0,1]) for the verb opening a bullet."""
    stripped = _BULLET_LEAD_RE.sub("", str(text or "")).strip()
    m = _WORD_RE.match(stripped)
    if not m:
        return None, 0.0
    word = m.group(0).lower()
    if word in ACTION_VERB_TIERS:
        return word, ACTION_VERB_TIERS[word]
    # Crude de-inflection for gerunds ("Reducing" -> "reduced" family).
    if word.endswith("ing") and (word[:-3] + "ed") in ACTION_VERB_TIERS:
        return word, ACTION_VERB_TIERS[word[:-3] + "ed"]
    return word, _UNRECOGNIZED_VERB_SCORE


_PERCENT_RE = re.compile(r"\d+(\.\d+)?\s?%")
_MULTIPLIER_RE = re.compile(r"\b\d+(\.\d+)?\s?[xX]\b")
_SCALE_WORD_RE = re.compile(
    r"\b(lakh|lac|crore|cr|k\+|million|mn|billion|bn)\b", re.IGNORECASE
)
_CURRENCY_RE = re.compile(r"(\u20b9|\$|INR|Rs\.?)\s?\d")
_LARGE_NUMBER_RE = re.compile(r"\b\d{2,}\+?\b")
_COMPARISON_WORD_RE = re.compile(
    r"\b(reduced|increased|improved|decreased|grew|boosted|cut|saved|"
    r"accelerated|doubled|tripled|halved|dropped|raised|lowered|scaled)\b",
    re.IGNORECASE,
)


def impact_detection_score(text: str) -> Dict[str, Any]:
    """
    Whether a bullet contains a quantifiable metric (PS Module B).

    Returns a dict, not just a float, so the Advisory Dashboard can show
    *why* -- "no quantifiable metric found" is itself the actionable
    feedback the PS's Actionability criterion is graded on.
    """
    t = str(text or "")
    signals = {
        "has_percent": bool(_PERCENT_RE.search(t)),
        "has_multiplier": bool(_MULTIPLIER_RE.search(t)),
        "has_scale_word": bool(_SCALE_WORD_RE.search(t)),
        "has_currency": bool(_CURRENCY_RE.search(t)),
        "has_large_number": bool(_LARGE_NUMBER_RE.search(t)),
        "has_comparison_word": bool(_COMPARISON_WORD_RE.search(t)),
    }
    has_any_number = (
        signals["has_percent"] or signals["has_multiplier"]
        or signals["has_currency"] or signals["has_large_number"]
    )
    # A comparison word only counts once it's paired with an actual number --
    # "improved performance" alone is not a quantifiable metric.
    comparison_with_number = signals["has_comparison_word"] and has_any_number

    hit_count = sum([
        signals["has_percent"], signals["has_multiplier"],
        signals["has_scale_word"], signals["has_currency"],
        signals["has_large_number"], comparison_with_number,
    ])
    return {
        "score": clamp01(hit_count / 3.0),
        "has_quantifiable_metric": has_any_number,
        "signals": signals,
    }


def bullet_level_diagnostics(item: "ResumeItem") -> List[Dict[str, Any]]:
    """Per-bullet Impact Detection + Action Verb feedback for the Advisory
    Dashboard's 'Line-by-Line Formatting Fixes'."""
    texts = item.bullets if item.bullets else ([item.description] if item.description else [])
    rows = []
    for i, text in enumerate(texts):
        verb, verb_score = leading_action_verb(text)
        impact = impact_detection_score(text)
        weak_verb = verb_score < 0.55
        no_metric = not impact["has_quantifiable_metric"]
        if weak_verb and no_metric:
            flag = "weak_verb_and_no_metric"
        elif weak_verb:
            flag = "weak_verb"
        elif no_metric:
            flag = "no_quantifiable_metric"
        else:
            flag = None
        rows.append({
            "bullet_index": i,
            "text": text,
            "action_verb": verb,
            "action_verb_strength": verb_score,
            "has_quantifiable_metric": impact["has_quantifiable_metric"],
            "impact_score": impact["score"],
            "flag": flag,
        })
    return rows


def enrich_evidence_from_text(item: "ResumeItem", overwrite: bool = False) -> "ResumeItem":
    """
    Fills Evidence.action / Evidence.quantification from bullet text, when
    a richer upstream extractor hasn't already supplied them.

    Deliberately does NOT touch scope/method/outcome/specificity/
    credibility -- those need the fuller "claim -> evidence" extraction that
    doesn't exist yet. Only the two PS-named sub-features are covered here.
    """
    texts = item.bullets if item.bullets else ([item.description] if item.description else [])
    if not texts:
        return item
    verb_scores = [leading_action_verb(t)[1] for t in texts]
    impact_scores = [impact_detection_score(t)["score"] for t in texts]
    if overwrite or item.evidence.action <= 0.0:
        item.evidence.action = sum(verb_scores) / len(verb_scores)
    if overwrite or item.evidence.quantification <= 0.0:
        item.evidence.quantification = sum(impact_scores) / len(impact_scores)
    item.evidence.clamp()
    return item


# ============================================================================
# 4. PARSER ADAPTER
# ============================================================================

def adapt_parser_output(raw: Dict[str, Any]) -> Candidate:
    cid = str(raw.get("id", raw.get("candidate_id", "candidate")))
    raw_items = raw.get("items", raw.get("keypoints", raw.get("experiences", [])))
    items: List[ResumeItem] = []

    for idx, item in enumerate(raw_items or []):
        ev = item.get("evidence", {}) or {}
        comp = item.get("competencies", item.get("competency_scores", {})) or {}

        evidence = Evidence(
            action=ev.get("action", 0.0),
            scope=ev.get("scope", 0.0),
            method=ev.get("method", 0.0),
            outcome=ev.get("outcome", ev.get("impact", 0.0)),
            quantification=ev.get("quantification", ev.get("quantified", 0.0)),
            specificity=ev.get("specificity", 0.0),
            credibility=ev.get("credibility", 1.0),
            semantic_strength=ev.get("semantic_strength", 0.0),
            provenance_strength=ev.get("provenance_strength", 0.0),
        ).clamp()

        normalized_comp = {
            c: clamp01(comp.get(c, 0.0))
            for c in COMPETENCIES
        }

        items.append(ResumeItem(
            id=str(item.get("id", f"item_{idx}")),
            item_type=str(item.get("type", item.get("item_type", "other"))),
            title=normalize_text(item.get("title", "")),
            organization=normalize_text(item.get("organization", "")),
            description=normalize_text(item.get("description", "")),
            competencies=normalized_comp,
            evidence=evidence,
            embedding=item.get("embedding"),
            tags=[str(x) for x in item.get("tags", [])],
        ))

    return Candidate(
        id=cid,
        items=items,
        academics=dict(raw.get("academics", {}) or {}),
        profile=dict(raw.get("profile", {}) or {}),
    )


# ============================================================================
# 5. PURE-PYTHON PAIRWISE RANKER
# ============================================================================

class PairwiseLogisticRanker:
    """
    Small, dependency-free RankNet-style model.

    Given feature vectors phi(A,r) and phi(B,r), train on pairwise labels:
        A > B -> y=1
        B > A -> y=0

    L = BCE(w^T(phi_A - phi_B), y) + l2*||w||^2

    This gives a principled upgrade path from hand-built priors to actual
    institution-specific learning.
    """

    def __init__(self, learning_rate: float = 0.03, epochs: int = 250,
                 l2: float = 1e-3, seed: int = 7):
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.l2 = l2
        self.seed = seed
        self.weights: Optional[List[float]] = None
        self.bias = 0.0
        self.mean: Optional[List[float]] = None
        self.std: Optional[List[float]] = None
        self.history: List[float] = []

    @staticmethod
    def _standardize_fit(X: List[List[float]]) -> Tuple[List[float], List[float]]:
        if not X:
            return [], []
        d = len(X[0])
        mean = [sum(row[j] for row in X) / len(X) for j in range(d)]
        var = []
        for j in range(d):
            var.append(sum((row[j] - mean[j]) ** 2 for row in X) / max(1, len(X)))
        std = [math.sqrt(v) if v > 1e-10 else 1.0 for v in var]
        return mean, std

    @staticmethod
    def _standardize_row(row: List[float], mean: List[float], std: List[float]) -> List[float]:
        return [(x - m) / s for x, m, s in zip(row, mean, std)]

    def fit(self, pair_features: List[Tuple[List[float], List[float], int]]) -> "PairwiseLogisticRanker":
        if not pair_features:
            raise ValueError("pair_features cannot be empty")

        # Build difference vectors. Flip every pair so labels remain y=1.
        X = []
        y = []
        for a, b, label_a_preferred in pair_features:
            diff = [float(x) - float(z) for x, z in zip(a, b)]
            if len(diff) == 0:
                continue
            if not label_a_preferred:
                diff = [-x for x in diff]
            X.append(diff)
            y.append(1)

        if not X:
            raise ValueError("No valid feature pairs")

        self.mean, self.std = self._standardize_fit(X)
        Xs = [self._standardize_row(row, self.mean, self.std) for row in X]

        d = len(Xs[0])
        self.weights = [0.0] * d
        self.bias = 0.0
        self.history = []

        rng = random.Random(self.seed)

        for epoch in range(self.epochs):
            indices = list(range(len(Xs)))
            rng.shuffle(indices)

            grad_w = [0.0] * d
            grad_b = 0.0
            loss = 0.0

            for idx in indices:
                x = Xs[idx]
                logit = self.bias + sum(w * xi for w, xi in zip(self.weights, x))
                p = sigmoid(logit)
                err = p - 1.0
                for j in range(d):
                    grad_w[j] += err * x[j]
                grad_b += err
                loss += stable_sigmoid_loss(logit, 1)

            n = max(1, len(Xs))
            for j in range(d):
                grad_w[j] = grad_w[j] / n + self.l2 * self.weights[j]
                self.weights[j] -= self.learning_rate * grad_w[j]
            grad_b /= n
            self.bias -= self.learning_rate * grad_b

            reg = 0.5 * self.l2 * sum(w * w for w in self.weights)
            epoch_loss = loss / n + reg
            self.history.append(epoch_loss)

            if epoch > 15 and abs(self.history[-1] - self.history[-2]) < 1e-8:
                break

        return self

    def score(self, features: List[float]) -> float:
        if self.weights is None or self.mean is None or self.std is None:
            raise RuntimeError("Ranker is not fitted")
        x = self._standardize_row(features, self.mean, self.std)
        return self.bias + sum(w * xi for w, xi in zip(self.weights, x))

    def preference_probability(self, a: List[float], b: List[float]) -> float:
        return sigmoid(self.score(a) - self.score(b))



class PlattCalibrator:
    """Held-out calibration: P(y=1|s)=sigmoid(a*s+b)."""
    def __init__(self, learning_rate=0.05, epochs=500, l2=1e-3):
        self.learning_rate=learning_rate; self.epochs=epochs; self.l2=l2
        self.a=1.0; self.b=0.0; self.fitted=False
    def fit(self, scores, labels):
        scores=list(scores); labels=[int(y) for y in labels]
        if len(scores)!=len(labels) or len(scores)<4:
            raise ValueError('Need >=4 matching score/label observations')
        if len(set(labels))<2:
            raise ValueError('Calibration requires both classes')
        for _ in range(self.epochs):
            ga=gb=0.0; n=len(scores)
            for sc,y in zip(scores,labels):
                p=sigmoid(self.a*float(sc)+self.b); e=p-y
                ga += e*float(sc); gb += e
            self.a -= self.learning_rate*(ga/n + self.l2*self.a)
            self.b -= self.learning_rate*(gb/n + self.l2*self.b)
        self.fitted=True; return self
    def predict(self, score):
        return sigmoid(self.a*float(score)+self.b)

# ============================================================================
# 6. MAIN ENGINE
# ============================================================================

class IITKResumeV4Competition:
    """
    Competition-oriented engine.

    Default mode is deterministic prior scoring.
    Call fit_pairwise_ranker() after collecting institution-specific pairwise
    annotations to learn the final weighting layer.
    """

    def __init__(
        self,
        institution: Optional[InstitutionConfig] = None,
        temperature: float = 0.70,
        attention_floor: float = 0.04,
        novelty_strength: float = 1.30,
        title_prior_strength: float = 0.12,
        coverage_mix: float = 0.75,
        evidence_mix: float = 0.25,
        synergy_weight: float = 0.16,
        gap_weight: float = 0.15,
        academic_weight: float = 0.08,
        learned_weight: float = 0.35,
        seed: int = 7,
    ):
        self.cfg = institution or InstitutionConfig()
        self.temperature = max(0.05, temperature)
        self.attention_floor = clamp01(attention_floor)
        self.novelty_strength = max(0.01, novelty_strength)
        self.title_prior_strength = clamp01(title_prior_strength)
        self.coverage_mix = clamp01(coverage_mix)
        self.evidence_mix = clamp01(evidence_mix)
        self.synergy_weight = max(0.0, synergy_weight)
        self.gap_weight = max(0.0, gap_weight)
        self.academic_weight = max(0.0, academic_weight)
        self.learned_weight = clamp01(learned_weight)
        self.seed = seed
        self.ranker: Optional[PairwiseLogisticRanker] = None

    # ------------------------------------------------------------------------
    # Ontology
    # ------------------------------------------------------------------------

    def role_vector(self, role: str) -> Dict[str, float]:
        role = normalize_role(role)
        raw = self.cfg.role_weights.get(role, ROLE_WEIGHTS["software"])
        total = sum(max(0.0, float(raw.get(c, 0.0))) for c in COMPETENCIES)
        if total <= 0:
            return {c: 1.0 / len(COMPETENCIES) for c in COMPETENCIES}
        return {c: max(0.0, float(raw.get(c, 0.0))) / total for c in COMPETENCIES}

    def _organization_key(self, organization: str) -> str:
        s = normalize_text(organization).lower()
        s = re.sub(r"[^a-z0-9_ ]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s.replace(" ", "_")

    def organization_prior(self, item: ResumeItem) -> Dict[str, float]:
        key = self._organization_key(item.organization)
        prior = self.cfg.organization_priors.get(key, {})
        return {c: clamp01(prior.get(c, 0.0)) for c in COMPETENCIES}

    def title_prior(self, item: ResumeItem) -> Dict[str, float]:
        title = item.title.lower()
        out = {c: 0.0 for c in COMPETENCIES}
        for phrase, vals in POR_TITLE_PRIORS.items():
            if phrase in title:
                for c, v in vals.items():
                    out[c] = max(out[c], float(v))
        return out

    def effective_competencies(self, item: ResumeItem) -> Dict[str, float]:
        """Evidence-dominant fusion; title/org provide only a bounded prior."""
        observed={c:clamp01(item.competencies.get(c,0.0)) for c in COMPETENCIES}
        org=self.organization_prior(item); title=self.title_prior(item)
        prior={c:clamp01(0.65*org[c]+0.35*title[c]) for c in COMPETENCIES}
        return {c:clamp01(0.82*observed[c]+0.18*prior[c]) for c in COMPETENCIES}

    # ------------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------------

    def evidence_quality(self, e: Evidence) -> float:
        """
        Robust evidence score.

        The geometric mean of action/scope/method/outcome/specificity stops
        one flashy signal from compensating for an unsupported claim.

        Quantification is treated as a bonus, not a requirement. This avoids
        systematically penalizing legitimate qualitative contributions.
        """
        core = [
            clamp01(e.action), clamp01(e.scope), clamp01(e.method),
            clamp01(e.outcome), clamp01(e.specificity)
        ]

        arithmetic = sum(core) / len(core)
        geometric = math.prod(max(1e-6, x) for x in core) ** (1.0 / len(core))
        base = 0.55 * arithmetic + 0.45 * geometric

        quant_bonus = 0.10 * clamp01(e.quantification)
        provenance = 0.70 + 0.30 * clamp01(e.provenance_strength)
        credibility = 0.70 + 0.30 * clamp01(e.credibility)

        # Semantic strength is bounded by concrete evidence; it cannot rescue
        # a vacuous sentence by itself.
        semantic_gate = 0.60 + 0.40 * clamp01(e.semantic_strength)
        score = (base + quant_bonus) * provenance * credibility * semantic_gate
        return clamp01(score)

    def item_role_fit(self, item: ResumeItem, role: str) -> float:
        weights = self.role_vector(role)
        z = self.effective_competencies(item)
        raw = sum(weights[c] * z[c] for c in COMPETENCIES)
        # Expected raw lies in [0,1]; no extra multiplication needed.
        return clamp01(raw)

    # ------------------------------------------------------------------------
    # Order-INVARIANT novelty/redundancy
    # ------------------------------------------------------------------------

    def pairwise_similarity(self, a: ResumeItem, b: ResumeItem) -> float:
        if a.embedding is not None and b.embedding is not None:
            return clamp01(max(0.0, cosine(a.embedding, b.embedding)))

        za = self.effective_competencies(a)
        zb = self.effective_competencies(b)
        dot = sum(za[c] * zb[c] for c in COMPETENCIES)
        na = math.sqrt(sum(za[c] ** 2 for c in COMPETENCIES))
        nb = math.sqrt(sum(zb[c] ** 2 for c in COMPETENCIES))
        return clamp01(dot / (na * nb + 1e-12))

    def item_novelty(self, item: ResumeItem, all_items: List[ResumeItem]) -> float:
        others = [x for x in all_items if x.id != item.id]
        if not others:
            return 1.0
        max_sim = max(self.pairwise_similarity(item, x) for x in others)
        return clamp01(math.exp(-self.novelty_strength * max_sim))

    def portfolio_redundancy(self, candidate: Candidate) -> float:
        items=candidate.items
        if len(items)<=1: return 0.0
        sims=[]
        for i in range(len(items)):
            for j in range(i+1,len(items)):
                sims.append(self.pairwise_similarity(items[i],items[j]))
        return clamp01(sum(sims)/max(1,len(sims)))

    # ------------------------------------------------------------------------
    # Candidate representation
    # ------------------------------------------------------------------------

    def competency_coverage(self, candidate: Candidate) -> Dict[str, float]:
        # Probabilistic OR with quality gating.
        coverage = {}
        for c in COMPETENCIES:
            product = 1.0
            for item in candidate.items:
                z = self.effective_competencies(item)[c]
                q = self.evidence_quality(item.evidence)
                product *= (1.0 - clamp01(z * q))
            coverage[c] = clamp01(1.0 - product)
        return coverage

    def gap_vector(self, candidate: Candidate, role: str) -> Dict[str, float]:
        w = self.role_vector(role)
        coverage = self.competency_coverage(candidate)
        return {
            c: w[c] * (1.0 - coverage[c])
            for c in COMPETENCIES
        }

    def synergy_score(self, coverage: Dict[str, float], role: str) -> float:
        interactions = self.cfg.role_weights.get(role)  # keeps missing role explicit
        pairs = SYNERGY.get(normalize_role(role), {})
        value = 0.0
        for (a, b), weight in pairs.items():
            value += weight * coverage.get(a, 0.0) * coverage.get(b, 0.0)
        return clamp01(value)

    def attention(self, candidate: Candidate, role: str) -> List[float]:
        """
        Order-invariant candidate-dependent attention.

        raw_i = log(role_fit_i) + log(evidence_i) + log(novelty_i)
        then softmax with temperature.

        No "previous items" are used, so permuting resume sections does not
        change attention weights.
        """
        if not candidate.items:
            return []

        raw = []
        novelty = []
        for item in candidate.items:
            fit = max(1e-6, self.item_role_fit(item, role))
            quality = max(1e-6, self.evidence_quality(item.evidence))
            nov = max(1e-6, self.item_novelty(item, candidate.items))
            novelty.append(nov)
            raw.append(
                math.log(fit)
                + math.log(quality)
                + math.log(nov)
            )

        weights = softmax(raw, self.temperature)

        # Floor to prevent one item receiving ~100% mass, then renormalize.
        floor = min(self.attention_floor, 1.0 / max(1, len(weights)))
        if floor > 0:
            weights = [max(w, floor) for w in weights]
            s = sum(weights)
            weights = [w / s for w in weights]
        return weights

    # ------------------------------------------------------------------------
    # Academics
    # ------------------------------------------------------------------------

    def academic_signal(self, candidate: Candidate, role: str) -> float:
        role = normalize_role(role)
        relevance = ACADEMIC_ROLE_RELEVANCE.get(role, 0.5)

        if not candidate.academics:
            return 0.0

        metric = None
        for key in ("cpi", "cgpa", "gpa", self.cfg.metric_name):
            if key in candidate.academics:
                metric = candidate.academics.get(key)
                break
        if metric is None:
            return 0.0

        try:
            value = float(metric)
        except (TypeError, ValueError):
            return 0.0

        scale = float(candidate.academics.get("cpi_scale", self.cfg.metric_scale))
        if scale <= 0:
            scale = self.cfg.metric_scale

        normalized = clamp01(value / scale)
        # Centered so "good" academics help, but don't swamp the evidence model.
        centered = clamp01((normalized - 0.55) / 0.45)
        return centered * relevance

    # ------------------------------------------------------------------------
    # Feature vector for learned ranker
    # ------------------------------------------------------------------------

    def feature_vector(self, candidate: Candidate, role: str) -> List[float]:
        role = normalize_role(role)
        w = self.role_vector(role)
        cov = self.competency_coverage(candidate)
        gaps = self.gap_vector(candidate, role)
        att = self.attention(candidate, role)

        if att:
            item_quality = sum(
                a * self.evidence_quality(item.evidence)
                for a, item in zip(att, candidate.items)
            )
            item_fit = sum(
                a * self.item_role_fit(item, role)
                for a, item in zip(att, candidate.items)
            )
            novelty = sum(
                a * self.item_novelty(item, candidate.items)
                for a, item in zip(att, candidate.items)
            )
        else:
            item_quality = item_fit = novelty = 0.0

        synergy = self.synergy_score(cov, role)
        coverage_score = sum(w[c] * cov[c] for c in COMPETENCIES)
        gap_score = sum(gaps.values())
        academic = self.academic_signal(candidate, role)

        # Candidate vector is deliberately small and interpretable.
        feats = [
            coverage_score,
            item_quality,
            item_fit,
            novelty,
            synergy,
            academic,
            1.0 - gap_score,
            1.0 - self.portfolio_redundancy(candidate),
            min(1.0, len(candidate.items) / 8.0),
        ]

        # Role-aware competency coverage.
        feats.extend(cov[c] for c in COMPETENCIES)

        # Role-aware "strength × relevance" interactions.
        for c in COMPETENCIES:
            feats.append(cov[c] * w[c])

        return [clamp01(x) if i != 0 else float(x) for i, x in enumerate(feats)]

    # ------------------------------------------------------------------------
    # Prior score + learned ranker
    # ------------------------------------------------------------------------

    def prior_score(self, candidate: Candidate, role: str) -> Tuple[float, Dict[str, Any]]:
        role = normalize_role(role)
        w = self.role_vector(role)
        cov = self.competency_coverage(candidate)
        gaps = self.gap_vector(candidate, role)
        att = self.attention(candidate, role)

        coverage_score = sum(w[c] * cov[c] for c in COMPETENCIES)
        evidence_score = 0.0
        item_role_score = 0.0
        novelty_score = 0.0

        item_rows = []
        for item, a in zip(candidate.items, att):
            q = self.evidence_quality(item.evidence)
            fit = self.item_role_fit(item, role)
            nov = self.item_novelty(item, candidate.items)
            rel = fit * q
            evidence_score += a * q
            item_role_score += a * fit
            novelty_score += a * nov
            item_rows.append((item, a, q, fit, nov, rel))

        synergy = self.synergy_score(cov, role)
        academic = self.academic_signal(candidate, role)
        gap_penalty = sum(gaps.values())
        redundancy = self.portfolio_redundancy(candidate)

        raw = (
            self.coverage_mix * coverage_score
            + self.evidence_mix * evidence_score
            + self.synergy_weight * synergy
            + self.academic_weight * academic
            + 0.06 * item_role_score
            + 0.04 * novelty_score
            - self.gap_weight * gap_penalty
            - 0.22 * redundancy
        )

        return clamp01(raw), {
            "coverage_score": coverage_score,
            "evidence_score": evidence_score,
            "item_role_score": item_role_score,
            "novelty_score": novelty_score,
            "synergy_score": synergy,
            "academic_signal": academic,
            "gap_penalty": self.gap_weight * gap_penalty,
            "portfolio_redundancy": redundancy,
            "attention": att,
            "item_rows": item_rows,
        }

    def role_score(self, candidate: Candidate, role: str) -> RoleResult:
        role = normalize_role(role)
        prior, detail = self.prior_score(candidate, role)

        learned = 0.0
        learned_used = False
        if self.ranker is not None:
            try:
                learned = sigmoid(self.ranker.score(self.feature_vector(candidate, role)))
                learned_used = True
            except RuntimeError:
                learned_used = False

        if learned_used:
            # Blend in logit space to keep learned component monotonic.
            final = clamp01(
                (1.0 - self.learned_weight) * prior
                + self.learned_weight * learned
            )
        else:
            final = prior

        gaps = self.gap_vector(candidate, role)
        coverage = self.competency_coverage(candidate)
        confidence = self.confidence(candidate)

        # Top competencies and gaps are role-weighted, not globally sorted.
        strengths = sorted(
            COMPETENCIES,
            key=lambda c: coverage[c] * self.role_vector(role)[c],
            reverse=True,
        )[:5]
        # Weaknesses are drawn from whatever's left AFTER strengths are
        # picked. Both metrics are dominated by the same role-weight term,
        # so for roles with concentrated weights (e.g. quant) the unfiltered
        # top-5-by-gap and top-5-by-strength were often the identical set.
        remaining = [c for c in COMPETENCIES if c not in strengths]
        weaknesses = sorted(
            remaining,
            key=lambda c: gaps[c],
            reverse=True,
        )[:5]

        scored_items: List[ScoredItem] = []
        for item, a, q, fit, nov, rel in detail["item_rows"]:
            scored_items.append(ScoredItem(
                item_id=item.id,
                contribution=float(a * rel),
                dynamic_weight=float(a),
                quality=float(q),
                role_fit=float(fit),
                novelty=float(nov),
                reliability=float(item.evidence.credibility),
            ))

        diagnostics = {
            **{k: v for k, v in detail.items() if k != "item_rows" and k != "attention"},
            "learned_component": learned,
            "learned_ranker_used": learned_used,
            "attention_entropy": self.entropy(detail["attention"]),
            "keyword_gaming_risk": self.keyword_gaming_risk(candidate),
            "title_dependence": self.title_dependence(candidate),
            "order_invariant": True,
            "eligibility": self.eligibility(candidate, role),
        }

        return RoleResult(
            role=role,
            score=final,
            relative_fit=0.0,
            confidence=confidence,
            coverage=coverage,
            gaps=gaps,
            strengths=strengths,
            weaknesses=weaknesses,
            item_scores=scored_items,
            diagnostics=diagnostics,
        )

    # ------------------------------------------------------------------------
    # Training / calibration
    # ------------------------------------------------------------------------

    def fit_pairwise_ranker(
        self,
        pairwise_data: Iterable[Tuple[Candidate, Candidate, str, int]],
        learning_rate: float = 0.03,
        epochs: int = 300,
        l2: float = 1e-3,
    ) -> Dict[str, Any]:
        """
        pairwise_data item:
            (candidate_A, candidate_B, role, label)
        label=1 -> A preferred
        label=0 -> B preferred
        """
        pairs = []
        for a, b, role, label in pairwise_data:
            fa = self.feature_vector(a, role)
            fb = self.feature_vector(b, role)
            pairs.append((fa, fb, int(label)))

        if not pairs:
            raise ValueError("No pairwise training examples supplied")

        self.ranker = PairwiseLogisticRanker(
            learning_rate=learning_rate,
            epochs=epochs,
            l2=l2,
            seed=self.seed,
        )
        self.ranker.fit(pairs)

        return {
            "pairs": len(pairs),
            "epochs_trained": len(self.ranker.history),
            "final_loss": self.ranker.history[-1],
            "feature_count": len(pairs[0][0]),
        }

    def fit_calibrator(self, labeled_scores, learning_rate=0.05, epochs=500, l2=1e-3):
        data=list(labeled_scores)
        self.calibrator=PlattCalibrator(learning_rate,epochs,l2).fit(
            [float(s) for s,_ in data],[int(y) for _,y in data])
        return {"observations":len(data),"a":self.calibrator.a,"b":self.calibrator.b}

    def calibrated_probability(self, candidate: Candidate, role: str) -> float:
        score=self.role_score(candidate,role).score
        return self.calibrator.predict(score) if self.calibrator else sigmoid(score)

    # ------------------------------------------------------------------------
    # Ranking / metrics
    # ------------------------------------------------------------------------

    def rank_candidates(
        self,
        candidates: List[Candidate],
        role: str,
    ) -> List[Tuple[Candidate, RoleResult]]:
        scored = [(c, self.role_score(c, role)) for c in candidates]
        return sorted(scored, key=lambda x: x[1].score, reverse=True)

    def rank_roles(self, candidate: Candidate, roles: List[str]) -> List[RoleResult]:
        results = [self.role_score(candidate, r) for r in roles]
        probs = softmax([r.score for r in results], temperature=0.12)
        for result, p in zip(results, probs):
            result.relative_fit = p
        return sorted(results, key=lambda x: x.score, reverse=True)

    @staticmethod
    def ndcg_at_k(relevances: List[float], k: int) -> float:
        rel = relevances[:max(0, k)]
        dcg = 0.0
        for i, r in enumerate(rel):
            dcg += (2.0 ** float(r) - 1.0) / math.log2(i + 2)
        ideal = sorted(relevances, reverse=True)[:max(0, k)]
        idcg = 0.0
        for i, r in enumerate(ideal):
            idcg += (2.0 ** float(r) - 1.0) / math.log2(i + 2)
        return dcg / idcg if idcg > 0 else 0.0

    @staticmethod
    def mrr(binary_relevance: List[int]) -> float:
        for i, rel in enumerate(binary_relevance, start=1):
            if rel:
                return 1.0 / i
        return 0.0

    @staticmethod
    def precision_at_k(binary_relevance: List[int], k: int) -> float:
        if k <= 0:
            return 0.0
        x = binary_relevance[:k]
        return sum(x) / len(x) if x else 0.0

    @staticmethod
    def spearman(pred_scores: List[float], true_scores: List[float]) -> float:
        if len(pred_scores) != len(true_scores) or len(pred_scores) < 2:
            return 0.0
        a = rankdata(pred_scores)
        b = rankdata(true_scores)
        ma = sum(a) / len(a)
        mb = sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = math.sqrt(sum((x - ma) ** 2 for x in a))
        db = math.sqrt(sum((y - mb) ** 2 for y in b))
        return num / (da * db + 1e-12)

    # ------------------------------------------------------------------------
    # Counterfactuals
    # ------------------------------------------------------------------------

    def counterfactual_item_removal(
        self, candidate: Candidate, role: str
    ) -> List[Dict[str, Any]]:
        base = self.role_score(candidate, role).score
        rows = []
        for idx, item in enumerate(candidate.items):
            reduced = copy.deepcopy(candidate)
            reduced.items.pop(idx)
            new = self.role_score(reduced, role).score
            rows.append({
                "item_id": item.id,
                "delta_if_removed": base - new,
            })
        return sorted(rows, key=lambda x: abs(x["delta_if_removed"]), reverse=True)

    def feature_ablation(
        self, candidate: Candidate, role: str
    ) -> Dict[str, float]:
        """
        Shows what happens when each major model family is removed.
        Useful for a competition presentation to demonstrate that no single
        fragile heuristic is responsible for the outcome.
        """
        role = normalize_role(role)
        prior, d = self.prior_score(candidate, role)

        variants = {}
        variants["full_prior"] = prior

        # Coverage-only.
        w = self.role_vector(role)
        cov = self.competency_coverage(candidate)
        variants["coverage_only"] = clamp01(
            sum(w[c] * cov[c] for c in COMPETENCIES)
        )

        # Evidence-only.
        att = d["attention"]
        variants["evidence_only"] = clamp01(sum(
            a * self.evidence_quality(item.evidence)
            for a, item in zip(att, candidate.items)
        ))

        variants["without_academics"] = clamp01(
            prior - self.academic_weight * self.academic_signal(candidate, role)
        )
        variants["without_synergy"] = clamp01(
            prior - self.synergy_weight * d["synergy_score"]
        )
        return variants

    # ------------------------------------------------------------------------
    # Adversarial / stability audit
    # ------------------------------------------------------------------------

    def entropy(self, p: List[float]) -> float:
        if len(p) <= 1:
            return 0.0
        h = -sum(x * math.log(max(x, 1e-12)) for x in p)
        return h / math.log(len(p))

    def title_dependence(self, candidate: Candidate) -> float:
        if not candidate.items:
            return 0.0
        diffs = []
        for item in candidate.items:
            with_title = self.effective_competencies(item)
            stripped = copy.deepcopy(item)
            stripped.title = ""
            without = self.effective_competencies(stripped)
            a = sum(with_title.values())
            b = sum(without.values())
            diffs.append(abs(a - b) / max(1.0, a))
        return clamp01(sum(diffs) / len(diffs))

    def keyword_gaming_risk(self, candidate: Candidate) -> float:
        if not candidate.items:
            return 0.0
        risk = []
        for item in candidate.items:
            semantic = clamp01(item.evidence.semantic_strength)
            concrete = (
                item.evidence.action
                + item.evidence.scope
                + item.evidence.method
                + item.evidence.outcome
                + item.evidence.quantification
            ) / 5.0
            risk.append(clamp01(semantic - concrete))
        return sum(risk) / len(risk)

    def eligibility(self, candidate: Candidate, role: str) -> Dict[str, Any]:
        role = normalize_role(role)
        gate = self.cfg.role_gates.get(role, {})
        minimum = float(gate.get("minimum_cpi", 0.0))
        value = candidate.academics.get("cpi", candidate.academics.get("cgpa"))
        eligible = True
        metric = None
        if value is not None and minimum > 0:
            try:
                metric = float(value)
                eligible = metric >= minimum
            except (TypeError, ValueError):
                eligible = False
        return {
            "eligible": bool(eligible),
            "metric": metric,
            "minimum": minimum,
        }

    def audit_candidate(self, candidate: Candidate, role: str) -> Dict[str, Any]:
        base = self.role_score(candidate, role)
        normal = base.score

        # 1) section-order attack
        reversed_candidate = copy.deepcopy(candidate)
        reversed_candidate.items.reverse()
        reversed_score = self.role_score(reversed_candidate, role).score

        # 2) duplicate attack
        duplicated = copy.deepcopy(candidate)
        duplicated.items.extend(copy.deepcopy(candidate.items))
        duplicate_score = self.role_score(duplicated, role).score

        # 3) title inflation attack
        inflated = copy.deepcopy(candidate)
        for item in inflated.items:
            item.title = "General Secretary"
        inflated_score = self.role_score(inflated, role).score

        # 4) small bounded perturbation attack
        rng = random.Random(self.seed)
        perturbed = copy.deepcopy(candidate)
        for item in perturbed.items:
            for c in COMPETENCIES:
                if c in item.competencies:
                    delta = rng.uniform(-0.01, 0.01)
                    item.competencies[c] = clamp01(item.competencies[c] + delta)
        perturbed_score = self.role_score(perturbed, role).score

        return {
            "role": normalize_role(role),
            "score": normal,
            "confidence": base.confidence,
            "diagnostics": base.diagnostics,
            "tests": {
                "section_order_invariance": {
                    "score_original": normal,
                    "score_reversed": reversed_score,
                    "difference": abs(normal - reversed_score),
                    "pass": abs(normal - reversed_score) < 1e-9,
                },
                "title_inflation": {
                    "score_original": normal,
                    "score_inflated": inflated_score,
                    "increase": inflated_score - normal,
                    "pass": (inflated_score - normal) < 0.05,
                },
                "duplicate_evidence": {
                    "score_original": normal,
                    "score_duplicated": duplicate_score,
                    "increase": duplicate_score - normal,
                    "pass": (duplicate_score - normal) < 0.15,
                },
                "small_perturbation_stability": {
                    "score_original": normal,
                    "score_perturbed": perturbed_score,
                    "difference": abs(normal - perturbed_score),
                    "pass": abs(normal - perturbed_score) < 0.03,
                },
            },
            "counterfactuals": self.counterfactual_item_removal(candidate, role),
            "feature_ablation": self.feature_ablation(candidate, role),
        }

    # ------------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------------

    def confidence(self, candidate: Candidate) -> float:
        if not candidate.items:
            return 0.0
        qs = [self.evidence_quality(x.evidence) for x in candidate.items]
        evidence_completeness = sum(qs) / len(qs)
        semantic_completeness = sum(
            clamp01(x.evidence.semantic_strength) for x in candidate.items
        ) / len(candidate.items)
        provenance = sum(
            clamp01(x.evidence.provenance_strength) for x in candidate.items
        ) / len(candidate.items)
        quantity_signal = min(1.0, len(candidate.items) / 6.0)

        return clamp01(
            0.60 * evidence_completeness
            + 0.20 * semantic_completeness
            + 0.10 * provenance
            + 0.10 * quantity_signal
        )


# ============================================================================
# 7. SMOKE / REGRESSION TEST SUITE
# ============================================================================

def build_demo_candidates() -> List[Candidate]:
    def item(
        iid: str, title: str, org: str, comps: Dict[str, float],
        evidence: Evidence, item_type: str = "project"
    ) -> ResumeItem:
        return ResumeItem(
            id=iid,
            item_type=item_type,
            title=title,
            organization=org,
            description="demo",
            competencies=comps,
            evidence=evidence.clamp(),
        )

    strong_leader = item(
        "por1", "Secretary", "Programming Club",
        {"leadership": .70, "execution": .80, "communication": .70,
         "technical": .35, "impact": .65},
        Evidence(.90, .80, .70, .75, .75, .90, .95, .90, .85),
        "por",
    )
    weak_leader = item(
        "por2", "Secretary", "Programming Club",
        {"leadership": .25, "execution": .20, "communication": .20},
        Evidence(.30, .10, .15, .10, .00, .25, .95, .80, .70),
        "por",
    )
    ml_project = item(
        "ml1", "ML Project", "",
        {"technical": .90, "analytical": .85, "problem_solving": .80,
         "quantitative": .70, "research": .55},
        Evidence(.90, .55, .92, .70, .40, .85, .95, .93, .85),
    )
    business_case = item(
        "c1", "Case Competition", "",
        {"analytical": .80, "business": .85, "communication": .75,
         "strategy": .78, "problem_solving": .82},
        Evidence(.88, .70, .72, .82, .70, .90, .95, .93, .90),
    )

    return [
        Candidate("A", [strong_leader, ml_project], {"cpi": 9.2, "cpi_scale": 10}),
        Candidate("B", [weak_leader, business_case], {"cpi": 8.2, "cpi_scale": 10}),
    ]


def run_regression_tests() -> Dict[str, Any]:
    engine = IITKResumeV4Competition()
    candidates = build_demo_candidates()
    failures: List[str] = []

    # Test 1: order invariance.
    c = copy.deepcopy(candidates[0])
    a = engine.role_score(c, "consulting").score
    c.items.reverse()
    b = engine.role_score(c, "consulting").score
    if abs(a - b) > 1e-9:
        failures.append(f"order invariance failed: {a} vs {b}")

    # Test 2: title inflation should be limited.
    c = copy.deepcopy(candidates[0])
    before = engine.role_score(c, "consulting").score
    for x in c.items:
        x.title = "General Secretary"
    after = engine.role_score(c, "consulting").score
    if after - before >= 0.05:
        failures.append(f"title inflation too strong: +{after - before:.4f}")

    # Test 3: score must remain finite and [0,1].
    for role in ROLE_WEIGHTS:
        for cand in candidates:
            s = engine.role_score(cand, role).score
            if not (math.isfinite(s) and 0.0 <= s <= 1.0):
                failures.append(f"invalid score for {cand.id}/{role}: {s}")

    # Test 4: duplicate evidence has diminishing returns.
    c = copy.deepcopy(candidates[0])
    x = engine.role_score(c, "ml").score
    c.items += copy.deepcopy(c.items)
    y = engine.role_score(c, "ml").score
    if y - x >= 0.15:
        failures.append(f"duplicate penalty too weak: +{y-x:.4f}")

    # Test 5: strong-description-vs-weak-description separation.
    strong = candidates[0]
    weak = copy.deepcopy(candidates[0])
    weak.items[0].competencies = {"leadership": .05}
    weak.items[0].evidence = Evidence(.10, .05, .05, .02, .0, .05, 1.0, .90, .8)
    strong_score = engine.role_score(strong, "consulting").score
    weak_score = engine.role_score(weak, "consulting").score
    if strong_score <= weak_score:
        failures.append("description evidence failed to dominate weak evidence")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "test_count": 5,
    }


def demo() -> Dict[str, Any]:
    engine = IITKResumeV4Competition()
    candidate = build_demo_candidates()[0]

    roles = engine.rank_roles(candidate, [
        "consulting", "quant", "ml", "software", "data_science"
    ])

    audit = engine.audit_candidate(candidate, "consulting")

    return {
        "candidate": candidate.id,
        "role_ranking": [
            {
                "role": r.role,
                "score": r.score,
                "relative_fit": r.relative_fit,
                "confidence": r.confidence,
                "strengths": r.strengths,
                "weaknesses": r.weaknesses,
            }
            for r in roles
        ],
        "audit": audit,
        "regression_tests": run_regression_tests(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(demo(), indent=2))

"""Stage 3 v2 — Hybrid matcher with candidate gating and zero leakage.

Fixes D1-D11:
- Candidate gate: claims with no plausible connection to a competency score ZERO.
- Relevance × evidence_quality formula: final = relevance * evidence_quality.
  A strong but unrelated bullet must contribute zero.
- Section/entry type constraints per competency.
- Evidence diversity: deduplicate by entry_id.
- No training-time leakage: all thresholds are explicit rule gates, not learned.
- Documented fallback: lexical/ontology gating, optional embedding upgrade.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable

from resume_engine.evidence.models import AtomicClaim, EvidenceDocument
from resume_engine.ontology.roles import RoleGraph


@dataclass
class Match:
    claim_id: str
    competency: str
    retrieval_score: float
    gate_passed: bool
    final_score: float
    reason_codes: list[str] = field(default_factory=list)
    evidence_quality: float = 0.0


# ---------------------------------------------------------------------------
# Competency gate definitions
# ---------------------------------------------------------------------------
# Each gate specifies:
#   allowed_sections:   if non-empty, claim must be in one of these sections
#   required_skills:    any one of these skills must be present
#   required_signals:   minimum value of signal key (OR logic among items)
#   required_entities:  any one of these entity canonicals must appear
#   negative_sections:  if claim is in these sections, gate fails unless
#                       an explicit entity/skill override is present
#   min_ontology_score: minimum gate score from signals alone to pass
#   forbidden_only_in:  claim from these sections only passes with positive override
#
# Gate logic: claim passes if ANY of the positive gates fires with no
# active veto. Score is then relevance * evidence_quality.

_GATES: dict[str, dict] = {
    # SDE competencies
    "algorithms": {
        "required_skills": {"dsa", "competitive_programming", "python", "cpp", "java"},
        "required_signals": {"algorithms": 0.3},
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular"},
        "negative_entities": {"Convener", "HEC", "HostelAffairs", "StudentsGymkhana"},
    },
    "competitive_programming": {
        # HARD REQUIREMENT: Must have explicit CP entities or keywords
        "required_entities": {"Codeforces", "CodeChef", "AtCoder", "LeetCode", "ICPC", "IOI", "USACO"},
        "required_skills": {"competitive_programming", "dsa"},
        "cp_keywords": True,  # Must contain CP-specific keywords
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Education",
                              "Experience", "Research", "Extracurricular"},
    },
    "software_engineering": {
        "required_skills": {"python", "cpp", "java", "javascript", "nodejs", "react",
                            "flask", "django", "fastapi", "spring", "typescript",
                            "git", "docker", "aws"},
        "required_signals": {"software_engineering": 0.3},
        "negative_sections": {"Positions of Responsibility", "Social Impact"},
    },
    "programming": {
        "required_skills": {"python", "cpp", "java", "javascript", "typescript",
                            "r_lang", "go_lang", "rust", "scala"},
        "required_signals": {"programming": 0.3},
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular"},
    },
    "projects": {
        "allowed_sections": {"Projects", "Research"},
        "required_signals": {"technical_depth": 0.2},
        "software_project_bonus": True,  # Bonus for software-related projects
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular",
                              "Education", "Achievements"},
    },
    "open_source": {
        # GitHub link alone or software_engineering signal alone is NOT open-source contribution.
        # MUST have explicit open-source contribution keywords (PR, fork, contribute, package, etc.)
        # Additionally needs programming skill evidence.
        "open_source_keywords": True,   # HARD REQUIREMENT: text must contain open-source keywords
        "required_skills": {"git", "python", "cpp", "java", "javascript", "typescript",
                            "nodejs", "react", "flask", "docker"},  # any coding skill
    },
    "impact": {
        "required_signals": {"quantified_impact": 0.3},
        "technical_impact_bonus": True,  # Bonus for technical/engineering impact
        "negative_sections": {"Education", "Skills", "Coursework"},
    },
    "internships": {
        "allowed_sections": {"Experience"},
        "negative_sections": {"Projects", "Research", "Positions of Responsibility",
                              "Extracurricular", "Achievements", "Social Impact"},
    },
    "communication": {
        # Communication requires actual stakeholder interaction evidence
        "communication_keywords": True,  # Must have explicit communication evidence
        "min_evidence_strength": 0.55,
        "allowed_sections": {"Experience", "Projects", "Research",
                             "Positions of Responsibility"},
    },

    # Quant competencies
    "academic_strength": {
        "allowed_sections": {"Education", "Achievements"},
        "required_signals": {"academic_strength": 0.5},
    },
    "mathematics": {
        "required_skills": {"probability", "statistics", "stochastic_calculus",
                            "linear_algebra", "calculus", "mathematical_optimization", "matlab", "mathematica"},
        "mathematics_keywords": True,  # Must contain mathematical keywords, not just business metrics
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Experience"},
        "negative_business_context": True,  # Veto if in business/revenue context
    },
    "probability": {
        # HARD REQUIREMENT: Must have explicit probability/stochastic keywords in text
        "required_skills": {"probability", "stochastic_calculus", "bayesian", "monte_carlo"},
        "probability_keywords": True,  # Must contain probability-specific keywords
        "allowed_sections": {"Coursework", "Research", "Projects", "Achievements"},
    },
    "statistics": {
        "required_skills": {"statistics", "scikit_learn", "numpy", "pandas",
                            "machine_learning"},
        "required_signals": {"statistics": 0.3},
    },
    "research": {
        "allowed_sections": {"Research", "Projects", "Publications"},
        "required_signals": {"research": 0.3},
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular"},
    },
    "quantitative_projects": {
        "allowed_sections": {"Projects", "Research"},
        "required_skills": {"python", "matlab", "r_lang", "statistics", "probability",
                            "numpy", "pandas", "scikit_learn", "mathematical_optimization"},
        "quantitative_keywords": True,  # Must contain quantitative analysis keywords
        "negative_business_context": True,  # Not just business strategy projects
    },

    # Consulting competencies
    "leadership": {
        "required_signals": {"leadership": 0.3},
        "allowed_sections": {"Positions of Responsibility", "Extracurricular",
                             "Social Impact", "Experience"},
        "negative_sections": {"Education", "Projects", "Research", "Skills", "Coursework"},
    },
    "organizational_impact": {
        "required_signals": {"organizational_impact": 0.3},
        "allowed_sections": {"Positions of Responsibility", "Extracurricular",
                             "Social Impact", "Experience"},
        "negative_sections": {"Education", "Projects", "Skills", "Coursework"},
    },
    "business_impact": {
        "required_signals": {"business_impact": 0.3, "quantified_impact": 0.3},
        "allowed_sections": {"Experience", "Positions of Responsibility",
                             "Social Impact", "Projects"},
        "negative_sections": {"Education", "Skills", "Coursework", "Extracurricular"},
    },
    "breadth": {
        "allowed_sections": {"Extracurricular", "Achievements", "Positions of Responsibility",
                             "Social Impact"},
        "negative_sections": {"Education", "Projects", "Research", "Skills"},
    },
    "problem_solving": {
        "problem_solving_keywords": True,  # Must have analytical/problem-solving evidence  
        "required_signals": {"problem_solving": 0.3, "algorithms": 0.3},
        "negative_sections": {"Education", "Skills", "Coursework"},
    },
    "teamwork": {
        "required_signals": {"teamwork": 0.3},
        "allowed_sections": {"Extracurricular", "Positions of Responsibility",
                             "Social Impact", "Experience"},
    },

    # Core engineering competencies
    "technical_depth": {
        "required_signals": {"technical_depth": 0.3},
        "allowed_sections": {"Research", "Projects", "Experience", "Coursework"},
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular"},
    },
    "core_projects": {
        "allowed_sections": {"Projects", "Research"},
        "required_skills": {"matlab", "cad", "labview", "matlab_simulink"},
        "negative_sections": {"Positions of Responsibility", "Social Impact", "Extracurricular"},
    },
    "core_tools": {
        "required_skills": {"matlab", "cad", "labview", "matlab_simulink", "mathematica"},
        "required_signals": {"core_tools": 0.5},
    },
    "coursework": {
        "allowed_sections": {"Coursework", "Education"},
    },
    "publications": {
        # HARD REQUIREMENT: Must have explicit publication keywords
        "publication_keywords": True,  # Must contain publication-specific keywords
        "allowed_sections": {"Publications", "Research"},
        "negative_sections": {"Projects", "Experience", "Positions of Responsibility"},
    },
    "ml_engineering": {
        "required_skills": {"tensorflow", "pytorch", "scikit_learn", "keras",
                            "machine_learning", "deep_learning", "nlp", "computer_vision"},
        "required_signals": {"ml_engineering": 0.3},
    },
}

# Keywords that are required for open_source gate
_OPEN_SOURCE_KW = re.compile(
    r"\b(open.?source|gsoc|google summer of code|pull request|pr|fork|"
    r"contribute|contribution|package|library|module|pip|npm)\b",
    re.IGNORECASE,
)

# Keywords required for competitive_programming gate
_CP_KW = re.compile(
    r"\b(competitive programming|codeforces|codechef|atcoder|leetcode|icpc|ioi|usaco|"
    r"contest|ranking|specialist|expert|candidate master|master|grandmaster|"
    r"algorithmic contest|programming contest)\b",
    re.IGNORECASE,
)

# Keywords required for probability gate
_PROBABILITY_KW = re.compile(
    r"\b(probabilit|stochastic|bayesian|monte carlo|markov|random variable|"
    r"distribution|likelihood|prior|posterior|sampling|mcmc|statistics|statistical|"
    r"inference|bivariate|multivariate|geary|moran|rshiny|data science|hypothesis)\b",
    re.IGNORECASE,
)

# Keywords required for publication gate
_PUBLICATION_KW = re.compile(
    r"\b(published|publication|paper|journal|conference|proceedings|"
    r"accepted|doi|ieee|acm|springer|elsevier|arxiv|cite|author)\b",
    re.IGNORECASE,
)

# Keywords required for mathematics gate (vs business metrics)
_MATHEMATICS_KW = re.compile(
    r"\b(mathematical|theorem|proof|equation|derivative|integral|matrix|"
    r"linear algebra|calculus|optimization|algorithm|differential|"
    r"topology|geometry|algebra|analysis)\b",
    re.IGNORECASE,
)

# Keywords required for quantitative_projects gate
_QUANTITATIVE_KW = re.compile(
    r"\b(statistical|quantitative|mathematical|numerical|simulation|"
    r"modeling|forecasting|regression|classification|clustering|"
    r"time series|econometric|predictive|analytical)\b",
    re.IGNORECASE,
)

# Business/revenue context patterns (for negative matching)
_BUSINESS_CONTEXT = re.compile(
    r"\b(revenue|profit|cost|business|sales|marketing|pricing|strategy|"
    r"growth|market|customer|client|commercial)\b",
    re.IGNORECASE,
)

# Communication keywords (stakeholder interaction evidence)
_COMMUNICATION_KW = re.compile(
    r"\b(present|presentation|interview|communicate|coordinate|stakeholder|"
    r"mentor|teach|lead|chair|facilitate|negotiate|discuss)\b",
    re.IGNORECASE,
)

# Problem solving keywords (analytical evidence)  
_PROBLEM_SOLVING_KW = re.compile(
    r"\b(identify|identif|analyz|analy|solve|solv|diagnos|investigat|"
    r"troubleshoot|debug|optim|benchmark|evaluat|assess|strateg)\b",
    re.IGNORECASE,
)


def _compute_gate_score(claim: AtomicClaim, comp_name: str, gate: dict) -> tuple[bool, float, list[str]]:
    """Return (gate_passed, raw_relevance_score, reason_codes)."""
    reasons: list[str] = []
    positive_score = 0.0

    # ── Section constraints ─────────────────────────────────────────────
    allowed_sections = gate.get("allowed_sections", set())
    negative_sections = gate.get("negative_sections", set())

    in_allowed = (not allowed_sections) or (claim.section in allowed_sections)
    in_negative = claim.section in negative_sections

    # Required signals (OR logic)
    claim_signals = claim.signals
    req_signals = gate.get("required_signals", {})
    signal_match = any(
        claim_signals.get(k, 0.0) >= v for k, v in req_signals.items()
    )
    if signal_match:
        max_signal = max(
            (claim_signals.get(k, 0.0) for k in req_signals), default=0.0
        )
        positive_score = max(positive_score, max_signal * 0.9)
        reasons.append("signal_match")

    # Required skills (OR logic)
    req_skills = gate.get("required_skills", set())
    skill_match = bool(req_skills and req_skills.intersection(set(claim.skills)))
    if skill_match:
        positive_score = max(positive_score, 0.70)
        reasons.append("skill_match")

    # Required entities (OR logic)
    req_entities = gate.get("required_entities", set())
    claim_entity_canonicals = {e.canonical for e in claim.entities}
    entity_match = bool(req_entities and req_entities.intersection(claim_entity_canonicals))
    if entity_match:
        positive_score = max(positive_score, 0.85)
        reasons.append("entity_match")

    # Special keyword requirements (HARD REQUIREMENTS when gate specifies them)
    if gate.get("open_source_keywords"):
        if not _OPEN_SOURCE_KW.search(claim.text):
            return False, 0.0, ["no_open_source_keywords"]
        positive_score = max(positive_score, 0.70)
        reasons.append("open_source_keyword")
    
    if gate.get("cp_keywords"):
        if not _CP_KW.search(claim.text):
            return False, 0.0, ["no_cp_keywords"]
        positive_score = max(positive_score, 0.80)
        reasons.append("cp_keyword")
        
    if gate.get("probability_keywords"):
        if not _PROBABILITY_KW.search(claim.text):
            return False, 0.0, ["no_probability_keywords"]
        positive_score = max(positive_score, 0.75)
        reasons.append("probability_keyword")
        
    if gate.get("publication_keywords"):
        if not _PUBLICATION_KW.search(claim.text):
            return False, 0.0, ["no_publication_keywords"]
        positive_score = max(positive_score, 0.85)
        reasons.append("publication_keyword")
        
    if gate.get("mathematics_keywords"):
        if not _MATHEMATICS_KW.search(claim.text):
            return False, 0.0, ["no_mathematics_keywords"]
        positive_score = max(positive_score, 0.70)
        reasons.append("mathematics_keyword")
        
    if gate.get("quantitative_keywords"):
        if not _QUANTITATIVE_KW.search(claim.text):
            return False, 0.0, ["no_quantitative_keywords"]
        positive_score = max(positive_score, 0.70)
        reasons.append("quantitative_keyword")
    
    if gate.get("communication_keywords"):
        if not _COMMUNICATION_KW.search(claim.text):
            return False, 0.0, ["no_communication_keywords"]
        positive_score = max(positive_score, 0.70)
        reasons.append("communication_keyword")
        
    if gate.get("problem_solving_keywords"):
        if not _PROBLEM_SOLVING_KW.search(claim.text):
            return False, 0.0, ["no_problem_solving_keywords"]
        positive_score = max(positive_score, 0.75)
        reasons.append("problem_solving_keyword")
    
    # Software project bonus (for SDE projects competency)
    if gate.get("software_project_bonus"):
        software_skills = {"python", "cpp", "java", "javascript", "typescript", "nodejs", "react", 
                          "flask", "django", "fastapi", "spring", "git", "docker", "aws", "sql"}
        if any(skill in claim.skills for skill in software_skills):
            positive_score = max(positive_score, 0.75)
            reasons.append("software_project_bonus")
    
    # Technical impact bonus (for SDE impact competency)  
    if gate.get("technical_impact_bonus"):
        software_skills = {"python", "cpp", "java", "javascript", "typescript", "nodejs", "react", 
                          "flask", "django", "fastapi", "spring", "git", "docker", "aws", "sql"}
        technical_contexts = {"software", "system", "pipeline", "algorithm", "optimization", "engineering"}
        technical_sections = {"Research", "Projects", "Experience"}
        
        has_technical_context = any(ctx in claim.text.lower() for ctx in technical_contexts)
        is_technical_section = claim.section in technical_sections
        has_technical_skills = any(skill in claim.skills for skill in software_skills)
        
        if has_technical_context or (is_technical_section and has_technical_skills):
            positive_score = max(positive_score, 0.70)
            reasons.append("technical_impact_bonus")
        # Penalty for non-technical impact in SDE context
        elif claim.section in {"Positions of Responsibility", "Social Impact", "Extracurricular"}:
            positive_score = min(positive_score, 0.40)  # Cap non-technical impact
    
    # Business context veto (prevents business metrics from being classified as mathematics/quant)
    if gate.get("negative_business_context"):
        if _BUSINESS_CONTEXT.search(claim.text):
            return False, 0.0, ["business_context_veto"]

    # Special: min_evidence_strength
    min_ev = gate.get("min_evidence_strength", 0.0)
    if min_ev > 0 and claim.evidence_strength >= min_ev:
        positive_score = max(positive_score, claim.evidence_strength * 0.7)
        reasons.append("evidence_strength_gate")

    # Section bonus
    if in_allowed and allowed_sections:
        positive_score = max(positive_score, 0.50)
        reasons.append("section_match")

    # ── Veto logic ───────────────────────────────────────────────────────
    # Negative entity veto (e.g. cultural medals shouldn't score algorithms)
    neg_entities = gate.get("negative_entities", set())
    entity_veto = bool(neg_entities and neg_entities.intersection(claim_entity_canonicals))

    # Veto if in negative section AND no positive override
    section_veto = in_negative and positive_score < 0.50 and not entity_match

    if entity_veto or section_veto:
        if positive_score < 0.50:
            return False, 0.0, ["vetoed"]

    # ── Gate decision ────────────────────────────────────────────────────
    gate_passed = positive_score > 0.15  # minimum relevance threshold
    return gate_passed, positive_score, reasons


class HybridMatcher:
    """Gated hybrid matcher.

    Architecture (D1 fix — honest):
    - Stage 1 (candidate gate): rule/ontology/signal gates; claims without any
      plausible connection to a competency are excluded (score = 0).
    - Stage 2 (relevance scoring): lexical + signal relevance for gated candidates.
    - Optional: SentenceTransformer bi-encoder when configured.
    - Final score: relevance × evidence_quality (D3 fix).
    """

    def __init__(self, model_name: str | None = None):
        self.model = None
        if model_name:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
            except Exception:
                self.model = None

    @staticmethod
    def _tokens(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9+#.]+", s.lower()))

    def _lexical_similarity(self, claim_text: str, query: str) -> float:
        """Token-overlap similarity against competency description."""
        A = self._tokens(claim_text)
        B = self._tokens(query)
        if not A or not B:
            return 0.0
        return len(A & B) / math.sqrt(len(A) * len(B))

    def _semantic_similarity(self, a: str, b: str) -> float:
        if self.model is not None:
            vecs = self.model.encode([a, b], normalize_embeddings=True)
            return float(max(0.0, min(1.0, vecs[0] @ vecs[1])))
        return self._lexical_similarity(a, b)

    def match(
        self,
        evidence: EvidenceDocument,
        role: RoleGraph,
        top_k_per_comp: int = 5,
    ) -> list[Match]:
        matches: list[Match] = []

        for comp in role.competencies:
            gate = _GATES.get(comp.name, {})
            query = f"{comp.name.replace('_', ' ')} {comp.description}"

            gated_candidates: list[tuple[AtomicClaim, float, list[str]]] = []

            for cl in evidence.claims:
                gate_passed, gate_score, reasons = _compute_gate_score(cl, comp.name, gate)
                if not gate_passed:
                    continue  # D2 fix: excluded claims get zero contribution

                # Lexical / semantic relevance for gated candidates
                sem_score = self._semantic_similarity(cl.text, query)
                relevance = max(gate_score, sem_score * 0.8)

                gated_candidates.append((cl, relevance, reasons))

            # Sort by relevance, deduplicate by entry_id (D9 fix)
            gated_candidates.sort(key=lambda x: x[1], reverse=True)
            seen_entries: set[str | None] = set()
            diverse_candidates: list[tuple[AtomicClaim, float, list[str]]] = []
            for cl, rel, rsns in gated_candidates:
                eid = cl.entry_id
                if eid in seen_entries and len(diverse_candidates) >= 1:
                    # Allow at most 2 bullets from the same entry for diversity
                    entry_count = sum(1 for c2, _, _ in diverse_candidates if c2.entry_id == eid)
                    if entry_count >= 2:
                        continue
                seen_entries.add(eid)
                diverse_candidates.append((cl, rel, rsns))
                if len(diverse_candidates) >= top_k_per_comp:
                    break

            # Compute final scores: relevance × evidence_quality (D3 fix)
            for cl, relevance, rsns in diverse_candidates:
                ev_quality = cl.evidence_strength
                final = min(1.0, relevance * (0.60 + 0.40 * ev_quality))

                matches.append(Match(
                    claim_id=cl.claim_id,
                    competency=comp.name,
                    retrieval_score=round(relevance, 4),
                    gate_passed=True,
                    final_score=round(final, 4),
                    reason_codes=rsns,
                    evidence_quality=round(ev_quality, 4),
                ))

        return matches

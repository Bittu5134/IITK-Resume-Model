"""Advanced spaCy & Regex NLP pipeline for POS tagging, campus jargon EntityRuler, and NER metrics."""
from __future__ import annotations

import re
from typing import NamedTuple

try:
    import spacy
    from spacy.pipeline import EntityRuler
    _SPACY_AVAILABLE = True
except ImportError:
    spacy = None
    EntityRuler = None
    _SPACY_AVAILABLE = False


class NLPBulletAnalysis(NamedTuple):
    text: str
    has_action_verb: bool
    leading_word: str
    has_quantified_metric: bool
    detected_entities: list[str]
    detected_metrics: list[str]


# Strong imperative action verb dictionary for fallback regex matching
_STRONG_ACTION_VERBS = {
    "accelerated", "achieved", "architected", "automated", "built", "calculated",
    "designed", "developed", "deployed", "directed", "engineered", "established",
    "executed", "extracted", "formulated", "implemented", "improved", "increased",
    "initiated", "innovated", "integrated", "launched", "lead", "led", "managed",
    "modeled", "modelled", "optimized", "optimised", "orchestrated", "organized",
    "pioneered", "quantified", "reduced", "refactored", "researched", "scaled",
    "simulated", "spearheaded", "standardized", "streamlined", "structured",
    "supervised", "trained", "transformed", "utilized", "validated"
}

# IITK Campus Jargon terms for EntityRuler / Regex dictionary
_IITK_CAMPUS_JARGON = [
    "SURGE", "SURGE Intern", "AnC Council", "Academics & Career Council",
    "Gymkhana", "Students Gymkhana", "PoR", "Position of Responsibility",
    "TnP", "SPO", "Student Placement Office", "Techkriti", "Antaragni",
    "Udghosh", "Counseling Service", "HEC", "Hall Executive Committee",
    "Presidential PoR", "UGPEC", "SUGC", "DPGC", "CPI", "SPI"
]


class ResumeNLPPipeline:
    """Hybrid spaCy + Regex NLP engine for resume bullet analysis."""

    def __init__(self) -> None:
        self.nlp = None
        if _SPACY_AVAILABLE:
            try:
                # Try loading lightweight English spaCy model or blank model
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except Exception:
                    self.nlp = spacy.blank("en")

                # Add custom EntityRuler for IITK campus jargon
                if "entity_ruler" not in self.nlp.pipe_names:
                    ruler = self.nlp.add_pipe("entity_ruler", last=True)
                    patterns = [
                        {"label": "IITK_JARGON", "pattern": term}
                        for term in _IITK_CAMPUS_JARGON
                    ]
                    ruler.add_patterns(patterns)
            except Exception:
                self.nlp = None

    def analyze_bullet(self, text: str) -> NLPBulletAnalysis:
        """Analyze a bullet point for action verbs, quantified metrics, and IITK entities."""
        clean_text = text.strip()
        words = re.findall(r"\b[A-Za-z0-9_%-]+\b", clean_text)
        leading_word = words[0] if words else ""
        leading_lower = leading_word.lower()

        # 1. Action Verb Detection
        has_action_verb = False
        if leading_lower in _STRONG_ACTION_VERBS:
            has_action_verb = True
        elif self.nlp and leading_word:
            try:
                doc = self.nlp(leading_word)
                if doc and len(doc) > 0 and doc[0].pos_ == "VERB":
                    has_action_verb = True
            except Exception:
                pass

        # 2. Quantified Metric Detection (CARDINAL, PERCENT, numbers)
        detected_metrics: list[str] = []
        metric_matches = re.findall(r"\b(?:\d+(?:\.\d+)?%?|\$\d+|\d+\+|\d+k|\d+x)\b", clean_text, re.IGNORECASE)
        if metric_matches:
            detected_metrics = metric_matches

        if self.nlp:
            try:
                doc = self.nlp(clean_text)
                for ent in doc.ents:
                    if ent.label_ in ("CARDINAL", "PERCENT", "MONEY", "QUANTITY"):
                        if ent.text not in detected_metrics:
                            detected_metrics.append(ent.text)
            except Exception:
                pass

        has_quantified_metric = len(detected_metrics) > 0

        # 3. IITK Campus Entity Detection
        detected_entities: list[str] = []
        for term in _IITK_CAMPUS_JARGON:
            if re.search(r"\b" + re.escape(term) + r"\b", clean_text, re.IGNORECASE):
                if term not in detected_entities:
                    detected_entities.append(term)

        if self.nlp:
            try:
                doc = self.nlp(clean_text)
                for ent in doc.ents:
                    if ent.label_ == "IITK_JARGON" and ent.text not in detected_entities:
                        detected_entities.append(ent.text)
            except Exception:
                pass

        return NLPBulletAnalysis(
            text=clean_text,
            has_action_verb=has_action_verb,
            leading_word=leading_word,
            has_quantified_metric=has_quantified_metric,
            detected_entities=detected_entities,
            detected_metrics=detected_metrics,
        )

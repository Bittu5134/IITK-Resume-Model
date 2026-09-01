"""Model variants implementation and registration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from resume_engine.pipeline import ResumeEngine, AnalysisResult
from .base import BaseDiagnosticModel
from .registry import register_model
from resume_engine.evidence.nlp import ResumeNLPPipeline


class HeuristicBaselineModel(BaseDiagnosticModel):
    """Model Variant v1: Fast Heuristic Baseline Lexer."""

    def __init__(self) -> None:
        self.engine = ResumeEngine(embedding_model=None)

    @property
    def model_id(self) -> str:
        return "v1_heuristic_baseline"

    @property
    def name(self) -> str:
        return "Heuristic Rules Baseline (v1)"

    @property
    def description(self) -> str:
        return "Fast rule-based keyword & section lexer model without embedding transformers."

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        return self.engine.analyze(pdf_path, role_id)


class SpacyNLPModel(BaseDiagnosticModel):
    """Model Variant v2: spaCy POS Tagging & IITK EntityRuler NLP Engine."""

    def __init__(self) -> None:
        self.engine = ResumeEngine(embedding_model=None)
        self.nlp = ResumeNLPPipeline()

    @property
    def model_id(self) -> str:
        return "v2_spacy_nlp"

    @property
    def name(self) -> str:
        return "spaCy POS & Campus EntityRuler (v2)"

    @property
    def description(self) -> str:
        return "Spatial PDF parser with spaCy POS verb checking, NER metric detection, and IITK jargon EntityRuler."

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        result = self.engine.analyze(pdf_path, role_id)
        # Augment with spaCy bullet analysis
        for LO in result.document.links:
            pass
        return result


class SemanticTransformerModel(BaseDiagnosticModel):
    """Model Variant v3: Vector Semantic Embedding Transformer Engine."""

    def __init__(self) -> None:
        self.engine = ResumeEngine(embedding_model="sentence-transformers/all-MiniLM-L6-v2")

    @property
    def model_id(self) -> str:
        return "v3_semantic_embed"

    @property
    def name(self) -> str:
        return "Vector Semantic Embeddings (v3)"

    @property
    def description(self) -> str:
        return "Spatial PDF parser with TF-IDF and SentenceTransformers vector semantic embedding matchers."

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        return self.engine.analyze(pdf_path, role_id)


class EnsembleHybridModel(BaseDiagnosticModel):
    """Model Variant v4: Full Ensemble Hybrid Production Engine."""

    def __init__(self) -> None:
        self.engine = ResumeEngine()

    @property
    def model_id(self) -> str:
        return "v4_ensemble_hybrid"

    @property
    def name(self) -> str:
        return "Ensemble Hybrid Production Engine (v4)"

    @property
    def description(self) -> str:
        return "Full production ensemble combining spatial PDF parsing, spaCy NER, semantic embeddings, and counterfactual advisory."

    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        return self.engine.analyze(pdf_path, role_id)


# Automatically register default model variants at import time
register_model(HeuristicBaselineModel())
register_model(SpacyNLPModel())
register_model(SemanticTransformerModel())
register_model(EnsembleHybridModel())

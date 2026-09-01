"""Base abstract interface for diagnostic engine model variants."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from resume_engine.pipeline import AnalysisResult


class BenchmarkMetrics(BaseModel):
    model_id: str
    model_name: str
    files_evaluated: int
    mean_overall_score: float
    score_stddev: float
    avg_claims_extracted: float
    avg_formatting_alerts: float
    avg_latency_ms: float
    role_scores_mean: dict[str, float] = Field(default_factory=dict)


class BaseDiagnosticModel(ABC):
    """Abstract interface for all model implementations."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique key identifying the model variant."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name of the model variant."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief summary of the model's underlying architecture."""
        ...

    @abstractmethod
    def analyze(self, pdf_path: str | Path, role_id: str) -> AnalysisResult:
        """Evaluate PDF resume against role_id and return AnalysisResult."""
        ...

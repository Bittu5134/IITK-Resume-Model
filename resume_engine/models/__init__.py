"""Multi-Model Architecture Package for IITK Context-Aware Resume Engine."""
from __future__ import annotations

from .base import BaseDiagnosticModel, BenchmarkMetrics
from .registry import register_model, get_model, list_models, get_all_models
from . import variants  # Register model variants

__all__ = [
    "BaseDiagnosticModel",
    "BenchmarkMetrics",
    "register_model",
    "get_model",
    "list_models",
    "get_all_models",
]

"""Model registry for registering, retrieving, and listing engine variants."""
from __future__ import annotations

from typing import Dict
from .base import BaseDiagnosticModel

_MODEL_REGISTRY: Dict[str, BaseDiagnosticModel] = {}


def register_model(model: BaseDiagnosticModel) -> None:
    """Register a model instance under its model_id."""
    _MODEL_REGISTRY[model.model_id] = model


def get_model(model_id: str) -> BaseDiagnosticModel:
    """Retrieve registered model by model_id. Raises KeyError if unknown."""
    mid = model_id.lower().strip()
    if mid not in _MODEL_REGISTRY:
        raise KeyError(
            f"Unknown model_id '{model_id}'. Registered models: {', '.join(sorted(_MODEL_REGISTRY.keys()))}"
        )
    return _MODEL_REGISTRY[mid]


def list_models() -> list[dict[str, str]]:
    """List all registered models with their metadata."""
    return [
        {
            "id": m.model_id,
            "name": m.name,
            "description": m.description,
        }
        for m in _MODEL_REGISTRY.values()
    ]


def get_all_models() -> dict[str, BaseDiagnosticModel]:
    """Return dictionary of all registered models."""
    return dict(_MODEL_REGISTRY)

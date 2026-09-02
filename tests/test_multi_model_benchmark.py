"""Automated test suite for Multi-Model Architecture, Benchmarking Engine, and Feedback Loop."""
from __future__ import annotations

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from resume_engine.api.app import app
from resume_engine.models import list_models, get_model, get_all_models
from resume_engine.feedback.store import FeedbackStore, FeedbackEntry
from resume_engine.feedback.learner import FeedbackLearner
from scripts.benchmark import run_benchmark


@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


def test_model_registry_contains_variants():
    """Registry must contain all 4 model variants."""
    models = list_models()
    assert len(models) >= 4
    model_ids = [m["id"] for m in models]
    assert "v1_heuristic_baseline" in model_ids
    assert "v2_spacy_nlp" in model_ids
    assert "v3_semantic_embed" in model_ids
    assert "v4_ensemble_hybrid" in model_ids


def test_get_model_by_id():
    """get_model must return valid BaseDiagnosticModel instances."""
    m1 = get_model("v1_heuristic_baseline")
    assert m1.model_id == "v1_heuristic_baseline"
    assert "Heuristic" in m1.name

    m4 = get_model("v4_ensemble_hybrid")
    assert m4.model_id == "v4_ensemble_hybrid"
    assert "Ensemble" in m4.name


def test_feedback_store_and_learner(tmp_path):
    """FeedbackStore must persist entries and FeedbackLearner must calibrate weights."""
    store_file = tmp_path / "test_feedback.json"
    store = FeedbackStore(store_path=store_file)
    assert len(store.list_feedback()) == 0

    entry1 = FeedbackEntry(
        role_id="sde",
        score_given=65.0,
        user_rating=4,
        score_adjustment=5.0,
        missing_skills=["Rust", "Kubernetes"],
        comments="Good analysis but missed Rust skill",
    )
    store.add_feedback(entry1)

    entries = store.list_feedback()
    assert len(entries) == 1
    assert entries[0]["role_id"] == "sde"

    stats = store.get_summary_stats()
    assert stats["total_entries"] == 1
    assert stats["average_user_rating"] == 4.0
    assert "rust" in stats["top_missing_skills"]

    learner = FeedbackLearner(store=store)
    result = learner.process_and_learn()
    assert result["status"] == "success"
    assert "Rust" in result["skills_added"]
    assert result["weight_adjustments"]["sde"] == 5.0


def test_api_benchmark_endpoint(api_client):
    """GET /api/v1/benchmark must return benchmark comparison results."""
    resp = api_client.get("/api/v1/benchmark")
    assert resp.status_code == 200
    data = resp.json()
    assert "models_registered" in data
    assert "benchmark_results" in data
    assert data["models_count"] > 0


def test_api_feedback_endpoint(api_client, tmp_path):
    """POST /api/v1/feedback must record feedback and update weights."""
    payload = {
        "role_id": "quant",
        "score_given": 72.0,
        "user_rating": 5,
        "score_adjustment": 3.0,
        "missing_skills": ["Stochastic Calculus"],
        "comments": "Accurate assessment",
    }
    resp = api_client.post("/api/v1/feedback", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "entry_id" in data

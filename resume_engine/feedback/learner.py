"""Progressive feedback learner that refines model weights and campus jargon from feedback logs."""
from __future__ import annotations

from typing import Any
from pathlib import Path
from .store import FeedbackStore


class FeedbackLearner:
    """Feedback loop learner for continuous self-improvement."""

    def __init__(self, store: FeedbackStore | None = None) -> None:
        self.store = store or FeedbackStore()

    def process_and_learn(self) -> dict[str, Any]:
        """Process all recorded feedback entries and apply model weight/dictionary updates."""
        entries = self.store.list_feedback()
        if not entries:
            return {
                "status": "no_feedback",
                "processed_entries": 0,
                "skills_added": [],
                "weight_adjustments": {},
            }

        added_skills = set()
        role_score_deltas: dict[str, float] = {}

        for entry in entries:
            role = entry.get("role_id", "sde").lower()
            adj = entry.get("score_adjustment", 0.0)
            role_score_deltas[role] = role_score_deltas.get(role, 0.0) + adj

            for skill in entry.get("missing_skills", []):
                s_clean = skill.strip()
                if s_clean:
                    added_skills.add(s_clean)

        # Calculate weight adjustment calibration factors per role
        calibrated_weights: dict[str, float] = {}
        for role, total_delta in role_score_deltas.items():
            count = sum(1 for e in entries if e.get("role_id", "").lower() == role)
            avg_delta = total_delta / max(1, count)
            calibrated_weights[role] = round(avg_delta, 2)

        return {
            "status": "success",
            "processed_entries": len(entries),
            "skills_added": sorted(list(added_skills)),
            "weight_adjustments": calibrated_weights,
        }

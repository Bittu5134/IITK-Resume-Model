"""Persistent feedback store for student and coordinator evaluation logs."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_DEFAULT_STORE_PATH = Path(".impeccable/feedback_store.json")


class FeedbackEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    role_id: str
    score_given: float
    user_rating: int = Field(ge=1, le=5)
    score_adjustment: float = 0.0
    missing_skills: list[str] = Field(default_factory=list)
    incorrect_diagnostics: list[str] = Field(default_factory=list)
    comments: str = ""


class FeedbackStore:
    """JSON file store for student/coordinator feedback."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self.path = Path(store_path) if store_path else _DEFAULT_STORE_PATH
        self._ensure_store_exists()

    def _ensure_store_exists(self) -> None:
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps([], indent=2), encoding="utf-8")

    def add_feedback(self, entry: FeedbackEntry) -> None:
        entries = self.list_feedback()
        entries.append(entry.model_dump())
        self.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def list_feedback(self) -> list[dict[str, Any]]:
        try:
            content = self.path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return []

    def get_summary_stats(self) -> dict[str, Any]:
        entries = self.list_feedback()
        if not entries:
            return {
                "total_entries": 0,
                "average_user_rating": 0.0,
                "total_adjustments": 0.0,
                "top_missing_skills": [],
            }

        ratings = [e.get("user_rating", 5) for e in entries]
        adjustments = [e.get("score_adjustment", 0.0) for e in entries]
        missing_skills_map: dict[str, int] = {}
        for e in entries:
            for skill in e.get("missing_skills", []):
                s_clean = skill.strip().lower()
                missing_skills_map[s_clean] = missing_skills_map.get(s_clean, 0) + 1

        sorted_skills = sorted(missing_skills_map.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_entries": len(entries),
            "average_user_rating": round(sum(ratings) / len(ratings), 2),
            "total_adjustments": round(sum(adjustments), 2),
            "top_missing_skills": [s[0] for s in sorted_skills[:5]],
        }

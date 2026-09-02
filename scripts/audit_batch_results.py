"""Audit batch JSON cross-examination results across more_resume directories.

Checks target folder category vs engine best-fit prediction accuracy across
SDE, Quant, Consulting, Core, Analyst, and Product tracks.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict


def audit_batch_json(flaw_dir: str | Path = "temp_flaw_reviews/more_resume"):
    base_dir = Path(flaw_dir)
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist.")
        return

    json_files = sorted(base_dir.glob("**/*.json"))
    print(f"Auditing {len(json_files)} cross-examination JSON files...\n")

    category_counts = defaultdict(lambda: defaultdict(int))
    mismatches = []
    total_audited = 0

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            file_info = data.get("file_info", {})
            rel_path = file_info.get("relative_path", "")
            parts = Path(rel_path).parts

            if len(parts) < 2:
                continue

            folder_category = parts[1].lower()  # e.g., "analytics", "software", "quant", "consulting", "core", "product", "finance"
            engine_best_fit = data.get("engine_best_fit_role", "").lower()
            scores = data.get("engine_multi_track_scores", {})

            # Map folder category to expected role ID
            expected_role = None
            if "software" in folder_category:
                expected_role = "sde"
            elif "quant" in folder_category:
                expected_role = "quant"
            elif "consulting" in folder_category:
                expected_role = "consulting"
            elif "core" in folder_category:
                expected_role = "core"
            elif "analytics" in folder_category:
                expected_role = "analyst"
            elif "product" in folder_category:
                expected_role = "product"
            elif "finance" in folder_category:
                expected_role = "quant"

            category_counts[folder_category][engine_best_fit] += 1
            total_audited += 1

            if expected_role and engine_best_fit != expected_role:
                # Check if expected role score was close
                exp_score = scores.get(expected_role, 0.0)
                best_score = scores.get(engine_best_fit, 0.0)
                mismatches.append({
                    "file": rel_path,
                    "target_folder": folder_category,
                    "expected_role": expected_role,
                    "predicted_best_fit": engine_best_fit,
                    "expected_role_score": exp_score,
                    "predicted_score": best_score,
                    "scores": scores
                })

        except Exception as e:
            pass

    print(f"=== BATCH AUDIT SUMMARY ({total_audited} Resumes Evaluated) ===")
    for folder, preds in sorted(category_counts.items()):
        print(f"\nFolder Category: '{folder.upper()}' ({sum(preds.values())} files)")
        for pred_role, count in sorted(preds.items(), key=lambda x: -x[1]):
            pct = (count / sum(preds.values())) * 100
            print(f"  -> Predicted {pred_role.upper()}: {count} ({pct:.1f}%)")

    print(f"\n=== TOP MISMATCHES TO TWEAK & BALANCE ({len(mismatches)} files) ===")
    for m in mismatches[:15]:
        print(f"• File: {m['file']}")
        print(f"  Target: {m['expected_role'].upper()} | Engine Predicted: {m['predicted_best_fit'].upper()} ({m['predicted_score']:.1f} vs {m['expected_role_score']:.1f})")
        print(f"  Scores: {m['scores']}\n")

    return mismatches


if __name__ == "__main__":
    audit_batch_json()

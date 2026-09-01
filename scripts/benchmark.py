#!/usr/bin/env python3
"""Multi-Model Benchmarking Engine CLI.

Evaluates all registered engine model variants across sample student resumes
in temp/ or tests/fixtures/ and outputs a comprehensive comparative benchmark report.
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
from typing import Any

from resume_engine.models.registry import get_all_models, list_models
from resume_engine.models.base import BenchmarkMetrics


def run_benchmark(sample_dir: str | Path = "temp") -> list[BenchmarkMetrics]:
    """Run comparative benchmark of all models against sample PDFs in sample_dir."""
    target_path = Path(sample_dir)
    if not target_path.exists():
        # Fallback to tests/fixtures if temp does not exist
        target_path = Path("tests/fixtures")

    pdf_files = list(target_path.glob("*.pdf"))
    if not pdf_files:
        # Search recursively
        pdf_files = list(target_path.rglob("*.pdf"))

    if not pdf_files:
        print(f"⚠️ No PDF files found in {target_path}")
        return []

    models = get_all_models()
    roles = ["sde", "quant", "consulting", "core"]
    results: list[BenchmarkMetrics] = []

    print(f"\n🚀 Running Multi-Model Benchmark across {len(pdf_files)} PDF resumes in '{target_path}'...\n")

    for mid, model in models.items():
        print(f"  Evaluating Model: {model.name} [{mid}]...")
        scores: list[float] = []
        claim_counts: list[int] = []
        alert_counts: list[int] = []
        latencies: list[float] = []
        role_scores: dict[str, list[float]] = {r: [] for r in roles}

        for pdf_file in pdf_files:
            for role_id in roles:
                t0 = time.perf_counter()
                try:
                    res = model.analyze(pdf_file, role_id)
                    t1 = time.perf_counter()
                    lat_ms = (t1 - t0) * 1000.0

                    s_val = res.score.score
                    scores.append(s_val)
                    role_scores[role_id].append(s_val)
                    claim_counts.append(res.evidence.claim_count)
                    alert_counts.append(len(res.document.warnings))
                    latencies.append(lat_ms)
                except Exception as e:
                    print(f"    ⚠️ Error evaluating {pdf_file.name} on {role_id}: {e}")

        if not scores:
            continue

        mean_score = sum(scores) / len(scores)
        variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
        stddev = math.sqrt(variance)

        role_means = {
            r: (sum(r_scores) / len(r_scores)) if r_scores else 0.0
            for r, r_scores in role_scores.items()
        }

        metrics = BenchmarkMetrics(
            model_id=model.model_id,
            model_name=model.name,
            files_evaluated=len(pdf_files),
            mean_overall_score=round(mean_score, 2),
            score_stddev=round(stddev, 2),
            avg_claims_extracted=round(sum(claim_counts) / len(claim_counts), 1),
            avg_formatting_alerts=round(sum(alert_counts) / len(alert_counts), 1),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2),
            role_scores_mean={r: round(m, 2) for r, m in role_means.items()},
        )
        results.append(metrics)

    return results


def print_benchmark_table(results: list[BenchmarkMetrics]) -> None:
    """Print formatted markdown benchmark comparison table."""
    if not results:
        return

    print("\n" + "=" * 90)
    print("📊 MULTI-MODEL RESUME DIAGNOSTIC ENGINE BENCHMARK REPORT")
    print("=" * 90 + "\n")

    header = f"| {'Model Name':<42} | {'Files':<5} | {'Mean Score':<10} | {'StdDev':<7} | {'Avg Claims':<10} | {'Latency':<8} |"
    divider = f"|{'-'*44}|{'-'*7}|{'-'*12}|{'-'*9}|{'-'*12}|{'-'*10}|"
    print(header)
    print(divider)

    for m in results:
        print(
            f"| {m.model_name:<42} | {m.files_evaluated:<5} | {m.mean_overall_score:<10.2f} | {m.score_stddev:<7.2f} | {m.avg_claims_extracted:<10.1f} | {m.avg_latency_ms:<6.1f}ms |"
        )
    print("\n" + "=" * 90 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Multi-Model Resume Diagnostic Engine Benchmarking.")
    parser.add_argument("--dir", default="temp", help="Directory containing PDF resumes for evaluation.")
    args = parser.parse_args()

    results = run_benchmark(args.dir)
    print_benchmark_table(results)


if __name__ == "__main__":
    main()

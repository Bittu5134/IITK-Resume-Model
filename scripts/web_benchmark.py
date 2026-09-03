#!/usr/bin/env python3
"""Comprehensive Performance and Load Benchmarking Suite for IITK Resume Engine.

Benchmarks:
1. Static SPA HTML endpoint GET /
2. Health Check endpoint GET /health
3. Single-Role PDF Diagnosis POST /analyze (across multiple concurrency levels)
4. Multi-Track PDF Diagnosis POST /analyze-all (evaluating all 6 roles under concurrent load)
5. Direct In-Process Core Pipeline Execution (CPU/Parsing/Scoring breakdown)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import httpx
from resume_engine.pipeline import ResumeEngine
from resume_engine.parser.pdf_parser import parse_pdf


@dataclass
class LoadBenchmarkResult:
    test_name: str
    endpoint: str
    total_requests: int
    concurrency: int
    duration_seconds: float
    successful_requests: int
    failed_requests: int
    req_per_sec: float
    latency_mean_ms: float
    latency_median_ms: float
    latency_p90_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_min_ms: float
    latency_max_ms: float
    status_codes: Dict[int, int]


async def benchmark_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
    endpoint: str,
    method: str = "GET",
    files: dict | None = None,
    data: dict | None = None,
    total_requests: int = 50,
    concurrency: int = 5,
    test_name: str = "Benchmark",
) -> LoadBenchmarkResult:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: List[float] = []
    status_codes: Dict[int, int] = {}
    success = 0
    failed = 0

    url = f"{base_url.rstrip('/')}{endpoint}"

    async def single_req():
        nonlocal success, failed
        async with semaphore:
            t0 = time.perf_counter()
            try:
                if method == "GET":
                    resp = await client.get(url, timeout=60.0)
                elif method == "POST":
                    if files:
                        form_files = {k: (v[0], v[1], v[2]) for k, v in files.items()}
                        resp = await client.post(url, files=form_files, data=data, timeout=60.0)
                    else:
                        resp = await client.post(url, data=data, timeout=60.0)
                else:
                    raise ValueError(f"Unsupported method {method}")
                
                t1 = time.perf_counter()
                lat_ms = (t1 - t0) * 1000.0
                latencies.append(lat_ms)
                status_codes[resp.status_code] = status_codes.get(resp.status_code, 0) + 1

                if resp.status_code == 200:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                t1 = time.perf_counter()
                lat_ms = (t1 - t0) * 1000.0
                latencies.append(lat_ms)
                failed += 1
                status_codes[0] = status_codes.get(0, 0) + 1

    start_time = time.perf_counter()
    tasks = [asyncio.create_task(single_req()) for _ in range(total_requests)]
    await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - start_time

    sorted_lat = sorted(latencies) if latencies else [0.0]

    def percentile(p: float) -> float:
        if not sorted_lat:
            return 0.0
        k = (len(sorted_lat) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_lat[int(k)]
        d0 = sorted_lat[int(f)] * (c - k)
        d1 = sorted_lat[int(c)] * (k - f)
        return d0 + d1

    rps = total_requests / total_duration if total_duration > 0 else 0.0

    return LoadBenchmarkResult(
        test_name=test_name,
        endpoint=endpoint,
        total_requests=total_requests,
        concurrency=concurrency,
        duration_seconds=round(total_duration, 2),
        successful_requests=success,
        failed_requests=failed,
        req_per_sec=round(rps, 2),
        latency_mean_ms=round(statistics.mean(sorted_lat), 2) if sorted_lat else 0.0,
        latency_median_ms=round(statistics.median(sorted_lat), 2) if sorted_lat else 0.0,
        latency_p90_ms=round(percentile(0.90), 2),
        latency_p95_ms=round(percentile(0.95), 2),
        latency_p99_ms=round(percentile(0.99), 2),
        latency_min_ms=round(sorted_lat[0], 2) if sorted_lat else 0.0,
        latency_max_ms=round(sorted_lat[-1], 2) if sorted_lat else 0.0,
        status_codes=status_codes,
    )


def benchmark_in_process_pipeline(pdf_path: str, iterations: int = 20) -> dict:
    """Benchmark raw in-process Python pipeline execution and breakdown."""
    engine = ResumeEngine()
    roles = ["sde", "quant", "consulting", "core", "analyst", "product"]

    # 1. Benchmark Spatial Parsing
    parse_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        doc = parse_pdf(pdf_path)
        parse_latencies.append((time.perf_counter() - t0) * 1000.0)

    # 2. Benchmark Evidence Extraction
    doc = parse_pdf(pdf_path)
    extract_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        ev = engine.extractor.extract(doc)
        extract_latencies.append((time.perf_counter() - t0) * 1000.0)

    # 3. Benchmark Role Scoring & Advisory per role
    ev = engine.extractor.extract(doc)
    score_latencies = {r: [] for r in roles}
    for r in roles:
        role_req = engine.roles[r]
        for _ in range(iterations):
            t0 = time.perf_counter()
            score = engine.scorer.score(ev, role_req)
            adv = engine.advisor.generate_advisory(doc, ev, score, role_req)
            score_latencies[r].append((time.perf_counter() - t0) * 1000.0)

    # 4. Benchmark Full analyze_all (End-to-End all 6 tracks)
    e2e_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = engine.analyze_all(pdf_path)
        e2e_latencies.append((time.perf_counter() - t0) * 1000.0)

    return {
        "pdf_file": Path(pdf_path).name,
        "iterations": iterations,
        "spatial_parsing_ms": {
            "mean": round(statistics.mean(parse_latencies), 2),
            "median": round(statistics.median(parse_latencies), 2),
            "p95": round(sorted(parse_latencies)[int(len(parse_latencies) * 0.95)], 2),
        },
        "evidence_extraction_ms": {
            "mean": round(statistics.mean(extract_latencies), 2),
            "median": round(statistics.median(extract_latencies), 2),
            "p95": round(sorted(extract_latencies)[int(len(extract_latencies) * 0.95)], 2),
        },
        "role_scoring_and_advisory_ms": {
            r: {
                "mean": round(statistics.mean(lats), 2),
                "median": round(statistics.median(lats), 2),
            }
            for r, lats in score_latencies.items()
        },
        "full_analyze_all_6_tracks_ms": {
            "mean": round(statistics.mean(e2e_latencies), 2),
            "median": round(statistics.median(e2e_latencies), 2),
            "p95": round(sorted(e2e_latencies)[int(len(e2e_latencies) * 0.95)], 2),
            "min": round(min(e2e_latencies), 2),
            "max": round(max(e2e_latencies), 2),
        },
    }


async def main_async(args):
    pdf_bytes = Path(args.pdf).read_bytes()
    pdf_name = Path(args.pdf).name

    print(f"\n================================================================================")
    print(f"🔥 IITK RESUME ENGINE WEB PERFORMANCE & LOAD BENCHMARK")
    print(f"================================================================================")
    print(f"Target URL: {args.url}")
    print(f"Sample PDF: {pdf_name} ({len(pdf_bytes) / 1024:.1f} KB)")
    print(f"================================================================================\n")

    results: List[LoadBenchmarkResult] = []

    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(limits=limits, timeout=60.0) as client:
        # Test 1: Health Endpoint (GET /health) - Low concurrency
        print("▶ [1/6] Benchmarking GET /health (Concurrency: 10, Requests: 100)...")
        r1 = await benchmark_endpoint(
            client,
            args.url,
            "/health",
            method="GET",
            total_requests=100,
            concurrency=10,
            test_name="Health Check (Light Load)",
        )
        results.append(r1)

        # Test 2: Health Endpoint (GET /health) - High concurrency
        print("▶ [2/6] Benchmarking GET /health (Concurrency: 30, Requests: 300)...")
        r2 = await benchmark_endpoint(
            client,
            args.url,
            "/health",
            method="GET",
            total_requests=300,
            concurrency=30,
            test_name="Health Check (High Concurrency)",
        )
        results.append(r2)

        # Test 3: Static SPA UI (GET /) - Concurrency 15
        print("▶ [3/6] Benchmarking GET / (SPA UI HTML) (Concurrency: 15, Requests: 100)...")
        r3 = await benchmark_endpoint(
            client,
            args.url,
            "/",
            method="GET",
            total_requests=100,
            concurrency=15,
            test_name="SPA Dashboard HTML (GET /)",
        )
        results.append(r3)

        # Test 4: Single Role POST /analyze (SDE) - Concurrency 5
        print("▶ [4/6] Benchmarking POST /analyze (Role: SDE, Concurrency: 5, Requests: 30)...")
        r4 = await benchmark_endpoint(
            client,
            args.url,
            "/analyze",
            method="POST",
            files={"file": (pdf_name, pdf_bytes, "application/pdf")},
            data={"role": "sde"},
            total_requests=30,
            concurrency=5,
            test_name="Single-Role PDF Analysis (POST /analyze [sde])",
        )
        results.append(r4)

        # Test 5: Single Role POST /analyze (Consulting) - Concurrency 8
        print("▶ [5/6] Benchmarking POST /analyze (Role: Consulting, Concurrency: 8, Requests: 40)...")
        r5 = await benchmark_endpoint(
            client,
            args.url,
            "/analyze",
            method="POST",
            files={"file": (pdf_name, pdf_bytes, "application/pdf")},
            data={"role": "consulting"},
            total_requests=40,
            concurrency=8,
            test_name="Single-Role PDF Analysis (POST /analyze [consulting])",
        )
        results.append(r5)

        # Test 6: Multi-Track POST /analyze-all (All 6 tracks simultaneous) - Concurrency 6
        print("▶ [6/6] Benchmarking POST /analyze-all (All 6 Tracks, Concurrency: 6, Requests: 24)...")
        r6 = await benchmark_endpoint(
            client,
            args.url,
            "/analyze-all",
            method="POST",
            files={"file": (pdf_name, pdf_bytes, "application/pdf")},
            total_requests=24,
            concurrency=6,
            test_name="Multi-Track 6-Role Analysis (POST /analyze-all)",
        )
        results.append(r6)

    # In-process Core Pipeline Benchmark
    print("\n▶ Running In-Process Python Pipeline Breakdown (20 iterations)...")
    pipeline_breakdown = benchmark_in_process_pipeline(args.pdf, iterations=20)

    # Print Summary Table
    print("\n" + "=" * 115)
    print(f"📊 LIVE HTTP BENCHMARK RESULTS ({args.url})")
    print("=" * 115)
    header = f"| {'Scenario':<40} | {'Reqs':<5} | {'Conc':<4} | {'RPS':<8} | {'Median':<9} | {'P95':<9} | {'P99':<9} | {'Success':<7} |"
    divider = f"|{'-'*42}|{'-'*7}|{'-'*6}|{'-'*10}|{'-'*11}|{'-'*11}|{'-'*11}|{'-'*9}|"
    print(header)
    print(divider)

    for r in results:
        print(
            f"| {r.test_name:<40} | {r.total_requests:<5} | {r.concurrency:<4} | {r.req_per_sec:<8.1f} | {r.latency_median_ms:<7.1f}ms | {r.latency_p95_ms:<7.1f}ms | {r.latency_p99_ms:<7.1f}ms | {r.successful_requests}/{r.total_requests:<5} |"
        )
    print("=" * 115 + "\n")

    print("⚡ IN-PROCESS CORE PIPELINE EXECUTION BREAKDOWN:")
    print(f"  • Spatial LaTeX-PDF Parsing:   {pipeline_breakdown['spatial_parsing_ms']['mean']:.2f} ms (p95: {pipeline_breakdown['spatial_parsing_ms']['p95']:.2f} ms)")
    print(f"  • Semantic Evidence Extraction: {pipeline_breakdown['evidence_extraction_ms']['mean']:.2f} ms (p95: {pipeline_breakdown['evidence_extraction_ms']['p95']:.2f} ms)")
    print(f"  • Full End-to-End (6 Tracks):   {pipeline_breakdown['full_analyze_all_6_tracks_ms']['mean']:.2f} ms (median: {pipeline_breakdown['full_analyze_all_6_tracks_ms']['median']:.2f} ms)")
    for r, v in pipeline_breakdown["role_scoring_and_advisory_ms"].items():
        print(f"    - Track [{r:<10}]: {v['mean']:.2f} ms")

    # Output JSON Report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "target_url": args.url,
        "sample_pdf": pdf_name,
        "load_benchmark_results": [asdict(r) for r in results],
        "in_process_pipeline_breakdown": pipeline_breakdown,
    }

    report_path = Path(args.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n✅ Full benchmark report saved to: {report_path.resolve()}\n")


def main():
    parser = argparse.ArgumentParser(description="IITK Resume Engine Web Benchmark")
    parser.add_argument("--url", default="https://iitk-resume.bittu.dev", help="Target base URL")
    parser.add_argument("--pdf", default="tests/fixtures/golden_resume_01.pdf", help="Sample PDF to upload")
    parser.add_argument("--output", default="docs/benchmark_report.json", help="Path to save JSON benchmark report")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

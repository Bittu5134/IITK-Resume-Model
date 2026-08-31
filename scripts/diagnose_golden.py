"""Diagnostic script -- golden resume AST, evidence, and score audit.

Run:
    python scripts/diagnose_golden.py tests/fixtures/golden_resume_01.pdf
"""
from __future__ import annotations

import sys
import json
import io
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.scoring.scorer import RoleScorer
from resume_engine.advisory.advisor import CounterfactualAdvisor


def sep(title: str, width: int = 72) -> None:
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print('=' * width)


def sub(title: str, width: int = 72) -> None:
    print(f"\n  {'-' * (width - 4)}")
    print(f"  {title}")
    print(f"  {'-' * (width - 4)}")


def main(pdf_path: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"\nDIAGNOSTIC AUDIT: {path.name}")

    # ── Stage 1: Parser ──────────────────────────────────────────────────
    sep("STAGE 1 — PARSER OUTPUT")
    ast = parse_pdf(path)

    print(f"\nSource:  {ast.source_file}")
    print(f"Parser:  {ast.parser_version}")
    print(f"Layout:  {ast.layout_diagnostics}")
    print(f"Sections detected ({len(ast.sections)}):")
    for s in ast.sections:
        entries = len(s.entries)
        bullets = len(s.bullets)
        print(f"  [{s.page_start}] {s.name:<38} entries={entries:>2}  bullets={bullets:>2}")

    # Per section detail
    print("\nPer-section entries and bullets:")
    for section in ast.sections:
        if section.name == "Header" and not section.entries and not section.bullets:
            continue
        print(f"\n  SECTION: {section.name}  (page {section.page_start})")
        for entry in section.entries:
            print(f"    ENTRY [{entry.page_start}]: {entry.title[:60] or '(untitled)'}")
            if entry.dates:
                print(f"           dates: {entry.dates}")
            for b in entry.bullets:
                txt = b.text[:90] + ("…" if len(b.text) > 90 else "")
                print(f"      • {txt}")
        # Bullets not assigned to any entry
        orphans = [b for b in section.bullets
                   if not any(b in e.bullets for e in section.entries)]
        for b in orphans:
            txt = b.text[:90] + ("…" if len(b.text) > 90 else "")
            print(f"      • (orphan) {txt}")

    sub("HYPERLINKS")
    for lo in ast.link_objects:
        section_info = f" → {lo.section}" if lo.section else ""
        print(f"  [{lo.page}] {lo.link_type:<20} {lo.uri}{section_info}")
        if lo.associated_text:
            print(f"            near: '{lo.associated_text[:60]}'")

    if ast.warnings:
        sub("PARSER WARNINGS")
        for w in ast.warnings:
            print(f"  ⚠  {w}")

    # ── Stage 2: Evidence ────────────────────────────────────────────────
    sep("STAGE 2 — EVIDENCE EXTRACTION")
    extractor = EvidenceExtractor()
    ev = extractor.extract(ast)

    print(f"\nTotal claims:        {len(ev.claims)}")
    print(f"Academic metrics:    {len(ev.academic_metrics)}")
    print(f"All skills detected: {ev.all_skills}")
    print(f"All entities:        {ev.all_entities}")

    if ev.academic_metrics:
        sub("ACADEMIC METRICS")
        for am in ev.academic_metrics:
            scale_str = f"/{am.scale:.1f}" if am.scale else ""
            print(f"  {am.metric_type.upper()}: {am.value}{scale_str}  (raw: '{am.raw}') [{am.institution or 'unknown institution'}]")

    sub("CLAIMS TABLE")
    print(f"  {'ID':<8} {'SEC':<30} {'VERB':<14} {'STR':>5} {'EV':>5}  METRICS  SKILLS  ENTITIES")
    print(f"  {'-'*7} {'-'*29} {'-'*13} {'-'*5} {'-'*5}  {'-'*7}  {'-'*6}  {'-'*7}")
    for cl in ev.claims:
        verb = (cl.action_verb or "-")[:12]
        metrics_str = ",".join(m.raw[:8] for m in cl.impact_metrics[:2]) or "-"
        skills_str = ",".join(cl.skills[:3]) or "-"
        entities_str = ",".join(e.canonical[:10] for e in cl.entities[:2]) or "-"
        print(
            f"  {cl.claim_id:<8} {cl.section[:29]:<30} {verb:<14} "
            f"{cl.action_strength:>5.2f} {cl.evidence_strength:>5.2f}  "
            f"{metrics_str[:8]:<8} {skills_str[:12]:<12} {entities_str[:14]}"
        )

    # ── Stage 3-5: Scoring per role ──────────────────────────────────────
    sep("STAGE 3-5 — ROLE SCORES AND ADVISORY")
    roles = load_role_graphs()
    matcher = HybridMatcher()
    scorer = RoleScorer()
    advisor = CounterfactualAdvisor()

    role_results: dict = {}
    for role_id in ["sde", "quant", "consulting", "core"]:
        role = roles[role_id]
        matches = matcher.match(ev, role)
        score = scorer.score(ev, role, matches, link_objects=ast.link_objects)
        advisory = advisor.build(ev, score)
        role_results[role_id] = (score, advisory, matches)

    # Summary table
    print("\n  ROLE          SCORE   COV    CONFIDENCE")
    print(f"  {'-'*12}  {'-'*5}  {'-'*4}   {'-'*10}")
    for role_id, (score, _, _) in role_results.items():
        print(
            f"  {role_id:<12}  {score.score:>5.1f}  "
            f"{score.coverage:.0%}    {score.confidence:.2f}"
        )

    for role_id, (score, advisory, matches) in role_results.items():
        sub(f"ROLE: {role_id.upper()}  —  Score {score.score:.1f}/100")

        # Competency breakdown
        print("\n  Competency breakdown:")
        for c in score.competency_scores:
            bar = "█" * int(c.strength * 20) + "░" * (20 - int(c.strength * 20))
            print(
                f"    {c.competency:<28} {bar}  "
                f"str={c.strength:.3f}  contrib={c.contribution:.1f}  "
                f"{'['+','.join(c.reason_codes[:2])+']' if c.reason_codes else ''}"
            )

        # Penalties
        if score.penalties:
            print("\n  Penalties:")
            for p in score.penalties:
                print(f"    ⚠  [{p['code']}] -{p['points']:.1f}pts: {p['reason']}")

        # Top strengths
        if advisory.top_strengths:
            print("\n  Top strengths:")
            for s in advisory.top_strengths:
                print(f"    ★  {s['competency']}: {s['strength']:.2f}  claims={s['claims'][:2]}")

        # Critical gaps
        if advisory.critical_gaps:
            print("\n  Critical gaps:")
            for g in advisory.critical_gaps:
                print(f"    ✗  {g['competency']}: strength={g['strength']:.2f}  weight={g['weight']:.2f}")

        # Top recommendations
        print("\n  Top 3 recommendations:")
        for rec in advisory.recommendations[:3]:
            snippet = (rec.text_snippet[:60] + "…") if rec.text_snippet and len(rec.text_snippet) > 60 else (rec.text_snippet or "(no source bullet)")
            print(f"    [{rec.priority}] {rec.competency}: +{rec.max_potential_gain_estimate:.1f}pts potential")
            print(f"       src: {rec.source_claim_id} | page={rec.page} | '{snippet}'")
            print(f"       → {rec.action[:100]}…")

        # Sample line diagnostics
        print("\n  Sample line diagnostics (first 5 non-trivial):")
        shown = 0
        for d in advisory.line_diagnostics:
            if d.severity != "info" and shown < 5:
                print(f"    [{d.severity}] {d.section} p{d.page}: '{d.text_snippet[:60]}…'")
                for issue in d.issues[:2]:
                    print(f"       ✗ {issue}")
                shown += 1

    # ── Invariant checks ─────────────────────────────────────────────────
    sep("INVARIANT VERIFICATION")
    errors: list[str] = []
    warnings_check: list[str] = []

    # Check: no CP evidence
    sde_score, _, _ = role_results["sde"]
    cp_comp = next((c for c in sde_score.competency_scores if c.competency == "competitive_programming"), None)
    if cp_comp and cp_comp.strength > 0:
        errors.append(f"FAIL: SDE competitive_programming strength={cp_comp.strength} (expected 0 — no CP in resume)")
    else:
        print("  ✓ SDE competitive_programming == 0 (no CP evidence)")

    # Check: projects > 0
    proj_comp = next((c for c in sde_score.competency_scores if c.competency == "projects"), None)
    if not proj_comp or proj_comp.strength == 0:
        errors.append("FAIL: SDE projects strength == 0 (should be > 0)")
    else:
        print(f"  ✓ SDE projects strength={proj_comp.strength:.3f} (>0)")

    # Check: internships > 0
    intern_comp = next((c for c in sde_score.competency_scores if c.competency == "internships"), None)
    if not intern_comp or intern_comp.strength == 0:
        errors.append("FAIL: SDE internships strength == 0 (should be > 0)")
    else:
        print(f"  ✓ SDE internships strength={intern_comp.strength:.3f} (>0)")

    # Check: no project penalty
    proj_penalties = [p for p in sde_score.penalties if "project" in p.get("code","")]
    if proj_penalties:
        errors.append(f"FAIL: Golden resume has project penalty: {proj_penalties}")
    else:
        print("  ✓ No project penalty for SDE")

    # Check: GitHub detected
    uris = [lo.uri for lo in ast.link_objects]
    has_gh = any("github.com" in u.lower() for u in uris)
    if has_gh:
        gh_pen = [p for p in sde_score.penalties if p.get("code") == "missing_github"]
        if gh_pen:
            errors.append("FAIL: GitHub link present but missing_github penalty still fires")
        else:
            print("  ✓ GitHub link detected, no missing_github penalty")
    else:
        warnings_check.append("INFO: No GitHub link detected in golden resume — skipping GitHub penalty check")

    # Check: consulting leadership
    con_score, _, _ = role_results["consulting"]
    lead = next((c for c in con_score.competency_scores if c.competency == "leadership"), None)
    if not lead or lead.strength == 0:
        warnings_check.append("WARN: Consulting leadership strength == 0")
    else:
        print(f"  ✓ Consulting leadership strength={lead.strength:.3f} (>0)")

    # Report
    for w in warnings_check:
        print(f"  ⚠  {w}")
    if errors:
        print(f"\n  INVARIANT FAILURES: {len(errors)}")
        for e in errors:
            print(f"  ✗  {e}")
        sys.exit(1)
    else:
        print(f"\n  All invariants PASSED ✓")


if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/golden_resume_01.pdf"
    main(pdf)

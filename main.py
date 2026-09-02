import argparse
import json
import sys
from resume_engine.pipeline import ResumeEngine

def main():
    ap = argparse.ArgumentParser(description="IITK Context-Aware Resume Diagnostic Engine")
    ap.add_argument("pdf", nargs="?", help="Path to SPO PDF resume file")
    ap.add_argument("--role", choices=["sde", "quant", "consulting", "core", "analyst", "product", "ib"], help="Target industry track")
    ap.add_argument("--all", action="store_true", help="Diagnose across all tracks and show multi-track comparison")
    ap.add_argument("-o", "--output", help="Save analysis output (.json or .md) to file")
    ap.add_argument("--serve", action="store_true", help="Launch the Web Advisory Dashboard server")
    ap.add_argument("--reload", action="store_true", default=True, help="Enable auto hot reload for development")
    ap.add_argument("--host", default="0.0.0.0", help="Host address for server (default: 0.0.0.0)")
    ap.add_argument("--port", type=int, default=8000, help="Port for web server (default: 8000)")

    args = ap.parse_args()

    if args.serve:
        import uvicorn
        print(f"🚀 Starting IITK Resume Diagnostic Web Engine on http://localhost:{args.port} (hot reload: {args.reload})")
        uvicorn.run("resume_engine.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return

    if not args.pdf:
        ap.print_help()
        print("\nTip: Run 'python main.py --serve' to launch the interactive web dashboard!")
        sys.exit(1)

    engine = ResumeEngine()

    if args.all:
        results = engine.analyze_all(args.pdf)
        best_role = results.get("best_fit_role", "sde").upper()
        
        print("\n" + "=" * 78)
        print(f"🎓 IITK CONTEXT-AWARE RESUME DIAGNOSTIC ENGINE — MULTI-TRACK AUDIT")
        print("=" * 78)
        print(f"Candidate Resume : {args.pdf}")
        print(f"Autonomous Fit   : ★ {best_role} (Best Alignment)")
        print("-" * 78)
        print(f"{'Track':<24} | {'Score':<8} | {'Tier':<20} | {'Top Critical Gap'}")
        print("-" * 78)

        track_names = {
            "sde": "Software Engineering",
            "quant": "Quantitative Finance",
            "consulting": "Management Consulting",
            "core": "Core Engineering",
            "analyst": "Data Analyst",
            "product": "Product Manager",
            "ib": "Investment Banking",
        }

        for r_id in ["sde", "quant", "consulting", "core", "analyst", "product", "ib"]:
            if r_id in results:
                sc = results[r_id].get("score", {})
                score_val = sc.get("score", 0.0)
                tier = sc.get("tier", "N/A")
                adv = results[r_id].get("advisory", {})
                gaps = adv.get("critical_gaps", [])
                top_gap = gaps[0].get("competency", "None").replace("_", " ").title() if gaps else "None"
                marker = "★ " if r_id == results.get("best_fit_role") else "  "
                print(f"{marker}{track_names.get(r_id, r_id):<22} | {score_val:5.1f}/100 | {tier:<20} | {top_gap}")

        print("=" * 78)
        
        best_data = results.get(results.get("best_fit_role", "sde"), {})
        recs = best_data.get("advisory", {}).get("recommendations", [])
        if recs:
            print("\n🎯 TOP ACTIONABLE REWRITES (Google XYZ Formula):")
            for idx, r in enumerate(recs[:3], 1):
                print(f"  {idx}. [{r.get('target_entry', 'Entry')}] {r.get('action')}")
                if r.get("suggested_bullet_template"):
                    print(f"     ↳ Senior Rewrite: \"{r.get('suggested_bullet_template')}\" (+{r.get('max_potential_gain_estimate', 0)} pts)")
            print("-" * 78)

        if args.output:
            if args.output.endswith(".json"):
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Full analysis JSON saved to {args.output}")
            else:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(f"# IITK Resume Diagnostic Report: {args.pdf}\n\n")
                    f.write(f"**Best Fit Role**: {best_role}\n\n")
                    f.write("## Multi-Track Scores\n")
                    for r_id in ["sde", "quant", "consulting", "core", "analyst", "product", "ib"]:
                        sc = results[r_id]["score"]
                        f.write(f"- **{track_names.get(r_id, r_id)}**: {sc['score']}/100 ({sc['tier']})\n")
                print(f"Summary report saved to {args.output}")
        return

    if not args.role:
        print("Error: --role argument or --all is required when analyzing a PDF via CLI.")
        sys.exit(1)

    result = engine.analyze(args.pdf, args.role)
    text = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Analysis saved to {args.output}")
    else:
        print(text)

if __name__ == "__main__":
    main()


"""Run deep diagnostic analysis on 5 target resumes across tracks."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.pipeline import ResumeEngine

TARGET_PDFS = [
    ("Software", "temp/more_resume/Y21/Software/Shashikant Yadav.pdf", "sde"),
    ("Finance", "temp/more_resume/Y21/Finance/Siddhant Singh.pdf", "quant"),
    ("Consulting", "temp/more_resume/Y21/Consulting/Mihir Tomar.pdf", "consulting"),
    ("Core", "temp/more_resume/Y21/Core/Diptansu Poddar.pdf", "core"),
    ("Analytics", "temp/more_resume/Y21/Analytics/Akshat Jain.pdf", "analyst"),
]

def main():
    engine = ResumeEngine()
    
    print("=========================================================================")
    print("        DEEP DIAGNOSTIC AUDIT OF 5 REPRESENTATIVE RESUMES               ")
    print("=========================================================================\n")

    for category, pdf_path_str, expected_role in TARGET_PDFS:
        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            # Fallback if specific file missing
            matches = list(Path("temp/more_resume").glob(f"**/{category}/*.pdf"))
            if matches:
                pdf_path = matches[0]
            else:
                print(f"Skipping {category}: file not found.")
                continue

        print(f"-------------------------------------------------------------------------")
        print(f"📄 FILE: {pdf_path.name}")
        print(f"📁 FOLDER CATEGORY: {category} | EXPECTED TRACK: {expected_role.upper()}")
        print(f"-------------------------------------------------------------------------")

        res = engine.analyze_all(str(pdf_path))
        best_role = res.get("best_fit_role", "sde")

        print(f"🎯 DIAGNOSED BEST FIT: {best_role.upper()} " + ("✅ MATCH" if best_role == expected_role else "⚠️ MISMATCH"))

        print("\n📊 6-TRACK MATCH SCORES:")
        for r in ["sde", "quant", "consulting", "core", "analyst", "product"]:
            r_data = res.get(r, {})
            score = round(r_data.get("score", {}).get("score", 0), 1)
            tier = r_data.get("score", {}).get("tier", "Unknown")
            active_marker = " 👈 (BEST FIT)" if r == best_role else ""
            expected_marker = " ★ (EXPECTED)" if r == expected_role else ""
            print(f"  - {r.upper():<12}: {score:>5.1f} / 100 [{tier.upper()}]{active_marker}{expected_marker}")

        best_res = res.get(best_role, {})
        evidence = best_res.get("evidence", {})
        advisory = best_res.get("advisory", {})

        print("\n🔍 EXTRACTED EVIDENCE & METRICS:")
        print(f"  - Extracted CPI: {evidence.get('cpi')}")
        print(f"  - Extracted Entities: {evidence.get('all_entities', [])[:8]}")
        print(f"  - Claims Count: {len(evidence.get('claims', []))}")
        print(f"  - Academic Metrics: {evidence.get('academic_metrics', [])}")

        swot = advisory.get("swot_analysis", {})
        print("\n📌 SWOT SUMMARY:")
        print(f"  - Strengths (S): {swot.get('strengths', [])[:2]}")
        print(f"  - Weaknesses (W): {swot.get('weaknesses', [])[:2]}")
        print(f"  - Opportunities (O): {swot.get('opportunities', [])[:2]}")
        print(f"  - Threats (T): {swot.get('threats', [])[:2]}")

        print("\n💡 TOP RECOMMENDATIONS:")
        recs = advisory.get("recommendations", [])
        for rec in recs[:2]:
            print(f"  - [{rec.get('priority', '').upper()}] Gain: +{rec.get('max_potential_gain_estimate', 0):.1f} pts | Competency: {rec.get('competency')}")
            print(f"    Action: {rec.get('action')}")

        print("\n")

if __name__ == "__main__":
    main()

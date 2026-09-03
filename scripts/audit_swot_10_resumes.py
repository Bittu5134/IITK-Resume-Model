#!/usr/bin/env python3
"""Audit 10 PDF Resumes against ResumeEngine SWOT Analysis."""

import json
from pathlib import Path
from resume_engine.pipeline import ResumeEngine

PDF_PATHS = [
    "tests/fixtures/golden_resume_01.pdf",
    "temp/220082_aditya_v_bs_sds.pdf",
    "temp/220486_anvay_joshi_bt_ee.pdf",
    "temp/220830_priyanshu_singh.pdf",
    "temp/SPO-IITK_0013_230189_arihant_kumar_bt_cse_30edf2754f664e2aaf7daade17cf0efc.pdf",
    "temp/more_resume/Y21/Analytics/Akshat Jain.pdf",
    "temp/more_resume/Y21/Consulting/Aditya Subramanian.pdf",
    "temp/more_resume/Y21/Core/Devansh Jain.pdf",
    "temp/more_resume/Y21/Finance/Amit Kumar.pdf",
    "temp/more_resume/Y21/Consulting/Vrinda Sharma.pdf",
]

def main():
    engine = ResumeEngine()
    results = []

    print(f"🚀 Running SWOT Diagnostic Audit across {len(PDF_PATHS)} PDF Resumes...\n")

    for idx, rel_path in enumerate(PDF_PATHS, 1):
        pdf_file = Path(rel_path)
        if not pdf_file.exists():
            print(f"⚠️ [{idx}/{len(PDF_PATHS)}] Skipping missing file: {rel_path}")
            continue

        print(f"▶ [{idx}/{len(PDF_PATHS)}] Analyzing {pdf_file.name}...")
        try:
            analysis_all = engine.analyze_all(pdf_file)
            best_role = analysis_all.get("best_fit_role", "sde")
            best_analysis = analysis_all.get(best_role, {})
            
            swot = best_analysis.get("advisory", {}).get("swot_analysis", {})
            score = best_analysis.get("score", {}).get("score", 0)
            tier = best_analysis.get("score", {}).get("tier", "Unknown")

            audit_item = {
                "id": idx,
                "file_name": pdf_file.name,
                "path": str(pdf_file),
                "best_fit_role": best_role.upper(),
                "score": score,
                "tier": tier,
                "swot": swot,
            }
            results.append(audit_item)
            print(f"   ✓ Best Fit: {best_role.upper()} | Score: {score:.1f}/100 ({tier})")
            print(f"     Strengths: {len(swot.get('strengths', []))} items")
            print(f"     Weaknesses: {len(swot.get('weaknesses', []))} items")
            print(f"     Opportunities: {len(swot.get('opportunities', []))} items")
            print(f"     Threats: {len(swot.get('threats', []))} items")
        except Exception as e:
            print(f"   ❌ Failed to analyze {pdf_file.name}: {e}")

    out_file = Path("docs/swot_10_resumes_audit.json")
    out_file.write_text(json.dumps(results, indent=2))
    print(f"\n✅ Audit finished! Report saved to {out_file}")

if __name__ == "__main__":
    main()

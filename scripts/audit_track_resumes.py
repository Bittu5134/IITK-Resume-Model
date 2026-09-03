"""Audit script to evaluate resumes categorized by domain track in temp/more_resume/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.pipeline import ResumeEngine

FOLDER_TO_ROLE = {
    "Analytics": "analyst",
    "Consulting": "consulting",
    "Core": "core",
    "Finance": "quant",
    "Product": "product",
    "Software": "sde"
}

def audit_categorized_resumes():
    base_dir = Path("temp/more_resume")
    if not base_dir.exists():
        print("Directory temp/more_resume does not exist.")
        return

    engine = ResumeEngine()

    results_summary = []
    total = 0
    correct = 0

    print("================================================================")
    print("      CATEGORIZED RESUME ACCURACY & DIAGNOSTIC AUDIT            ")
    print("================================================================")

    for folder_name, expected_role in FOLDER_TO_ROLE.items():
        pdf_files = sorted(list(base_dir.glob(f"**/{folder_name}/*.pdf")))
        print(f"\n--- Domain Track: {folder_name} (Expected: {expected_role}) | Total PDFs: {len(pdf_files)} ---")

        for pdf_path in pdf_files:
            total += 1
            try:
                res = engine.analyze_all(str(pdf_path))
                best_role = res.get("best_fit_role", "sde")
                
                # Get scores for all roles
                scores = {}
                for r in FOLDER_TO_ROLE.values():
                    r_res = res.get(r, {})
                    scores[r] = round(r_res.get("score", {}).get("score", 0), 1)

                is_correct = (best_role == expected_role)
                if is_correct:
                    correct += 1

                status_icon = "✅" if is_correct else "❌"
                print(f"{status_icon} [{pdf_path.name[:25]:<25}] Diagnosed: {best_role:<10} (Expected: {expected_role:<10}) | Scores: {scores}")

                results_summary.append({
                    "pdf": pdf_path.name,
                    "folder": folder_name,
                    "expected": expected_role,
                    "diagnosed": best_role,
                    "correct": is_correct,
                    "scores": scores,
                    "cpi": res.get(best_role, {}).get("evidence", {}).get("cpi")
                })
            except Exception as e:
                print(f"ERR [{pdf_path.name}]: {e}")

    accuracy = (correct / total * 100) if total > 0 else 0
    print("\n================================================================")
    print(f"AUDIT COMPLETE: {correct}/{total} Correctly Diagnosed ({accuracy:.1f}% Accuracy)")
    print("================================================================")

if __name__ == "__main__":
    audit_categorized_resumes()

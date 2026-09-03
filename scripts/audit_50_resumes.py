"""Audit 50 PDF resumes to evaluate diagnostic accuracy and identify systemic flaws."""
import sys
import json
import re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.pipeline import ResumeEngine
from resume_engine.parser.pdf_parser import parse_pdf

def main():
    pdf_candidates = []
    
    # 1. Real Student Resumes from temp/more_resume/
    more_resumes = sorted(list(Path("temp/more_resume").glob("**/*.pdf")))
    pdf_candidates.extend(more_resumes)
    
    # 2. Resumes from temp/
    temp_resumes = sorted([p for p in Path("temp").glob("*.pdf") if "Schedule" not in p.name])
    pdf_candidates.extend(temp_resumes)
    
    # 3. Scrap / Adversarial Resumes from temp/scrap/
    scrap_resumes = sorted([p for p in Path("temp/scrap").glob("*.pdf") if "Role_References" not in p.name])
    pdf_candidates.extend(scrap_resumes)

    # Filter out non-resumes and select top 50 distinct PDFs
    valid_pdfs = []
    seen_names = set()
    for p in pdf_candidates:
        if p.name in seen_names:
            continue
        if "Schedule" in p.name or "Handbook" in p.name or "DiagnosticEngine" in p.name or "cdev_ps" in p.name:
            continue
        valid_pdfs.append(p)
        seen_names.add(p.name)
        if len(valid_pdfs) >= 50:
            break

    print(f"Loaded {len(valid_pdfs)} target resume PDFs for deep diagnostic audit.\n")

    engine = ResumeEngine()

    audit_summary = []
    issues_found = Counter()
    role_distribution = Counter()
    anomalies = []

    for idx, pdf_path in enumerate(valid_pdfs, 1):
        rel_path = str(pdf_path)
        print(f"[{idx:02d}/50] Auditing: {pdf_path.name}...")
        
        try:
            # Step A: Parse Raw AST
            ast = parse_pdf(rel_path)
            
            # Step B: Run Multi-Track Pipeline
            results = engine.analyze_all(rel_path)
            best_role = results.get("best_fit_role", "sde")
            role_distribution[best_role] += 1
            
            best_res = results.get(best_role, {})
            score_data = best_res.get("score", {})
            evidence_data = best_res.get("evidence", {})
            advisory_data = best_res.get("advisory", {})
            doc_data = results.get("document", {})
            
            score_val = score_data.get("score", 0.0)
            tier = score_data.get("tier", "")
            cpi = evidence_data.get("cpi")
            claims = evidence_data.get("claims", [])
            skills = evidence_data.get("skills_matched", [])
            penalties = score_data.get("penalties_applied", [])
            bonuses = score_data.get("bonuses_applied", [])
            
            # Diagnostic Anomaly Checks
            
            # 1. CPI extraction anomaly check:
            raw_text = ast.raw_text
            cpi_regex_match = re.search(r"(\b[0-9]\.[0-9]{1,2})\s*/\s*10", raw_text, re.I)
            if cpi_regex_match and cpi is None:
                extracted_cpi_val = float(cpi_regex_match.group(1))
                # Check if it is CPI or high percentage
                if extracted_cpi_val <= 10.0:
                    anomalies.append({
                        "pdf": pdf_path.name,
                        "type": "CPI_MISSED",
                        "details": f"Raw text contains '{cpi_regex_match.group(0)}' but evidence.cpi is None"
                    })
                    issues_found["CPI_MISSED"] += 1

            # 2. CPI parsing false positive check (e.g. 10/10/2023 date or 10/10 score parsed as CPI):
            if cpi is not None and (cpi > 10.0 or cpi < 0.0):
                anomalies.append({
                    "pdf": pdf_path.name,
                    "type": "INVALID_CPI_VAL",
                    "details": f"Extracted invalid CPI value: {cpi}"
                })
                issues_found["INVALID_CPI_VAL"] += 1

            # 3. GitHub Link recognition check:
            links = doc_data.get("links", [])
            github_in_text = "github" in raw_text.lower()
            github_in_links = any("github" in l.get("url", "").lower() for l in links) or any("github" in str(s).lower() for s in ast.raw_text.split())
            if github_in_text and best_role == "sde" and any("Missing active GitHub profile link" in p for p in penalties):
                anomalies.append({
                    "pdf": pdf_path.name,
                    "type": "GITHUB_PENALTY_FALSE_POSITIVE",
                    "details": "Resume text mentions GitHub but candidate received GitHub penalty"
                })
                issues_found["GITHUB_PENALTY_FALSE_POSITIVE"] += 1

            # 4. Low atomic claims extraction on detailed resumes:
            if len(claims) < 4 and len(raw_text.split()) > 150 and not evidence_data.get("is_scrap", False):
                anomalies.append({
                    "pdf": pdf_path.name,
                    "type": "FEW_CLAIMS_PARSED",
                    "details": f"Only {len(claims)} claims parsed out of {len(raw_text.split())} words text"
                })
                issues_found["FEW_CLAIMS_PARSED"] += 1

            # 5. Overly suppressed score on strong candidate:
            if score_val < 45.0 and not evidence_data.get("is_scrap", False) and cpi is not None and cpi >= 8.0:
                anomalies.append({
                    "pdf": pdf_path.name,
                    "type": "HIGH_CPI_LOW_SCORE",
                    "details": f"Candidate with CPI {cpi:.2f} scored {score_val:.1f} in best role {best_role}"
                })
                issues_found["HIGH_CPI_LOW_SCORE"] += 1

            # 6. Uncategorized or missing section headers:
            sections = doc_data.get("sections", [])
            if len(sections) <= 1 and len(raw_text.split()) > 100:
                anomalies.append({
                    "pdf": pdf_path.name,
                    "type": "UNPARSED_SECTIONS",
                    "details": f"Only {len(sections)} section extracted for full resume"
                })
                issues_found["UNPARSED_SECTIONS"] += 1

            audit_summary.append({
                "pdf": pdf_path.name,
                "best_fit_role": best_role,
                "score": score_val,
                "tier": tier,
                "cpi": cpi,
                "claims_count": len(claims),
                "skills_count": len(skills),
                "penalties_count": len(penalties),
                "bonuses_count": len(bonuses),
                "is_scrap": evidence_data.get("is_scrap", False)
            })

        except Exception as e:
            print(f"  ❌ ERROR analyzing {pdf_path.name}: {e}")
            anomalies.append({
                "pdf": pdf_path.name,
                "type": "PIPELINE_CRASH",
                "details": str(e)
            })
            issues_found["PIPELINE_CRASH"] += 1

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY RESULTS ACROSS 50 RESUMES")
    print("=" * 80)
    print("Best Fit Role Distribution:")
    for role, cnt in role_distribution.most_common():
        print(f"  {role:<12}: {cnt} resumes")
    
    print("\nSystemic Flaws & Diagnostic Anomalies Detected:")
    for issue, cnt in issues_found.most_common():
        print(f"  • {issue:<32}: {cnt} instances")

    if anomalies:
        print("\nDetailed Anomaly Breakdown:")
        for a in anomalies:
            print(f"  [{a['type']}] {a['pdf']}: {a['details']}")

    # Save audit report to JSON
    with open("scratch/audit_50_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "summary": audit_summary,
            "anomalies": anomalies,
            "issues_count": dict(issues_found)
        }, f, indent=2)
    print("\nFull audit report saved to scratch/audit_50_results.json")

if __name__ == "__main__":
    main()

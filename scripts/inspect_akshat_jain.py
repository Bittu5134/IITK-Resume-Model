"""Inspect Akshat Jain resume parsing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.pipeline import ResumeEngine
from resume_engine.parser.pdf_parser import parse_pdf

pdf_path = "temp/more_resume/Y21/Analytics/Akshat Jain.pdf"
ast = parse_pdf(pdf_path)
print("=== RAW TEXT ===")
print(ast.raw_text[:1500])

engine = ResumeEngine()
res = engine.analyze_all(pdf_path)
print("\n=== ANALYST BREAKDOWN ===")
analyst_comp = res["analyst"]["score"]["competencies"]
for c in analyst_comp:
    print(f"- {c['name']:<35}: raw={c['raw_score']} weighted={c['weighted_score']} claims={len(c['evidence_claims'])}")

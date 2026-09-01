#!/usr/bin/env python
"""Quick validation of coursework extraction."""

from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.pipeline import ResumeEngine
from pathlib import Path

# Test 1: Check if coursework extraction works at evidence level
print("="*80)
print("TEST 1: Evidence Extraction")
print("="*80)

test_file = "tests/fixtures/Software/Akshat Mehta.pdf"
if Path(test_file).exists():
    ast = parse_pdf(test_file)
    ev = EvidenceExtractor().extract(ast)
    
    print(f"Total claims: {len(ev.claims)}")
    courses_found = [c for c in ev.claims if c.courses]
    print(f"Claims with courses: {len(courses_found)}")
    
    if courses_found:
        print(f"\n✅ Coursework extraction WORKING!")
        for claim in courses_found[:2]:
            print(f"  Section: {claim.section}")
            print(f"  Text: {claim.text[:60]}...")
            print(f"  Courses: {claim.courses}")
    else:
        print("\n❌ No courses extracted")
        # Check if coursework section exists
        cw_sections = [s for s in ast.sections if 'course' in s.name.lower()]
        if cw_sections:
            print(f"  But coursework section EXISTS: {cw_sections[0].name}")
            print(f"  Bullets: {len(cw_sections[0].bullets)}")
            if cw_sections[0].bullets:
                print(f"  Sample bullet: {cw_sections[0].bullets[0].text[:80]}")
else:
    print(f"Test file not found: {test_file}")

# Test 2: Check end-to-end scoring
print("\n" + "="*80)
print("TEST 2: End-to-End Scoring")
print("="*80)

engine = ResumeEngine()
result = engine.analyze("examples/resume2.pdf", "sde")

cw_comp = [c for c in result.score.competency_scores if c.competency == 'coursework']
if cw_comp:
    print(f"✅ Coursework in SDE role!")
    print(f"   Strength: {cw_comp[0].strength}")
    print(f"   Contribution: {cw_comp[0].contribution}/100")
else:
    print("❌ Coursework NOT in SDE competencies")

print(f"\nTotal Score: {result.score.score}")
print(f"Penalties: {result.score.penalties}")

# Test 3: Compare before/after penalty changes
print("\n" + "="*80)
print("TEST 3: Penalty Reduction")
print("="*80)
print(f"GitHub penalty removed: {not any('github' in str(p) for p in result.score.penalties)}")
print(f"Total penalties: {len(result.score.penalties)}")
print(f"Penalty points: {sum(p.get('points', 0) for p in result.score.penalties)}")

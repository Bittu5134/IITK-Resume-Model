from resume_engine.pipeline import ResumeEngine
from pathlib import Path

# Test on multiple resumes
test_resumes = [
    "tests/fixtures/Software/Aditya Kumar.pdf",
    "tests/fixtures/Quant/Akshat Mehta.pdf",
    "tests/fixtures/Core/Akshat Jain.pdf",
]

engine = ResumeEngine()

for resume_path in test_resumes:
    if not Path(resume_path).exists():
        continue
    
    print(f"\n{'='*80}")
    print(f"Testing: {resume_path}")
    print('='*80)
    
    result = engine.analyze(resume_path, 'sde')
    
    # Check coursework
    cw_comp = [c for c in result.score.competency_scores if c.competency == 'coursework']
    if cw_comp:
        print(f"✅ Coursework competency found!")
        print(f"   Strength: {cw_comp[0].strength}")
        print(f"   Contribution: {cw_comp[0].contribution}")
        print(f"   Supporting claims: {len(cw_comp[0].supporting_claims)}")
    else:
        print(f"❌ Coursework competency NOT in role")
    
    # Check extracted courses in evidence
    evidence = engine.extractor.extract(engine.matcher.role)  # This won't work, need to fix
    
    print(f"Total Score: {result.score.score}")
    print(f"Penalties: {len(result.score.penalties)}")
    
    break  # Test just first one for speed

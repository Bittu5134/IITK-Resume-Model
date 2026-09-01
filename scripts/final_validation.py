"""
Final validation: Test unbiasing changes across sample resumes from each role.
"""

from resume_engine.pipeline import ResumeEngine
from pathlib import Path
import json

# Sample resumes from each role
test_cases = {
    'Software': [
        'tests/fixtures/Software/Akshat Mehta.pdf',
        'tests/fixtures/Software/Ananya.pdf',
        'tests/fixtures/Software/Dhruv Misra.pdf',
    ],
    'Quant': [
        'tests/fixtures/Quant/Akshat Mehta.pdf',
        'tests/fixtures/Quant/Aditya Kumar.pdf',
    ],
    'Core': [
        'tests/fixtures/Core/Akshat Jain.pdf',
        'tests/fixtures/Core/Devansh Jain.pdf',
    ],
    'Consulting': [
        'tests/fixtures/Consulting/Akshat Jain.pdf',
        'tests/fixtures/Consulting/Dhruv Misra.pdf',
    ]
}

engine = ResumeEngine()
results = {
    'coursework_success': 0,
    'coursework_total': 0,
    'penalty_reduction': 0,
    'total_tests': 0,
    'details': []
}

print("="*80)
print("VALIDATION: Unbiasing Changes Across Resume Database")
print("="*80)

for role_category, resumes in test_cases.items():
    print(f"\n{role_category} Resumes:")
    print("-"*80)
    
    for resume_path in resumes:
        if not Path(resume_path).exists():
            print(f"  SKIP: {Path(resume_path).name} (not found)")
            continue
        
        results['total_tests'] += 1
        resume_name = Path(resume_path).stem
        
        try:
            # Test with SDE role
            result = engine.analyze(resume_path, 'sde')
            
            # Check coursework
            cw_comp = [c for c in result.score.competency_scores if c.competency == 'coursework']
            has_coursework = len(cw_comp) > 0
            cw_contribution = cw_comp[0].contribution if cw_comp else 0.0
            
            results['coursework_total'] += 1
            if cw_contribution > 0:
                results['coursework_success'] += 1
            
            # Check penalties
            penalty_count = len(result.score.penalties)
            penalty_points = sum(p.get('points', 0) for p in result.score.penalties)
            
            # Check if GitHub penalty removed
            has_github_penalty = any('github' in str(p).lower() for p in result.score.penalties)
            
            status = "[OK]" if cw_contribution > 0 else "[  ]"
            
            print(f"  {status} {resume_name[:30]:30} | Score: {result.score.score:5.2f} | CW: {cw_contribution:4.2f} | Penalties: {penalty_count} ({penalty_points:.1f}pts)")
            
            if not has_github_penalty:
                results['penalty_reduction'] += 1
            
            results['details'].append({
                'resume': resume_name,
                'role_category': role_category,
                'score': result.score.score,
                'coursework_contribution': cw_contribution,
                'penalty_count': penalty_count,
                'penalty_points': penalty_points,
                'github_penalty_removed': not has_github_penalty
            })
            
        except Exception as e:
            print(f"  ERROR: {resume_name[:30]:30} | {str(e)[:40]}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total resumes tested: {results['total_tests']}")
print(f"Coursework extraction success: {results['coursework_success']}/{results['coursework_total']} ({100*results['coursework_success']/results['coursework_total']:.1f}%)")
print(f"GitHub penalty removed: {results['penalty_reduction']}/{results['total_tests']} ({100*results['penalty_reduction']/results['total_tests']:.1f}%)")

# Calculate average scores
avg_score = sum(d['score'] for d in results['details']) / len(results['details']) if results['details'] else 0
avg_cw = sum(d['coursework_contribution'] for d in results['details']) / len(results['details']) if results['details'] else 0
avg_penalties = sum(d['penalty_points'] for d in results['details']) / len(results['details']) if results['details'] else 0

print(f"\nAverage score: {avg_score:.2f}")
print(f"Average coursework contribution: {avg_cw:.2f} points")
print(f"Average penalty points: {avg_penalties:.2f} points (reduced from ~5-7 before)")

# Save results
with open('data/validation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nDetailed results saved to: data/validation_results.json")

# Key success criteria
print("\n" + "="*80)
print("SUCCESS CRITERIA")
print("="*80)
criteria_met = 0
total_criteria = 4

if results['coursework_success'] / results['coursework_total'] >= 0.7:
    print("[OK] Coursework extraction: >70% success rate")
    criteria_met += 1
else:
    print(f"[FAIL] Coursework extraction: {100*results['coursework_success']/results['coursework_total']:.1f}% (target: >70%)")

if results['penalty_reduction'] / results['total_tests'] >= 0.8:
    print("[OK] Penalty reduction: GitHub penalty removed in >80% cases")
    criteria_met += 1
else:
    print(f"[FAIL] Penalty reduction: {100*results['penalty_reduction']/results['total_tests']:.1f}% (target: >80%)")

if avg_cw > 1.0:
    print(f"[OK] Coursework contributes meaningfully: {avg_cw:.2f} points avg")
    criteria_met += 1
else:
    print(f"[FAIL] Coursework contribution too low: {avg_cw:.2f} points (target: >1.0)")

if avg_penalties < 3.0:
    print(f"[OK] Penalties softened: {avg_penalties:.2f} points avg (was ~5-7)")
    criteria_met += 1
else:
    print(f"[FAIL] Penalties still harsh: {avg_penalties:.2f} points (target: <3.0)")

print(f"\nOverall: {criteria_met}/{total_criteria} criteria met")
if criteria_met == total_criteria:
    print("\nSUCCESS: ALL SUCCESS CRITERIA MET! Unbiasing complete.")
else:
    print(f"\nWARNING: {total_criteria - criteria_met} criteria need attention.")

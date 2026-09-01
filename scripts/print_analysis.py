import json
with open('resume_analysis_by_role.json') as f:
    data = json.load(f)

for role, info in data['summary'].items():
    print(f'\n{role}:')
    print(f'  Resumes: {info["total_resumes"]}')
    print(f'  With coursework: {info["resumes_with_coursework"]}')
    print(f'  Top courses: {info["top_10_courses"]}')
    print(f'  Top skills: {info["top_10_skills"]}')
    print(f'  Top PoR: {info["top_10_por"]}')
    print(f'  Project types: {info["top_project_types"]}')
    print(f'  Internships: {info["top_internship_patterns"]}')

print("\n\n=== DEEP COURSEWORK SCAN ===")
for role in ['Software', 'Quant', 'Core', 'Consulting']:
    print(f"\n{role} - Deep Coursework (top 20):")
    deep = data['by_role'][role].get('deep_coursework_scan', {})
    for k, v in list(deep.items())[:20]:
        print(f"  [{v:2d}] {k}")

print("\n\n=== COURSEWORK SECTION HEADERS ===")
for role in ['Software', 'Quant', 'Core', 'Consulting']:
    headers = data['by_role'][role].get('coursework_section_header_formats', [])
    print(f"\n{role}: {headers}")

print("\n\n=== COURSEWORK EXAMPLES ===")
for role in ['Software', 'Quant', 'Core', 'Consulting']:
    examples = data['by_role'][role].get('coursework_raw_examples', [])
    print(f"\n{role} examples:")
    for ex in examples[:3]:
        print(f"  File: {ex['file']}")
        for line in ex['lines']:
            print(f"    {line}")

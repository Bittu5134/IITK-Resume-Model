"""
Analyze all 84 resumes in tests/fixtures to extract:
1. Coursework patterns and course names across all roles
2. Common skills and their frequencies
3. PoR patterns
4. Project types
5. Internship patterns

This data will be used to unbias the scoring system and fix the coursework=0 issue.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor


def extract_coursework_from_text(text: str) -> List[str]:
    """Extract potential course names from text."""
    courses = []
    
    # Pattern 1: Course codes (e.g., ESC101, MTH101, CS220, PHY103)
    course_code_pattern = r'\b([A-Z]{2,4}\s*\d{3}[A-Z]?)\b'
    courses.extend(re.findall(course_code_pattern, text))
    
    # Pattern 2: Common course names
    course_keywords = [
        'data structures', 'algorithms', 'machine learning', 'deep learning',
        'artificial intelligence', 'computer networks', 'operating systems',
        'database', 'dbms', 'probability', 'statistics', 'linear algebra',
        'calculus', 'differential equations', 'stochastic', 'optimization',
        'computer architecture', 'compiler', 'software engineering',
        'web development', 'computer graphics', 'theory of computation',
        'discrete mathematics', 'numerical methods', 'signals', 'control',
        'thermodynamics', 'fluid mechanics', 'mechanics', 'electronics',
        'quantum mechanics', 'electromagnetism', 'circuit', 'communication'
    ]
    
    text_lower = text.lower()
    for keyword in course_keywords:
        if keyword in text_lower:
            courses.append(keyword.title())
    
    return courses


def analyze_section_content(section_name: str, content: str) -> Dict:
    """Analyze content from a specific section."""
    result = {
        'courses': extract_coursework_from_text(content),
        'skills': [],
        'pors': [],
        'tools': [],
        'metrics': []
    }
    
    # Extract skills/tools
    skill_patterns = [
        r'\b(Python|Java|C\+\+|C|JavaScript|TypeScript|Go|Rust|R|MATLAB|SQL)\b',
        r'\b(TensorFlow|PyTorch|Keras|scikit-learn|NumPy|Pandas|React|Angular|Vue|Node\.js|Django|Flask|Spring|Docker|Kubernetes)\b',
        r'\b(Git|GitHub|AWS|Azure|GCP|Linux|MongoDB|PostgreSQL|MySQL|Redis|Kafka)\b'
    ]
    
    for pattern in skill_patterns:
        result['skills'].extend(re.findall(pattern, content, re.IGNORECASE))
    
    # Extract metrics (numbers with context)
    metric_pattern = r'(\d+\.?\d*\s*[%xX×]|\d+\+?\s*(users|students|members|increase|improvement|reduction))'
    result['metrics'].extend(re.findall(metric_pattern, content, re.IGNORECASE))
    
    return result


def analyze_resume(pdf_path: Path, role_category: str) -> Dict:
    """Analyze a single resume."""
    try:
        ast = parse_pdf(pdf_path)
        
        analysis = {
            'filename': pdf_path.name,
            'role_category': role_category,
            'sections_found': [],
            'coursework': [],
            'skills': [],
            'pors': [],
            'projects': [],
            'internships': [],
            'cpi': None
        }
        
        # Collect all text for CPI extraction
        full_text = ''
        
        # Analyze each section
        for section in ast.sections:
            section_name = section.name.lower()
            analysis['sections_found'].append(section_name)
            
            # Extract full section text
            section_text = section.raw_heading + ' '
            for entry in section.entries:
                section_text += entry.title + ' ' + entry.organization + ' '
                for bullet in entry.bullets:
                    section_text += bullet.text + ' '
            
            full_text += section_text + ' '
            
            # Analyze coursework section
            if any(kw in section_name for kw in ['course', 'relevant', 'academic']):
                section_analysis = analyze_section_content(section_name, section_text)
                analysis['coursework'].extend(section_analysis['courses'])
                analysis['skills'].extend(section_analysis['skills'])
            
            # Analyze PoR section
            if any(kw in section_name for kw in ['position', 'leadership', 'responsibility', 'por', 'extracurricular', 'activities']):
                for entry in section.entries:
                    analysis['pors'].append({
                        'title': entry.title,
                        'organization': entry.organization,
                        'bullets': [b.text for b in entry.bullets]
                    })
            
            # Analyze projects
            if 'project' in section_name:
                for entry in section.entries:
                    analysis['projects'].append({
                        'title': entry.title,
                        'bullets': [b.text for b in entry.bullets]
                    })
            
            # Analyze internships/experience
            if any(kw in section_name for kw in ['experience', 'internship', 'work']):
                for entry in section.entries:
                    analysis['internships'].append({
                        'title': entry.title,
                        'company': entry.organization,
                        'bullets': [b.text for b in entry.bullets]
                    })
        
        # Extract CPI from text
        cpi_match = re.search(r'(?:CPI|CGPA|GPA)[\s:]*(\d+\.?\d*)', full_text, re.IGNORECASE)
        if cpi_match:
            analysis['cpi'] = float(cpi_match.group(1))
        
        return analysis
    
    except Exception as e:
        print(f"Error analyzing {pdf_path.name}: {e}")
        return None


def main():
    fixtures_dir = Path(__file__).parent.parent / 'tests' / 'fixtures'
    
    roles = {
        'Software': list((fixtures_dir / 'Software').glob('*.pdf')),
        'Quant': list((fixtures_dir / 'Quant').glob('*.pdf')),
        'Core': list((fixtures_dir / 'Core').glob('*.pdf')),
        'Consulting': list((fixtures_dir / 'Consulting').glob('*.pdf'))
    }
    
    all_analyses = []
    role_statistics = defaultdict(lambda: {
        'count': 0,
        'coursework_counter': Counter(),
        'skills_counter': Counter(),
        'por_titles': Counter(),
        'avg_cpi': [],
        'sections_counter': Counter()
    })
    
    print("Analyzing 84 resumes...")
    print("=" * 80)
    
    for role, pdf_files in roles.items():
        print(f"\n{role}: {len(pdf_files)} resumes")
        
        for pdf_path in pdf_files:
            analysis = analyze_resume(pdf_path, role)
            if analysis:
                all_analyses.append(analysis)
                
                stats = role_statistics[role]
                stats['count'] += 1
                stats['coursework_counter'].update(analysis['coursework'])
                stats['skills_counter'].update(analysis['skills'])
                stats['sections_counter'].update(analysis['sections_found'])
                
                for por in analysis['pors']:
                    stats['por_titles'][por['title']] += 1
                
                if analysis['cpi']:
                    stats['avg_cpi'].append(analysis['cpi'])
    
    # Generate summary report
    summary = {
        'total_resumes': len(all_analyses),
        'by_role': {}
    }
    
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    for role, stats in role_statistics.items():
        avg_cpi = sum(stats['avg_cpi'])/len(stats['avg_cpi']) if stats['avg_cpi'] else None
        print(f"\n{role} ({stats['count']} resumes):")
        print(f"  Avg CPI: {avg_cpi:.2f}" if avg_cpi else "  Avg CPI: N/A")
        print(f"  Top 10 Courses extracted: {len(stats['coursework_counter'])} unique")
        print(f"  Top 10 Skills extracted: {len(stats['skills_counter'])} unique")
        print(f"  PoR entries found: {sum(stats['por_titles'].values())}")
        
        summary['by_role'][role] = {
            'count': stats['count'],
            'avg_cpi': avg_cpi,
            'top_courses': dict(stats['coursework_counter'].most_common(20)),
            'top_skills': dict(stats['skills_counter'].most_common(20)),
            'top_pors': dict([(k, v) for k, v in stats['por_titles'].most_common(20)]),
            'common_sections': dict(stats['sections_counter'].most_common(10))
        }
    
    # Save results
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'resume_database_analysis.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    with open(output_dir / 'all_resume_analyses.json', 'w') as f:
        json.dump(all_analyses, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print(f"Results saved to {output_dir}/")
    print(f"  - resume_database_analysis.json (summary)")
    print(f"  - all_resume_analyses.json (detailed)")


if __name__ == '__main__':
    main()

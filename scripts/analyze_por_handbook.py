"""
Extract all Positions of Responsibility from PoR-Handbook.pdf
and assign role-specific weights based on leadership/technical/organizational focus.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine.parser.pdf_parser import parse_pdf


def extract_pors_from_handbook(pdf_path: Path) -> dict:
    """Extract PoRs from the handbook PDF."""
    ast = parse_pdf(pdf_path)
    
    pors = []
    current_por = None
    
    # Collect all bullets/text
    all_text = []
    for section in ast.sections:
        for entry in section.entries:
            title_text = entry.title.strip()
            if title_text:
                all_text.append(('title', title_text, entry.organization))
            for bullet in entry.bullets:
                all_text.append(('bullet', bullet.text.strip(), ''))
    
    # Simple heuristic: titles in bold/larger font often indicate PoR names
    # Analyze patterns
    por_patterns = [
        # Technical/Cultural/Sports councils and clubs
        r'(?:secretary|head|coordinator|captain|president|chairperson|convener|representative)\s+[-–—]\s+(.*)',
        r'(.*?)\s+(?:secretary|head|coordinator|captain|president|chairperson)',
        # Club/Cell/Council positions
        r'(.*?)\s+(?:club|cell|council|team|society)',
    ]
    
    for text_type, text, org in all_text:
        # Look for position patterns
        if any(keyword in text.lower() for keyword in [
            'secretary', 'head', 'coordinator', 'captain', 'president', 
            'chairperson', 'convener', 'representative', 'senator', 'council',
            'club', 'society', 'cell', 'team', 'festival', 'mentor', 'manager'
        ]):
            if text not in [p['title'] for p in pors]:  # Avoid duplicates
                pors.append({
                    'title': text,
                    'organization': org,
                    'source': 'handbook'
                })
    
    return {'pors': pors, 'total': len(pors)}


def assign_role_weights(por_title: str) -> dict:
    """
    Assign role-specific weights to a PoR based on its characteristics.
    
    Weights reflect how valuable this PoR is for each role:
    - Consulting: Values leadership, impact, organizational roles
    - SDE: Values technical roles, coding clubs, technical teams
    - Quant: Values academic roles, research positions
    - Core: Values technical societies, domain-specific clubs
    """
    title_lower = por_title.lower()
    
    # Default weights
    weights = {
        'sde': 0.3,
        'quant': 0.3,
        'consulting': 0.5,
        'core': 0.3
    }
    
    # High-level leadership (valuable for consulting)
    if any(kw in title_lower for kw in [
        'general secretary', 'president', 'overall coordinator', 
        'senator', 'chairperson', 'students\' senate'
    ]):
        weights = {'sde': 0.4, 'quant': 0.4, 'consulting': 1.0, 'core': 0.4}
    
    # Technical clubs/societies (valuable for SDE/Core)
    elif any(kw in title_lower for kw in [
        'programming', 'coding', 'robotics', 'electronics', 'technical',
        'science and technology', 'aeromodelling', 'automobile'
    ]):
        weights = {'sde': 0.9, 'quant': 0.5, 'consulting': 0.6, 'core': 0.9}
    
    # Cultural/Sports (moderate for consulting, low for others)
    elif any(kw in title_lower for kw in [
        'cultural', 'sports', 'games', 'dramatics', 'music', 'dance', 'quiz'
    ]):
        weights = {'sde': 0.4, 'quant': 0.4, 'consulting': 0.7, 'core': 0.4}
    
    # Academic/Mentoring (good for consulting and quant)
    elif any(kw in title_lower for kw in [
        'academic', 'mentor', 'counselling', 'peer', 'tutor'
    ]):
        weights = {'sde': 0.5, 'quant': 0.7, 'consulting': 0.8, 'core': 0.5}
    
    # Media/PR/Marketing (good for consulting)
    elif any(kw in title_lower for kw in [
        'media', 'public relations', 'marketing', 'publicity', 'communication'
    ]):
        weights = {'sde': 0.4, 'quant': 0.4, 'consulting': 0.85, 'core': 0.4}
    
    # Entrepreneurship/Business (best for consulting, good for SDE)
    elif any(kw in title_lower for kw in [
        'entrepreneurship', 'business', 'finance', 'economics', 'consulting'
    ]):
        weights = {'sde': 0.6, 'quant': 0.7, 'consulting': 0.9, 'core': 0.5}
    
    # Hostel affairs (moderate for consulting)
    elif any(kw in title_lower for kw in [
        'hostel', 'mess', 'bhawan'
    ]):
        weights = {'sde': 0.4, 'quant': 0.4, 'consulting': 0.7, 'core': 0.4}
    
    # Social service/NGO (good for consulting)
    elif any(kw in title_lower for kw in [
        'social', 'ngo', 'service', 'community', 'outreach'
    ]):
        weights = {'sde': 0.4, 'quant': 0.4, 'consulting': 0.75, 'core': 0.4}
    
    # Festival/Event coordination (valuable for consulting)
    elif any(kw in title_lower for kw in [
        'fest', 'festival', 'event', 'antaragni', 'techkriti', 'udghosh'
    ]):
        weights = {'sde': 0.5, 'quant': 0.5, 'consulting': 0.85, 'core': 0.5}
    
    return weights


def main():
    handbook_path = Path(__file__).parent.parent / 'PoR-Handbook.pdf'
    
    if not handbook_path.exists():
        print(f"Error: {handbook_path} not found")
        return
    
    print("Analyzing PoR Handbook...")
    print("=" * 80)
    
    result = extract_pors_from_handbook(handbook_path)
    
    print(f"\nExtracted {result['total']} PoR entries from handbook")
    print("\nSample PoRs:")
    for por in result['pors'][:20]:
        print(f"  - {por['title']}")
    
    # Assign weights
    por_ontology = {
        'source': 'PoR-Handbook.pdf',
        'total_pors': result['total'],
        'pors': []
    }
    
    for por in result['pors']:
        weights = assign_role_weights(por['title'])
        por_ontology['pors'].append({
            'title': por['title'],
            'organization': por['organization'],
            'role_weights': weights
        })
    
    # Statistics by role
    print("\n" + "=" * 80)
    print("ROLE-SPECIFIC ANALYSIS")
    print("=" * 80)
    
    for role in ['sde', 'quant', 'consulting', 'core']:
        high_value_pors = [
            p for p in por_ontology['pors'] 
            if p['role_weights'][role] >= 0.8
        ]
        print(f"\n{role.upper()}: {len(high_value_pors)} high-value PoRs (weight >= 0.8)")
        for por in high_value_pors[:5]:
            print(f"  - {por['title']} (weight: {por['role_weights'][role]})")
    
    # Save to config
    output_path = Path(__file__).parent.parent / 'resume_engine' / 'config' / 'por_ontology.yaml'
    
    # Convert to YAML format
    yaml_content = "# PoR Ontology - Extracted from PoR Handbook\n"
    yaml_content += "# Role-specific weights: 0-1 scale\n\n"
    yaml_content += "pors:\n"
    
    for por in por_ontology['pors']:
        yaml_content += f"  - title: \"{por['title']}\"\n"
        if por['organization']:
            yaml_content += f"    organization: \"{por['organization']}\"\n"
        yaml_content += f"    role_weights:\n"
        for role, weight in por['role_weights'].items():
            yaml_content += f"      {role}: {weight}\n"
        yaml_content += "\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    print(f"\n{'=' * 80}")
    print(f"PoR ontology saved to: {output_path}")
    
    # Also save JSON for easy processing
    json_output = Path(__file__).parent.parent / 'data' / 'por_ontology.json'
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(por_ontology, f, indent=2, ensure_ascii=False)
    
    print(f"JSON version saved to: {json_output}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor

ast = parse_pdf('tests/fixtures/golden_resume_01.pdf')
extractor = EvidenceExtractor()
evidence = extractor.extract(ast)

# Find leadership claims in PoR section
por_leadership = [c for c in evidence.claims if c.section == 'Positions of Responsibility' and 
                 any(word in c.text.lower() for word in ['elected', 'convener', 'oversaw'])]
print(f'PoR leadership claims: {len(por_leadership)}')
for c in por_leadership:
    print(f'{c.claim_id}: {c.text}')
    print(f'  Evidence strength: {c.evidence_strength}')
    print(f'  Evidence types: {[e.value for e in c.evidence_types]}')
    print(f'  Action verb: {c.action_verb}, strength: {c.action_strength}')
    print(f'  Domain relevance consulting: {c.domain_relevance["consulting"]}')
    print(f'  Role relevance consulting: {c.role_relevance_score["consulting"]}')
    print()
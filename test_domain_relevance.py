#!/usr/bin/env python3

from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor

ast = parse_pdf('tests/fixtures/golden_resume_01.pdf')
extractor = EvidenceExtractor()
evidence = extractor.extract(ast)

exp_claims = [c for c in evidence.claims if c.section == 'Experience']
print('Experience claims entry context:')
for c in exp_claims:
    print(f'{c.claim_id}: {c.text[:50]}...')
    print(f'  Entry context: "{c.entry_context}"')
    print(f'  Evidence: {[e.value for e in c.evidence_types]}')
    ba_in_context = 'business analyst' in c.entry_context.lower()
    ba_in_text = 'business analyst' in c.text.lower()
    has_ba_evidence = any(str(et).endswith('business_analysis') for et in c.evidence_types)
    print(f'  BA in context: {ba_in_context}, BA in text: {ba_in_text}, Has BA evidence: {has_ba_evidence}')
    print()

print(f"\nTotal Experience claims: {len(exp_claims)}")
ba_claims = [c for c in exp_claims if 
            (('business analyst' in c.entry_context.lower() or 'navikra' in c.entry_context.lower()) or
             ('business analyst' in c.text.lower() or 'navikra' in c.text.lower()) or
             any(str(et).endswith('business_analysis') for et in c.evidence_types))]
print(f"Business Analyst claims found: {len(ba_claims)}")
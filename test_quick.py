from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.parser.pdf_parser import parse_pdf

ast = parse_pdf('tests/fixtures/Software/Akshat Mehta.pdf')
ev = EvidenceExtractor().extract(ast)

courses = [c for c in ev.claims if c.courses]
print(f'Claims with courses: {len(courses)}')
if courses:
    print(f'Sample courses extracted: {courses[0].courses[:3]}')
    print(f'SUCCESS!')
else:
    print('FAILED - no courses extracted')

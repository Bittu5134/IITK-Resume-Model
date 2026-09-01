"""
Deep extraction of actual coursework blocks from all resumes.
This script finds the actual "Relevant Courses" / "Coursework" sections
and extracts individual course names.
"""
import sys
import re
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import fitz
    PDF_BACKEND = "pymupdf"
except ImportError:
    PDF_BACKEND = None

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
ROLES = ["Software", "Quant", "Core", "Consulting"]

# Strict coursework section headers
CW_HEADER_RE = re.compile(
    r"(?i)^[\s•\-\*]*(relevant\s+course\s*work|relevant\s+courses?|"
    r"coursework|key\s+courses?|academic\s+courses?|"
    r"technical\s+courses?|courses?\s+taken|course\s+highlights?|"
    r"technical\s+skills\s+(and|&)\s+relevant\s+courses?|"
    r"relevant\s+coursework)[\s:]*$"
)

# Lines that indicate we've left the coursework section
NEXT_SECTION_RE = re.compile(
    r"(?i)^[\s•\-\*]*(projects?|internship|experience|skills?|"
    r"position|por|extra.?curr|activit|leader|achieve|award|"
    r"publication|research|work\s+exp|education|academics?|"
    r"competitive|programming|scholastic|co.?curr|volunteer|"
    r"certif)[\s:]*$"
)

# Section indicators that are definitely not courses (false positives to skip)
SKIP_LINE_RE = re.compile(
    r"(?i)(all\s+india\s+rank|jee|kvpy|ntse|iit\s+kanpur|"
    r"professor|prof\.|supervisor|course\s+project|"
    r"@|github|linkedin|email|phone|\d{10}|"
    r"b\.tech|m\.tech|ph\.d|cgpa|cpi|gpa|"
    r"^[A-Z][a-z]+\s+[A-Z][a-z]+\s*$)"  # Just a name
)

def extract_text_pymupdf(path):
    import fitz
    try:
        doc = fitz.open(str(path))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n".join(pages)
    except Exception as e:
        return ""

def extract_courses_from_text(text, filename=""):
    """Extract courses using multiple strategies."""
    courses_found = []
    
    lines = text.splitlines()
    
    # Strategy 1: Find coursework section header, then extract lines until next section
    in_cw = False
    cw_block = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if CW_HEADER_RE.match(stripped):
            in_cw = True
            cw_block = []
            continue
        
        if in_cw:
            # Stop conditions
            if NEXT_SECTION_RE.match(stripped) and len(stripped) < 60:
                in_cw = False
                break
            
            # Skip blank and very long lines
            if not stripped or len(stripped) > 120:
                continue
            
            # Skip lines that are clearly not courses
            if SKIP_LINE_RE.search(stripped):
                continue
            
            # Split the line on common separators to get individual courses
            # Some resumes put multiple courses on one line
            parts = re.split(r'[|,;•·∙◦▪\t]|\s{3,}', stripped)
            for part in parts:
                part = part.strip(" •-*·∙◦▪\t()")
                # Remove grade markers like *, †, §, A*, (A*)
                part = re.sub(r'\s*[\*†§#]+\s*$', '', part)
                part = re.sub(r'\s*\([A-Z][^\)]{0,5}\)\s*$', '', part)  # (A*), (A+)
                part = part.strip()
                
                if 5 < len(part) < 80:
                    # Filter out obvious non-course content
                    if not SKIP_LINE_RE.search(part):
                        cw_block.append(part.lower())
            
            if len(cw_block) > 20:  # Safety limit
                in_cw = False
        
    courses_found.extend(cw_block)
    
    # Strategy 2: Inline course list "Relevant Courses: X, Y, Z" or "Courses: X | Y | Z"
    inline_re = re.findall(
        r"(?i)(?:relevant\s+)?courses?\s*:\s*([^\n]{10,400})",
        text
    )
    for match in inline_re:
        parts = re.split(r'[|,;•·∙◦]|\s{2,}', match)
        for p in parts:
            p = p.strip(" •-*·∙◦▪\t()[]")
            p = re.sub(r'\s*[\*†§#]+\s*$', '', p)
            p = re.sub(r'\s*\([A-Z][^\)]{0,5}\)\s*$', '', p)
            p = p.strip()
            if 5 < len(p) < 80:
                if not SKIP_LINE_RE.search(p):
                    courses_found.append(p.lower())
    
    # Strategy 3: Look for lines that look like IITK course codes (ESO207, CS771, etc.)
    # These usually follow a coursework section
    course_code_re = re.compile(
        r"(?i)\b(ESC|ESO|CS|MSO|PHY|CHE|ME|CE|EE|MTH|MBA|ECO|AE|TA|SE|IE)\d{2,4}[A-Z]?\b"
    )
    for line in lines:
        if course_code_re.search(line):
            # Extract the course name (text around the code)
            # Clean the line
            line_clean = line.strip()
            if 5 < len(line_clean) < 100:
                # Remove the course code for the name
                name = course_code_re.sub("", line_clean).strip(" |-|:")
                name = name.strip()
                if 4 < len(name) < 80 and not SKIP_LINE_RE.search(name):
                    courses_found.append(name.lower())
            # Also keep the raw code
            for m in course_code_re.findall(line):
                courses_found.append(m.lower())
    
    return courses_found


def main():
    all_results = {}
    
    for role in ROLES:
        role_dir = FIXTURES_DIR / role
        files = list(role_dir.glob("*.pdf"))
        
        print(f"\n{'='*60}")
        print(f"Deep coursework scan: {role} ({len(files)} PDFs)")
        print(f"{'='*60}")
        
        role_courses = Counter()
        role_course_codes = Counter()
        per_file = {}
        
        for fpath in sorted(files):
            text = extract_text_pymupdf(fpath)
            if not text:
                continue
            
            courses = extract_courses_from_text(text, fpath.name)
            
            # Separate course codes from names
            code_re = re.compile(r'^(esc|eso|cs|mso|phy|che|me|ce|ee|mth|mba|eco|ae|ta|se|ie)\d{2,4}[a-z]?$')
            names = []
            codes = []
            for c in courses:
                if code_re.match(c):
                    codes.append(c.upper())
                else:
                    names.append(c)
            
            per_file[fpath.name] = {
                "course_names": list(set(names))[:20],
                "course_codes": list(set(codes))
            }
            
            for n in names:
                role_courses[n] += 1
            for c in codes:
                role_course_codes[c.upper()] += 1
            
            if names or codes:
                print(f"  {fpath.name}: {len(names)} names, {len(codes)} codes")
                if names:
                    print(f"    Sample names: {names[:5]}")
                if codes:
                    print(f"    Codes: {codes[:8]}")
        
        all_results[role] = {
            "top_course_names": dict(role_courses.most_common(50)),
            "top_course_codes": dict(role_course_codes.most_common(30)),
            "per_file": per_file
        }
    
    # Save
    out_path = FIXTURES_DIR.parent.parent / "deep_coursework_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to {out_path}")
    
    # Print summary
    print("\n\n=== TOP COURSES BY ROLE ===")
    for role in ROLES:
        print(f"\n{role}:")
        print("  Course Names (top 25):")
        for k, v in list(all_results[role]["top_course_names"].items())[:25]:
            print(f"    [{v:2d}] {k}")
        print("  Course Codes (top 15):")
        for k, v in list(all_results[role]["top_course_codes"].items())[:15]:
            print(f"    [{v:2d}] {k}")


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    main()

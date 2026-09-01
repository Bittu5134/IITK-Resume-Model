"""
Analyze all resumes in tests/fixtures/ organized by role.
Extracts coursework, skills, PoRs, projects, and internship patterns.
Outputs role-specific frequency maps to resume_analysis_by_role.json
"""

import os
import re
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pdfplumber
    PDF_BACKEND = "pdfplumber"
except ImportError:
    try:
        import fitz  # PyMuPDF
        PDF_BACKEND = "pymupdf"
    except ImportError:
        import pdfminer.high_level as pdfminer_hl
        PDF_BACKEND = "pdfminer"

print(f"Using PDF backend: {PDF_BACKEND}")

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
OUTPUT_FILE = Path(__file__).parent.parent / "resume_analysis_by_role.json"

ROLES = ["Software", "Quant", "Core", "Consulting"]


# ─── PDF text extraction ─────────────────────────────────────────────────────

def extract_text_pdfplumber(path: Path) -> str:
    import pdfplumber
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
    except Exception as e:
        print(f"  [WARN] pdfplumber failed for {path.name}: {e}")
    return "\n".join(pages)


def extract_text_pymupdf(path: Path) -> str:
    import fitz
    pages = []
    try:
        doc = fitz.open(str(path))
        for page in doc:
            pages.append(page.get_text())
        doc.close()
    except Exception as e:
        print(f"  [WARN] pymupdf failed for {path.name}: {e}")
    return "\n".join(pages)


def extract_text_pdfminer(path: Path) -> str:
    import pdfminer.high_level as pdfminer_hl
    try:
        return pdfminer_hl.extract_text(str(path))
    except Exception as e:
        print(f"  [WARN] pdfminer failed for {path.name}: {e}")
        return ""


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            print(f"  [WARN] docx failed for {path.name}: {e}")
            return ""
    
    if PDF_BACKEND == "pdfplumber":
        return extract_text_pdfplumber(path)
    elif PDF_BACKEND == "pymupdf":
        return extract_text_pymupdf(path)
    else:
        return extract_text_pdfminer(path)


# ─── Section detection ────────────────────────────────────────────────────────

SECTION_PATTERNS = {
    "coursework": re.compile(
        r"(?i)(relevant\s+)?course(work|s)?|key\s+courses?|academic\s+courses?|"
        r"course\s+highlights?|courses?\s+taken|curriculum|scholastic\s+achievements?|"
        r"technical\s+courses?|online\s+courses?|certifications?\s+and\s+courses?"
    ),
    "skills": re.compile(
        r"(?i)(technical\s+)?(skills?|competencies|expertise|proficiencies?|"
        r"programming\s+languages?|technologies?|tools?\s+and\s+technologies?|"
        r"software\s+skills?)"
    ),
    "por": re.compile(
        r"(?i)(positions?\s+of\s+responsibility|extra.?curricular|"
        r"leadership|volunteer|activities|club|society|responsibilities|"
        r"co.?curricular|achievements?|awards?)"
    ),
    "projects": re.compile(
        r"(?i)(projects?|personal\s+projects?|academic\s+projects?|"
        r"key\s+projects?|notable\s+projects?|research\s+projects?|"
        r"course\s+projects?)"
    ),
    "internship": re.compile(
        r"(?i)(intern(ship)?s?|work\s+experience|industry\s+experience|"
        r"professional\s+experience|employment|experience)"
    ),
    "education": re.compile(
        r"(?i)(education|academic\s+background|qualification)"
    ),
}

# Section header line: short line that matches a section pattern
HEADER_LINE_RE = re.compile(r"^(.{3,60})$")


def detect_section(line: str) -> str | None:
    """Return the section name if the line looks like a section header."""
    line = line.strip()
    if not line or len(line) > 80:
        return None
    for section, pat in SECTION_PATTERNS.items():
        if pat.search(line):
            return section
    return None


def split_into_sections(text: str) -> dict[str, list[str]]:
    """Split resume text into labelled sections."""
    sections = defaultdict(list)
    current_section = "header"
    
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        
        detected = detect_section(stripped)
        if detected and len(stripped) < 80:
            current_section = detected
            continue
        
        sections[current_section].append(stripped)
    
    return dict(sections)


# ─── Extraction helpers ───────────────────────────────────────────────────────

# Courses: common IITK course names
COURSE_KEYWORDS = [
    # CS/EE
    "data structures", "algorithms", "dsa", "operating systems", "os",
    "computer networks", "dbms", "database", "machine learning", "ml",
    "deep learning", "artificial intelligence", "ai", "computer vision",
    "natural language processing", "nlp", "computer architecture",
    "compiler", "software engineering", "theory of computation",
    "discrete mathematics", "discrete math", "digital electronics",
    "microprocessors", "embedded", "signal processing", "control systems",
    "object oriented", "oop", "oops", "distributed systems",
    "parallel computing", "cloud computing", "cryptography", "network security",
    "computer graphics", "visualization", "web development",
    "programming", "c++", "python", "java",
    # Math/Stat
    "probability", "statistics", "stochastic", "linear algebra", "calculus",
    "differential equations", "numerical methods", "optimization",
    "real analysis", "abstract algebra", "graph theory", "combinatorics",
    "time series", "bayesian", "regression", "econometrics",
    "financial mathematics", "mathematical finance", "quantitative finance",
    "game theory", "mathematical modeling",
    # Core engg
    "thermodynamics", "fluid mechanics", "solid mechanics", "mechanics",
    "structural analysis", "geotechnical", "transportation", "surveying",
    "hydrology", "environmental engineering", "materials science",
    "heat transfer", "mass transfer", "reaction kinetics", "process control",
    "chemical engineering", "mechanical engineering", "civil engineering",
    "electrical engineering", "electronics", "vlsi", "power systems",
    "manufacturing", "cad", "finite element", "matlab",
    # Econ/Finance
    "microeconomics", "macroeconomics", "econometrics", "corporate finance",
    "accounting", "business analytics", "management", "strategy",
]

SKILLS_KEYWORDS = [
    # Languages
    "python", "c++", "c", "java", "javascript", "typescript", "go", "golang",
    "rust", "scala", "r", "julia", "matlab", "sql", "bash", "shell",
    "html", "css", "php", "ruby", "swift", "kotlin",
    # ML/AI
    "tensorflow", "pytorch", "keras", "sklearn", "scikit-learn", "pandas",
    "numpy", "scipy", "matplotlib", "seaborn", "opencv", "transformers",
    "huggingface", "xgboost", "lightgbm", "nltk", "spacy",
    # Web
    "react", "angular", "vue", "node", "express", "django", "flask",
    "fastapi", "spring", "laravel", "nextjs", "redux",
    # Data
    "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    # Cloud/DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "jenkins", "github actions", "ci/cd", "linux",
    # Tools
    "git", "github", "gitlab", "vim", "latex", "figma",
    "autocad", "solidworks", "ansys", "catia", "staad",
    # Quant
    "quantitative", "stochastic calculus", "monte carlo", "black-scholes",
    "derivatives", "options", "financial modeling", "bloomberg",
    "risk management", "portfolio", "backtesting",
    # Competitive programming
    "codeforces", "leetcode", "codechef", "atcoder", "hackerrank",
    "competitive programming",
]

# PoR indicators
POR_ROLE_KEYWORDS = [
    "secretary", "coordinator", "manager", "head", "lead", "president",
    "vice president", "convener", "mentor", "tutor", "anchor", "captain",
    "organizer", "director", "executive", "member", "representative",
    "associate", "editor", "designer", "developer", "volunteer",
    "incharge", "in-charge", "chair", "co-chair", "deputy",
    "cultural", "technical", "academic", "sports", "hostel", "welfare",
    "placement", "alumni", "media", "marketing", "finance", "operations",
    "outreach", "research", "training",
]

# IITK-specific PoR entities
IITK_POR_ENTITIES = [
    "gymkhana", "senate", "antaragni", "techkriti", "prayas", "vox populi",
    "students' placement office", "spo", "counselling service", "css",
    "student wellness", "nss", "ncc", "bsa", "astronomy club",
    "programming club", "robotics", "quiz club", "film club", "music club",
    "drama club", "literary club", "debating", "model united nations", "mun",
    "science olympiad", "hackathon", "coding club", "entrepreneurship",
    "e-cell", "ifc", "hall council", "hostel council",
    "academic mentor", "peer mentor", "english proficiency",
    "english language teacher", "academic council", "student council",
]

# Internship company types
INTERNSHIP_INDICATORS = [
    "intern", "internship", "summer intern", "winter intern",
    "research intern", "software intern", "engineering intern",
    "analyst intern", "quant intern", "data science intern",
    "product intern", "consulting intern",
]

# Project keywords
PROJECT_TYPES = {
    "ml_ai": ["machine learning", "deep learning", "neural network", "nlp",
               "computer vision", "classification", "regression", "clustering",
               "recommendation", "transformer", "bert", "gpt", "llm",
               "sentiment", "detection", "prediction", "generative"],
    "web": ["website", "web app", "full stack", "frontend", "backend",
            "rest api", "api", "django", "flask", "react", "node.js",
            "deployment", "authentication", "database"],
    "systems": ["operating system", "compiler", "interpreter", "scheduler",
                "memory management", "file system", "distributed",
                "parallel", "multithreading", "socket", "network"],
    "competitive": ["algorithm", "dynamic programming", "graph", "tree",
                   "competitive programming", "codeforces", "contest"],
    "research": ["research", "paper", "publication", "thesis", "survey",
                 "analysis", "study", "investigation", "experiment"],
    "simulation": ["simulation", "modelling", "cfd", "finite element",
                   "ansys", "matlab", "numerical", "monte carlo"],
    "data": ["data analysis", "data science", "analytics", "visualization",
             "dashboard", "tableau", "powerbi", "excel", "pandas"],
    "finance_quant": ["stock", "trading", "portfolio", "options", "derivatives",
                      "backtesting", "financial", "market", "alpha", "factor"],
    "hardware": ["fpga", "arduino", "raspberry pi", "embedded", "iot",
                 "circuit", "pcb", "microcontroller", "sensor"],
    "mobile": ["android", "ios", "mobile app", "flutter", "react native"],
    "security": ["security", "cryptography", "encryption", "vulnerability",
                 "penetration testing", "ctf", "malware"],
}


def normalize(text: str) -> str:
    return text.lower().strip()


def count_keyword_hits(text_lower: str, keywords: list[str]) -> Counter:
    hits = Counter()
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            hits[kw_lower] += 1
    return hits


def extract_coursework_lines(sections: dict[str, list[str]], full_text: str) -> list[str]:
    """Extract lines that are likely course names."""
    course_lines = []
    
    # 1. From detected coursework section
    for line in sections.get("coursework", []):
        line_stripped = line.strip(" •-|,;:")
        if 5 < len(line_stripped) < 100:
            # Split on common separators
            parts = re.split(r"[|,;•·]", line_stripped)
            for part in parts:
                part = part.strip()
                if 3 < len(part) < 60:
                    course_lines.append(part.lower())
    
    # 2. From education section — look for courses mentioned
    for line in sections.get("education", []):
        line_lower = line.lower()
        for kw in COURSE_KEYWORDS:
            if kw in line_lower:
                course_lines.append(kw)
    
    # 3. Scan full text for explicit course mentions
    text_lower = full_text.lower()
    # After "courses:", "coursework:", etc.
    course_section_match = re.search(
        r"(?i)(relevant\s+courses?|coursework|key\s+courses?|courses?\s+taken|"
        r"technical\s+courses?)[:\s]+([^\n]{10,300})",
        full_text
    )
    if course_section_match:
        course_text = course_section_match.group(2)
        parts = re.split(r"[|,;•·\n]", course_text)
        for p in parts:
            p = p.strip(" •-|,;:\t")
            if 3 < len(p) < 70:
                course_lines.append(p.lower())
    
    return course_lines


def extract_skills_from_text(sections: dict[str, list[str]], full_text: str) -> list[str]:
    skills_found = []
    text_lower = full_text.lower()
    for kw in SKILLS_KEYWORDS:
        if kw.lower() in text_lower:
            skills_found.append(kw.lower())
    return skills_found


def extract_por_lines(sections: dict[str, list[str]], full_text: str) -> list[str]:
    por_lines = []
    for line in sections.get("por", []):
        line_stripped = line.strip()
        if 5 < len(line_stripped) < 200:
            por_lines.append(line_stripped.lower())
    return por_lines


def extract_project_keywords(sections: dict[str, list[str]], full_text: str) -> dict[str, int]:
    type_hits = Counter()
    text_lower = full_text.lower()
    for ptype, keywords in PROJECT_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                type_hits[ptype] += 1
    return dict(type_hits)


def extract_internship_patterns(sections: dict[str, list[str]], full_text: str) -> list[str]:
    patterns = []
    text_lower = full_text.lower()
    
    # Look for internship role + company patterns
    intern_matches = re.findall(
        r"(?i)(software|data\s*science?|quant(?:itative)?|research|"
        r"analytics?|ml|ai|product|consulting|financial|trading|"
        r"mechanical|civil|chemical|electrical|core|business)[\s\w]*"
        r"intern(?:ship)?",
        full_text
    )
    for m in intern_matches:
        patterns.append(m.strip().lower())
    
    # Look for company names in internship section
    for line in sections.get("internship", []):
        line_stripped = line.strip()
        if 5 < len(line_stripped) < 150:
            patterns.append(line_stripped.lower())
    
    return patterns


# ─── Main analysis ─────────────────────────────────────────────────────────────

def analyze_role(role: str) -> dict:
    role_dir = FIXTURES_DIR / role
    files = list(role_dir.glob("*.pdf")) + list(role_dir.glob("*.docx"))
    
    print(f"\n{'='*60}")
    print(f"Analyzing {role}: {len(files)} files")
    print(f"{'='*60}")
    
    all_courses = Counter()
    all_skills = Counter()
    all_por = Counter()
    all_projects = Counter()  # by type
    all_project_keywords = Counter()
    all_internship = Counter()
    
    # Raw coursework lines for section format analysis
    course_section_formats = []
    
    resume_count = 0
    resumes_with_coursework = 0
    
    for fpath in sorted(files):
        print(f"  Processing: {fpath.name}")
        text = extract_text(fpath)
        if not text.strip():
            print(f"    [SKIP] No text extracted")
            continue
        
        resume_count += 1
        text_lower = text.lower()
        sections = split_into_sections(text)
        
        # 1. Coursework
        course_lines = extract_coursework_lines(sections, text)
        if course_lines:
            resumes_with_coursework += 1
            for cl in course_lines:
                if cl:
                    all_courses[cl] += 1
            # Check section header format
            for line in text.splitlines():
                stripped = line.strip()
                if SECTION_PATTERNS["coursework"].search(stripped) and len(stripped) < 80:
                    course_section_formats.append(stripped)
        
        # Also count COURSE_KEYWORDS present in text
        for kw in COURSE_KEYWORDS:
            if kw in text_lower:
                all_courses[kw] += 1
        
        # 2. Skills
        for kw in SKILLS_KEYWORDS:
            if kw.lower() in text_lower:
                all_skills[kw.lower()] += 1
        
        # 3. PoRs
        for line in sections.get("por", []):
            line_lower = line.lower()
            for kw in POR_ROLE_KEYWORDS:
                if kw in line_lower:
                    all_por[kw] += 1
            for entity in IITK_POR_ENTITIES:
                if entity in line_lower:
                    all_por[entity] += 1
        # Also scan full text for POR entities
        for entity in IITK_POR_ENTITIES:
            if entity in text_lower:
                all_por[entity] += 1
        
        # 4. Projects
        for ptype, keywords in PROJECT_TYPES.items():
            for kw in keywords:
                if kw in text_lower:
                    all_projects[ptype] += 1
                    all_project_keywords[kw] += 1
        
        # 5. Internships
        for indicator in INTERNSHIP_INDICATORS:
            if indicator in text_lower:
                all_internship["has_internship"] += 1
                break
        
        intern_matches = re.findall(
            r"(?i)(software|data\s*science?|quant(?:itative)?|research|"
            r"analytics?|machine\s*learning|ai|ml|product|consulting|"
            r"financial|trading|mechanical|civil|chemical|electrical|"
            r"core|business)[\s\w]*intern(?:ship)?",
            text
        )
        for m in intern_matches:
            all_internship[m.strip().lower()] += 1
    
    # Identify raw coursework section lines from actual text
    raw_course_section_examples = []
    # Re-scan a few resumes to get example course sections
    for fpath in sorted(files)[:min(5, len(files))]:
        text = extract_text(fpath)
        if not text:
            continue
        # Find coursework section blocks
        lines = text.splitlines()
        in_course = False
        block = []
        for line in lines:
            stripped = line.strip()
            if SECTION_PATTERNS["coursework"].search(stripped) and len(stripped) < 80:
                in_course = True
                block = [f"[HEADER: {stripped}]"]
                continue
            if in_course:
                if any(SECTION_PATTERNS[s].search(stripped) and len(stripped) < 80
                       for s in SECTION_PATTERNS if s != "coursework"):
                    break
                if stripped:
                    block.append(stripped)
                if len(block) > 12:
                    break
        if len(block) > 1:
            raw_course_section_examples.append({
                "file": fpath.name,
                "lines": block
            })
    
    return {
        "role": role,
        "resume_count": resume_count,
        "resumes_with_coursework_section": resumes_with_coursework,
        "coursework_section_header_formats": list(set(course_section_formats)),
        "coursework_raw_examples": raw_course_section_examples,
        "top_courses": dict(all_courses.most_common(50)),
        "top_skills": dict(all_skills.most_common(40)),
        "top_por_keywords": dict(all_por.most_common(30)),
        "project_type_frequency": dict(all_projects.most_common()),
        "top_project_keywords": dict(all_project_keywords.most_common(30)),
        "internship_patterns": dict(all_internship.most_common(20)),
    }


# ─── Extra: deep coursework scan ─────────────────────────────────────────────

def deep_coursework_scan(role: str) -> dict:
    """
    More aggressive coursework extraction: look for ANY line that seems like
    a course name (not just in detected coursework section).
    """
    role_dir = FIXTURES_DIR / role
    files = list(role_dir.glob("*.pdf")) + list(role_dir.glob("*.docx"))
    
    # Patterns that suggest a coursework section
    cw_header_re = re.compile(
        r"(?i)^(relevant\s+courses?|coursework|key\s+courses?|"
        r"courses?\s+taken|technical\s+courses?|academic\s+courses?|"
        r"scholastic|course\s+highlights?)\s*:?\s*$"
    )
    
    all_raw_course_text = []
    
    for fpath in sorted(files):
        text = extract_text(fpath)
        if not text:
            continue
        
        lines = text.splitlines()
        in_cw = False
        depth = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if cw_header_re.match(stripped):
                in_cw = True
                depth = 0
                continue
            
            if in_cw:
                # Stop at next section header
                if any(SECTION_PATTERNS[s].search(stripped) and 3 < len(stripped) < 70
                       for s in ["skills", "por", "projects", "internship", "education"]):
                    in_cw = False
                    continue
                if stripped:
                    all_raw_course_text.append(stripped)
                    depth += 1
                if depth > 15:
                    in_cw = False
        
        # Also search using regex for inline course lists
        # Pattern: "Courses: X, Y, Z" or "Relevant Courses: X | Y | Z"
        inline_matches = re.findall(
            r"(?i)(?:relevant\s+)?courses?\s*:?\s*([^\n]{15,300})",
            text
        )
        for m in inline_matches:
            parts = re.split(r"[|,;•·]", m)
            for p in parts:
                p = p.strip(" •-|,;:\t")
                if 3 < len(p) < 70:
                    all_raw_course_text.append(p)
    
    # Deduplicate and count
    cleaned = []
    for c in all_raw_course_text:
        c = c.strip(" •-|,;:\t*·")
        if 3 < len(c) < 80:
            cleaned.append(c.lower())
    
    return dict(Counter(cleaned).most_common(60))


# ─── Run ───────────────────────────────────────────────────────────────────────

def main():
    results = {}
    
    for role in ROLES:
        role_result = analyze_role(role)
        deep_courses = deep_coursework_scan(role)
        role_result["deep_coursework_scan"] = deep_courses
        results[role] = role_result
    
    # Summary section
    summary = {}
    for role in ROLES:
        r = results[role]
        summary[role] = {
            "total_resumes": r["resume_count"],
            "resumes_with_coursework": r["resumes_with_coursework_section"],
            "top_10_courses": list(r["top_courses"].keys())[:10],
            "top_10_skills": list(r["top_skills"].keys())[:10],
            "top_10_por": list(r["top_por_keywords"].keys())[:10],
            "top_project_types": list(r["project_type_frequency"].keys())[:5],
            "top_internship_patterns": list(r["internship_patterns"].keys())[:5],
        }
    
    output = {
        "metadata": {
            "analysis_date": "2026-09-01",
            "total_roles": len(ROLES),
            "roles": ROLES,
            "purpose": "Role-specific frequency analysis for coursework scoring fix",
        },
        "summary": summary,
        "by_role": results,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Analysis complete. Output written to: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    # Print summary
    for role in ROLES:
        r = results[role]
        print(f"\n{role}:")
        print(f"  Resumes: {r['resume_count']}")
        print(f"  With coursework section: {r['resumes_with_coursework_section']}")
        print(f"  Coursework section headers: {r['coursework_section_header_formats'][:3]}")
        print(f"  Top courses: {list(r['top_courses'].keys())[:8]}")
        print(f"  Top skills: {list(r['top_skills'].keys())[:8]}")
        print(f"  Top PoRs: {list(r['top_por_keywords'].keys())[:5]}")
        print(f"  Project types: {list(r['project_type_frequency'].keys())[:5]}")


if __name__ == "__main__":
    main()

"""
IITK Campus Lingo PDF Analyzer
Extracts and categorizes all IITK-specific terminology into a structured JSON.
"""

import json
import re
from pathlib import Path

# ── Full raw text (already extracted; load from file) ─────────────────────────
raw_text = Path("lingo_raw.txt").read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 1 — Course Codes / Department Abbreviations
# The PDF lists branch codes explicitly.
# ─────────────────────────────────────────────────────────────────────────────
course_codes = {
    "BT_CSE": {
        "code": "BT CSE",
        "full_name": "Computer Science and Engineering (B.Tech)",
        "hindi_name": "संगणक विज्ञान एवं अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.9,
        "notes": "Most competitive branch at IITK; highest demand for placement"
    },
    "BT_EE": {
        "code": "BT EE",
        "full_name": "Electrical Engineering (B.Tech)",
        "hindi_name": "विद्युत अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.85,
        "notes": "Called 'Batti' in campus slang"
    },
    "BT_ME": {
        "code": "BT ME",
        "full_name": "Mechanical Engineering (B.Tech)",
        "hindi_name": "यांत्रिक अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.8,
        "notes": "Called 'MechEngi' in campus slang"
    },
    "BT_CHE": {
        "code": "BT CHE",
        "full_name": "Chemical Engineering (B.Tech)",
        "hindi_name": "रासायनिक अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.75,
        "notes": "Called 'Kam-akal' in campus slang (homonym of Chemical)"
    },
    "BT_AE": {
        "code": "BT AE",
        "full_name": "Aerospace Engineering (B.Tech)",
        "hindi_name": "वाँतरिक्ष अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 1,
        "weight": 0.7
    },
    "BT_CE": {
        "code": "BT CE",
        "full_name": "Civil Engineering (B.Tech)",
        "hindi_name": "जनपद अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.7,
        "notes": "Called 'Majdoor' in campus slang"
    },
    "BT_MSE": {
        "code": "BT MSE",
        "full_name": "Materials Science and Engineering (B.Tech)",
        "hindi_name": "पदार्थ विज्ञान एवं अभयांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.65,
        "notes": "Called 'Masse' in campus slang"
    },
    "BSBE": {
        "code": "BSBE",
        "full_name": "Biological Sciences and Bioengineering (B.S.)",
        "hindi_name": "जीव विज्ञान एवं जैविक अभियांत्रिकी",
        "category": "branch_code",
        "frequency": 2,
        "weight": 0.65,
        "notes": "Called 'Basbey' in campus slang"
    },
    "BS_MTH": {
        "code": "BS MTH",
        "full_name": "Mathematics and Scientific Computing (B.S.)",
        "hindi_name": "गणित एवं वैज्ञानिक सांख्यिकी",
        "category": "branch_code",
        "frequency": 1,
        "weight": 0.7
    },
    "BS_PHY": {
        "code": "BS PHY",
        "full_name": "Physics (B.S.)",
        "hindi_name": "भौतिक शास्त्र",
        "category": "branch_code",
        "frequency": 1,
        "weight": 0.65
    },
    "BS_CHM": {
        "code": "BS CHM",
        "full_name": "Chemistry (B.S.)",
        "hindi_name": "रसायन शास्त्र",
        "category": "branch_code",
        "frequency": 1,
        "weight": 0.6
    },
    "BS_ECO": {
        "code": "BS ECO",
        "full_name": "Economics (B.S.)",
        "hindi_name": "अर्थशास्त्र",
        "category": "branch_code",
        "frequency": 1,
        "weight": 0.65
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 2 — Position of Responsibility (PoR) Terms
# ─────────────────────────────────────────────────────────────────────────────
por_terms = {
    "Voli": {
        "term": "Voli",
        "full_form": "Volunteer",
        "category": "por_title",
        "frequency": 3,
        "weight": 0.5,
        "hierarchy_level": 1,
        "notes": "Entry-level PoR; volunteers for clubs/fests"
    },
    "Secy": {
        "term": "Secy",
        "full_form": "Secretary",
        "category": "por_title",
        "frequency": 3,
        "weight": 0.75,
        "hierarchy_level": 2,
        "notes": "Club/society Secretary"
    },
    "Cordi": {
        "term": "Cordi",
        "full_form": "Coordinator",
        "category": "por_title",
        "frequency": 4,
        "weight": 0.85,
        "hierarchy_level": 3,
        "notes": "Event/club coordinator; mid-senior PoR"
    },
    "Festi": {
        "term": "Festi",
        "full_form": "Festival Coordinator",
        "category": "por_title",
        "frequency": 2,
        "weight": 0.9,
        "hierarchy_level": 4,
        "notes": "Coordinator of a major IITK fest (Techkriti/Antaragni/Udghosh)"
    },
    "GenSec": {
        "term": "GenSec",
        "full_form": "General Secretary",
        "category": "por_title",
        "frequency": 3,
        "weight": 0.9,
        "hierarchy_level": 5,
        "notes": "Senior leadership PoR; hall or council GenSec"
    },
    "Presi": {
        "term": "Presi",
        "full_form": "President",
        "category": "por_title",
        "frequency": 2,
        "weight": 1.0,
        "hierarchy_level": 6,
        "notes": "Highest student leadership PoR"
    },
    "Convener": {
        "term": "Convener",
        "full_form": "Convener / Co-Convener",
        "category": "por_title",
        "frequency": 2,
        "weight": 0.9,
        "hierarchy_level": 5,
        "notes": "Convener of major student bodies (councils, committees)"
    },
    "Repi": {
        "term": "Repi",
        "full_form": "Representative / Wing Representative",
        "category": "por_title",
        "frequency": 2,
        "weight": 0.4,
        "hierarchy_level": 1,
        "notes": "Hall wing representative; ensures wingies attend orientation"
    },
    "HEC_member": {
        "term": "HEC Member",
        "full_form": "Hall Executive Committee Member",
        "category": "por_title",
        "frequency": 2,
        "weight": 0.7,
        "hierarchy_level": 3,
        "notes": "Elected hall-level leadership role"
    },
    "Student_Guide": {
        "term": "Student Guide (SG / Baap / Amma)",
        "full_form": "Student Guide",
        "category": "por_title",
        "frequency": 3,
        "weight": 0.65,
        "hierarchy_level": 2,
        "notes": "Seniors assigned to mentor first-year students (Baccha/Bacchi)"
    },
    "Senator": {
        "term": "Senator",
        "full_form": "Student Senator",
        "category": "por_title",
        "frequency": 2,
        "weight": 0.95,
        "hierarchy_level": 6,
        "notes": "Anagram of 'treason' per campus lingo; high-level institute governance"
    },
    "PoR": {
        "term": "PoR",
        "full_form": "Position of Responsibility",
        "category": "por_meta",
        "frequency": 5,
        "weight": 1.0,
        "notes": "Generic term for any leadership/organizational role on campus"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 3 — IITK-Specific Programs
# ─────────────────────────────────────────────────────────────────────────────
programs = {
    "SURGE": {
        "term": "SURGE",
        "full_form": "Summer Undergraduate Research Grant for Excellence",
        "category": "research_program",
        "frequency": 3,
        "weight": 0.95,
        "notes": "Flagship summer research program; highly valued for core/quant roles"
    },
    "SRIP": {
        "term": "SRIP",
        "full_form": "Summer Research Internship Program",
        "category": "research_program",
        "frequency": 2,
        "weight": 0.85,
        "notes": "Summer research program; externally-funded or department variant"
    },
    "UGP": {
        "term": "UGP",
        "full_form": "Undergraduate Project (B.Tech Project / BTP)",
        "category": "academic_program",
        "frequency": 3,
        "weight": 0.8,
        "notes": "Mandatory final-year research project; also called BTP"
    },
    "BC": {
        "term": "BC",
        "full_form": "Branch Change",
        "category": "academic_program",
        "frequency": 3,
        "weight": 0.85,
        "notes": "Highly coveted; wet dream of 9/10 first-year undergrads per lingo doc"
    },
    "AP": {
        "term": "AP",
        "full_form": "Academic Probation",
        "category": "academic_status",
        "frequency": 2,
        "weight": 0.6,
        "notes": "Warning status for poor academic performance"
    },
    "DP": {
        "term": "DP",
        "full_form": "Disciplinary Probation",
        "category": "academic_status",
        "frequency": 2,
        "weight": 0.5,
        "notes": "Warning status for disciplinary issues"
    },
    "JEE": {
        "term": "JEE",
        "full_form": "Joint Entrance Examination",
        "category": "admission_exam",
        "frequency": 2,
        "weight": 0.9,
        "notes": "Primary entrance exam for IITs; called JEE Advanced for IITs"
    },
    "Gyaan_session": {
        "term": "Gyaan / Gyan Session",
        "full_form": "Knowledge/Wisdom Session",
        "category": "campus_tradition",
        "frequency": 3,
        "weight": 0.6,
        "notes": "Post-midnight informal mentoring session between junior and senior"
    },
    "Kholna": {
        "term": "Kholna / खोलना",
        "full_form": "Formal Introduction Ritual",
        "category": "campus_tradition",
        "frequency": 4,
        "weight": 0.7,
        "notes": "Tradition of reciting full intro (name, parents, hometown, branch, JEE rank) to seniors"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 4 — Clubs, Societies, Organizations, Councils
# ─────────────────────────────────────────────────────────────────────────────
clubs_orgs = {
    "Students_Gymkhana": {
        "term": "Students' Gymkhana",
        "aliases": ["Gymkhana"],
        "category": "student_governance",
        "frequency": 3,
        "weight": 1.0,
        "notes": "Apex student body of IITK governing all student activities"
    },
    "AnC_Council": {
        "term": "Academics and Career Council (AnC)",
        "aliases": ["AnC", "A&C Council"],
        "category": "student_council",
        "frequency": 3,
        "weight": 0.9,
        "notes": "Manages academic and career-related activities; very prominent in resumes"
    },
    "SnT_Council": {
        "term": "Science and Technology Council (SnT)",
        "aliases": ["SnT", "S&T Council"],
        "category": "student_council",
        "frequency": 3,
        "weight": 0.9,
        "notes": "Manages technical clubs and activities"
    },
    "HEC": {
        "term": "Hall Executive Committee (HEC)",
        "aliases": ["HEC"],
        "category": "hall_governance",
        "frequency": 4,
        "weight": 0.7,
        "notes": "'Unskilled people with a degree dictating skilled people without degrees' per lingo"
    },
    "SPO": {
        "term": "Students' Placement Office (SPO)",
        "aliases": ["SPO"],
        "category": "institute_office",
        "frequency": 3,
        "weight": 0.85,
        "notes": "Manages campus placements; extremely influential"
    },
    "DOSA": {
        "term": "DOSA",
        "aliases": ["Dean of Student Affairs", "AA", "RA", "FA"],
        "category": "institute_administration",
        "frequency": 2,
        "weight": 0.6,
        "notes": "Dean of Student/Academic/Research & Alumni/Faculty Affairs"
    },
    "Techkriti": {
        "term": "Techkriti",
        "aliases": [],
        "category": "annual_festival",
        "frequency": 2,
        "weight": 0.85,
        "notes": "Annual technical festival of IITK; Asia's largest tech fest"
    },
    "Antaragni": {
        "term": "Antaragni",
        "aliases": [],
        "category": "annual_festival",
        "frequency": 2,
        "weight": 0.8,
        "notes": "Annual cultural festival of IITK"
    },
    "Udghosh": {
        "term": "Udghosh",
        "aliases": [],
        "category": "annual_festival",
        "frequency": 2,
        "weight": 0.75,
        "notes": "Annual sports festival of IITK"
    },
    "Galaxy": {
        "term": "Galaxy",
        "aliases": ["Hall Galaxy", "Inter-Hall GC"],
        "category": "intra_iitk_competition",
        "frequency": 3,
        "weight": 0.7,
        "notes": "Inter-hall general championship; comprehensive competition across domains"
    },
    "Takneek": {
        "term": "Takneek",
        "aliases": ["Freshers Technical Event"],
        "category": "intra_iitk_competition",
        "frequency": 3,
        "weight": 0.65,
        "notes": "Annual technical competition for first-years; nightout preparation mentioned in lingo"
    },
    "Inferno": {
        "term": "Inferno",
        "aliases": [],
        "category": "intra_iitk_competition",
        "frequency": 2,
        "weight": 0.6,
        "notes": "Cultural inter-hall competition"
    },
    "Inter_IIT": {
        "term": "Inter-IIT",
        "aliases": ["Inter IIT Tech Meet", "Inter IIT Sports"],
        "category": "inter_iit_competition",
        "frequency": 2,
        "weight": 0.9,
        "notes": "Competitions between all IITs; gold/silver/bronze medals are strong resume signals"
    },
    "Hall_2": {
        "term": "Hall 2",
        "aliases": ["H2", "Bakait Hall"],
        "category": "hostel",
        "frequency": 3,
        "weight": 0.5,
        "notes": "Renowned hostel; home of 'Bakaits'; culturally distinct identity"
    },
    "Senate": {
        "term": "Student Senate",
        "aliases": ["Senate", "Senator"],
        "category": "institute_governance",
        "frequency": 2,
        "weight": 0.95,
        "notes": "Highest student governance body; senators are elected representatives"
    },
    "GBM": {
        "term": "GBM",
        "aliases": ["General Body Meeting"],
        "category": "hall_event",
        "frequency": 2,
        "weight": 0.4,
        "notes": "Late-night hall-level meetings for first years by HEC"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 5 — Academic Terminology Unique to IITK
# ─────────────────────────────────────────────────────────────────────────────
academic_terms = {
    "CPI": {
        "term": "CPI",
        "full_form": "Cumulative Performance Index",
        "category": "academic_metric",
        "frequency": 5,
        "weight": 1.0,
        "notes": "IITK's equivalent of CGPA; 10-point scale; critical for quant/consult roles"
    },
    "SPI": {
        "term": "SPI",
        "full_form": "Semester Performance Index",
        "category": "academic_metric",
        "frequency": 5,
        "weight": 0.9,
        "notes": "Semester GPA; 10-point scale. Special slang: Dassa=10, Nehli=9, Atthi=8, etc."
    },
    "Dassa": {
        "term": "Dassa / 10 Pointer",
        "full_form": "SPI of 10.0",
        "category": "academic_slang",
        "frequency": 3,
        "weight": 0.95,
        "notes": "Perfect 10 SPI; extremely rare and prestigious"
    },
    "SPI_grades": {
        "term": "Chaugi/Pangi/Chaggi/Satti/Atthi/Nehli",
        "full_form": "SPI 4/5/6/7/8/9 respectively",
        "category": "academic_slang",
        "frequency": 3,
        "weight": 0.7,
        "notes": "Hindi-origin number slang for SPI values"
    },
    "Fakka": {
        "term": "Fakka",
        "full_form": "F Grade (Fail)",
        "category": "academic_slang",
        "frequency": 2,
        "weight": 0.5,
        "notes": "F grade in a course"
    },
    "Endsem": {
        "term": "Endsem",
        "full_form": "End Semester Examination",
        "category": "academic_term",
        "frequency": 3,
        "weight": 0.85,
        "notes": "Final examination of the semester"
    },
    "Midsem": {
        "term": "Mid-sem / Midsem",
        "full_form": "Mid Semester Examination",
        "category": "academic_term",
        "frequency": 3,
        "weight": 0.8,
        "notes": "Midterm exam; called 'mid-sem' universally at IITK"
    },
    "Acads": {
        "term": "Acads",
        "full_form": "Academics",
        "category": "academic_slang",
        "frequency": 3,
        "weight": 0.75
    },
    "Kholu": {
        "term": "Kholu",
        "full_form": "Opening Rank (JEE)",
        "category": "academic_term",
        "frequency": 2,
        "weight": 0.7,
        "notes": "The minimum JEE rank required to get into a branch in a given year"
    },
    "Dhakkan": {
        "term": "Dhakkan",
        "full_form": "Closing Rank (JEE)",
        "category": "academic_term",
        "frequency": 2,
        "weight": 0.7,
        "notes": "The maximum JEE rank accepted for a branch in a given year"
    },
    "Dabba_CSE": {
        "term": "Dabba (II)",
        "full_form": "Department of Computer Science and Engineering",
        "category": "dept_nickname",
        "frequency": 2,
        "weight": 0.7,
        "notes": "CSE dept also called 'Dabba'; Dabba I means laptop"
    },
    "Batti_EE": {
        "term": "Batti",
        "full_form": "Department of Electrical Engineering",
        "category": "dept_nickname",
        "frequency": 2,
        "weight": 0.65
    },
    "Majdoor_CE": {
        "term": "Majdoor",
        "full_form": "Department of Civil Engineering",
        "category": "dept_nickname",
        "frequency": 2,
        "weight": 0.55
    },
    "Undies": {
        "term": "Undies",
        "full_form": "Undergraduates (B.Tech/B.S.)",
        "category": "student_category",
        "frequency": 2,
        "weight": 0.6,
        "notes": "Used by Matkas (M.Techs) and Phuddus (PhDs)"
    },
    "Matka": {
        "term": "Matka",
        "full_form": "M.Tech Student",
        "category": "student_category",
        "frequency": 2,
        "weight": 0.55
    },
    "Phuddu": {
        "term": "Phuddu",
        "full_form": "PhD Student",
        "category": "student_category",
        "frequency": 2,
        "weight": 0.5
    },
    "Y_batch": {
        "term": "Y-Batch (e.g. Y21, Y26)",
        "full_form": "Year of Entry Batch",
        "category": "batch_identifier",
        "frequency": 3,
        "weight": 0.8,
        "notes": "IITK identifies students by entry year: Y21=2021 entry, Y26=2026 entry etc."
    },
    "Fundae": {
        "term": "Fundae",
        "full_form": "Fundamental Principles / Life Advice",
        "category": "campus_knowledge",
        "frequency": 2,
        "weight": 0.6,
        "notes": "Takeaways from a Gyan session; principles shared by seniors"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 6 — Campus Places & Infrastructure (bonus/supplementary)
# ─────────────────────────────────────────────────────────────────────────────
campus_places = {
    "LHC": {
        "term": "LHC",
        "full_form": "Lecture Hall Complex",
        "category": "campus_building",
        "frequency": 2,
        "weight": 0.6
    },
    "CC": {
        "term": "CC",
        "full_form": "Computer Center",
        "category": "campus_building",
        "frequency": 2,
        "weight": 0.65
    },
    "FacB": {
        "term": "FacB",
        "full_form": "Faculty Building",
        "category": "campus_building",
        "frequency": 2,
        "weight": 0.5
    },
    "Lib": {
        "term": "Lib",
        "full_form": "Library (P.K. Kelkar Library)",
        "category": "campus_building",
        "frequency": 2,
        "weight": 0.55
    },
    "Audi": {
        "term": "Audi",
        "full_form": "Auditorium",
        "category": "campus_building",
        "frequency": 2,
        "weight": 0.5
    },
    "MT": {
        "term": "MT",
        "full_form": "Chai ki tapri near Motor Transport Section",
        "category": "campus_place",
        "frequency": 2,
        "weight": 0.5,
        "notes": "Popular chai stall"
    },
    "RM_KD": {
        "term": "RM/KD",
        "full_form": "Epicenter of communism in IITK (canteen/mess)",
        "category": "campus_place",
        "frequency": 2,
        "weight": 0.45,
        "notes": "Informal mess/canteen area known for communist vibes"
    },
    "TB": {
        "term": "TB",
        "full_form": "Tutorial Block",
        "category": "campus_building",
        "frequency": 1,
        "weight": 0.5
    },
    "WL_SL_NL": {
        "term": "WL / SL / NL",
        "full_form": "Western / Southern / Northern Labs",
        "category": "campus_building",
        "frequency": 1,
        "weight": 0.5
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 7 — General Campus Slang (non-academic)
# ─────────────────────────────────────────────────────────────────────────────
campus_slang = {
    "Bakait": {
        "term": "Bakait",
        "meaning": "Hall 2 resident; smart, confident, fearless person; anyone with strong character",
        "category": "personality_descriptor",
        "frequency": 8,
        "weight": 0.9
    },
    "Chapu": {
        "term": "Chapu / Chapna / Chap diya",
        "meaning": "Great, impressive; used for anything excellent (food, person, score)",
        "category": "quality_descriptor",
        "frequency": 7,
        "weight": 0.85
    },
    "Bhaukaal": {
        "term": "Bhaukaal",
        "meaning": "Aura, impressive presence",
        "category": "personality_descriptor",
        "frequency": 3,
        "weight": 0.7
    },
    "Maggu": {
        "term": "Maggu / Magai",
        "meaning": "Nerd who only studies; despised by IITians; magai = routine studying",
        "category": "personality_descriptor",
        "frequency": 4,
        "weight": 0.6
    },
    "Telu": {
        "term": "Telu / Tel machana",
        "meaning": "To bungle/screw up something; opposite of chapu",
        "category": "outcome_descriptor",
        "frequency": 4,
        "weight": 0.65
    },
    "Bulla": {
        "term": "Bulla",
        "meaning": "Group idle talk/hangout session; often ends in GPL",
        "category": "social_activity",
        "frequency": 3,
        "weight": 0.6
    },
    "GPL": {
        "term": "GPL",
        "meaning": "Gand pe laat; birthday/celebration tradition of kicking on the butt",
        "category": "campus_tradition",
        "frequency": 3,
        "weight": 0.55
    },
    "Nightout": {
        "term": "Nightout",
        "meaning": "Staying up all night for bulla, fest prep, or studies",
        "category": "campus_tradition",
        "frequency": 3,
        "weight": 0.6
    },
    "Arbit": {
        "term": "Arbit",
        "meaning": "Arbitrary; strange or incomprehensible",
        "category": "quality_descriptor",
        "frequency": 4,
        "weight": 0.65
    },
    "Frust": {
        "term": "Frust",
        "meaning": "Frustrated/stressed; state of mind before an exam after a wasted nightout",
        "category": "emotional_state",
        "frequency": 3,
        "weight": 0.6
    },
    "Fraud": {
        "term": "Fraud / Fraudy",
        "meaning": "Silent group member who shows up only for treats/benefits",
        "category": "personality_descriptor",
        "frequency": 3,
        "weight": 0.6
    },
    "Junta": {
        "term": "Junta",
        "meaning": "People/gathering; most widely used word at IITK",
        "category": "collective_noun",
        "frequency": 6,
        "weight": 0.8
    },
    "Bhasad": {
        "term": "Bhasad / Bhasadu",
        "meaning": "Chaos; one who creates chaos",
        "category": "situation_descriptor",
        "frequency": 3,
        "weight": 0.55
    },
    "Phatta": {
        "term": "Phatta",
        "meaning": "Non-standard cricket played anywhere on campus",
        "category": "campus_activity",
        "frequency": 2,
        "weight": 0.45
    },
    "Chill_hai": {
        "term": "Chill hai",
        "meaning": "All is well; IITK equivalent of 'All is well'",
        "category": "affirmation",
        "frequency": 3,
        "weight": 0.5
    },
    "Sexx_Saxx": {
        "term": "Sexx / Saxx",
        "meaning": "Excellent/impressive; general positive intensifier",
        "category": "quality_descriptor",
        "frequency": 4,
        "weight": 0.6
    },
    "Enthu_Tempo": {
        "term": "Enthu / Tempo",
        "meaning": "Enthusiasm; must be higher than Mt. Everest",
        "category": "emotional_state",
        "frequency": 3,
        "weight": 0.6
    },
    "Gyaan": {
        "term": "Gyaan",
        "meaning": "Informal wisdom/mentoring session; post-midnight senior-junior chat",
        "category": "campus_tradition",
        "frequency": 4,
        "weight": 0.7
    },
    "Baap_Amma": {
        "term": "Baap / Amma",
        "meaning": "Student Guide assigned to first-years; also SG's partner if lucky",
        "category": "campus_relationship",
        "frequency": 4,
        "weight": 0.65
    },
    "Baccha_Bacchi": {
        "term": "Baccha / Bacchi",
        "meaning": "First-year students assigned to a Student Guide",
        "category": "campus_relationship",
        "frequency": 3,
        "weight": 0.6
    },
    "Bhandhu_Bhai": {
        "term": "Bhai / Behen",
        "meaning": "Bacchas/Bacchis under the same Student Guide; SG siblings",
        "category": "campus_relationship",
        "frequency": 2,
        "weight": 0.55
    },
    "Termi": {
        "term": "Termi",
        "meaning": "Termination (of hostel residence); Hall 2 Bakait tradition",
        "category": "campus_event",
        "frequency": 2,
        "weight": 0.5
    },
    "Bakchod": {
        "term": "Bakchod",
        "meaning": "Overachiever with 8 jobs/3 scholarships; 8-dassa or chaapu in many fields",
        "category": "personality_descriptor",
        "frequency": 3,
        "weight": 0.7
    },
    "8_dassa": {
        "term": "8-dassa",
        "meaning": "Person who scores 8 in something (10-pointer in acads or achiever in life)",
        "category": "achievement_descriptor",
        "frequency": 2,
        "weight": 0.6
    },
    "Hapa_Hap": {
        "term": "Hapa-Hap / Hapak ke / Hathad ke",
        "meaning": "Lots and lots of; used as intensifier",
        "category": "intensifier",
        "frequency": 2,
        "weight": 0.4
    },
    "Sutta_Maal": {
        "term": "Sutta / Maal / Khamba",
        "meaning": "Cigarette / Joint / Liquor bottle",
        "category": "campus_contraband",
        "frequency": 2,
        "weight": 0.3
    },
    "Bandi": {
        "term": "Bandi",
        "meaning": "Female student; 'rarest species of IITK'",
        "category": "gender_reference",
        "frequency": 2,
        "weight": 0.4
    },
    "Lassu": {
        "term": "Lassu / Lasna",
        "meaning": "Flirt; one who hangs around girls' hostel; to flirt",
        "category": "personality_descriptor",
        "frequency": 2,
        "weight": 0.4
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# ASSEMBLE FINAL JSON
# ─────────────────────────────────────────────────────────────────────────────
output = {
    "metadata": {
        "source": "IITK Campus Lingo.pdf",
        "extraction_date": "2026-09-01",
        "total_characters_extracted": 10040,
        "total_lines_extracted": 230,
        "description": "Structured extraction of IITK-specific terminology, course codes, PoR titles, programs, organizations, and campus slang. Weights (0.0-1.0) reflect a combination of frequency in source text and importance/relevance to IITK resume evaluation.",
        "weight_schema": "0.0=negligible, 0.5=moderate, 0.75=important, 0.9+=critical",
        "categories": [
            "branch_codes",
            "por_terms",
            "programs",
            "clubs_and_organizations",
            "academic_terminology",
            "campus_places",
            "campus_slang"
        ]
    },
    "branch_codes": course_codes,
    "por_terms": por_terms,
    "programs": programs,
    "clubs_and_organizations": clubs_orgs,
    "academic_terminology": academic_terms,
    "campus_places": campus_places,
    "campus_slang": campus_slang,
    "summary_stats": {
        "total_branch_codes": len(course_codes),
        "total_por_terms": len(por_terms),
        "total_programs": len(programs),
        "total_clubs_orgs": len(clubs_orgs),
        "total_academic_terms": len(academic_terms),
        "total_campus_places": len(campus_places),
        "total_slang_terms": len(campus_slang),
        "total_entities": (
            len(course_codes) + len(por_terms) + len(programs) +
            len(clubs_orgs) + len(academic_terms) + len(campus_places) +
            len(campus_slang)
        )
    }
}

out_path = "iitk_lingo_extracted.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Written: {out_path}")
print(f"Summary stats: {json.dumps(output['summary_stats'], indent=2)}")

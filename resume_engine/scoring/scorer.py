"""Role-Conditioned Competency Scorer.

Calculates grounded, normalized 0-100 scores based on:
1. Evidence saturation across required & preferred skills.
2. Strict "Zero-Evidence, Zero-Score" programmatic rule.
3. Academic gating (CPI vs benchmark, Olympiads, JEE).
4. PoRs & Leadership impact.
5. Embedded Link detection (GitHub for SDE, Portfolio for PM).
6. Penalties (multi-page SPO violation, missing GitHub for SDE, low CPI for Quant).
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from resume_engine.evidence.models import EvidenceBundle, AcademicMetric
from resume_engine.ontology.roles import RoleRequirement
from resume_engine.parser.models import LinkObject


class CompetencyBreakdown(BaseModel):
    name: str
    weight: float
    raw_score: float  # 0.0 to 1.0
    weighted_score: float  # raw_score * weight * 100
    evidence_claims: List[str] = Field(default_factory=list)


class RoleScore(BaseModel):
    role_id: str
    score: float  # 0.0 to 100.0
    overall_score: float  # mirror for backward compatibility
    tier: str  # Strong Alignment, Moderate Fit, Significant Gaps
    competencies: List[CompetencyBreakdown] = Field(default_factory=list)
    penalties_applied: List[str] = Field(default_factory=list)
    bonuses_applied: List[str] = Field(default_factory=list)


class RoleScorer:
    """Computes transparent, explainable role alignment scores with gradient evidence evaluation."""

    def score(
        self,
        evidence: EvidenceBundle,
        role: RoleRequirement,
        link_objects: Optional[List[LinkObject]] = None,
    ) -> RoleScore:
        links = link_objects or []
        has_github = any(l.link_type == "github" for l in links)
        has_linkedin = any(l.link_type == "linkedin" for l in links)
        has_cp_profile = any(l.link_type in ["codeforces", "leetcode"] for l in links)
        
        has_surge = any("SURGE" in e for e in evidence.all_entities)
        has_pors = any(ce.category == "por_role" or ce.category == "council" for ce in evidence.campus_entities)
        quant_metric_count = sum(1 for c in evidence.claims if c.has_quantifiable_impact)

        candidate_skills = set(evidence.all_skills)
        competency_breakdowns: List[CompetencyBreakdown] = []

        total_weighted_points = 0.0
        BASE_MAX_SCORE = 85.0

        for comp_name, comp_weight in role.competency_weights.items():
            raw_val = 0.0
            comp_claims: List[str] = []

            # ── 1. SDE Competency Mapping & Gradient Evaluation ────────────
            if role.role_id == "sde":
                if "algorithms" in comp_name or "dsa" in comp_name:
                    CP_SIGNALS = [
                        r"\b(codeforces|leetcode|codechef|starters|div\.?\s*2|expert|rating|contest|icpc|atcoder)\b",
                        r"\b(dsa|algorithms?|data structures?|dijkstra|huffman|sorting|insertion sort|graphs?|trees?|dynamic programming|greedy|bfs|dfs|shortest path|mst|binary search|trie|segment tree)\b",
                        r"\b(mips|processor|assembler|custom isa|interpreter|compiler|cs210|cs 210|cs345|cs 345|esc101)\b",
                    ]
                    matched = candidate_skills.intersection({"algorithms", "dsa", "data structures", "c++", "cpp", "python", "mips", "assembly", "cs210", "cs 210", "cs345", "cs 345", "esc101"})
                    cp_claims = []
                    proj_algo_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        is_cp = bool(re.search(r"\b(codeforces|leetcode|codechef|starters|div\.?\s*2|expert|rating|contest|icpc|atcoder)\b", text_lower, re.I))
                        is_algo = any(re.search(pat, text_lower, re.I) for pat in CP_SIGNALS) or any(s in c.skills_matched for s in matched)
                        if is_cp:
                            cp_claims.append(c.text_snippet)
                        elif is_algo:
                            proj_algo_claims.append(c.text_snippet)
                    comp_claims = (cp_claims + proj_algo_claims)[:6]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        # Gradient: 1.0 for CF Expert / ICPC; 0.75 for CF Specialist/Custom ISA; 0.50 for standard academic BFS/sorting; 0.25 coursework
                        if re.search(r"\b(expert|candidate master|icpc|round \d+|global rank [1-9]\d{0,2}\b|optiver)\b", text_all):
                            raw_val = 1.0
                        elif re.search(r"\b(codeforces|codechef|atcoder|mips|processor|custom isa|interpreter|compiler)\b", text_all):
                            raw_val = 0.75
                        elif re.search(r"\b(dijkstra|bfs|dfs|sorting|huffman|shortest path|mst|binary search|cs210|cs 210|cs345)\b", text_all):
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "git" in comp_name or "open_source" in comp_name:
                    OS_SIGNALS = [
                        r"\b(open[- ]source|foss|linux foundation|openprinting|zephyr (?:rtos|project)?|github|gitlab|pull request|pr\b|contributor)\b"
                    ]
                    OS_ENTITIES = {"Linux Foundation", "OpenPrinting", "Zephyr"}
                    OS_SKILLS = {"git", "docker", "open source", "open-source", "linux", "bash"}
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        has_sig = any(re.search(pat, text_lower, re.I) for pat in OS_SIGNALS)
                        has_sk = any(s in c.skills_matched for s in OS_SKILLS)
                        has_ent = any(e in c.entities_matched for e in OS_ENTITIES)
                        if has_sig or has_sk or has_ent:
                            comp_claims.append(c.text_snippet)
                    if has_github:
                        comp_claims.append("Verified GitHub profile hyperlink in Header")
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(linux foundation|openprinting|zephyr|pull request|core contributor)\b", text_all):
                            raw_val = 0.95
                        elif has_github and len(comp_claims) > 1:
                            raw_val = 0.75
                        elif has_github:
                            raw_val = 0.50
                        else:
                            raw_val = 0.30

                elif "system_design" in comp_name or "architecture" in comp_name:
                    SD_SIGNALS = [
                        r"\b(system design|architecture|real[- ]time|caching|indexing|load balancing|rest api|microservices|distributed|database|postgresql|express|node\.?js|docker|kubernetes|kafka|redis|high availability|concurrency)\b"
                    ]
                    matched = candidate_skills.intersection({"system design", "docker", "kubernetes", "aws", "fastapi", "django", "react", "node.js", "express", "postgresql", "rest api"})
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in SD_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        # Gradient: 0.95 for distributed/docker/cloud; 0.75 for full-stack API/DB; 0.50 for collegiate OOP; 0.25 basic
                        if re.search(r"\b(distributed|microservices?|kubernetes|high concurrency|throughput|load balanc|docker compose|containerized|dockerfiles?|aws|cloud infrastructure)\b", text_all):
                            raw_val = 0.95
                        elif re.search(r"\b(django|fastapi|express|rest api|spring boot|postgresql|mongodb|mysql|full[- ]stack)\b", text_all):
                            raw_val = 0.75
                        elif re.search(r"\b(oop|object[- ]oriented|file handling|gui|tkinter|course project|rental system|management system)\b", text_all):
                            raw_val = 0.50
                        else:
                            raw_val = 0.30

                elif "project_complexity" in comp_name or "projects" in comp_name:
                    PROJ_SIGNALS = [
                        r"\b(processor|single-cycle|custom isa|assembler|full[- ]stack|backend|pipeline|distributed|concurrency|database|rest api|team of \d+)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        in_proj_sec = "project" in c.section.lower()
                        has_sig = any(re.search(pat, text_lower, re.I) for pat in PROJ_SIGNALS)
                        if in_proj_sec or has_sig:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(deployed|production|scale|real-time alerts?|active users|team of \d+|custom isa|processor)\b", text_all):
                            raw_val = 0.85
                        elif re.search(r"\b(full[- ]stack|app|database|pipeline|backend)\b", text_all):
                            raw_val = 0.65
                        elif re.search(r"\b(course project|mini[- ]project|simulation)\b", text_all):
                            raw_val = 0.50
                        else:
                            raw_val = 0.30

                elif "programming" in comp_name or "languages" in comp_name:
                    matched = candidate_skills.intersection({"python", "c++", "cpp", "c", "java", "rust", "golang", "sql", "verilog", "assembly"})
                    comp_claims = [c.text_snippet for c in evidence.claims if any(s in c.skills_matched for s in matched)][:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        has_systems_lang = bool(re.search(r"\b(rust|golang|verilog|mips|assembly)\b", text_all))
                        if len(matched) >= 4 and has_systems_lang:
                            raw_val = 0.95
                        elif len(matched) >= 3:
                            raw_val = 0.75
                        elif len(matched) >= 2:
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "cpi" in comp_name or "academic" in comp_name:
                    if evidence.is_scrap or (evidence.cpi is not None and evidence.cpi == 0.0):
                        comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0 (Scrap / Zero CPI)" if evidence.cpi is not None else "Scrap Resume Content"]
                        raw_val = 0.0
                    elif evidence.cpi is not None:
                        comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0"]
                        if evidence.cpi >= 9.2:
                            raw_val = 1.0
                        elif evidence.cpi >= 8.5:
                            raw_val = 0.88
                        elif evidence.cpi >= 7.5:
                            raw_val = 0.75
                        elif evidence.cpi >= 6.5:
                            raw_val = 0.60
                        elif evidence.cpi >= 5.0:
                            raw_val = 0.45
                        else:
                            raw_val = 0.15
                    else:
                        for m in evidence.academic_metrics:
                            comp_claims.append(f"{m.name}: {m.value}")
                        if comp_claims:
                            raw_val = 0.60

            # ── 2. Quant Role Competency Mapping & Gradient Evaluation ─────
            elif role.role_id == "quant":
                if "mathematical" in comp_name or "rigor" in comp_name:
                    MATH_SIGNALS = [
                        r"\b(inmo|rmo|ioqm|inpho|incho|isi|kvpy|jee advanced|mathematical olympiad)\b",
                        r"\b(probability|linear algebra|stochastic|calculus|differential equations|game complexity|quantum query|co-integration|augmented-dickey-fuller|stationary|statistics|real analysis)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in MATH_SIGNALS) or any(e in c.entities_matched for e in {"INMO", "RMO", "IOQM", "INPhO", "INChO", "ISI", "KVPY"}):
                            comp_claims.append(c.text_snippet)
                    if evidence.academic_metrics:
                        for m in evidence.academic_metrics:
                            if any(k in m.name.lower() for k in ["jee advanced", "kvpy", "iiser"]):
                                comp_claims.append(f"{m.name}: {m.value}")
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        # Strict Olympiad: INMO, RMO, IOQM, IMO, Putnam, or top ISI rank
                        if re.search(r"\b(inmo|rmo|ioqm|imo|putnam)\b", text_all) or re.search(r"\bisi\b.*\b(rank|top \d+|entrance|b\.?stat|m\.?stat)\b", text_all) or "INMO" in [e.upper() for c in evidence.claims for e in c.entities_matched]:
                            raw_val = 1.0
                        elif re.search(r"\b(kvpy|inpho|incho)\b", text_all):
                            raw_val = 0.85
                        elif "jee advanced" in text_all:
                            # Check JEE Advanced rank
                            rank_match = re.search(r"air\s*(\d+)", text_all) or re.search(r"rank\s*(\d+)", text_all)
                            if rank_match:
                                r_val = int(rank_match.group(1))
                                if r_val <= 250:
                                    raw_val = 0.90
                                elif r_val <= 1000:
                                    raw_val = 0.78
                                elif r_val <= 3000:
                                    raw_val = 0.65
                                else:
                                    raw_val = 0.45
                            else:
                                raw_val = 0.65
                        elif re.search(r"\b(probability|stochastic|differential equations|discrete math|game complexity)\b", text_all):
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "algorithmic" in comp_name or "problem_solving" in comp_name:
                    CP_SIGNALS = [
                        r"\b(codeforces|leetcode|codechef|atcoder|starters|div\.?\s*2|expert|rating|contest|icpc|hackathon|trade-a-thon|optiver|pairs trading|mean reversal|algorithmic trading|nifty|sharpe|quantanalytics|dsa|algorithms?|data structures?)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in CP_SIGNALS):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        has_cf_exp = re.search(r"\b(candidate master|grandmaster|international grandmaster|optiver|rank 1|trade-a-thon)\b", text_all) or (
                            re.search(r"\bexpert\b", text_all) and not re.search(r"\b(subject matter expert|domain expert)\b", text_all)
                        ) or bool(re.search(r"\brating\s*(?:of|:)?\s*(1[6-9]\d{2}|[2-3]\d{3})\b", text_all))
                        
                        if has_cf_exp:
                            raw_val = 1.0
                        elif re.search(r"\b(codeforces|codechef|algorithmic trading|nifty|sharpe|pairs trading)\b", text_all):
                            raw_val = 0.75
                        elif re.search(r"\b(dsa|algorithms?|data structures?|hackathon)\b", text_all):
                            raw_val = 0.50
                        else:
                            raw_val = 0.25

                elif "quantitative" in comp_name or "modeling" in comp_name:
                    MODEL_SIGNALS = [
                        r"\b(pairs trading|mean reversal|augmented-dickey-fuller|backtested|blueshift|co-integration|stochastic|probability|linear algebra|monte carlo|black scholes|time series|arima|garch|volatility|sharpe ratio|sortino|portfolio optimization|markowitz|statistical arbitrage|derivatives|hedging|econometric|nifty|risk modeling)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in MODEL_SIGNALS) or any(s in c.skills_matched for s in {"pairs trading", "backtesting", "probability", "statistics", "stochastic calculus", "linear algebra"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        # Gradient: 0.95 for real backtested quant models or mathematical proofs; 0.70 for statistical/econometric modeling; 0.40 for basic probability
                        if re.search(r"\b(pairs trading|augmented-dickey-fuller|backtested|blueshift|sharpe ratio|nifty|quantum query|game complexity|black scholes|monte carlo|portfolio optimization|statistical arbitrage)\b", text_all):
                            raw_val = 0.95
                        elif re.search(r"\b(time series|arima|garch|stochastic|markowitz|volatility|linear regression|econometrics|derivatives)\b", text_all):
                            raw_val = 0.70
                        elif re.search(r"\b(probability|statistics|linear algebra|hypothesis testing)\b", text_all):
                            raw_val = 0.45
                        else:
                            raw_val = 0.30

                elif "speed" in comp_name or "programming" in comp_name:
                    matched = candidate_skills.intersection({"python", "c++", "cpp", "c", "java", "sql", "bash", "verilog", "mips"})
                    comp_claims = [c.text_snippet for c in evidence.claims if any(s in c.skills_matched for s in matched) or any(sig in c.text_snippet.lower() for sig in ["codeforces", "atcoder", "codechef"])][:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(mips|verilog|assembly|c\+\+|cpp)\b", text_all) and re.search(r"\b(codeforces|atcoder|codechef)\b", text_all):
                            raw_val = 0.90
                        elif len(matched) >= 3:
                            raw_val = 0.75
                        elif len(matched) >= 2:
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "cpi" in comp_name or "academic" in comp_name:
                    if evidence.cpi is not None:
                        comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0"]
                        if evidence.cpi >= 9.5:
                            raw_val = 1.0
                        elif evidence.cpi >= 9.0:
                            raw_val = 0.88
                        elif evidence.cpi >= 8.5:
                            raw_val = 0.75
                        elif evidence.cpi >= 8.0:
                            raw_val = 0.55
                        else:
                            raw_val = 0.30
                    else:
                        for m in evidence.academic_metrics:
                            comp_claims.append(f"{m.name}: {m.value}")
                        if comp_claims:
                            raw_val = 0.60

            # ── 3. Core Role Competency Mapping & Gradient Evaluation ──────
            elif role.role_id == "core":
                if "core_domain" in comp_name or "domain" in comp_name:
                    CORE_DOMAIN_SIGNALS = [
                        r"\b(manufacturing|fabrication|lathing|milling|3d printing|cnc|torque|assembly|machining|hardware|robotics|circuits?|vlsi|cadence|matlab|solidworks|ansys|autocad|simulink|verilog|cfd|fea|ros|aerodynamics|finite element|kinematics|thermodynamics|propulsion|structures?)\b"
                    ]
                    matched = candidate_skills.intersection({"matlab", "solidworks", "ansys", "autocad", "simulink", "verilog", "cfd", "fea", "ros", "labview", "embedded c", "pcb design", "vhdl", "fpga"})
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in CORE_DOMAIN_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(surge|vlsi|cadence|ansys|solidworks|cfd|fea|aerodynamics|robotics)\b", text_all):
                            raw_val = 0.85
                        elif len(matched) >= 2 or len(comp_claims) >= 2:
                            raw_val = 0.70
                        else:
                            raw_val = 0.45

                elif "research" in comp_name or "internships" in comp_name:
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        is_intern_section = c.section in ("Work Experience", "Experience", "Internship", "Internships", "Research Experience", "Key Projects", "Projects")
                        has_intern_keyword = any(k in text_lower for k in ["surge", "research", "intern", "internship", "r&d", "laboratory", "ugp", "btp", "course project", "b.tech project", "publication", "patent"])
                        if is_intern_section or has_intern_keyword:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(surge|intern|internship|r&d|publication|patent)\b", text_all):
                            raw_val = 0.85
                        elif len(comp_claims) >= 2:
                            raw_val = 0.65
                        else:
                            raw_val = 0.45

                elif "engineering_tools" in comp_name or comp_name == "engineering_tools_cad_matlab":
                    matched = candidate_skills.intersection({"matlab", "solidworks", "ansys", "autocad", "simulink", "verilog", "cfd", "fea", "ros", "labview", "altium", "catia", "kicad", "creo", "fusion 360", "abaqus", "comsol"})
                    TOOL_SIGNALS = [r"\b(labview|ni-opc|solidworks|autocad|catia|ansys|simulink|matlab|cnc|3d printing|xilinx|spartan|verilog|vhdl|altium|kicad|creo|abaqus|comsol)\b"]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in TOOL_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        if len(matched) >= 2 or len(comp_claims) >= 2:
                            raw_val = 0.75
                        else:
                            raw_val = 0.50

                elif "prototyping" in comp_name or "hands_on" in comp_name:
                    PROTO_SIGNALS = [r"\b(fabrication|lathing|milling|3d printing|cnc|assembly|automation|prototyping|hardware|motor|actuator|sensor|circuit|pcb|breadboard|soldering|chassis|dynamometer)\b"]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in PROTO_SIGNALS):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        raw_val = 0.80 if len(comp_claims) >= 2 else 0.50

                elif "cpi" in comp_name or "academic" in comp_name or "foundation" in comp_name:
                    if evidence.cpi is not None:
                        comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0"]
                        if evidence.cpi >= 9.0:
                            raw_val = 0.90
                        elif evidence.cpi >= role.min_cpi_benchmark:
                            raw_val = 0.70
                        else:
                            raw_val = 0.40
                    else:
                        for m in evidence.academic_metrics:
                            comp_claims.append(f"{m.name}: {m.value}")
                        if comp_claims:
                            raw_val = 0.60

            # ── 4. Consulting & Management Role ────────────────────────────
            elif "leadership" in comp_name or "pors" in comp_name or "cross_functional_leadership" in comp_name:
                LEADERSHIP_SIGNALS = {
                    "led", "leading", "managed", "co-convened", "convened", "coordinated", "mentored",
                    "organized", "organised", "spearheaded", "directed", "founded",
                    "headed", "oversaw", "supervised", "team of", "budget of", "convenor", "coordinator",
                }
                LEADERSHIP_ENTITIES = {
                    "Debating Society", "NSS", "BCS IITK", "ESummit", "Techkriti",
                    "Antaragni", "Udghosh", "Gymkhana", "Programming Club",
                }
                comp_claims = []
                for c in evidence.claims:
                    text_lower = c.text_snippet.lower()
                    has_leadership_verb = any(sig in text_lower for sig in LEADERSHIP_SIGNALS)
                    has_leadership_entity = any(e in c.entities_matched for e in LEADERSHIP_ENTITIES)
                    has_por_section = c.section in ("Positions of Responsibility", "Responsibilities", "Leadership")
                    if has_leadership_verb or (has_leadership_entity and has_por_section):
                        comp_claims.append(c.text_snippet)
                comp_claims = comp_claims[:4]
                if comp_claims:
                    por_count = sum(1 for ce in evidence.campus_entities if ce.category in ["por_role", "council", "club"])
                    text_all = " ".join(comp_claims).lower()
                    if por_count >= 2 and re.search(r"\b(spearheaded|overall coordinator|head|manager|team of \d+)\b", text_all):
                        raw_val = 0.85
                    elif por_count >= 1:
                        raw_val = 0.70
                    else:
                        raw_val = 0.45

            elif "communication" in comp_name or "extracurriculars" in comp_name:
                COMM_SIGNALS = {"debate", "debating", "speaker", "adjudicator", "music", "piano", "dance", "drama", "quiz", "literary", "sport", "athletics", "tournament", "cultural", "oratorix", "inter-iit"}
                comp_claims = []
                for c in evidence.claims:
                    text_lower = c.text_snippet.lower()
                    if any(sig in text_lower for sig in COMM_SIGNALS):
                        comp_claims.append(c.text_snippet)
                comp_claims = comp_claims[:4]
                if comp_claims:
                    raw_val = 0.75 if len(comp_claims) >= 2 else 0.45

            elif "business" in comp_name or "impact" in comp_name or "quantifiable" in comp_name:
                comp_claims = [c.text_snippet for c in evidence.claims if c.has_quantifiable_impact][:4]
                if comp_claims:
                    text_all = " ".join(comp_claims).lower()
                    if re.search(r"\b(vc|pre[- ]seed|funding|lakh|crore|roi|revenue|drawdown)\b", text_all):
                        raw_val = 0.90
                    elif len(comp_claims) >= 3:
                        raw_val = 0.70
                    else:
                        raw_val = 0.45

            # ── 5. Data Analyst Role (Refined 6-Dimension Framework) ────────
            elif role.role_id == "analyst":
                if "sql" in comp_name or "data_manipulation" in comp_name:
                    SQL_SIGNALS = [
                        r"\b(sql|mysql|postgresql|sqlite|cte|ctes|window functions?|partition by|row_number|dense_rank|rank\(\)|inner join|left join|group by|having|subquer(?:y|ies)|database queries|complex queries)\b",
                        r"\b(pandas|dataframe|data manipulation|data cleaning|data wrangling|etl pipeline)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in SQL_SIGNALS) or "sql" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(window functions?|partition by|cte|ctes|row_number|postgresql|complex queries|optimized queries)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(sql|mysql|inner join|left join|group by|having|queries)\b", t_all):
                            raw_val = 0.80
                        elif re.search(r"\b(pandas|dataframe|data cleaning|wrangling)\b", t_all):
                            raw_val = 0.60
                        else:
                            raw_val = 0.35

                elif "statistics" in comp_name or "experimentation" in comp_name:
                    STAT_SIGNALS = [
                        r"\b(a/b testing|hypothesis test(?:ing)?|t-test|z-test|p-value|chi-square|anova|inferential statistics|descriptive statistics|confidence interval|regression analysis|scipy|statsmodels)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in STAT_SIGNALS) or any(s in c.skills_matched for s in {"statistics", "a/b testing"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(a/b test(?:ing)?|hypothesis test(?:ing)?|p-value|significance|experimentation)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(regression|inferential|chi-square|anova|statsmodels|scipy)\b", t_all):
                            raw_val = 0.80
                        elif re.search(r"\b(statistics|descriptive|distributions?|variance|mean)\b", t_all):
                            raw_val = 0.60
                        else:
                            raw_val = 0.35

                elif "visualization" in comp_name or "reporting" in comp_name:
                    DASH_SIGNALS = [
                        r"\b(tableau|power bi|powerbi|rshiny|streamlit|dashboard|dashboards|executive reporting|kpi reporting|matplotlib|seaborn|plotly|data visualization)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in DASH_SIGNALS) or any(s in c.skills_matched for s in {"tableau", "power bi", "powerbi", "rshiny"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(tableau|power bi|powerbi|interactive dashboard|drill-down)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(dashboard|streamlit|rshiny|reporting)\b", t_all):
                            raw_val = 0.75
                        elif re.search(r"\b(matplotlib|seaborn|plotly|visualiz(?:ation|ed))\b", t_all):
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "python" in comp_name or "analytics_tooling" in comp_name:
                    TOOL_SIGNALS = [
                        r"\b(python|pandas|numpy|r language|\br\b|jupyter|etl|data pipeline|scraping|scraped|data wrangling|data cleaning)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in TOOL_SIGNALS) or any(s in c.skills_matched for s in {"python", "pandas", "numpy", "r"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(pipeline|etl|automated|cleaning pipeline|data wrangling)\b", t_all):
                            raw_val = 0.90
                        elif re.search(r"\b(pandas|numpy|python|r)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "business_insight" in comp_name:
                    BIZ_SIGNALS = [
                        r"\b(recommendation|strategic decision|root cause|anomaly|business question|actionable insight|kpi drivers|churn reduction|cost reduction|revenue optimization|client findings)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in BIZ_SIGNALS) or (c.has_quantifiable_impact and any(k in t_low for k in ["business", "cost", "revenue", "user", "client"])):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(decision|recommendation|strategic|churn|actionable)\b", t_all):
                            raw_val = 0.90
                        elif re.search(r"\b(kpi|revenue|cost|metric|business)\b", t_all):
                            raw_val = 0.70
                        else:
                            raw_val = 0.45

                elif "quantified_impact" in comp_name or "communication" in comp_name:
                    comp_claims = [c.text_snippet for c in evidence.claims if c.has_quantifiable_impact and any(k in c.text_snippet.lower() for k in ["rows", "records", "users", "dataset", "%", "hours", "inr", "kpi"])][:4]
                    if comp_claims:
                        raw_val = 0.90 if len(comp_claims) >= 2 else 0.65

            # ── 6. Product Manager Role (Refined 6-Dimension Framework) ──────
            elif role.role_id == "product":
                if "execution" in comp_name or "cross_functional" in comp_name:
                    EXEC_SIGNALS = [
                        r"\b(shipped|launched|mvp|cross-functional|engineering and design|founder|co-founder|sprint|agile|scrum|jira|stakeholder management|leadership|managed team)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in EXEC_SIGNALS) or any(ce.category in ["por_role", "council"] for ce in evidence.campus_entities):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(shipped|launched|mvp|co-founder|founder)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(cross-functional|sprint|agile|scrum|jira|engineering and design)\b", t_all):
                            raw_val = 0.80
                        else:
                            raw_val = 0.55

                elif "product_thinking" in comp_name or "problem_framing" in comp_name:
                    PRD_SIGNALS = [
                        r"\b(prd|product requirement|problem statement|problem framing|value proposition|user stories|product teardown|customer journey|feature specification|product strategy)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in PRD_SIGNALS) or "prd" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(prd|product requirement|value proposition|problem framing)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(user stories|customer journey|product strategy|product teardown)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "user_research" in comp_name or "customer_insights" in comp_name:
                    UX_SIGNALS = [
                        r"\b(user research|customer interviews?|user testing|usability testing|customer discovery|surveys?|personas?|wireframing|figma|wireframe|user feedback)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in UX_SIGNALS) or any(s in c.skills_matched for s in {"figma", "wireframing", "user research"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(customer interviews?|user testing|usability testing|customer discovery)\b", t_all) and "figma" in t_all:
                            raw_val = 1.0
                        elif re.search(r"\b(user research|interviews?|figma|wireframing)\b", t_all):
                            raw_val = 0.80
                        else:
                            raw_val = 0.50

                elif "prioritization" in comp_name or "roadmapping" in comp_name:
                    PRIOR_SIGNALS = [
                        r"\b(prioritization|prioritized|roadmap|roadmapping|rice framework|moscow|value vs effort|backlog|feature roadmap|product milestones)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in PRIOR_SIGNALS) or "product roadmap" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(rice|moscow|value vs effort|prioritization framework)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(roadmap|prioritized|milestones|backlog)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "product_analytics" in comp_name or "experimentation" in comp_name:
                    ANALYTICS_SIGNALS = [
                        r"\b(a/b testing|funnel analysis|conversion rate|retention|churn|mixpanel|amplitude|google analytics|posthog|product metrics|activation)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in ANALYTICS_SIGNALS) or "a/b testing" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(funnel analysis|conversion rate|retention|a/b testing)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(mixpanel|amplitude|google analytics|product metrics)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "business_impact" in comp_name:
                    comp_claims = [c.text_snippet for c in evidence.claims if c.has_quantifiable_impact and any(k in c.text_snippet.lower() for k in ["users", "dau", "mau", "adoption", "retention", "conversion", "revenue", "nps", "%"])][:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(adoption|retention|conversion|revenue|dau|mau)\b", t_all):
                            raw_val = 0.95
                        else:
                            raw_val = 0.70

            # ── 7. Investment Banking (NEW 7-Dimension Framework) ───────────
            elif role.role_id == "ib":
                if "financial_modeling" in comp_name:
                    MODEL_SIGNALS = [
                        r"\b(three-statement|3-statement|financial model|financial modeling|working capital schedule|debt schedule|scenario analysis|sensitivity analysis|forecasted revenue|projections)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in MODEL_SIGNALS) or any(s in c.skills_matched for s in {"three-statement model", "financial modeling"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(three-statement|3-statement|dynamic model|scenario analysis|debt schedule)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(financial model|forecasted|working capital|projections)\b", t_all):
                            raw_val = 0.80
                        else:
                            raw_val = 0.50

                elif "valuation" in comp_name or "dcf" in comp_name:
                    VAL_SIGNALS = [
                        r"\b(dcf|discounted cash flow|wacc|terminal value|trading comps|comparable company|precedent transactions?|ev/ebitda|p/e multiple|lbo|gordon growth)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in VAL_SIGNALS) or any(s in c.skills_matched for s in {"dcf", "valuation", "trading comps", "precedent transactions"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(dcf|discounted cash flow)\b", t_all) and re.search(r"\b(comps|comparable|precedent|wacc)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(dcf|discounted cash flow|wacc|trading comps|precedent)\b", t_all):
                            raw_val = 0.80
                        elif re.search(r"\b(valuation|ev/ebitda|multiples?)\b", t_all):
                            raw_val = 0.55
                        else:
                            raw_val = 0.35

                elif "accounting" in comp_name or "financial_statements" in comp_name:
                    ACCT_SIGNALS = [
                        r"\b(balance sheet|income statement|cash flow statement|10-k|10-q|annual report|ebitda|working capital|capital structure|ratio analysis|sec filings?|us gaap|ifrs)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in ACCT_SIGNALS) or any(s in c.skills_matched for s in {"accounting", "balance sheet", "income statement", "cash flow statement"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(10-k|10-q|sec filing|annual report|capital structure)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(balance sheet|income statement|cash flow|ebitda|working capital)\b", t_all):
                            raw_val = 0.80
                        else:
                            raw_val = 0.50

                elif "transaction" in comp_name or "m_and_a" in comp_name:
                    DEAL_SIGNALS = [
                        r"\b(m&a|mergers? and acquisitions?|accretion/dilution|merger model|pitch book|pitchbook|information memorandum|cim|fairness opinion|deal structuring|transaction)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in DEAL_SIGNALS) or any(s in c.skills_matched for s in {"m&a", "pitch book"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(accretion/dilution|merger model|pitch book|cim|deal structur)\b", t_all):
                            raw_val = 1.0
                        elif re.search(r"\b(m&a|mergers? and acquisitions?|transaction)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "excel" in comp_name:
                    EXCEL_SIGNALS = [
                        r"\b(advanced excel|financial excel|index/match|xlookup|sensitivity table|data table|vba|macro|financial modeling in excel)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in EXCEL_SIGNALS) or "excel" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(sensitivity table|index/match|data table|dynamic financial model)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(excel|vlookup|xlookup|macros?)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.45

                elif "company" in comp_name or "industry_research" in comp_name:
                    RES_SIGNALS = [
                        r"\b(equity research|industry report|company profile|competitor benchmarking|macro trends?|market sizing|bloomberg|capiq|factset)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        t_low = c.text_snippet.lower()
                        if any(re.search(pat, t_low, re.I) for pat in RES_SIGNALS) or "equity research" in c.skills_matched:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        t_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(equity research|published report|bloomberg|capiq)\b", t_all):
                            raw_val = 0.95
                        elif re.search(r"\b(industry report|competitor benchmarking|company profile)\b", t_all):
                            raw_val = 0.75
                        else:
                            raw_val = 0.50

                elif "communication" in comp_name or "deadline" in comp_name:
                    COMM_SIGNALS = [
                        r"\b(pitch deck|board presentation|cfa research challenge|finance competition|investment banking competition|senior bankers|executive presentation)\b"
                    ]
                    comp_claims = [c.text_snippet for c in evidence.claims if any(re.search(pat, c.text_snippet.lower(), re.I) for pat in COMM_SIGNALS)][:4]
                    if comp_claims:
                        raw_val = 0.90 if len(comp_claims) >= 2 else 0.65

            # ── 7. Universal Academic / CPI Fallback ────────────────────────
            elif "cpi" in comp_name or "academic" in comp_name or "pedigree" in comp_name or "rigor" in comp_name or "foundation" in comp_name or "consistency" in comp_name:
                if evidence.is_scrap or (evidence.cpi is not None and evidence.cpi == 0.0):
                    comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0 (Scrap / Zero CPI)" if evidence.cpi is not None else "Scrap Resume Content"]
                    raw_val = 0.0
                elif evidence.cpi is not None:
                    comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0"]
                    if evidence.cpi >= 9.0:
                        raw_val = 0.90
                    elif evidence.cpi >= role.min_cpi_benchmark:
                        raw_val = 0.75
                    elif evidence.cpi >= 6.5:
                        raw_val = 0.60
                    elif evidence.cpi >= 5.0:
                        raw_val = 0.45
                    else:
                        raw_val = 0.15
                else:
                    for m in evidence.academic_metrics:
                        comp_claims.append(f"{m.name}: {m.value}")
                    if comp_claims:
                        raw_val = 0.60

            else:
                req_matched = candidate_skills.intersection(set(role.required_skills))
                comp_claims = [c.text_snippet for c in evidence.claims if any(s in c.skills_matched for s in req_matched)][:4]
                if comp_claims:
                    raw_val = min(len(req_matched) / max(len(role.required_skills) * 0.5, 1.0), 0.75)

            # ── Strict Zero-Evidence Rule & 85-Base Scaling ───────────────
            if len(comp_claims) == 0:
                raw_val = 0.0
                weighted_pts = 0.0
            else:
                raw_val = round(max(0.05, min(raw_val, 1.0)), 3)
                weighted_pts = raw_val * comp_weight * BASE_MAX_SCORE

            total_weighted_points += weighted_pts

            competency_breakdowns.append(
                CompetencyBreakdown(
                    name=comp_name,
                    weight=comp_weight,
                    raw_score=raw_val,
                    weighted_score=round(weighted_pts, 2),
                    evidence_claims=comp_claims,
                )
            )

        # ── Outlier Bonuses (Max 15.0 pts total) ──────────────────────
        base_score = total_weighted_points
        bonuses: List[str] = []
        outlier_bonus = 0.0

        # 1. Academic Excellence / CPI Outlier
        if evidence.cpi is not None:
            if evidence.cpi >= 9.8:
                outlier_bonus += 5.0
                bonuses.append(f"Top 0.5% CPI ({evidence.cpi:.2f}/10.0) Academic Outlier (+5 pts)")
            elif evidence.cpi >= 9.5:
                outlier_bonus += 3.0
                bonuses.append(f"Top 2% CPI ({evidence.cpi:.2f}/10.0) Academic Outlier (+3 pts)")
            elif evidence.cpi >= 9.2:
                outlier_bonus += 1.5
                bonuses.append(f"High CPI ({evidence.cpi:.2f}/10.0) Honor (+1.5 pts)")

        # 2. Strict National / International Olympiad & Top 250 JEE Advanced Outlier
        has_national_math_olympiad = any(
            bool(re.search(r"\b(inmo|rmo|ioqm|international mathematical olympiad|imo|putnam)\b", c.text_snippet.lower()))
            or bool(re.search(r"\bisi\b.*\b(rank|top \d+|entrance|b\.?stat|m\.?stat)\b", c.text_snippet.lower()))
            or "INMO" in c.entities_matched
            for c in evidence.claims
        )
        has_top_jee_adv = False
        for m in evidence.academic_metrics:
            if "advanced" in m.name.lower():
                rank_match = re.search(r"(\d+)", m.value.replace(",", ""))
                if rank_match and int(rank_match.group(1)) <= 250:
                    has_top_jee_adv = True

        if has_national_math_olympiad:
            outlier_bonus += 5.0
            bonuses.append("National / International Mathematics Olympiad (INMO/RMO/ISI) (+5 pts)")
        elif has_top_jee_adv:
            outlier_bonus += 4.0
            bonuses.append("JEE Advanced Top 250 All India Rank (+4 pts)")

        # 3. Competitive Programming / Trade-a-thon Outlier (Rating-Aware)
        def is_cf_expert_claim(snippet: str) -> bool:
            t = snippet.lower()
            if not any(k in t for k in ["codeforces", "codechef", "atcoder"]):
                return False
            if re.search(r"\b(candidate master|grandmaster|international grandmaster)\b", t):
                return True
            if re.search(r"\bexpert\b", t) and not re.search(r"\b(subject matter expert|domain expert)\b", t):
                return True
            m = re.search(r"\brating\s*(?:of|:)?\s*(\d{4})\b", t)
            if m:
                val = int(m.group(1))
                return 1650 <= val <= 3800
            return False

        has_cf_expert = any(is_cf_expert_claim(c.text_snippet) for c in evidence.claims) or any("expert" in str(getattr(l, "label", "")).lower() for l in links)

        has_optiver_1st = any(
            bool(re.search(r"\b(optiver|trade-a-thon)\b.*\b(rank 1|first position|1st)\b", c.text_snippet.lower()))
            for c in evidence.claims
        )

        if has_cf_expert or has_optiver_1st:
            outlier_bonus += 4.0
            bonuses.append("Elite Competitive Programming / Quantitative Trading Rank 1 (+4 pts)")

        # 4. Deployed Systems / Cloud Scalability / VC Funding Outlier
        has_production_deploy = any(
            bool(re.search(r"\b(vc firm|pre[- ]seed|seed funding|docker compose|kubernetes|aws|active users|production deployment)\b", c.text_snippet.lower()))
            for c in evidence.claims
        )
        if has_production_deploy:
            outlier_bonus += 2.0
            bonuses.append("Production Deployed Systems / Cloud Infrastructure / VC Funding (+2 pts)")

        # 5. Verified GitHub Profile Link (for SDE) with Header Text Fallback
        has_github_link = has_github
        if not has_github_link and evidence.raw_text:
            header_chunk = evidence.raw_text[:400].lower()
            if "github" in header_chunk:
                has_github_link = True

        if role.role_id == "sde" and has_github_link:
            outlier_bonus += 2.0
            bonuses.append("Verified GitHub profile link present (+2 pts)")

        # 6. Consulting "Triple Spike" Outlier (Academics + High-Impact PoR + Sports/Cultural)
        if role.role_id == "consulting":
            has_academic_spike = (evidence.cpi is not None and evidence.cpi >= 7.8) or any(
                "award" in ce.category for ce in evidence.campus_entities
            )
            has_leadership_spike = any(
                ce.category in ["por_role", "council"] for ce in evidence.campus_entities
            ) or any(
                bool(re.search(r"\b(general secretary|overall coordinator|manager|head|convenor|president|senator|secretary)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            has_cult_sports_spike = any(
                bool(re.search(r"\b(inter-iit|galaxy|inferno|antaragni|udghosh|takneek|gold medal|silver medal|bronze medal|debsoc|dramatics|sports|championship)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            if has_academic_spike and has_leadership_spike and has_cult_sports_spike:
                outlier_bonus += 3.0
                bonuses.append("Consulting 'Triple Spike' (Academics + Campus Leadership + Cult/Sports) (+3 pts)")

        # 7. Investment Banking / Finance Competition Outlier
        if role.role_id == "ib":
            has_ib_comp = any(
                bool(re.search(r"\b(cfa research challenge|investment banking challenge|m&a competition|finance challenge)\b.*\b(winner|national finalist|finalist|rank 1|first position)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            has_bb_intern = any(
                bool(re.search(r"\b(goldman sachs|morgan stanley|j\.?p\.? morgan|evercore|lazard|jefferies|avendus)\b.*\b(investment bank|analyst intern|ib intern)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            if has_ib_comp:
                outlier_bonus += 4.0
                bonuses.append("CFA Research Challenge / National M&A Competition Winner/Finalist (+4 pts)")
            elif has_bb_intern:
                outlier_bonus += 3.0
                bonuses.append("Bulge Bracket / Elite Boutique Investment Banking Internship (+3 pts)")

        # Strict capping of outlier bonus at 15.0 pts
        outlier_bonus = min(outlier_bonus, 15.0)

        # ── Apply Role Penalties ───────────────────────────────────────
        penalties: List[str] = []
        final_score = base_score + outlier_bonus

        # Universal CPI & Scrap Penalties (Reduced / Milder Deduction)
        if evidence.is_scrap or (evidence.cpi is not None and evidence.cpi == 0.0):
            final_score -= 15.0
            penalties.append("Zero CPI / Scrap Academic Record detected (-15 pts)")
        elif evidence.cpi is not None and evidence.cpi < 5.0:
            final_score -= 8.0
            penalties.append(f"Academic deficit: CPI {evidence.cpi:.2f}/10.0 below 5.0 probation cutoff (-8 pts)")

        if role.role_id == "sde":
            if not has_github_link:
                final_score -= 6.0
                penalties.append("Missing active GitHub profile link in Header (-6 pts)")

        elif role.role_id == "quant":
            if evidence.cpi and evidence.cpi < 8.0 and not has_cf_expert and not has_optiver_1st:
                final_score -= 5.0
                penalties.append(f"CPI below Quant benchmark of 8.0 (current: {evidence.cpi:.2f}) (-5 pts)")

        elif role.role_id == "consulting":
            if not has_pors:
                final_score -= 8.0
                penalties.append("Lack of prominent campus PoRs / Gymkhana leadership (-8 pts)")
            if quant_metric_count < 3:
                final_score -= 4.0
                penalties.append("Insufficient quantified business metrics across bullets (-4 pts)")

        elif role.role_id == "core":
            if role.penalizes_generic_webdev:
                webdev_skills = {"react", "vue", "angular", "node.js", "django", "flask", "fastapi", "bootstrap", "tailwind", "html", "css"}
                matched_webdev = candidate_skills.intersection(webdev_skills)
                core_tools = {"ansys", "matlab", "solidworks", "autocad", "simulink", "verilog", "cfd", "fea", "catia", "creo", "comsol"}
                matched_core = candidate_skills.intersection(core_tools)
                if len(matched_webdev) >= 2 and len(matched_core) < 2 and not has_surge:
                    final_score -= 5.0
                    penalties.append("Generic web dev projects displacing core engineering electives/lab experience (-5 pts)")

        elif role.role_id == "analyst":
            has_sql_demonstrated = any(
                bool(re.search(r"\b(sql|mysql|postgresql|sqlite|query|queries|cte|window function|select|join)\b", c.text_snippet.lower()))
                for c in evidence.claims if "project" in c.section.lower() or "experience" in c.section.lower()
            )
            if not has_sql_demonstrated and quant_metric_count == 0:
                final_score -= 5.0
                penalties.append("Keyword-heavy tool listing without demonstrated SQL queries or quantifiable business outcomes (-5 pts)")

        elif role.role_id == "product":
            has_user_evidence = any(
                bool(re.search(r"\b(user research|interview|feedback|survey|usability|customer|adoption|retention|dau|mau|nps)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            if not has_user_evidence:
                final_score -= 6.0
                penalties.append("Technical project mislabeled as product without user evidence, customer discovery, or product outcomes (-6 pts)")

        elif role.role_id == "ib":
            has_modeling_or_val = any(
                bool(re.search(r"\b(three-statement|3-statement|financial model|dcf|discounted cash flow|valuation|wacc|comps|precedent transaction|lbo|accretion|dilution)\b", c.text_snippet.lower()))
                for c in evidence.claims
            )
            if not has_modeling_or_val:
                final_score -= 6.0
                penalties.append("Generic finance terms listed without demonstrated financial modeling, DCF valuation, or accounting evidence (-6 pts)")

        final_score = round(max(0.0, min(final_score, 100.0)), 1)

        if final_score >= 75.0:
            tier = "Strong Alignment"
        elif final_score >= 50.0:
            tier = "Moderate Fit"
        else:
            tier = "Significant Gaps"

        return RoleScore(
            role_id=role.role_id,
            score=final_score,
            overall_score=final_score,
            tier=tier,
            competencies=competency_breakdowns,
            penalties_applied=penalties,
            bonuses_applied=bonuses,
        )

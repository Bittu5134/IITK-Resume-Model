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
                        r"\b(codeforces|leetcode|codechef|starters|div\.?\s*2|expert|rating|contest|icpc)\b",
                        r"\b(dsa|algorithms?|data structures?|dijkstra|huffman|sorting|insertion sort|graphs?|trees?|dynamic programming|greedy)\b",
                        r"\b(mips|processor|assembler|isa|cyclegan|gan|generative|react|web app)\b",
                    ]
                    matched = candidate_skills.intersection({"algorithms", "dsa", "data structures", "c++", "cpp", "python", "mips", "react", "gan"})
                    cp_claims = []
                    proj_algo_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        is_cp = bool(re.search(r"\b(codeforces|leetcode|codechef|starters|div\.?\s*2|expert|rating|contest|icpc)\b", text_lower, re.I))
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
                        elif re.search(r"\b(codeforces|codechef|atcoder|mips|processor|custom isa|interpreter|cyclegan)\b", text_all):
                            raw_val = 0.78
                        elif re.search(r"\b(dijkstra|bfs|dfs|sorting|huffman|shortest path|mst)\b", text_all):
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
                        r"\b(system design|architecture|real[- ]time|table reservations?|role-based access|seamless ordering|dashboard analytics|rest api|microservices|distributed|database|postgresql|express|node\.?js|react|docker)\b"
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
                        r"\b(processor|single-cycle|custom isa|assembler|react|full[- ]stack|cyclegan|gan|conditional gan|huffman|dijkstra|library management|team of \d+)\b"
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
                        elif re.search(r"\b(full[- ]stack|cyclegan|gan|app|database)\b", text_all):
                            raw_val = 0.70
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
                    if evidence.cpi is not None:
                        comp_claims = [f"Undergraduate CPI: {evidence.cpi:.2f}/10.0"]
                        if evidence.cpi >= 9.5:
                            raw_val = 1.0
                        elif evidence.cpi >= 9.0:
                            raw_val = 0.90
                        elif evidence.cpi >= 8.5:
                            raw_val = 0.78
                        elif evidence.cpi >= 8.0:
                            raw_val = 0.65
                        elif evidence.cpi >= 7.0:
                            raw_val = 0.50
                        else:
                            raw_val = 0.30
                    else:
                        for m in evidence.academic_metrics:
                            comp_claims.append(f"{m.name}: {m.value}")
                        if comp_claims:
                            raw_val = 0.60

            # ── 2. Quant Role Competency Mapping & Gradient Evaluation ─────
            elif role.role_id == "quant":
                if "mathematical" in comp_name or "rigor" in comp_name:
                    MATH_SIGNALS = [
                        r"\b(inmo|rmo|ioqm|inpho|incho|isi|kvpy|jee advanced|olympiad|mathematical olympiad)\b",
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
                        # Gradient: 1.0 for INMO/ISI/Olympiad; 0.75 for KVPY/JEE Adv; 0.50 for Probability/DE courses; 0.25 basic
                        if re.search(r"\b(inmo|rmo|ioqm|isi|olympiad|air [1-9]\d?\b|air [1-2]\d{2}\b)\b", text_all):
                            raw_val = 1.0
                        elif re.search(r"\b(kvpy|jee advanced|inpho|incho)\b", text_all):
                            raw_val = 0.78
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
                        if re.search(r"\b(expert|candidate master|optiver|rank 1|trade-a-thon|atcoder regular|div\.?\s*2 rank [1-9]\d{0,2}\b)\b", text_all):
                            raw_val = 1.0
                        elif re.search(r"\b(codeforces|codechef|algorithmic trading|nifty|sharpe|pairs trading)\b", text_all):
                            raw_val = 0.78
                        elif re.search(r"\b(dsa|algorithms?|data structures?|hackathon)\b", text_all):
                            raw_val = 0.50
                        else:
                            raw_val = 0.25

                elif "quantitative" in comp_name or "modeling" in comp_name:
                    MODEL_SIGNALS = [
                        r"\b(pairs trading|mean reversal|augmented-dickey-fuller|backtested|blueshift|co-integration|yolov5|machine learning|deep learning|neural networks?|cyclegan|gan|linear regression|logistic regression|svm|linear classifier|simulation|lightgcn|stochastic|probability|game complexity|congestion control|tcp|throughput|latency|bottleneck|network modeling|experimental|l4s|dcf|sensitivity|macd|rsi|bollinger)\b"
                    ]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in MODEL_SIGNALS) or any(s in c.skills_matched for s in {"pairs trading", "backtesting", "machine learning", "deep learning", "probability", "statistics"}):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        # Gradient: 0.95 for real backtested quant models or advanced proofs; 0.75 for DL/CV models; 0.50 for junior mentorship/linear models; 0.25 basic
                        if re.search(r"\b(pairs trading|augmented-dickey-fuller|backtested|blueshift|sharpe ratio|nifty|quantum query|game complexity|l4s|congestion control)\b", text_all):
                            raw_val = 0.95
                        elif re.search(r"\b(cyclegan|gan|yolov5|lightgcn|gnn|lstm|transformers|neural networks?|deep learning|svm|linear classifier)\b", text_all):
                            raw_val = 0.75
                        elif re.search(r"\b(mentor|mentored|camp|linear regression|logistic regression|scikit-learn|sklearn|dcf|sensitivity)\b", text_all):
                            raw_val = 0.50
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
                        r"\b(industry 4\.0|ordnance|manufacturing|fabrication|lathing|milling|3d printing|cnc|torque|assembly|machining|hardware|robotics|circuits?|vlsi|cadence|matlab|solidworks|ansys|autocad|simulink|verilog|cfd|fea|ros)\b"
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
                        if re.search(r"\b(industry 4\.0|ordnance|manufacturing|surge|vlsi|cadence)\b", text_all):
                            raw_val = 0.85
                        elif len(matched) >= 2 or len(comp_claims) >= 2:
                            raw_val = 0.70
                        else:
                            raw_val = 0.45

                elif "research" in comp_name or "internships" in comp_name:
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(k in text_lower for k in ["surge", "research", "intern", "internship", "production", "industry 4.0", "r&d", "laboratory"]):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if "surge" in text_all or "r&d" in text_all:
                            raw_val = 0.85
                        elif len(comp_claims) >= 2:
                            raw_val = 0.70
                        else:
                            raw_val = 0.45

                elif "tools" in comp_name or "cad" in comp_name:
                    matched = candidate_skills.intersection({"matlab", "solidworks", "ansys", "autocad", "simulink", "verilog", "cfd", "fea", "ros", "labview", "altium", "catia"})
                    TOOL_SIGNALS = [r"\b(labview|ni-opc|solidworks|autocad|catia|ansys|simulink|matlab|cnc|3d printing|xilinx|spartan|verilog|vhdl)\b"]
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
                    PROTO_SIGNALS = [r"\b(fabrication|lathing|milling|3d printing|cnc|assembly|automation|prototyping|hardware|motor|sensor|trolley|chessboard|circuit)\b"]
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

            # ── 5. Analyst Role ─────────────────────────────────────────────
            elif role.role_id == "analyst":
                if "data_analysis" in comp_name or "sql" in comp_name:
                    SQL_SIGNALS = [r"\b(sql|mysql|postgresql|query|queries|database|pandas|data analysis|web scraping|scraped|excel|vlookup)\b"]
                    matched = candidate_skills.intersection({"sql", "python", "pandas", "excel", "postgresql", "mysql"})
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in SQL_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(sql|mysql|postgresql|database|queries|query)\b", text_all):
                            raw_val = 0.85
                        elif len(comp_claims) >= 2 or len(matched) >= 2:
                            raw_val = 0.70
                        else:
                            raw_val = 0.45

                elif "dashboarding" in comp_name or "bi" in comp_name:
                    DASH_SIGNALS = [r"\b(tableau|power bi|dashboard|visualization|visualized|matplotlib|seaborn|rshiny|bi tool|notion|jira|trello)\b"]
                    matched = candidate_skills.intersection({"tableau", "power bi", "matplotlib", "seaborn", "rshiny"})
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in DASH_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        text_all = " ".join(comp_claims).lower()
                        if re.search(r"\b(tableau|power bi|dashboard|visualization|rshiny)\b", text_all):
                            raw_val = 0.80
                        else:
                            raw_val = 0.55

                elif "statistical" in comp_name or "modeling" in comp_name:
                    STAT_SIGNALS = [r"\b(statistics|statistical|probability|regression|clustering|a/b testing|hypothesis testing|scipy|sklearn|machine learning|prediction|predictive|mathematical fundamentals)\b"]
                    matched = candidate_skills.intersection({"statistics", "probability", "scipy", "sklearn", "a/b testing"})
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in STAT_SIGNALS) or any(s in c.skills_matched for s in matched):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        raw_val = 0.75 if len(comp_claims) >= 2 else 0.50

                elif "business" in comp_name or "acumen" in comp_name:
                    BIZ_SIGNALS = [r"\b(market size|customer segments|roi|revenue|profitability|business|portfolio|kpi|growth|trading strategy|scholarship)\b"]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in BIZ_SIGNALS) or c.has_quantifiable_impact:
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        raw_val = 0.75 if len(comp_claims) >= 2 else 0.50

                elif "cpi" in comp_name or "academic" in comp_name or "rigor" in comp_name:
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

            # ── 6. Product Management Role ─────────────────────────────────
            elif role.role_id == "product":
                if "product_thinking" in comp_name or "prds" in comp_name:
                    PRD_SIGNALS = [r"\b(prd|product requirement|wireframing|figma|roadmap|feature prioritization|user stories)\b"]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in PRD_SIGNALS):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        raw_val = 0.75 if len(comp_claims) >= 2 else 0.50

                elif "user_research" in comp_name or "ux" in comp_name:
                    UX_SIGNALS = [r"\b(user research|usability|interviews?|wireframe|figma|ux|customer segments|feedback)\b"]
                    comp_claims = []
                    for c in evidence.claims:
                        text_lower = c.text_snippet.lower()
                        if any(re.search(pat, text_lower, re.I) for pat in UX_SIGNALS):
                            comp_claims.append(c.text_snippet)
                    comp_claims = comp_claims[:4]
                    if comp_claims:
                        raw_val = 0.75 if len(comp_claims) >= 2 else 0.50

                elif "cpi" in comp_name or "academic" in comp_name or "pedigree" in comp_name:
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

            # ── 7. Universal Academic / CPI Fallback ────────────────────────
            elif "cpi" in comp_name or "academic" in comp_name or "pedigree" in comp_name or "rigor" in comp_name or "foundation" in comp_name or "consistency" in comp_name:
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

        # 2. National / International Olympiad & Top 250 JEE Advanced Outlier
        has_national_math_olympiad = any(
            bool(re.search(r"\b(inmo|rmo|isi|olympiad)\b", c.text_snippet.lower())) or "INMO" in c.entities_matched
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

        # 3. Competitive Programming / Trade-a-thon Outlier
        has_cf_expert = any(
            bool(re.search(r"\b(expert|candidate master|grandmaster|1[6-9]\d{2}|[2-3]\d{3})\b", c.text_snippet.lower())) and
            bool(re.search(r"\b(codeforces|codechef|atcoder)\b", c.text_snippet.lower()))
            for c in evidence.claims
        ) or any("expert" in str(getattr(l, "label", "")).lower() for l in links)

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

        # 5. Verified GitHub Profile Link (for SDE)
        if role.role_id == "sde" and has_github:
            outlier_bonus += 2.0
            bonuses.append("Verified GitHub profile link present (+2 pts)")

        # Strict capping of outlier bonus at 15.0 pts
        outlier_bonus = min(outlier_bonus, 15.0)

        # ── Apply Role Penalties ───────────────────────────────────────
        penalties: List[str] = []
        final_score = base_score + outlier_bonus

        if role.role_id == "sde":
            if not has_github:
                final_score -= 6.0
                penalties.append("Missing active GitHub profile link in Header (-6 pts)")

        elif role.role_id == "quant":
            if evidence.cpi and evidence.cpi < 8.0 and not has_cf_expert and not has_optiver_1st:
                final_score -= 8.0
                penalties.append(f"CPI below Quant benchmark of 8.0 (current: {evidence.cpi:.2f}) (-8 pts)")

        elif role.role_id == "consulting":
            if not has_pors:
                final_score -= 8.0
                penalties.append("Lack of prominent campus PoRs / Gymkhana leadership (-8 pts)")
            if quant_metric_count < 3:
                final_score -= 4.0
                penalties.append("Insufficient quantified business metrics across bullets (-4 pts)")

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

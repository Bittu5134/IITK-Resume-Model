# Pitch Deck: IITK Context-Aware Resume Diagnostic Engine 🚀
### Career Development Wing | Academics & Career Council — Anweshan '26 (150 Points)
*Presentation Team: 2 Y26s & 3 Y25s | Format: 12-Slide High-Impact Executive Deck*

---

## Slide 1: Title & Vision
- **Header**: The IITK Context-Aware Resume Diagnostic Engine
- **Subheader**: Transforming Placement Season Anxiety into Standardized, Grounded Career Intelligence
- **Presenter Team**: 2 Y26s and 3 Y25s (Pool Submission)
- **GitHub Repository**: [https://github.com/choudharyraj2903-collab/IITK-Resume-Engine](https://github.com/choudharyraj2903-collab/IITK-Resume-Engine)
- **Key Message**: Not an arbitrary rejection filter for recruiters — an automated, intelligent career advisor designed exclusively for the upliftment of IIT Kanpur students.

---

## Slide 2: The Core Dilemma at IIT Kanpur
- **The Crucible of Day Zero**: 1,500+ IITK students compressing 3-4 years of intense academics, BTPs, and Gymkhana leadership into a single-page SPO LaTeX template.
- **The Failure of Existing Tools**:
  - Commercial ATS tools scramble multi-column LaTeX tables into garbled text.
  - Generic AI gives superficial advice (*"be more impactful"*).
  - Students rely on scattered, subjective, and conflicting senior advice before Day Zero.
- **Our Mission**: Build an institutional diagnostic engine that understands IITK context natively, runs in sub-250ms, and provides hyper-specific line-by-line rewrites.

---

## Slide 3: 3-Module System Architecture
- **Module A: Spatial LaTeX-PDF Parsing Engine**
  - PyMuPDF bounding-box extraction.
  - Horizontal gap-aware row clustering preserving 2-column layouts.
  - Active hyperlink classification (GitHub, Codeforces, LeetCode).
- **Module B: Semantic Weighting & IITK NLP Engine**
  - 100+ IITK institutional entities (SURGE, AnC, Gymkhana, PoRs, Fests).
  - Official IITK course codes (`CS210`, `CS330`, `MTH415`, `ME352`).
  - Action verb strength and quantifiable impact detection.
- **Module C: The Advisory Command Center**
  - High-density dark-mode SPA (Tailwind + Chart.js) & CLI runner.
  - Profile match scores, radar charts, and Google/SPO XYZ bullet rewrites.

---

## Slide 4: Module A — Defeating the Multi-Column Scrambling Problem
- **The Flaw in Standard Parsers**: Horizontal line scanning concatenates left column bullets with adjacent right column achievements.
- **Our Algorithmic Innovation: Horizontal Gap Partitioning**:
  - Step 1: Vertical Y-midpoint grouping ($\delta_y \le 8.0\text{ pt}$).
  - Step 2: X-axis gap constraint: Adjacent text cells are merged into table rows **only if** $\Delta x \le 30.0\text{ pt}$.
  - Gaps $> 30.0\text{ pt}$ demarcate distinct column boundaries.
- **Impact**: Zero garbled text, flawless section segmentation, and preserved hyperlink provenance.

---

## Slide 5: Module B — Deep IITK Domain & Academic Ontology
- **Campus Jargon Native Recognition**:
  - Councils: Students' Gymkhana, AnC Council, CDW, SnT, MnC, GnS, Senate.
  - Fests: Techkriti, Antaragni, Udghosh, Takneek, Galaxy, Inferno.
  - Research: SURGE fellowships, UGP, BTP, MTP.
- **Academic Benchmarking**:
  - CPI / CGPA scaling (10.0 scale).
  - Class X / XII percentages.
  - JEE Advanced AIR (Top 250 detection), KVPY, and Olympiads (INMO, RMO, ISI).
- **Departmental Course Codes**: Maps exact course codes that human seniors prioritize.

---

## Slide 6: Comprehensive 7-Track Dynamic Evaluation Baselines
*Evaluates resumes across 4 canonical PS tracks + 3 industry extensions (CFA Institute, Atlassian, Dataquest):*
1. **Software Engineering (SDE)**:
   - Prioritizes DSA (`CS210`), Competitive Programming (Codeforces/LeetCode), and full-stack projects; penalizes missing GitHub (-6 pts).
2. **Quantitative Finance**:
   - Heavily prioritizes CPI $\ge 8.5$, stochastic calculus, probability (`MTH415/515`), and pairs trading; penalizes low CPI (-8 pts).
3. **Management Consulting**:
   - Rewards "Triple Spikes" (CPI + PoRs + Sports/Cult); penalizes lack of business metrics (-4 pts) and missing leadership (-8 pts).
4. **Core Engineering**:
   - Prioritizes SURGE research, core electives (`ME352`, `EE480`), and CAD/FEA/CFD simulations; penalizes web-dev displacing core electives (-5 pts).
5. **Data Analyst** *(Ref: CFA Institute Career Guide & Dataquest)*:
   - Evaluates SQL querying (CTEs, window functions), statistics & A/B testing, and BI dashboards; penalizes tool-listing without queries/metrics (-5 pts).
6. **Product Manager** *(Ref: Atlassian PM & Strategy Guides)*:
   - Evaluates customer discovery, PRDs, prioritization frameworks (RICE), and conversion funnels; penalizes tech projects mislabeled as products (-6 pts).
7. **Investment Banking** *(Ref: CFA Institute Financial Modeling & SG Analytics)*:
   - Evaluates linked 3-statement models, DCF with WACC, trading comps, and M&A pitch books; penalizes generic buzzwords lacking modeling (-6 pts).

---

## Slide 7: Mathematical Scoring Rigor & Gradient Calibration
- **85-Base Linear Gradient Formulation**:
  $$S_{\text{base}} = 85.0 \times \sum w_i s_i$$
  Evidence is evaluated continuously (0.0 to 1.0) rather than binary keyword flags.
- **Outlier Bonuses (Capped at 15.0 pts)**:
  - Top 0.5% CPI ($\ge 9.80$): $+5\text{ pts}$.
  - National Math Olympiad (INMO/RMO/ISI) / JEE AIR $\le 250$: $+5\text{ pts}$.
  - Elite CP (Candidate Master/Expert) / Optiver Trade-a-thon Rank 1: $+4\text{ pts}$.
  - Production Deployed Systems / VC Funding: $+2\text{ pts}$.
  - Consulting "Triple Spike" (Academics + PoR + Sports/Cult): $+3\text{ pts}$.
- **Transparent Tiering**: Strong Alignment ($\ge 75$), Moderate Fit ($50-74$), Significant Gaps ($<50$).

---

## Slide 8: Actionability — Google/SPO XYZ Formula Rewriter
- **Why Generic Tips Fail**: Telling a student *"quantify impact"* does not tell them *how*.
- **Named Project Provenance**: Diagnostics cite the exact entry title:
  - `[In Project 'IITK-Mini-MIPS']: Missing quantifiable hardware metric.`
- **Concrete XYZ Counterfactual Rewrites**:
  - *Original*: *"Worked on website for Techkriti attracting students"*
  - *Engine Rewrite*: *"Spearheaded front-end web portal for Techkriti using React, scaling to 15,000+ active users and reducing load latency by 35%."*
- **Score Lift Delta**: Directly shows estimated gain: *(+4.8 pts)*.

---

## Slide 9: Robustness & Edge-Case Demonstration
- **Adversarial Keyword Stuffing**:
  - Evaluated on `IITK_Adversarial_Test_Resume.pdf` (filled with random tech jargon).
  - *Result*: Programmatic zero-evidence rule suppresses score to **24.4 / 100** (Significant Gaps). Anti-gaming verified.
- **Multi-Page SPO Template Violations**:
  - Evaluates page geometry; generates immediate placement-risk alert if $> 1$ page.
- **Non-Standard Bullet Glyphs**:
  - Robust regex lexer handles middle dots (`\u00b7`), en-dashes (`–`), checkmarks, and Unicode markers without breaking AST parsing.

---

## Slide 10: Empirical Testing Across 24 Golden Resumes
- **Benchmark Corpus**: Tested across 24 real multi-track IIT Kanpur resumes in `tests/fixtures/`.
- **Classification & Scoring Results**:
  - Software Track Alignment: **83.3%**
  - Quant Track Alignment: **83.3%**
  - Consulting Track Alignment: **83.3%**
  - Core Engineering Track Alignment: **83.3%**
  - **Overall Autonomous Track Accuracy**: **83.3%**
- **Test Suite Health**: **37 passed, 1 skipped in 1.90s** (100% clean test suite).
- **Execution Latency**: **231 ms** average multi-track audit latency.

---

## Slide 11: Intuitive Advisory Dashboard & Developer CLI
- **Interactive Web SPA (Tailwind + Chart.js)**:
  - Drag-and-drop SPO PDF upload.
  - Multi-track radar and bar chart visualizations.
  - Expandable line-by-line audit table with severity badges.
  - Responsive dark-slate aesthetic matching official IITK identity (`#002147` Navy, `#FFC72C` Gold).
- **Power-User CLI Runner**:
  - Run `python main.py resume.pdf --all` for high-density terminal ASCII audits.
  - Export diagnostic JSON and Markdown reports with `--output`.

---

## Slide 12: Impact, Future Vision & Q&A
- **Student Uplift Impact**: Replaces weeks of waiting for ad-hoc senior reviews with instantaneous, objective, Day-Zero calibration.
- **Future Roadmap**:
  - Placement Cell (SPO) aggregate cohort dashboard for batch readiness trends.
  - Auto-generation of LaTeX rewrite diff patches.
- **Summary**: Flawless LaTeX parsing + Deep IITK context + Mathematical rigor + Actionable Google XYZ rewrites.
- **Thank you! We invite questions from the panel.**

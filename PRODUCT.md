# Product Requirement Document

## Platform
web

## Users
IIT Kanpur undergraduate and postgraduate students preparing for campus placement and internship seasons via the Student Placement Office (SPO).

## Product Purpose
An intelligent, context-aware resume advisor designed exclusively for the upliftment of IIT Kanpur students. Replaces subjective, conflicting senior advice with reliable, automated, standardized resume diagnosis that semantically weighs candidate achievements against target industry expectations.

## Positioning
An IITK-specific career diagnostic engine — not a recruiter rejection filter, but a candidate upliftment tool powered by SPO LaTeX multi-column parsing, IITK jargon recognition (SURGE, CPI, PoR, Gymkhana, AnC Council), and grounded counterfactual advisory feedback.

## Operating Context
Campus placement season preparation, resume review sessions, mock interviews, and student self-diagnosis. Used via an interactive single-page Web Advisory Dashboard or command-line interface (CLI).

## Capabilities and Constraints
- Multi-column SPO LaTeX PDF parsing respecting 2-column grid layout and extracting embedded hyperlinks.
- Semantic weighting & entity recognition for IITK-specific jargon, quantifiable impact metrics, and action verbs.
- Dynamic 6-track evaluation (SDE, Quant Finance, Management Consulting, Core Engineering, Data Analytics, Product Management) with auto-detection of best-fit role.
- Candidate diagnostic record storage for placement analytics and senior advising trend analysis.
- Single-page SPO LaTeX template compliance checking and line-by-line formatting fixes.

## Brand Commitments
- Official IIT Kanpur Academics & Career Council (AnC) and Career Development Wing (CDW) identity.
- Visual Theme: GeoShuffle Solid Pastel Hybrid UI supporting Light (`geoshuffle`) and Dark (`geoshuffle-dark`) modes with flat border-first styling and high-contrast typography.

## Evidence on Hand
- Official Problem Statement PDF: `cdev_ps_anweshan26_final.pdf` (CDW 150 Points Problem Statement).
- Sample SPO resume PDFs in `examples/resume2.pdf` and test fixtures.
- Pytest diagnostic test suite with 44 unit & E2E integration test cases passing in `tests/`.

## Product Principles
1. **Candidate Upliftment First**: Focus on actionable guidance and constructive improvement rather than arbitrary rejection.
2. **Contextual & Grounded Integrity**: Understand IITK context (SURGE, CPI, PoRs) without fabricating achievements or hallucinating metrics.
3. **Hyper-Specific Actionability**: Pinpoint exact lines, bullet text snippets, and specific rewrites rather than providing generic resume tips.
4. **Multi-Track Conditioning**: Evaluate candidate profiles dynamically against distinct role baselines (DSA/CP for SDE, CPI/Math for Quant, PoR/Impact for Consulting, Research/CAD for Core, SQL/Stats for Analyst, Discovery/Analytics for Product).

## Accessibility & Inclusion
Responsive dual-mode GeoShuffle UI (light & dark modes) with high visual contrast, legible typography (Fredoka / Space Grotesk / JetBrains Mono), keyboard navigation, and color-coded diagnostic severity indicators.

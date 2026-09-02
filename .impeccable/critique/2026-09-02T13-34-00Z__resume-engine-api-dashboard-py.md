---
target: resume_engine/api/dashboard.py
total_score: 29
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
timestamp: 2026-09-02T13-34-00Z
slug: resume-engine-api-dashboard-py
---
# Design Critique — `resume_engine/api/dashboard.py`

**Method**: dual-agent (A: b42bcf93-fadd-4a74-9811-bed77c401ba7 · B: e955b739-1999-4429-a1a0-ed3bd507debb)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|:---:|-----------|
| 1 | Visibility of System Status | 3 | Indeterminate loading overlay with clear status text; lacks granular upload progress bar |
| 2 | Match System / Real World | 3 | Authentic SPO placement terminology (CPI, PoR, Gymkhana, SURGE, SDE, Quant) |
| 3 | User Control and Freedom | 3 | 1-click role track switching and file removal; lacks full dashboard reset button |
| 4 | Consistency and Standards | 3 | WAI-ARIA tablist & diagnostic badges; theme toggle broken by fixed dark utility classes |
| 5 | Error Prevention | 2 | PDF dropzone restriction works; missing client-side 10MB file size validation |
| 6 | Recognition Rather Than Recall | 4 | Auto-detect best fit banner, 4-track comparative chart, and monospaced bullet snippets |
| 7 | Flexibility and Efficiency | 3 | Multi-track re-evaluation and filter pills; lacks keyboard shortcuts (e.g. 1-4 for role tracks) |
| 8 | Aesthetic and Minimalist Design | 3 | Slate dark-mode aesthetic; missing web font CDN stylesheets (`Inter` & `JetBrains Mono`) |
| 9 | Error Recovery | 3 | Inline accessible `#errorBanner` with smooth scroll; lacks corrupt PDF troubleshooting hints |
| 10 | Help and Documentation | 2 | API specs link included; lacks inline SPO LaTeX formatting guidelines or scoring explanation |
| **Total** | | **29/40** | **Good (72.5% - Solid Foundation)** |

## Design Specificity Verdict

- **LLM Assessment**: High-to-Moderate SPO Domain Specificity. The interface is authentically tailored for IIT Kanpur placement advisory with official identity colors (`#002147` IITK Navy, `#FFC72C` IITK Gold), student terminology, and 4 role tracks.
- **Deterministic Scan**: 4 advisory findings across 2 categories (`#334155`, `#475569`, `border-radius: 4px` on scrollbars, `#64748b` tick color in Chart.js). All 4 are legitimate micro-UI / 3rd-party canvas exemptions. Zero errors, zero warnings.

## Overall Impression
A highly functional, dark-mode command center SPA for resume diagnostics with excellent multi-track fit comparison and monospaced audit provenance.

## What's Working
1. **Auto-Detection & Interactive 4-Track Comparison**: Instantly highlights optimal role match while allowing single-click re-evaluation.
2. **Accessible WAI-ARIA Tab Navigation**: Full keyboard arrow key listener implementation.
3. **Monospaced Provenance**: Strict adherence to `DESIGN.md` monospace rules for auditability.

## Priority Issues

- **[P1] Broken Light/Dark Theme Toggle**: `toggleTheme()` toggles html class, but cards use fixed `bg-slate-900` instead of `dark:bg-slate-900 light:bg-white`.
  - *Fix*: Update card background utility classes to `bg-slate-900 dark:bg-slate-900 light:bg-white`.
  - *Suggested Command*: `/impeccable colorize`
- **[P1] Missing Google Fonts Imports (`Inter` & `JetBrains Mono`)**: `<head>` lacks font CDN stylesheets.
  - *Fix*: Add Google Fonts stylesheet links for `Inter` and `JetBrains Mono`.
  - *Suggested Command*: `/impeccable typeset`
- **[P2] Missing Client-Side File Size Validation (>10MB)**: Stated 10MB limit is not validated before HTTP upload.
  - *Fix*: Check `file.size > 10 * 1024 * 1024` in `handleFileSelect()` and trigger `showErrorBanner()`.
  - *Suggested Command*: `/impeccable harden`
- **[P2] WCAG AA Low Contrast Text (`text-slate-500` on `bg-slate-950`)**: Contrast ratio ~3.2:1 fails 4.5:1 minimum.
  - *Fix*: Upgrade `text-slate-500` labels to `text-slate-400`.
  - *Suggested Command*: `/impeccable audit`
- **[P3] Filter Control Group ARIA Radio Semantics & Choice Count**: 5 un-grouped filter buttons.
  - *Fix*: Wrap filter buttons in `role="radiogroup"` with `aria-checked` states.
  - *Suggested Command*: `/impeccable distill`

## Persona Red Flags
- **Alex (Power User / Placement Candidate)**: Lacks 1-click bullet copy or LaTeX export; harsh red `CRIT` badges cause placement anxiety.
- **Sam (Accessibility User)**: Low-contrast muted labels (`text-slate-500`) fail contrast guidelines.

## Minor Observations
- Add inline help documentation link for SPO single-page LaTeX guidelines.
- Add granular file upload progress bar for large files.

## Questions to Consider
1. *What if we added a 1-click "Copy Bullet Rewrite" button for candidates?*
2. *What if the line-by-line diagnostics table featured a side-by-side LaTeX document previewer?*

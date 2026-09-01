---
name: IITK Context-Aware Resume Diagnostic Engine
description: High-density dark-mode advisory deck for SPO resume diagnostic intelligence.
colors:
  primary: "#2563eb"
  primary-glow: "#3b82f6"
  iitk-navy: "#002147"
  iitk-gold: "#FFC72C"
  bg-dark: "#020617"
  surface-card: "#0f172a"
  border-stroke: "#1e293b"
  text-heading: "#f8fafc"
  text-muted: "#94a3b8"
  signal-strong: "#10b981"
  signal-warning: "#f59e0b"
  signal-critical: "#ef4444"
typography:
  display:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 800
    lineHeight: "1.25"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: "1.33"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: "1.4"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: "1.5"
  label:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.625rem"
    fontWeight: 700
    letterSpacing: "0.05em"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "12px 24px"
  button-role:
    backgroundColor: "{colors.bg-dark}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.lg}"
    padding: "10px 14px"
  button-role-active:
    backgroundColor: "rgba(37, 99, 235, 0.2)"
    textColor: "{colors.primary-glow}"
    rounded: "{rounded.lg}"
    padding: "10px 14px"
---

# Design System: IITK Context-Aware Resume Diagnostic Engine

## Overview

**Creative North Star: "The SPO Academic Command Center"**

The SPO Academic Command Center is a high-density, authoritative dark-mode interface designed for IIT Kanpur placement advising. Built to handle complex, multi-column LaTeX resume data, the aesthetic balances academic rigor with modern tech command-center precision. It presents high-density diagnostic insights—profile match scores, track comparisons, line-by-line bullet fixes, and extracted IITK jargon—in a crisp, scannable visual layout.

The visual mood is serious, deliberate, and empowering. Dark slate surfaces (`#020617` and `#0f172a`) create a calm, focused environment, while strategic cyan-blue and gold accents draw attention to critical score signals and actionable rewrite recommendations.

**Key Characteristics:**
- **High-Density Data Framing:** Structured grid layouts with 1px dark slate borders (`#1e293b`) for maximum scannability.
- **Color-Coded Diagnostic Signals:** Emerald green for strengths, Amber for warnings/gaps, Red for critical formatting fixes.
- **Dual-Font Hierarchy:** Clean sans-serif (Inter) for structural UI and monospaced font (JetBrains Mono) for exact bullet snippets and PDF location metadata.
- **Instant Role-Switching Affordance:** Prominent 4-track selection pills (SDE, Quant, Consulting, Core) with active glowing states.

## Colors

The color palette uses a deep Slate canvas with official IITK Navy and Gold identity markers, accented by high-contrast diagnostic signal colors.

### Primary
- **IITK Brand Navy & Engine Blue** (`#002147` / `#2563eb`): Used for primary actions, header branding, active role selectors, and core score rings.

### Secondary
- **IITK Accent Gold** (`#FFC72C`): Reserved for key academic highlights and honor badges.

### Neutral
- **Deep Slate Canvas** (`#020617`): Base page background color.
- **Surface Dark Slate** (`#0f172a`): Container and card surface background.
- **Stroke Border Slate** (`#1e293b`): 1px structural borders dividing cards, tables, and tabs.
- **Muted Text Slate** (`#94a3b8`): Secondary labels, body copy, and metadata text.
- **Bright White** (`#f8fafc`): Headings, primary metrics, and high-emphasis numbers.

### Diagnostic Signal Roles
- **Signal Strong** (`#10b981` / `emerald-400`): Used for profile strengths, score tier badges (75+), and score gain estimates.
- **Signal Warning** (`#f59e0b` / `amber-400`): Used for missing competencies, formatting warnings, and moderate score tiers.
- **Signal Critical** (`#ef4444` / `red-400`): Used for critical line fixes, weak action verbs, and severe gaps.

### Named Rules
**The Rarity of Blue Accent Rule.** Primary blue fill (`#2563eb`) is strictly reserved for primary CTA buttons and active track selection. Neutral slate dominates 90% of the viewport to keep the interface calm.

## Typography

**Display Font:** Inter (fallback: system-ui, sans-serif)  
**Body Font:** Inter (fallback: system-ui, sans-serif)  
**Label/Mono Font:** JetBrains Mono (fallback: ui-monospace, monospace)

**Character:** Technical, clean, and legible. Monospaced font is used exclusively for code snippets, page/section locations, and PDF URL links to clearly separate metadata from descriptive text.

### Hierarchy
- **Display** (800 font-weight, `1.125rem` / 18px, 1.25 line-height): Header title and modal headers.
- **Headline** (700 font-weight, `1.0rem` / 16px, 1.33 line-height): Card section titles and auto-detection banner.
- **Title** (700 font-weight, `0.875rem` / 14px, 1.4 line-height): Competency names, table column headers, tab labels.
- **Body** (400 font-weight, `0.75rem` / 12px, 1.5 line-height): Actionable recommendations, diagnostic suggestions, and notice text.
- **Label / Code** (700 font-weight, `0.625rem` / 10px, uppercase, `0.05em` letter-spacing): Location tags (`Pg 1`), severity badges (`CRIT`, `WARN`), and table line snippets.

### Named Rules
**The Monospace Provenance Rule.** Any text representing extracted resume data (bullet snippets, page numbers, line identifiers, parsed URLs) must use the monospaced font family for clear auditability.

## Layout

The spatial model uses a max-width 7xl container (`1280px`) with a multi-column responsive grid:
- **Header**: Sticky top bar (`top-0 z-50`) with backdrop blur (`backdrop-blur`).
- **Upload & Role Control Zone**: Top 12-column grid dividing dropzone (7 cols) and role selection pills (5 cols).
- **Executive Summary Row**: 12-column split (5 cols for Score Gauge Card, 7 cols for 4-Track Comparison Bar Chart).
- **Tabbed Advisory Container**: Tab bar at top with tabbed panel content below.
- **Spacing Rhythm**: 8px base unit with 12px, 16px, 24px container padding.

## Elevation & Depth

Surfaces are flat at rest with 1px border strokes (`#1e293b`) and subtle background contrast (`#020617` vs `#0f172a`). Elevation and depth are conveyed through tonal layering and glowing accent halos rather than heavy drop shadows.

### Shadow Vocabulary
- **Ambient Glow** (`shadow-lg shadow-blue-500/20`): Used under the primary CTA button and active status indicators.
- **Card Depth** (`shadow-xl`): Applied to main container cards to separate them from the dark background.

### Named Rules
**The Stroke-First Layering Rule.** Surfaces rely on 1px subtle slate borders (`#1e293b`) for visual boundary separation. Heavy box-shadows are strictly forbidden.

## Shapes

- **Card Radius:** `rounded-2xl` (16px) for major container cards and upload dropzone.
- **Button & Selector Radius:** `rounded-xl` (12px) for track selector pills, tabs, and action buttons.
- **Badge Radius:** `rounded-full` (9999px) for status badges and tier pills.
- **Table Cell Radius:** `rounded-md` (6px) for filter buttons and table tags.

## Components

### Buttons
- **Shape:** `rounded-xl` (12px)
- **Primary Action:** `bg-gradient-to-r from-blue-600 to-indigo-600` (`#2563eb` to `#4f46e5`), text white, `padding: 12px 24px`, font weight 600.
- **Role Selector Pill:** `bg-slate-950 border border-slate-800 text-slate-400`, `padding: 10px 14px`. Active state: `border-blue-500 bg-blue-600/20 text-blue-300`.

### Cards & Containers
- **Corner Style:** `rounded-2xl` (16px)
- **Background:** `bg-slate-900` (`#0f172a`) with `border border-slate-800` (`#1e293b`).
- **Padding:** `p-6` (24px) for major cards, `p-4` (16px) for sub-cards.

### Diagnostic Badges
- **Strong Tier:** `bg-emerald-500/10 text-emerald-400 border border-emerald-500/20`, `rounded-full`, `px-3 py-1`, font weight 700.
- **Warning / Gap Tier:** `bg-amber-500/10 text-amber-400 border border-amber-500/20`, `rounded-full`, `px-3 py-1`, font weight 700.
- **Critical Fix:** `bg-red-500/20 text-red-400`, `px-2 py-0.5`, `rounded`, font weight 700.

### Navigation Tabs
- **Style:** Horizontal tab bar with `border-b border-slate-800`.
- **Active Tab:** `border-b-2 border-blue-500 text-blue-400 bg-slate-900/50`.
- **Inactive Tab:** `text-slate-400 hover:text-slate-200 border-transparent`.

## Do's and Don'ts

### Do:
- **Do** use `JetBrains Mono` monospace font for all bullet snippets, line IDs, page numbers, and hyperlinks.
- **Do** highlight the highest-scoring track automatically upon PDF upload with the Auto-Detect Best Fit banner.
- **Do** use 1px slate borders (`#1e293b`) for structural division across cards and tables.
- **Do** display hyper-specific action feedback pinpointing exact bullet snippets and non-hallucinated rewrite suggestions.

### Don't:
- **Don't** use light or white backgrounds for card containers; keep the UI in the dark slate palette.
- **Don't** fabricate metrics or experience when suggesting bullet point rewrites.
- **Don't** use heavy drop-shadows or multi-colored gradients on body text.

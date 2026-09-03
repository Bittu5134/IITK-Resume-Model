---
name: IITK Context-Aware Resume Diagnostic Engine
description: High-density Solid Pastel Hybrid advisory interface with GeoShuffle theme palettes for SPO resume diagnostic intelligence.
colors:
  geoshuffle-light:
    base-100: "#F4F3EE"
    base-200: "#FFFFFF"
    base-300: "#E6E4DC"
    base-content: "#121316"
    primary: "#FF5A36"
    secondary: "#00CC66"
    accent: "#FFD166"
    neutral: "#121316"
  geoshuffle-dark:
    base-100: "#121316"
    base-200: "#1C1D22"
    base-300: "#262830"
    base-content: "#F4F3EE"
    primary: "#FF6B4A"
    secondary: "#10B981"
    accent: "#FBBF24"
    neutral: "#E5E7EB"
  signals:
    strong: "#00CC66"
    warning: "#FFB703"
    critical: "#FF2E63"
    info: "#00B4D8"
typography:
  sans: "Fredoka, Space Grotesk, system-ui, sans-serif"
  mono: "JetBrains Mono, monospace"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
---

# Design System: IITK Context-Aware Resume Diagnostic Engine

## Overview

**Creative North Star: "The GeoShuffle Solid Pastel Hybrid Command Center"**

The SPO Academic Command Center is a high-density, authoritative single-page application (SPA) designed for IIT Kanpur placement advising. Built to process complex, multi-column LaTeX resume data, the aesthetic blends the bold, structured clarity of Neo-Brutalism with soft, high-contrast pastel palettes in a **Solid Pastel Hybrid** layout.

### Key Characteristics:
- **Solid Pastel Hybrid Aesthetics:** Flat, border-first component framing with zero offset drop-shadows, clean 2px solid neutral borders, and smooth rounded corners (`0.5rem` - `0.75rem`).
- **GeoShuffle Theme Engine:** Dual-mode theme support via CSS variables with `data-theme="geoshuffle"` (light warm cream background) and `data-theme="geoshuffle-dark"` (deep slate-charcoal background).
- **Refined Pastel Emblem Header:** Top navigation header featuring a rounded pastel icon badge (`w-11 h-11 rounded-xl`) displaying the official IIT Kanpur SPO advisory brand.
- **High-Density Data Framing:** Clear grid layout separating candidate PDF upload, 6-track role selection, executive match scores, and a 3-tab diagnostic matrix (SWOT analysis, line-by-line formatting fixes, extracted campus entities).
- **Dual-Font Hierarchy:** Friendly display font (Fredoka / Space Grotesk) for headings and structural copy, combined with monospaced `JetBrains Mono` for audit provenance (bullet snippets, page locations, CPI/JEE metrics, and URLs).
- **Instant 6-Track Affordance:** Prominent selection pills for all 6 placement tracks: **SDE**, **QUANT**, **CONSULT**, **CORE**, **ANALYST**, and **PRODUCT**.

---

## Color Palettes & Contrast Rules

The interface features custom GeoShuffle OKLCH/Hex color variables calibrated for maximum contrast and readability:

### Light Theme (`data-theme="geoshuffle"`)
- **Page Background (`--color-base-100`)**: `#F4F3EE` (Soft warm cream)
- **Card Surface (`--color-base-200`)**: `#FFFFFF` (Pure white)
- **Container / Box (`--color-base-300`)**: `#E6E4DC` (Subtle neutral grey)
- **Base Text (`--color-base-content`)**: `#121316` (Deep charcoal)
- **Primary Accent (`--color-primary`)**: `#FF5A36` (Vibrant coral)
- **Secondary Accent (`--color-secondary`)**: `#00CC66` (Emerald green)
- **Accent Highlight (`--color-accent`)**: `#FFD166` (Warm pastel yellow)
- **Neutral Border (`--color-neutral`)**: `#121316` (Sharp dark border)

### Dark Theme (`data-theme="geoshuffle-dark"`)
- **Page Background (`--color-base-100`)**: `#121316` (Deep dark charcoal)
- **Card Surface (`--color-base-200`)**: `#1C1D22` (Rich dark slate)
- **Container / Box (`--color-base-300`)**: `#262830` (Subtle dark grey)
- **Base Text (`--color-base-content`)**: `#F4F3EE` (High-contrast cream)
- **Primary Accent (`--color-primary`)**: `#FF6B4A` (Radiant coral)
- **Secondary Accent (`--color-secondary`)**: `#10B981` (Vibrant green)
- **Accent Highlight (`--color-accent`)**: `#FBBF24` (Pastel gold)
- **Neutral Border (`--color-neutral`)**: `#E5E7EB` (Light crisp border)

### Diagnostic Signal Palette
- **Strength / Success**: `#00CC66` / `#34D399` (Verified spikes & score gains)
- **Warning / Threat**: `#FFB703` / `#FBBF24` (Missing competencies & domain risks)
- **Critical / Error**: `#FF2E63` / `#F87171` (Weak action verbs & formatting fixes)
- **Info / Opportunity**: `#00B4D8` / `#38BDF8` (Score uplift potential & extracted hyperlinks)

---

## Component Specifications

### 1. `.neo-card`
- **Background**: `var(--color-base-200)`
- **Border**: `2px solid var(--color-neutral)`
- **Radius**: `0.75rem` (12px)
- **Shadow**: None (`box-shadow: none`)

### 2. `.neo-box`
- **Background**: `var(--color-base-300)`
- **Border**: `2px solid var(--color-neutral)`
- **Radius**: `0.5rem` (8px)
- **Shadow**: None (`box-shadow: none`)

### 3. `.neo-btn`
- **Background**: `var(--color-base-200)`
- **Border**: `2px solid var(--color-neutral)`
- **Radius**: `0.75rem` (12px)
- **Hover**: `opacity: 0.88`
- **Active**: `transform: scale(0.97)`
- **Shadow**: None (`box-shadow: none`)

### 4. Header & Logo Emblem
- **Header**: Sticky top navigation bar with `2px` bottom border in `var(--color-neutral)`
- **Logo Badge**: `w-11 h-11 rounded-xl` emblem with `var(--color-accent)` background and `2px solid var(--color-neutral)` border.

---

## Accessibility & UI Guidelines

1. **Flat Border-First Layering**: Rely on 2px solid neutral borders (`var(--color-neutral)`) for visual separation. Heavy offset box-shadows are strictly avoided.
2. **Text Legibility**: Text inherits `var(--color-base-content)` or uses `.text-muted` for secondary labels, ensuring high contrast ratio in both Light and Dark themes.
3. **Monospace Provenance**: All raw resume snippets, bullet section titles, page markers, and URLs use `JetBrains Mono` for instant audit recognition.

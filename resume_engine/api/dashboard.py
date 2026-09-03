"""Advisory Dashboard HTML frontend module.

Provides a rich, interactive single-page application (SPA) styled with a true
Neo-Brutalist design language, GeoShuffle theme palettes, local static assets,
FontAwesome icons, and Chart.js.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="geoshuffle-dark" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IITK Context-Aware Resume Diagnostic Engine — SPO Advisory</title>
    <!-- Local Static Assets -->
    <script src="/static/tailwind.min.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Fredoka', 'Space Grotesk', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace']
                    }
                }
            }
        }
    </script>
    <!-- Local Fonts: Space Grotesk & JetBrains Mono -->
    <link rel="stylesheet" href="/static/fonts/fonts.css">
    <!-- Local FontAwesome & Chart.js -->
    <link rel="stylesheet" href="/static/fontawesome/css/all.min.css">
    <script src="/static/chart.min.js"></script>
    <style>
        /* GeoShuffle Theme – High-contrast Neo-Brutalist CSS Variables */
        [data-theme="geoshuffle"] {
            --color-base-100: #F4F3EE; /* Page background - warm soft cream */
            --color-base-200: #FFFFFF; /* Card background - crisp white */
            --color-base-300: #E6E4DC; /* Box background - subtle neutral */
            --color-base-content: #121316; /* Base text - high contrast charcoal/black */
            --color-primary: #FF5A36;
            --color-primary-content: #FFFFFF;
            --color-secondary: #00CC66;
            --color-secondary-content: #000000;
            --color-accent: #FFD166;
            --color-accent-content: #000000;
            --color-neutral: #121316; /* Sharp border & shadow color */
            --color-neutral-content: #FFFFFF;
            --color-success: #00CC66;
            --color-warning: #FFB703;
            --color-error: #FF2E63;
            --color-info: #00B4D8;
            --color-text-muted: #555861;
        }

        [data-theme="geoshuffle-dark"] {
            --color-base-100: #121316; /* Page background - dark charcoal */
            --color-base-200: #1C1D22; /* Card background - rich dark slate */
            --color-base-300: #262830; /* Box background */
            --color-base-content: #F4F3EE; /* Base text - high contrast off-white */
            --color-primary: #FF6B4A;
            --color-primary-content: #121316;
            --color-secondary: #10B981;
            --color-secondary-content: #121316;
            --color-accent: #FBBF24;
            --color-accent-content: #121316;
            --color-neutral: #E5E7EB; /* Light border & shadow for dark theme */
            --color-neutral-content: #121316;
            --color-success: #34D399;
            --color-warning: #FBBF24;
            --color-error: #F87171;
            --color-info: #38BDF8;
            --color-text-muted: #9CA3AF;
        }

        body {
            font-family: "Fredoka", "Space Grotesk", system-ui, sans-serif;
            background-color: var(--color-base-100);
            color: var(--color-base-content);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .font-mono {
            font-family: 'JetBrains Mono', monospace;
        }

        .neo-header {
            background-color: var(--color-base-200);
            color: var(--color-base-content);
            border-bottom: 3px solid var(--color-neutral);
        }

        .neo-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            border: 2px solid var(--color-neutral) !important;
            border-radius: 0.75rem !important;
            background-color: var(--color-base-200);
            color: var(--color-base-content);
            transition: opacity 0.15s ease, transform 0.1s ease, background-color 0.2s ease;
            cursor: pointer;
        }

        .neo-btn:hover:not(:disabled) {
            opacity: 0.88;
        }

        .neo-btn:active:not(:disabled) {
            transform: scale(0.97);
        }

        .neo-btn-primary {
            background-color: var(--color-primary) !important;
            color: var(--color-primary-content) !important;
        }

        .neo-btn-success {
            background-color: var(--color-success) !important;
            color: var(--color-secondary-content) !important;
        }

        .neo-btn-warning {
            background-color: var(--color-warning) !important;
            color: #000000 !important;
        }

        .neo-btn-accent {
            background-color: var(--color-accent) !important;
            color: var(--color-accent-content) !important;
        }

        .neo-btn-neutral {
            background-color: var(--color-neutral) !important;
            color: var(--color-neutral-content) !important;
        }

        .neo-card {
            background-color: var(--color-base-200) !important;
            color: var(--color-base-content) !important;
            border: 2px solid var(--color-neutral) !important;
            border-radius: 0.75rem !important;
            overflow: hidden;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .neo-box {
            background-color: var(--color-base-300) !important;
            color: var(--color-base-content) !important;
            border: 2px solid var(--color-neutral) !important;
            border-radius: 0.5rem;
        }

        .swot-s {
            background-color: var(--color-base-200);
            border: 2px solid var(--color-success) !important;
            border-radius: 0.5rem;
        }

        .swot-w {
            background-color: var(--color-base-200);
            border: 2px solid var(--color-error) !important;
            border-radius: 0.5rem;
        }

        .swot-o {
            background-color: var(--color-base-200);
            border: 2px solid var(--color-info) !important;
            border-radius: 0.5rem;
        }

        .swot-t {
            background-color: var(--color-base-200);
            border: 2px solid var(--color-warning) !important;
            border-radius: 0.5rem;
        }

        .text-muted {
            color: var(--color-text-muted) !important;
        }

        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
            background: var(--color-base-100);
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: var(--color-accent);
            border-radius: 3px;
        }

        ::selection {
            background-color: var(--color-accent);
            color: var(--color-accent-content);
        }
    </style>
</head>
<body class="h-full flex flex-col antialiased">

    <!-- Neo-Brutalist Top Navigation Bar -->
    <header class="neo-header sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3.5">
                <div class="w-11 h-11 rounded-xl flex items-center justify-center font-black text-xl" style="background-color: var(--color-accent); color: var(--color-accent-content); border: 2px solid var(--color-neutral);">
                    <i class="fa-solid fa-graduation-cap"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-lg sm:text-xl font-black uppercase tracking-tight text-current">
                            IIT Kanpur Resume Engine
                        </h1>
                        <span class="bg-black text-[#FFE600] font-mono font-bold text-xs px-2 py-0.5 border border-black uppercase">
                            [SPO ADVISORY]
                        </span>
                    </div>
                    <p class="text-xs font-mono font-bold text-muted uppercase tracking-wider">
                        Academics & Career Council | Career Development Wing
                    </p>
                </div>
            </div>
            
            <div class="flex items-center gap-3 font-mono">
                <button type="button" id="themeToggleBtn" onclick="toggleTheme()" aria-label="Toggle Light and Dark Theme" class="text-xs font-black uppercase neo-btn px-3.5 py-2 flex items-center gap-2">
                    <i id="themeToggleIcon" class="fa-solid fa-moon text-yellow-400"></i>
                    <span id="themeToggleText">DARK</span>
                </button>
                <a href="/docs" target="_blank" class="text-xs font-black uppercase neo-btn px-3.5 py-2 flex items-center gap-2">
                    <i class="fa-solid fa-code"></i>
                    <span>[API SPECS]</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        <!-- Inline Error Banner -->
        <div id="errorBanner" class="hidden bg-[#FF0055] text-white border-2 border-[var(--color-neutral)] rounded-xl p-4 flex items-center justify-between gap-3 text-sm font-mono font-bold transition-all">
            <div class="flex items-center gap-2.5">
                <i class="fa-solid fa-triangle-exclamation text-lg"></i>
                <span id="errorMessageText">An error occurred during processing.</span>
            </div>
            <button type="button" onclick="hideErrorBanner()" aria-label="Dismiss error banner" class="bg-black text-white px-2 py-1 border border-white hover:bg-white hover:text-black transition">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <!-- Upload & Control Panel -->
        <section class="neo-card p-6 relative transition-colors">
            <div class="border-b-3 border-[var(--color-neutral)] pb-3 mb-5 flex items-center justify-between">
                <span class="font-mono font-black text-xs uppercase tracking-widest text-current">
                    [COMMAND HERO // RESUME AUDIT INPUT]
                </span>
                <span class="text-xs font-mono font-bold bg-[#FFE600] text-black px-2.5 py-0.5 border border-black uppercase rounded">
                    STEP 1 & 2
                </span>
            </div>

            <form id="analyzeForm" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                <!-- Dropzone -->
                <div class="lg:col-span-7">
                    <label class="block font-mono font-black text-xs text-current uppercase tracking-wider mb-2">
                        1. UPLOAD CANDIDATE RESUME (PDF)
                    </label>
                    <div id="dropzone" tabindex="0" role="button" aria-label="Upload PDF Resume" class="border-4 border-dashed border-[var(--color-neutral)] hover:bg-[#FFE600]/10 transition-colors p-6 text-center bg-[var(--color-base-300)] cursor-pointer group flex flex-col items-center justify-center min-h-[140px] focus:outline-none focus:ring-4 focus:ring-[#FFE600] rounded-xl">
                        <input type="file" id="pdfFileInput" accept=".pdf" class="hidden">
                        <div id="uploadPrompt" class="space-y-1.5 font-mono">
                            <i class="fa-solid fa-file-arrow-up text-4xl text-current group-hover:scale-110 transition-transform mb-1"></i>
                            <p class="text-sm font-black text-current uppercase">CLICK TO BROWSE OR DROP PDF HERE</p>
                            <p class="text-xs font-bold text-muted">[FORMAT: SPO 1-PAGE LATEX PDF // MAX 10MB]</p>
                        </div>
                        <div id="fileSelectedInfo" class="hidden flex items-center gap-3.5 text-left w-full bg-[var(--color-base-200)] p-3.5 border-3 border-[var(--color-neutral)] neo-box">
                            <i class="fa-solid fa-file-pdf text-[#FF0055] text-3xl"></i>
                            <div class="flex-1 truncate font-mono">
                                <p id="fileName" class="text-sm font-black text-current truncate">resume.pdf</p>
                                <p id="fileSize" class="text-xs font-bold text-muted">0 KB</p>
                            </div>
                            <button type="button" id="removeFileBtn" aria-label="Remove uploaded PDF resume" class="bg-[#FF0055] text-white px-2.5 py-1 border-2 border-black font-black hover:bg-black transition">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Role Selector & Action -->
                <div class="lg:col-span-5 flex flex-col justify-between space-y-4">
                    <div>
                        <label class="block font-mono font-black text-xs text-current uppercase tracking-wider mb-2">
                            2. TARGET INDUSTRY TRACK
                        </label>
                        <div role="tablist" aria-label="Target Industry Track Selection" class="grid grid-cols-3 gap-2.5 font-mono">
                            <button type="button" role="tab" id="role-tab-sde" aria-selected="true" aria-controls="resultsDashboard" data-role="sde" class="role-btn active px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[#FFE600] text-black rounded-lg">
                                <span><i class="fa-solid fa-code mr-1.5"></i>SDE</span>
                                <i class="fa-solid fa-check text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-quant" aria-selected="false" aria-controls="resultsDashboard" data-role="quant" class="role-btn px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[var(--color-base-300)] text-current hover:bg-[#FFE600]/20 rounded-lg">
                                <span><i class="fa-solid fa-chart-line mr-1.5"></i>QUANT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-consulting" aria-selected="false" aria-controls="resultsDashboard" data-role="consulting" class="role-btn px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[var(--color-base-300)] text-current hover:bg-[#FFE600]/20 rounded-lg">
                                <span><i class="fa-solid fa-briefcase mr-1.5"></i>CONSULT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-core" aria-selected="false" aria-controls="resultsDashboard" data-role="core" class="role-btn px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[var(--color-base-300)] text-current hover:bg-[#FFE600]/20 rounded-lg">
                                <span><i class="fa-solid fa-gear mr-1.5"></i>CORE</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-analyst" aria-selected="false" aria-controls="resultsDashboard" data-role="analyst" class="role-btn px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[var(--color-base-300)] text-current hover:bg-[#FFE600]/20 rounded-lg">
                                <span><i class="fa-solid fa-chart-pie mr-1.5"></i>ANALYST</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-product" aria-selected="false" aria-controls="resultsDashboard" data-role="product" class="role-btn px-3 py-3 border-2 border-[var(--color-neutral)] text-xs font-black uppercase transition flex items-center justify-between bg-[var(--color-base-300)] text-current hover:bg-[#FFE600]/20 rounded-lg">
                                <span><i class="fa-solid fa-rocket mr-1.5"></i>PRODUCT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="w-full py-4 neo-btn neo-btn-primary font-black text-sm uppercase tracking-widest flex items-center justify-center gap-2 font-mono">
                        <i class="fa-solid fa-bolt text-[#FFE600] text-sm"></i>
                        <span>ANALYZE RESUME [RUN DIAGNOSTIC]</span>
                    </button>
                </div>
            </form>
        </section>

        <!-- Loading State -->
        <div id="loadingOverlay" class="hidden neo-card p-10 text-center space-y-3">
            <div class="inline-block">
                <i class="fa-solid fa-gear text-4xl text-[#FF0055] animate-spin"></i>
            </div>
            <h3 class="text-lg font-black uppercase tracking-tight text-current">
                [PARSING RESUME & COMPUTING DIAGNOSTIC MATRIX...]
            </h3>
            <p class="text-xs font-mono font-bold text-muted max-w-md mx-auto">
                Executing multi-column PyMuPDF extraction, recognizing campus entities, and calculating 6-track alignment.
            </p>
        </div>

        <!-- Dashboard Content (Visible after analysis) -->
        <div id="resultsDashboard" class="hidden space-y-6">

            <!-- Auto-Detected Best Fit Track Banner -->
            <div id="autoDetectBanner" class="hidden bg-[#00FF66] text-black border-2 border-black p-4 flex flex-wrap items-center justify-between gap-3 font-mono rounded-xl">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-black text-[#00FF66] flex items-center justify-center font-black text-xl border-2 border-black rounded-lg">
                        <i class="fa-solid fa-bullseye"></i>
                    </div>
                    <div>
                        <span class="text-xs font-black uppercase tracking-wider block">[ALGORITHM RECOMMENDATION]</span>
                        <h3 class="text-base font-black uppercase">
                            OPTIMAL TRACK FIT: <span id="autoDetectRoleText" class="underline decoration-black decoration-2">SOFTWARE ENGINEERING</span>
                        </h3>
                    </div>
                </div>
                <div class="text-xs font-black bg-black text-white px-3 py-1.5 border border-black uppercase rounded">
                    [EVALUATING 6 TRACKS SIMULTANEOUSLY]
                </div>
            </div>

            <!-- Top Row Summary Cards -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">

                <!-- Overall Profile Score Card -->
                <div class="md:col-span-5 neo-card p-6 flex flex-col justify-between">
                    <div class="flex items-center justify-between border-b-3 border-[var(--color-neutral)] pb-3">
                        <div>
                            <span class="text-xs font-mono font-black uppercase tracking-wider text-muted block">
                                [PROFILE MATCH SCORE]
                            </span>
                            <h2 id="activeRoleTitle" class="text-lg font-black uppercase tracking-tight text-current">
                                SOFTWARE ENGINEERING
                            </h2>
                        </div>
                        <span id="scoreBadgeTier" class="px-3 py-1 text-xs font-mono font-black uppercase bg-[#00FF66] text-black border-2 border-black rounded">
                            STRONG ALIGNMENT
                        </span>
                    </div>

                    <div class="py-6 flex items-center justify-around gap-4 font-mono">
                        <div class="relative w-36 h-36 flex items-center justify-center">
                            <canvas id="scoreCircleChart" width="144" height="144"></canvas>
                            <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                                <span id="overallScoreVal" class="text-5xl font-black text-current tracking-tighter">0</span>
                                <span class="text-xs font-black text-muted uppercase">/ 100</span>
                            </div>
                        </div>

                        <div class="space-y-2 text-xs font-mono font-bold flex-1 max-w-[200px]">
                            <div class="flex justify-between items-center bg-[var(--color-base-300)] p-1.5 border-2 border-[var(--color-neutral)] rounded">
                                <span>CLAIMS:</span>
                                <span id="statClaims" class="font-black text-current">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[var(--color-base-300)] p-1.5 border-2 border-[var(--color-neutral)] rounded">
                                <span>ENTITIES:</span>
                                <span id="statEntities" class="font-black text-current">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[var(--color-base-300)] p-1.5 border-2 border-[var(--color-neutral)] rounded">
                                <span>LINKS:</span>
                                <span id="statLinks" class="font-black text-current">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[#FFE600] text-black p-1.5 border-2 border-black rounded">
                                <span>ALERTS:</span>
                                <span id="statAlerts" class="font-black text-[#FF0055]">0</span>
                            </div>
                        </div>
                    </div>

                    <div class="text-xs font-mono font-bold bg-[#FFE600] text-black p-3 border-2 border-black rounded-lg">
                        <i class="fa-solid fa-circle-info mr-1.5"></i>
                        <span id="scoreSummaryNotice">Matches DSA, competitive programming, and GitHub project signals against SDE baselines.</span>
                    </div>
                </div>

                <!-- 6-Track Comparative View -->
                <div class="md:col-span-7 neo-card p-6 flex flex-col justify-between">
                    <div class="flex items-center justify-between border-b-3 border-[var(--color-neutral)] pb-3 mb-4">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-chart-column text-[#FF0055] text-lg"></i>
                            <h3 class="text-xs font-mono font-black text-current uppercase tracking-wider">
                                [6-TRACK READINESS COMPARISON]
                            </h3>
                        </div>
                        <span class="text-xs font-mono font-bold bg-black text-white px-2 py-0.5 uppercase">
                            LIVE RADAR
                        </span>
                    </div>
                    
                    <div class="h-48 relative w-full">
                        <canvas id="multiTrackChart"></canvas>
                    </div>

                    <div class="grid grid-cols-3 sm:grid-cols-6 gap-2 pt-3.5 border-t-3 border-[var(--color-neutral)] font-mono text-center">
                        <button onclick="switchRole('sde')" class="p-2 border-2 border-[var(--color-neutral)] bg-[#FFE600] text-black text-left neo-box rounded">
                            <span class="text-xs font-black block">SDE</span>
                            <span id="sdeScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('quant')" class="p-2 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current text-left neo-box hover:bg-[#FFE600] hover:text-black rounded">
                            <span class="text-xs font-black block">QUANT</span>
                            <span id="quantScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('consulting')" class="p-2 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current text-left neo-box hover:bg-[#FFE600] hover:text-black rounded">
                            <span class="text-xs font-black block">CONSULT</span>
                            <span id="consultingScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('core')" class="p-2 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current text-left neo-box hover:bg-[#FFE600] hover:text-black rounded">
                            <span class="text-xs font-black block">CORE</span>
                            <span id="coreScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('analyst')" class="p-2 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current text-left neo-box hover:bg-[#FFE600] hover:text-black rounded">
                            <span class="text-xs font-black block">ANALYST</span>
                            <span id="analystScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('product')" class="p-2 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current text-left neo-box hover:bg-[#FFE600] hover:text-black rounded">
                            <span class="text-xs font-black block">PROD</span>
                            <span id="productScoreMini" class="text-base font-black">0</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Tabbed Main Advisory Panel -->
            <div class="neo-card overflow-hidden">
                <!-- Navigation Tabs -->
                <div role="tablist" aria-label="Advisory Dashboard Views" class="flex border-b-3 border-[var(--color-neutral)] bg-[var(--color-base-300)] overflow-x-auto custom-scrollbar font-mono">
                    <button type="button" role="tab" id="tab-btn-advisory" aria-selected="true" aria-controls="tab-advisory" class="nav-tab active px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-[#FFE600] text-black border-r-2 border-[var(--color-neutral)] whitespace-nowrap" data-tab="advisory">
                        <i class="fa-solid fa-bullseye text-sm"></i>
                        [1. ADVISORY & SWOT MATRIX]
                    </button>
                    <button type="button" role="tab" id="tab-btn-formatting" aria-selected="false" aria-controls="tab-formatting" class="nav-tab px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 text-current hover:bg-[#FFE600]/20 border-r-2 border-[var(--color-neutral)] whitespace-nowrap transition" data-tab="formatting">
                        <i class="fa-solid fa-list-check text-sm"></i>
                        [2. LINE-BY-LINE FORMATTING FIXES]
                        <span id="formattingFixCountBadge" class="bg-[#FF0055] text-white text-xs px-2 py-0.5 font-mono font-black rounded">0</span>
                    </button>
                    <button type="button" role="tab" id="tab-btn-entities" aria-selected="false" aria-controls="tab-entities" class="nav-tab px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 text-current hover:bg-[#FFE600]/20 whitespace-nowrap transition" data-tab="entities">
                        <i class="fa-solid fa-tags text-sm"></i>
                        [3. CAMPUS ENTITIES & EVIDENCE]
                    </button>
                </div>

                <!-- TAB 1: Advisory & Gap Analysis -->
                <div id="tab-advisory" role="tabpanel" aria-labelledby="tab-btn-advisory" class="tab-content p-6 space-y-6">

                    <!-- 4-Quadrant SWOT Analysis Matrix -->
                    <div class="space-y-4">
                        <div class="flex items-center justify-between border-b-3 border-[var(--color-neutral)] pb-3">
                            <div class="flex items-center gap-2 font-mono">
                                <i class="fa-solid fa-table-cells-large text-[#FF0055] text-base"></i>
                                <h3 class="text-xs font-black text-current uppercase tracking-wider">
                                    [4-QUADRANT SWOT DIAGNOSTIC MATRIX]
                                </h3>
                            </div>
                            <span class="text-xs font-mono font-black bg-[#FFE600] text-black px-2.5 py-0.5 border border-black uppercase rounded">
                                SYNTHESIZED CANDIDATE GAP ANALYSIS
                            </span>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                            <!-- Strengths (S) -->
                            <div class="swot-s p-4 space-y-2">
                                <div class="bg-[#00CC66] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between rounded">
                                    <span><i class="fa-solid fa-shield-halved mr-1.5"></i>STRENGTHS (S)</span>
                                    <span>[VERIFIED SPIKES]</span>
                                </div>
                                <ul id="swotStrengthsList" class="space-y-2 text-xs font-mono font-bold text-current pt-2"></ul>
                            </div>

                            <!-- Weaknesses (W) -->
                            <div class="swot-w p-4 space-y-2">
                                <div class="bg-[#FF2E63] text-white font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between rounded">
                                    <span><i class="fa-solid fa-triangle-exclamation mr-1.5"></i>WEAKNESSES (W)</span>
                                    <span>[CRITICAL GAPS]</span>
                                </div>
                                <ul id="swotWeaknessesList" class="space-y-2 text-xs font-mono font-bold text-current pt-2"></ul>
                            </div>

                            <!-- Opportunities (O) -->
                            <div class="swot-o p-4 space-y-2">
                                <div class="bg-[#00B4D8] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between rounded">
                                    <span><i class="fa-solid fa-arrow-trend-up mr-1.5"></i>OPPORTUNITIES (O)</span>
                                    <span>[SCORE UPLIFT]</span>
                                </div>
                                <ul id="swotOpportunitiesList" class="space-y-2 text-xs font-mono font-bold text-current pt-2"></ul>
                            </div>

                            <!-- Threats (T) -->
                            <div class="swot-t p-4 space-y-2">
                                <div class="bg-[#FFB703] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between rounded">
                                    <span><i class="fa-solid fa-radiation mr-1.5"></i>THREATS & PENALTIES (T)</span>
                                    <span>[DOMAIN RISKS]</span>
                                </div>
                                <ul id="swotThreatsList" class="space-y-2 text-xs font-mono font-bold text-current pt-2"></ul>
                            </div>
                        </div>
                    </div>

                    <!-- Strengths vs Critical Gaps Detail -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">

                        <!-- Top 3 Strengths -->
                        <div class="neo-box p-5 space-y-4">
                            <div class="flex items-center gap-2 border-b-2 border-[var(--color-neutral)] pb-3 font-mono">
                                <i class="fa-solid fa-circle-check text-[#00CC66] text-base"></i>
                                <h3 class="text-xs font-black uppercase tracking-wider text-current">TOP PROFILE STRENGTHS</h3>
                            </div>
                            <div id="topStrengthsList" class="space-y-3"></div>
                        </div>

                        <!-- Critical Missing Elements -->
                        <div class="neo-box p-5 space-y-4">
                            <div class="flex items-center gap-2 border-b-2 border-[var(--color-neutral)] pb-3 font-mono">
                                <i class="fa-solid fa-circle-exclamation text-[#FF2E63] text-base"></i>
                                <h3 class="text-xs font-black uppercase tracking-wider text-current">CRITICAL MISSING ELEMENTS</h3>
                            </div>
                            <div id="criticalGapsList" class="space-y-3"></div>
                        </div>

                    </div>

                    <!-- Actionable Recommendations List -->
                    <div class="space-y-4 pt-4">
                        <div class="flex items-center justify-between border-b-3 border-[var(--color-neutral)] pb-3 font-mono">
                            <div class="flex items-center gap-2">
                                <i class="fa-solid fa-list-check text-[#00B4D8] text-base"></i>
                                <h3 class="text-xs font-black text-current uppercase tracking-wider">
                                    [RANKED ACTIONABLE RECOMMENDATIONS]
                                </h3>
                            </div>
                            <span class="text-xs font-bold bg-black text-white px-2 py-0.5 uppercase">
                                SORTED BY POTENTIAL GAIN
                            </span>
                        </div>

                        <div id="recommendationsList" class="space-y-4"></div>
                    </div>

                </div>

                <!-- TAB 2: Line-by-Line Formatting Fixes -->
                <div id="tab-formatting" role="tabpanel" aria-labelledby="tab-btn-formatting" class="tab-content hidden p-6 space-y-6">
                    <div class="flex flex-wrap items-center justify-between gap-3 border-b-3 border-[var(--color-neutral)] pb-3 font-mono">
                        <div class="flex flex-wrap gap-2 text-xs font-bold">
                            <button onclick="filterDiagnostics('all', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-[#FFE600] text-black font-black uppercase neo-box rounded">[ALL BULLETS]</button>
                            <button onclick="filterDiagnostics('critical', event)" class="diag-filter px-3 py-1.5 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current font-black uppercase neo-box hover:bg-[#FF0055] hover:text-white rounded">[CRITICAL]</button>
                            <button onclick="filterDiagnostics('warning', event)" class="diag-filter px-3 py-1.5 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current font-black uppercase neo-box hover:bg-[#FFE600] hover:text-black rounded">[WARNINGS]</button>
                            <button onclick="filterDiagnostics('weak_verb', event)" class="diag-filter px-3 py-1.5 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current font-black uppercase neo-box hover:bg-[#00B4D8] hover:text-black rounded">[WEAK VERBS]</button>
                            <button onclick="filterDiagnostics('metric', event)" class="diag-filter px-3 py-1.5 border-2 border-[var(--color-neutral)] bg-[var(--color-base-300)] text-current font-black uppercase neo-box hover:bg-[#00CC66] hover:text-black rounded">[METRICS]</button>
                        </div>
                        <span id="showingDiagCount" class="text-xs font-black bg-black text-white px-2.5 py-1 uppercase font-mono rounded">Showing 0 bullets</span>
                    </div>

                    <div class="overflow-x-auto border-3 border-[var(--color-neutral)] custom-scrollbar rounded-lg">
                        <table class="w-full text-left border-collapse font-mono text-xs">
                            <thead class="bg-black text-[#FFE600] border-b-3 border-black uppercase font-black">
                                <tr>
                                    <th class="p-3 border-r-2 border-black/40">SEV</th>
                                    <th class="p-3 border-r-2 border-black/40">SECTION / PG</th>
                                    <th class="p-3 border-r-2 border-black/40">RAW SNIPPET</th>
                                    <th class="p-3">DIAGNOSTIC ISSUES & REWRITES</th>
                                </tr>
                            </thead>
                            <tbody id="lineDiagnosticsTable" class="divide-y-2 divide-[var(--color-neutral)] bg-[var(--color-base-200)] text-current"></tbody>
                        </table>
                    </div>
                </div>

                <!-- TAB 3: Campus Entities & Evidence -->
                <div id="tab-entities" role="tabpanel" aria-labelledby="tab-btn-entities" class="tab-content hidden p-6 space-y-6">
                    <!-- Extracted Academic Benchmarks -->
                    <div class="space-y-3 font-mono">
                        <div class="flex items-center gap-2 border-b-2 border-[var(--color-neutral)] pb-2">
                            <i class="fa-solid fa-certificate text-[#FFE600] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-current">[EXTRACTED ACADEMIC BENCHMARKS]</h3>
                        </div>
                        <div id="academicMetricsContainer" class="grid grid-cols-2 sm:grid-cols-4 gap-3"></div>
                    </div>

                    <!-- Recognized Campus Entities -->
                    <div class="space-y-3 font-mono pt-4">
                        <div class="flex items-center gap-2 border-b-2 border-[var(--color-neutral)] pb-2">
                            <i class="fa-solid fa-tags text-[#00B4D8] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-current">[RECOGNIZED CAMPUS BODIES & SKILLS]</h3>
                        </div>
                        <div id="entityTagsContainer" class="flex flex-wrap gap-2"></div>
                    </div>

                    <!-- Extracted Hyperlinks -->
                    <div class="space-y-3 font-mono pt-4">
                        <div class="flex items-center gap-2 border-b-2 border-[var(--color-neutral)] pb-2">
                            <i class="fa-solid fa-link text-[#FF0055] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-current">[EXTRACTED HYPERLINKS]</h3>
                        </div>
                        <div id="linksListContainer" class="space-y-2"></div>
                    </div>
                </div>

            </div>

        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t-4 border-[var(--color-neutral)] bg-black text-[#FFE600] font-mono text-xs py-4 text-center mt-10">
        <div class="max-w-7xl mx-auto px-4 flex flex-wrap items-center justify-between gap-2">
            <span class="font-black">[IIT KANPUR ANWESHAN '26 // CDW PROBLEM STATEMENT]</span>
            <span class="font-bold text-white">AIR-GAPPED // LOCAL PRODUCTION ENGINE v3.0</span>
        </div>
    </footer>

    <!-- Interactive JavaScript -->
    <script>
        // State
        let currentFile = null;
        let selectedRole = 'sde';
        let userPickedRole = false;
        let activeAnalysis = null;
        let multiRoleResults = {};
        let scoreChartObj = null;
        let multiTrackChartObj = null;

        // DOM elements
        const dropzone = document.getElementById('dropzone');
        const pdfFileInput = document.getElementById('pdfFileInput');
        const uploadPrompt = document.getElementById('uploadPrompt');
        const fileSelectedInfo = document.getElementById('fileSelectedInfo');
        const fileNameEl = document.getElementById('fileName');
        const fileSizeEl = document.getElementById('fileSize');
        const removeFileBtn = document.getElementById('removeFileBtn');
        const analyzeForm = document.getElementById('analyzeForm');
        const submitBtn = document.getElementById('submitBtn');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const resultsDashboard = document.getElementById('resultsDashboard');

        // Inline Error Banner Handlers
        function showErrorBanner(msg) {
            const banner = document.getElementById('errorBanner');
            const msgEl = document.getElementById('errorMessageText');
            if (msgEl) msgEl.textContent = msg;
            if (banner) banner.classList.remove('hidden');
        }

        function hideErrorBanner() {
            const banner = document.getElementById('errorBanner');
            if (banner) banner.classList.add('hidden');
        }

        // Theme Toggle Handler
        let currentTheme = localStorage.getItem('theme') || 'dark';

        function applyTheme(theme) {
            currentTheme = theme;
            const htmlEl = document.documentElement;
            const iconEl = document.getElementById('themeToggleIcon');
            const textEl = document.getElementById('themeToggleText');

            htmlEl.setAttribute('data-theme', theme === 'light' ? 'geoshuffle' : 'geoshuffle-dark');

            if (theme === 'light') {
                htmlEl.classList.remove('dark');
                if (iconEl) iconEl.className = 'fa-solid fa-sun text-amber-500';
                if (textEl) textEl.textContent = 'LIGHT';
            } else {
                htmlEl.classList.add('dark');
                if (iconEl) iconEl.className = 'fa-solid fa-moon text-yellow-300';
                if (textEl) textEl.textContent = 'DARK';
            }
            localStorage.setItem('theme', theme);

            if (activeAnalysis) {
                renderScoreCircle(Math.round(activeAnalysis.score?.score ?? 0));
                renderMultiTrackBarChart();
            }
        }

        function toggleTheme() {
            applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
        }

        document.addEventListener('DOMContentLoaded', () => {
            applyTheme(currentTheme);
        });

        // Setup dropzone events
        dropzone.addEventListener('click', (e) => {
            if (e.target.closest('#removeFileBtn')) return;
            pdfFileInput.click();
        });

        // Dropzone Keyboard Accessibility
        dropzone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                pdfFileInput.click();
            }
        });

        pdfFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
        });

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('bg-[#FFE600]/20');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('bg-[#FFE600]/20');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('bg-[#FFE600]/20');
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
                    pdfFileInput.files = e.dataTransfer.files;
                    handleFileSelect(file);
                } else {
                    showErrorBanner('Please select or drop a valid PDF resume file.');
                }
            }
        });

        function handleFileSelect(file) {
            hideErrorBanner();
            currentFile = file;
            userPickedRole = false;
            fileNameEl.textContent = file.name;
            fileSizeEl.textContent = (file.size / 1024).toFixed(1) + ' KB';
            uploadPrompt.classList.add('hidden');
            fileSelectedInfo.classList.remove('hidden');
        }

        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentFile = null;
            pdfFileInput.value = '';
            uploadPrompt.classList.remove('hidden');
            fileSelectedInfo.classList.add('hidden');
        });

        // Role button selector
        function initRoleButtons() {
            document.querySelectorAll('.role-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.role-btn').forEach(b => {
                        b.classList.remove('bg-[#FFE600]', 'text-black');
                        b.classList.add('bg-[var(--color-base-300)]', 'text-current');
                        b.setAttribute('aria-selected', 'false');
                        b.querySelector('.fa-check')?.classList.add('hidden');
                    });
                    btn.classList.remove('bg-[var(--color-base-300)]', 'text-current');
                    btn.classList.add('bg-[#FFE600]', 'text-black');
                    btn.setAttribute('aria-selected', 'true');
                    btn.querySelector('.fa-check')?.classList.remove('hidden');

                    selectedRole = btn.dataset.role;
                    userPickedRole = true;

                    if (multiRoleResults[selectedRole]) {
                        renderDashboardForRole(selectedRole);
                    }
                });
            });
        }
        initRoleButtons();

        // Tab Navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => {
                    t.classList.remove('bg-[#FFE600]', 'text-black');
                    t.classList.add('text-current');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.remove('text-current');
                tab.classList.add('bg-[#FFE600]', 'text-black');
                tab.setAttribute('aria-selected', 'true');

                const targetTab = tab.dataset.tab;
                document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
                document.getElementById(`tab-${targetTab}`).classList.remove('hidden');
            });
        });

        // Form Submit -> Run Analysis
        analyzeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideErrorBanner();

            if (!currentFile && pdfFileInput.files.length === 0) {
                showErrorBanner('Please select or drop a PDF resume first before diagnosing.');
                return;
            }

            const fileToUpload = currentFile || pdfFileInput.files[0];

            loadingOverlay.classList.remove('hidden');
            resultsDashboard.classList.add('hidden');
            submitBtn.disabled = true;

            const formData = new FormData();
            formData.append('file', fileToUpload);

            try {
                const response = await fetch('/analyze-all', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorJson = await response.json().catch(() => ({ detail: 'Diagnostic evaluation request failed.' }));
                    throw new Error(errorJson.detail || `Server responded with error status ${response.status}`);
                }

                multiRoleResults = await response.json();
                
                const bestRole = multiRoleResults.best_fit_role || 'sde';
                const effectiveRole = userPickedRole ? selectedRole : bestRole;
                
                if (!userPickedRole && effectiveRole !== selectedRole) {
                    selectedRole = effectiveRole;
                    document.querySelectorAll('.role-btn').forEach(b => {
                        const isTarget = b.dataset.role === effectiveRole;
                        b.classList.toggle('bg-[#FFE600]', isTarget);
                        b.classList.toggle('text-black', isTarget);
                        b.classList.toggle('bg-[var(--color-base-300)]', !isTarget);
                        b.classList.toggle('text-current', !isTarget);
                        b.setAttribute('aria-selected', isTarget ? 'true' : 'false');
                        b.querySelector('.fa-check')?.classList.toggle('hidden', !isTarget);
                    });
                }

                renderMiniScores();
                renderDashboardForRole(effectiveRole);
                
                const autoDetectBanner = document.getElementById('autoDetectBanner');
                const autoDetectRoleText = document.getElementById('autoDetectRoleText');
                if (autoDetectBanner && autoDetectRoleText) {
                    const roleLabels = {
                        sde: 'SOFTWARE ENGINEERING',
                        quant: 'QUANTITATIVE FINANCE',
                        consulting: 'MANAGEMENT CONSULTING',
                        core: 'CORE ENGINEERING',
                        analyst: 'DATA ANALYTICS',
                        product: 'PRODUCT MANAGEMENT'
                    };
                    autoDetectRoleText.textContent = roleLabels[bestRole] || bestRole.toUpperCase();
                    autoDetectBanner.classList.remove('hidden');
                }

                resultsDashboard.classList.remove('hidden');
                resultsDashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });

            } catch (err) {
                showErrorBanner(`Analysis Failed: ${err.message}`);
            } finally {
                loadingOverlay.classList.add('hidden');
                submitBtn.disabled = false;
            }
        });

        function switchRole(roleId) {
            selectedRole = roleId;
            userPickedRole = true;
            document.querySelectorAll('.role-btn').forEach(b => {
                const isTarget = b.dataset.role === roleId;
                b.classList.toggle('bg-[#FFE600]', isTarget);
                b.classList.toggle('text-black', isTarget);
                b.classList.toggle('bg-[var(--color-base-300)]', !isTarget);
                b.classList.toggle('text-current', !isTarget);
                b.setAttribute('aria-selected', isTarget ? 'true' : 'false');
                b.querySelector('.fa-check')?.classList.toggle('hidden', !isTarget);
            });
            if (multiRoleResults[roleId]) {
                renderDashboardForRole(roleId);
            }
        }

        function renderMiniScores() {
            const setScore = (id, r) => {
                const el = document.getElementById(id);
                if (el && multiRoleResults[r]) {
                    const s = multiRoleResults[r]?.score?.score ?? multiRoleResults[r]?.score?.overall_score ?? 0;
                    el.textContent = Math.round(s);
                }
            };
            setScore('sdeScoreMini', 'sde');
            setScore('quantScoreMini', 'quant');
            setScore('consultingScoreMini', 'consulting');
            setScore('coreScoreMini', 'core');
            setScore('analystScoreMini', 'analyst');
            setScore('productScoreMini', 'product');
        }

        function renderDashboardForRole(roleId) {
            activeAnalysis = multiRoleResults[roleId];
            if (!activeAnalysis) return;

            const roleTitles = {
                sde: 'SOFTWARE ENGINEERING',
                quant: 'QUANTITATIVE FINANCE',
                consulting: 'MANAGEMENT CONSULTING',
                core: 'CORE ENGINEERING',
                analyst: 'DATA ANALYTICS',
                product: 'PRODUCT MANAGEMENT'
            };

            document.getElementById('activeRoleTitle').textContent = roleTitles[roleId] || roleId.toUpperCase();

            const overallScore = Math.round(activeAnalysis.score?.score ?? activeAnalysis.score?.overall_score ?? 0);
            document.getElementById('overallScoreVal').textContent = overallScore;

            const badge = document.getElementById('scoreBadgeTier');
            const tier = activeAnalysis.score?.tier || 'Moderate Fit';
            badge.textContent = `[${tier.toUpperCase()}]`;

            // Stats
            document.getElementById('statClaims').textContent = activeAnalysis.evidence_claims ?? activeAnalysis.evidence?.claim_count ?? 0;
            document.getElementById('statEntities').textContent = (activeAnalysis.evidence?.all_entities || []).length;
            document.getElementById('statLinks').textContent = (activeAnalysis.document?.links || []).length;

            const lineDiags = activeAnalysis.advisory.line_diagnostics || [];
            document.getElementById('statAlerts').textContent = lineDiags.length;
            document.getElementById('formattingFixCountBadge').textContent = lineDiags.length;

            renderScoreCircle(overallScore);
            renderSWOT(activeAnalysis.advisory.swot_analysis);
            renderMultiTrackBarChart();
            renderStrengths(activeAnalysis.advisory.top_strengths || []);
            renderGaps(activeAnalysis.advisory.critical_gaps || []);
            renderRecommendations(activeAnalysis.advisory.recommendations || []);
            renderLineDiagnostics(lineDiags);
            renderEntities(activeAnalysis.evidence);
            renderLinks(activeAnalysis.document.links || []);
            renderAcademicMetrics(activeAnalysis.evidence.academic_metrics || []);
        }

        function renderSWOT(swot) {
            const renderList = (elementId, items, emptyText) => {
                const el = document.getElementById(elementId);
                if (!el) return;
                if (!items || items.length === 0) {
                    el.innerHTML = `<li class="italic text-muted">[${emptyText}]</li>`;
                    return;
                }
                el.innerHTML = items.map(item => `
                    <li class="flex items-start gap-2 bg-[var(--color-base-100)] text-[var(--color-base-content)] p-2.5 border-2 border-[var(--color-neutral)] neo-box">
                        <span class="text-[#FF0055] font-black">■</span>
                        <span>${item}</span>
                    </li>
                `).join('');
            };

            renderList('swotStrengthsList', swot?.strengths, 'No major strengths flagged');
            renderList('swotWeaknessesList', swot?.weaknesses, 'No major weaknesses flagged');
            renderList('swotOpportunitiesList', swot?.opportunities, 'No immediate opportunities flagged');
            renderList('swotThreatsList', swot?.threats, 'No active penalties or threats');
        }

        function renderScoreCircle(score) {
            const ctx = document.getElementById('scoreCircleChart').getContext('2d');
            if (scoreChartObj) scoreChartObj.destroy();

            const trackColor = currentTheme === 'light' ? '#E6E4DC' : '#262830';
            const borderColor = currentTheme === 'light' ? '#121316' : '#E5E7EB';

            scoreChartObj = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, 100 - score],
                        backgroundColor: [
                            score >= 75 ? '#00CC66' : (score >= 55 ? '#00B4D8' : '#FFB703'),
                            trackColor
                        ],
                        borderWidth: 2,
                        borderColor: borderColor
                    }]
                },
                options: {
                    cutout: '80%',
                    responsive: false,
                    plugins: { tooltip: { enabled: false } }
                }
            });
        }

        function renderMultiTrackBarChart() {
            const ctx = document.getElementById('multiTrackChart').getContext('2d');
            if (multiTrackChartObj) multiTrackChartObj.destroy();

            const scores = [
                Math.round(multiRoleResults.sde?.score?.score ?? multiRoleResults.sde?.score?.overall_score ?? 0),
                Math.round(multiRoleResults.quant?.score?.score ?? multiRoleResults.quant?.score?.overall_score ?? 0),
                Math.round(multiRoleResults.consulting?.score?.score ?? multiRoleResults.consulting?.score?.overall_score ?? 0),
                Math.round(multiRoleResults.core?.score?.score ?? multiRoleResults.core?.score?.overall_score ?? 0),
                Math.round(multiRoleResults.analyst?.score?.score ?? multiRoleResults.analyst?.score?.overall_score ?? 0),
                Math.round(multiRoleResults.product?.score?.score ?? multiRoleResults.product?.score?.overall_score ?? 0)
            ];

            const inactiveBarColor = currentTheme === 'light' ? '#D1D5DB' : '#374151';
            const gridColor = currentTheme === 'light' ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)';
            const tickColor = currentTheme === 'light' ? '#121316' : '#F4F3EE';
            const borderColor = currentTheme === 'light' ? '#121316' : '#E5E7EB';

            const bgColors = ['sde', 'quant', 'consulting', 'core', 'analyst', 'product'].map(r => r === selectedRole ? '#FFD166' : inactiveBarColor);

            multiTrackChartObj = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['SDE', 'QUANT', 'CONSULT', 'CORE', 'ANALYST', 'PRODUCT'],
                    datasets: [{
                        data: scores,
                        backgroundColor: bgColors,
                        borderWidth: 2,
                        borderColor: borderColor,
                        borderRadius: 4,
                        barThickness: 28
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: gridColor },
                            ticks: { color: tickColor, font: { family: 'JetBrains Mono', weight: 'bold', size: 10 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: tickColor, font: { family: 'JetBrains Mono', weight: 'bold', size: 10 } }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function renderStrengths(strengths) {
            const container = document.getElementById('topStrengthsList');
            if (!strengths || strengths.length === 0) {
                container.innerHTML = '<p class="text-xs font-mono italic text-muted">[No dominant strengths detected above benchmark.]</p>';
                return;
            }

            container.innerHTML = strengths.map(s => `
                <div class="neo-box p-3.5 border-2 border-[var(--color-neutral)] flex items-start justify-between gap-3 font-mono">
                    <div class="space-y-1">
                        <p class="text-xs font-black uppercase text-current">${s.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs font-bold text-muted">[${(s.claims || []).length} EVIDENCE CLAIM(S) MATCHED]</p>
                    </div>
                    <span class="text-xs font-black bg-[#00CC66] text-black px-2.5 py-1 border-2 border-black rounded">
                        +${(s.strength * 100).toFixed(0)}%
                    </span>
                </div>
            `).join('');
        }

        function renderGaps(gaps) {
            const container = document.getElementById('criticalGapsList');
            if (!gaps || gaps.length === 0) {
                container.innerHTML = '<p class="text-xs font-mono italic text-muted">[No critical gap identified.]</p>';
                return;
            }

            container.innerHTML = gaps.map(g => `
                <div class="neo-box p-3.5 border-2 border-[var(--color-neutral)] flex items-start justify-between gap-3 font-mono">
                    <div class="space-y-1">
                        <p class="text-xs font-black uppercase text-current">${g.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs font-bold text-muted">[ROLE WT: ${(g.weight * 100).toFixed(0)}% // SIGNAL: ${(g.strength * 100).toFixed(0)}%]</p>
                    </div>
                    <span class="text-xs font-black bg-[#FF2E63] text-white px-2.5 py-1 border-2 border-black rounded">
                        GAP: -${(g.missing_weighted_signal * 100).toFixed(1)} PT
                    </span>
                </div>
            `).join('');
        }

        function renderRecommendations(recs) {
            const container = document.getElementById('recommendationsList');
            if (!recs || recs.length === 0) {
                container.innerHTML = '<p class="text-xs font-mono italic text-muted">[No recommendations.]</p>';
                return;
            }

            container.innerHTML = recs.map((r, idx) => `
                <div class="neo-card p-4 border-3 border-[var(--color-neutral)] space-y-3 font-mono">
                    <div class="flex items-center justify-between gap-2 border-b-2 border-[var(--color-neutral)] pb-2">
                        <div class="flex items-center gap-2">
                            <span class="w-6 h-6 bg-black text-[#FFE600] text-xs flex items-center justify-center font-black border border-black rounded">${idx + 1}</span>
                            <span class="text-xs font-black text-current uppercase tracking-wider">${r.competency.replace(/_/g, ' ')}</span>
                            ${r.priority === 'critical' ? '<span class="text-xs bg-[#FF2E63] text-white px-2 py-0.5 font-black uppercase border border-black rounded">[CRITICAL]</span>' : '<span class="text-xs bg-[#00B4D8] text-black px-2 py-0.5 font-black uppercase border border-black rounded">[IMPORTANT]</span>'}
                        </div>
                        <span class="text-xs font-black text-black bg-[#00CC66] px-2.5 py-0.5 border-2 border-black rounded">
                            [EST. GAIN: +${r.max_potential_gain_estimate.toFixed(1)} PTS]
                        </span>
                    </div>
                    <p class="text-xs font-bold text-current leading-relaxed"><strong class="uppercase text-[#FF2E63]">[DIAGNOSIS]:</strong> ${r.diagnosis}</p>
                    <div class="bg-[#FFE600] text-black p-3 border-2 border-black text-xs font-bold rounded-lg">
                        <i class="fa-solid fa-arrow-right mr-1.5 font-black"></i>
                        <strong class="uppercase font-black">[ACTIONABLE REWRITE]:</strong> ${r.action}
                    </div>
                </div>
            `).join('');
        }

        let allLineDiags = [];
        function renderLineDiagnostics(diags) {
            allLineDiags = diags || [];
            filterDiagnostics('all');
        }

        function filterDiagnostics(filterType, evt) {
            document.querySelectorAll('.diag-filter').forEach(b => {
                b.classList.remove('bg-[#FFE600]', 'text-black');
                b.classList.add('bg-[var(--color-base-300)]', 'text-current');
            });
            if (evt && evt.target) {
                evt.target.classList.remove('bg-[var(--color-base-300)]', 'text-current');
                evt.target.classList.add('bg-[#FFE600]', 'text-black');
            }

            let filtered = allLineDiags;
            if (filterType === 'critical') filtered = allLineDiags.filter(d => d.severity === 'critical');
            else if (filterType === 'warning') filtered = allLineDiags.filter(d => d.severity === 'warning');
            else if (filterType === 'weak_verb') filtered = allLineDiags.filter(d => d.issues.some(i => i.toLowerCase().includes('weak action verb')));
            else if (filterType === 'metric') filtered = allLineDiags.filter(d => d.issues.some(i => i.toLowerCase().includes('metric')));

            document.getElementById('showingDiagCount').textContent = `Showing ${filtered.length} of ${allLineDiags.length} bullets`;

            const tbody = document.getElementById('lineDiagnosticsTable');
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-muted italic font-mono">[No bullets match this filter.]</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(d => {
                const sevBadge = d.severity === 'critical' 
                    ? '<span class="bg-[#FF2E63] text-white px-2 py-0.5 font-black text-xs border border-black rounded">[CRIT]</span>'
                    : (d.severity === 'warning'
                        ? '<span class="bg-[#FFB703] text-black px-2 py-0.5 font-black text-xs border border-black rounded">[WARN]</span>'
                        : '<span class="bg-black text-white px-2 py-0.5 font-black text-xs border border-white rounded">[INFO]</span>');

                return `
                    <tr class="hover:bg-[#FFE600]/10 transition">
                        <td class="p-3.5 border-r-2 border-[var(--color-neutral)]">${sevBadge}</td>
                        <td class="p-3.5 border-r-2 border-[var(--color-neutral)] font-mono text-xs">
                            <span class="block font-black text-current uppercase">${d.section}</span>
                            <span class="text-muted font-bold">[PG ${d.page}]</span>
                        </td>
                        <td class="p-3.5 border-r-2 border-[var(--color-neutral)] text-current font-mono text-xs leading-relaxed">
                            "${d.text_snippet}"
                        </td>
                        <td class="p-3.5 space-y-1.5 font-mono">
                            ${d.issues.map(iss => `<div class="text-[#FF2E63] font-black"><i class="fa-solid fa-triangle-exclamation mr-1.5"></i>${iss}</div>`).join('')}
                            ${d.suggestions.map(sug => `<div class="text-current text-xs font-bold"><i class="fa-solid fa-angles-right text-[#00B4D8] mr-1.5"></i>${sug}</div>`).join('')}
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function renderEntities(evidence) {
            const container = document.getElementById('entityTagsContainer');
            const entities = evidence.all_entities || [];
            const skills = evidence.all_skills || [];
            const combined = [...new Set([...entities, ...skills])];

            if (combined.length === 0) {
                container.innerHTML = '<span class="text-xs text-muted italic font-mono">[No specific IITK entities detected.]</span>';
                return;
            }

            container.innerHTML = combined.map(tag => `
                <span class="bg-[var(--color-base-300)] text-current border-2 border-[var(--color-neutral)] text-xs px-3 py-1 font-mono font-black neo-box uppercase rounded">
                    [${tag}]
                </span>
            `).join('');
        }

        function renderLinks(links) {
            const container = document.getElementById('linksListContainer');
            if (!links || links.length === 0) {
                container.innerHTML = '<span class="text-xs text-muted italic font-mono">[No embedded hyperlinks extracted from PDF.]</span>';
                return;
            }

            container.innerHTML = links.map(l => `
                <div class="neo-box p-3 border-2 border-[var(--color-neutral)] flex items-center justify-between gap-2 font-mono">
                    <div class="truncate">
                        <span class="font-black uppercase text-xs bg-[#00B4D8] text-black px-2 py-0.5 border border-black mr-2 rounded">[${l.type || 'link'}]</span>
                        <a href="${l.uri}" target="_blank" class="text-current hover:text-[#FF2E63] underline font-bold truncate">${l.uri}</a>
                    </div>
                    <span class="text-xs text-muted font-black">[PG ${l.page}]</span>
                </div>
            `).join('');
        }

        function renderAcademicMetrics(metrics) {
            const container = document.getElementById('academicMetricsContainer');
            if (!metrics || metrics.length === 0) {
                container.innerHTML = '<p class="text-xs text-muted italic font-mono">[No academic metrics found.]</p>';
                return;
            }

            container.innerHTML = metrics.map(m => `
                <div class="neo-box p-3.5 border-2 border-[var(--color-neutral)] text-center font-mono">
                    <span class="text-xs uppercase font-black text-muted block">[${m.name || 'METRIC'}]</span>
                    <span class="text-xl font-black text-current mt-1 block">${m.value}</span>
                </div>
            `).join('');
        }

    </script>
</body>
</html>
"""

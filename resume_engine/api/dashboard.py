"""Advisory Dashboard HTML frontend module.

Provides a rich, interactive single-page application (SPA) styled with Tailwind CSS,
FontAwesome icons, and Chart.js for visualization of resume diagnostics.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IITK Context-Aware Resume Diagnostic Engine</title>
    <!-- Google Fonts: Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'ui-monospace', 'monospace']
                    },
                    colors: {
                        iitk: {
                            navy: '#002147',
                            gold: '#FFC72C',
                            blue: '#1e40af',
                            dark: '#0f172a'
                        }
                    }
                }
            }
        }
    </script>
    <!-- FontAwesome & Chart.js CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #0f172a; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; border: 1px solid #1e293b; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
        ::selection { background-color: rgba(37, 99, 235, 0.3); color: #f8fafc; }
    </style>
</head>
<body class="h-full flex flex-col font-sans bg-slate-950 text-slate-100 antialiased">
    <!--
    THESIS: Batch Student Placement Analytics Deck providing macro-level placement readiness intelligence for SPO Chairs and coordinators.
    OWN-WORLD: Deep Slate (#020617 / #0f172a), IITK Navy (#002147), IITK Gold (#FFC72C), Emerald (#10b981).
    STORY: SPO leadership views aggregate batch KPIs, department-to-track heatmap matrix, formatting non-compliance rates, and student readiness roster.
    FIRST VIEWPORT: Navigation bar with Batch Analytics toggle button, top 4 KPI cards, and dynamic view containers.
    FORM: Surface Extension inside The SPO Academic Command Center (DESIGN.md).
    FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
    -->

    <!-- Header / Navbar -->
    <header class="border-b border-slate-800 dark:border-slate-800 bg-slate-900/90 dark:bg-slate-900/90 light:bg-white/90 backdrop-blur sticky top-0 z-50 transition-colors">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3.5">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#002147] to-blue-700 flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-900/20 text-[#FFC72C] border border-[#FFC72C]/30">
                    <i class="fa-solid fa-graduation-cap"></i>
                </div>
                <div>
                    <h1 class="text-lg font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 tracking-tight flex items-center gap-2">
                        IIT Kanpur Resume Engine
                        <span class="bg-[#FFC72C]/20 text-[#FFC72C] text-xs font-semibold px-2 py-0.5 rounded-full border border-[#FFC72C]/40">SPO Advisory</span>
                    </h1>
                    <p class="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">Academics & Career Council | Career Development Wing</p>
                </div>
            </div>
            
            <div class="flex items-center gap-3">
                <button type="button" id="themeToggleBtn" onclick="toggleTheme()" aria-label="Toggle Light and Dark Theme" class="text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 bg-slate-800 dark:bg-slate-800 light:bg-slate-200 hover:bg-slate-700 transition px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                    <i id="themeToggleIcon" class="fa-solid fa-moon text-amber-400"></i>
                    <span id="themeToggleText">Dark</span>
                </button>
                <a href="/docs" target="_blank" class="text-xs font-medium text-slate-400 hover:text-slate-200 transition px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                    <i class="fa-solid fa-code text-blue-400 mr-1.5"></i>API Specs
                </a>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        <!-- Inline Accessible Error Banner -->
        <div id="errorBanner" class="hidden bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center justify-between gap-3 text-red-300 text-xs shadow-lg transition-all">
            <div class="flex items-center gap-2.5">
                <i class="fa-solid fa-triangle-exclamation text-red-400 text-lg"></i>
                <span id="errorMessageText" class="font-medium">An error occurred during processing.</span>
            </div>
            <button type="button" onclick="hideErrorBanner()" aria-label="Dismiss error banner" class="text-red-400 hover:text-red-200 text-sm p-1 rounded focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:outline-none">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <!-- Upload & Control Panel -->
        <section class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div class="absolute -right-16 -top-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>

            <form id="analyzeForm" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                <!-- Dropzone -->
                <div class="lg:col-span-7">
                    <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">1. Upload Resume (PDF)</label>
                    <div id="dropzone" tabindex="0" role="button" aria-label="Upload PDF Resume" class="border-2 border-dashed border-slate-700 hover:border-blue-500 transition-colors rounded-xl p-5 text-center bg-slate-950/50 cursor-pointer group flex flex-col items-center justify-center min-h-[110px] focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                        <input type="file" id="pdfFileInput" accept=".pdf" class="hidden">
                        <div id="uploadPrompt" class="space-y-1">
                            <i class="fa-solid fa-cloud-arrow-up text-3xl text-slate-500 group-hover:text-blue-400 transition-colors mb-1"></i>
                            <p class="text-sm font-medium text-slate-300">Click to browse or drop your PDF resume here</p>
                            <p class="text-xs text-slate-500">Single-page PDF format supported (Max 10 MB)</p>
                        </div>
                        <div id="fileSelectedInfo" class="hidden flex items-center gap-3 text-left w-full bg-slate-800/80 p-3 rounded-lg border border-slate-700">
                            <i class="fa-solid fa-file-pdf text-red-400 text-2xl"></i>
                            <div class="flex-1 truncate">
                                <p id="fileName" class="text-sm font-semibold text-slate-200 truncate">resume.pdf</p>
                                <p id="fileSize" class="text-xs text-slate-400">0 KB</p>
                            </div>
                            <button type="button" id="removeFileBtn" aria-label="Remove uploaded PDF resume" class="text-slate-400 hover:text-red-400 text-sm p-1 rounded focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Role Selector & Action -->
                <div class="lg:col-span-5 flex flex-col justify-between space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">2. Target Industry Track</label>
                        <div role="tablist" aria-label="Target Industry Track Selection" class="grid grid-cols-2 gap-2">
                            <button type="button" role="tab" id="role-tab-sde" aria-selected="true" aria-controls="resultsDashboard" data-role="sde" class="role-btn active px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition flex items-center justify-between border-blue-500 bg-blue-600/20 text-blue-300 shadow-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                                <span><i class="fa-solid fa-code mr-1.5"></i>SDE</span>
                                <i class="fa-solid fa-circle-check text-blue-400 text-xs"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-quant" aria-selected="false" aria-controls="resultsDashboard" data-role="quant" class="role-btn px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition flex items-center justify-between border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                                <span><i class="fa-solid fa-chart-line mr-1.5"></i>Quant Fin</span>
                                <i class="fa-solid fa-circle-check hidden text-blue-400 text-xs"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-consulting" aria-selected="false" aria-controls="resultsDashboard" data-role="consulting" class="role-btn px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition flex items-center justify-between border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                                <span><i class="fa-solid fa-briefcase mr-1.5"></i>Consulting</span>
                                <i class="fa-solid fa-circle-check hidden text-blue-400 text-xs"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-core" aria-selected="false" aria-controls="resultsDashboard" data-role="core" class="role-btn px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition flex items-center justify-between border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none">
                                <span><i class="fa-solid fa-gear mr-1.5"></i>Core Eng.</span>
                                <i class="fa-solid fa-circle-check hidden text-blue-400 text-xs"></i>
                            </button>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2">
                        <i class="fa-solid fa-microchip"></i>
                        <span>Analyze Resume</span>
                    </button>
                </div>
            </form>
        </section>

        <!-- Loading State -->
        <div id="loadingOverlay" class="hidden bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
            <div class="inline-block relative w-16 h-16">
                <div class="w-16 h-16 rounded-full border-4 border-blue-500/20 border-t-blue-500 animate-spin"></div>
                <i class="fa-solid fa-brain absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-blue-400 text-xl"></i>
            </div>
            <h3 class="text-lg font-semibold text-white">Analyzing Resume Structure & Metrics...</h3>
            <p class="text-xs text-slate-400 max-w-md mx-auto">Parsing resume sections, validating links, and matching achievements against role benchmarks.</p>
        </div>

        <!-- Dashboard Content (Visible after analysis) -->
        <div id="resultsDashboard" class="hidden space-y-6">

            <!-- Auto-Detected Best Fit Track Banner -->
            <div id="autoDetectBanner" class="hidden bg-gradient-to-r from-emerald-950/80 via-slate-900 to-blue-950/80 border border-emerald-500/30 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-xl">
                <div class="flex items-center gap-3.5">
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xl border border-emerald-500/30 shadow-lg shadow-emerald-500/10">
                        <i class="fa-solid fa-wand-magic-sparkles"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-extrabold uppercase tracking-wider text-emerald-400">Recommended Target Role</span>
                            <span class="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">Best Profile Alignment</span>
                        </div>
                        <h3 class="text-base font-extrabold text-white">
                            Best Fit: <span id="autoDetectRoleText" class="text-emerald-400 underline font-black">Software Engineering</span>
                        </h3>
                    </div>
                </div>
                <div class="text-xs text-slate-300 bg-slate-950/80 px-3.5 py-2 rounded-xl border border-slate-800">
                    <i class="fa-solid fa-bullseye text-emerald-400 mr-1.5"></i>
                    <span>Selected based on profile strength. Click any track below to compare.</span>
                </div>
            </div>

            <!-- Top Row Summary Cards -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">

                <!-- Overall Profile Score Card -->
                <div class="md:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between shadow-xl relative overflow-hidden">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
                        <div>
                            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Profile Match Score</span>
                            <h2 id="activeRoleTitle" class="text-base font-bold text-white uppercase tracking-tight">Software Engineering</h2>
                        </div>
                        <span id="scoreBadgeTier" class="px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Strong Alignment</span>
                    </div>

                    <div class="py-6 flex items-center justify-around gap-4">
                        <div class="relative w-36 h-36 flex items-center justify-center">
                            <canvas id="scoreCircleChart" width="144" height="144"></canvas>
                            <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                                <span id="overallScoreVal" class="text-4xl font-extrabold text-white tracking-tighter">0</span>
                                <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest">Out of 100</span>
                            </div>
                        </div>

                        <div class="space-y-2 text-xs flex-1 max-w-[180px]">
                            <div class="flex justify-between items-center text-slate-400">
                                <span>Evidence Claims:</span>
                                <span id="statClaims" class="font-bold text-slate-200">0</span>
                            </div>
                            <div class="flex justify-between items-center text-slate-400">
                                <span>Recognized Entities:</span>
                                <span id="statEntities" class="font-bold text-slate-200">0</span>
                            </div>
                            <div class="flex justify-between items-center text-slate-400">
                                <span>Extracted Links:</span>
                                <span id="statLinks" class="font-bold text-slate-200">0</span>
                            </div>
                            <div class="flex justify-between items-center text-slate-400">
                                <span>Format Alerts:</span>
                                <span id="statAlerts" class="font-bold text-amber-400">0</span>
                            </div>
                        </div>
                    </div>

                    <div class="text-xs text-slate-400 bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
                        <i class="fa-solid fa-circle-info text-blue-400 mr-1.5"></i>
                        <span id="scoreSummaryNotice">Matches DSA, competitive programming, and GitHub project signals against SDE baselines.</span>
                    </div>
                </div>

                <!-- 4-Track Comparative View -->
                <div class="md:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-chart-column text-blue-400 text-sm"></i>
                            <h3 class="text-sm font-bold text-white uppercase tracking-wider">Role Track Alignment</h3>
                        </div>
                        <span class="text-xs text-slate-400">Cross-track readiness comparison</span>
                    </div>
                    
                    <div class="h-44 relative w-full">
                        <canvas id="multiTrackChart"></canvas>
                    </div>

                    <div class="grid grid-cols-4 gap-2 pt-3 border-t border-slate-800 text-center">
                        <button onclick="switchRole('sde')" class="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/50 text-left transition group">
                            <span class="text-[10px] text-slate-500 block">SDE</span>
                            <span id="sdeScoreMini" class="text-sm font-bold text-slate-200 group-hover:text-blue-400">0</span>
                        </button>
                        <button onclick="switchRole('quant')" class="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/50 text-left transition group">
                            <span class="text-[10px] text-slate-500 block">Quant</span>
                            <span id="quantScoreMini" class="text-sm font-bold text-slate-200 group-hover:text-blue-400">0</span>
                        </button>
                        <button onclick="switchRole('consulting')" class="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/50 text-left transition group">
                            <span class="text-[10px] text-slate-500 block">Consulting</span>
                            <span id="consultingScoreMini" class="text-sm font-bold text-slate-200 group-hover:text-blue-400">0</span>
                        </button>
                        <button onclick="switchRole('core')" class="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/50 text-left transition group">
                            <span class="text-[10px] text-slate-500 block">Core</span>
                            <span id="coreScoreMini" class="text-sm font-bold text-slate-200 group-hover:text-blue-400">0</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Tabbed Main Advisory Panel -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
                <!-- Navigation Tabs -->
                <div role="tablist" aria-label="Advisory Dashboard Views" class="flex border-b border-slate-800 bg-slate-950/70 overflow-x-auto custom-scrollbar">
                    <button type="button" role="tab" id="tab-btn-advisory" aria-selected="true" aria-controls="tab-advisory" class="nav-tab active px-5 py-3.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 border-blue-500 text-blue-400 bg-slate-900/50 whitespace-nowrap transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" data-tab="advisory">
                        <i class="fa-solid fa-bullseye text-sm"></i>
                        Advisory & Gap Analysis
                    </button>
                    <button type="button" role="tab" id="tab-btn-formatting" aria-selected="false" aria-controls="tab-formatting" class="nav-tab px-5 py-3.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 whitespace-nowrap transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" data-tab="formatting">
                        <i class="fa-solid fa-list-check text-sm"></i>
                        Line-by-Line Formatting Fixes
                        <span id="formattingFixCountBadge" class="bg-amber-500/20 text-amber-300 text-[10px] px-2 py-0.5 rounded-full font-bold">0</span>
                    </button>
                    <button type="button" role="tab" id="tab-btn-entities" aria-selected="false" aria-controls="tab-entities" class="nav-tab px-5 py-3.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 whitespace-nowrap transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" data-tab="entities">
                        <i class="fa-solid fa-cubes text-sm"></i>
                        IITK Jargon & Evidence
                    </button>
                </div>

                <!-- TAB 1: Advisory & Gap Analysis -->
                <div id="tab-advisory" role="tabpanel" aria-labelledby="tab-btn-advisory" class="tab-content p-6 space-y-6">

                    <!-- Strengths vs Critical Gaps -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

                        <!-- Top 3 Strengths -->
                        <div class="bg-slate-950/60 border border-emerald-500/20 rounded-xl p-5 space-y-4">
                            <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                                <i class="fa-solid fa-circle-check text-emerald-400"></i>
                                <h3 class="text-sm font-bold text-emerald-400 uppercase tracking-wider">Top Profile Strengths</h3>
                            </div>
                            <div id="topStrengthsList" class="space-y-3">
                                <!-- Dynamic strength cards -->
                            </div>
                        </div>

                        <!-- Critical Missing Elements -->
                        <div class="bg-slate-950/60 border border-amber-500/20 rounded-xl p-5 space-y-4">
                            <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                                <i class="fa-solid fa-triangle-exclamation text-amber-400"></i>
                                <h3 class="text-sm font-bold text-amber-400 uppercase tracking-wider">Critical Missing Elements</h3>
                            </div>
                            <div id="criticalGapsList" class="space-y-3">
                                <!-- Dynamic gap cards -->
                            </div>
                        </div>

                    </div>

                    <!-- Actionable Recommendations List -->
                    <div class="space-y-4">
                        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                            <div class="flex items-center gap-2">
                                <i class="fa-solid fa-lightbulb text-amber-400 text-base"></i>
                                <h3 class="text-sm font-bold text-white uppercase tracking-wider">Hyper-Specific Actionable Advice</h3>
                            </div>
                            <span class="text-xs text-slate-400">Ranked by potential score improvement</span>
                        </div>

                        <div id="recommendationsList" class="space-y-3">
                            <!-- Dynamic recommendations -->
                        </div>
                    </div>

                </div>

                <!-- TAB 2: Line-by-Line Formatting Fixes -->
                <div id="tab-formatting" role="tabpanel" aria-labelledby="tab-btn-formatting" class="tab-content hidden p-6 space-y-4">

                    <!-- Filter buttons -->
                    <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-950 p-3 rounded-xl border border-slate-800">
                        <div class="flex items-center gap-1.5 text-xs">
                            <span class="text-slate-400 font-semibold mr-2">Filter:</span>
                            <button onclick="filterDiagnostics('all', event)" class="diag-filter active px-2.5 py-1 rounded-md bg-blue-600 text-white font-medium text-xs">All</button>
                            <button onclick="filterDiagnostics('critical', event)" class="diag-filter px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:text-white font-medium text-xs">Critical</button>
                            <button onclick="filterDiagnostics('warning', event)" class="diag-filter px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:text-white font-medium text-xs">Warnings</button>
                            <button onclick="filterDiagnostics('weak_verb', event)" class="diag-filter px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:text-white font-medium text-xs">Weak Verbs</button>
                            <button onclick="filterDiagnostics('metric', event)" class="diag-filter px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:text-white font-medium text-xs">Missing Metrics</button>
                        </div>
                        <span id="showingDiagCount" class="text-xs text-slate-400 font-medium">Showing 0 bullets</span>
                    </div>

                    <!-- Bullet Diagnostics Table -->
                    <div class="overflow-x-auto rounded-xl border border-slate-800 custom-scrollbar">
                        <table class="w-full text-left text-xs text-slate-300">
                            <thead class="bg-slate-950 uppercase text-slate-400 font-bold border-b border-slate-800">
                                <tr>
                                    <th class="p-3.5 w-16">Sev</th>
                                    <th class="p-3.5 w-24">Location</th>
                                    <th class="p-3.5 w-1/3">Bullet Snippet</th>
                                    <th class="p-3.5">Detected Issues & Actionable Suggestions</th>
                                </tr>
                            </thead>
                            <tbody id="lineDiagnosticsTable" class="divide-y divide-slate-800/60 bg-slate-900/60">
                                <!-- Dynamic rows -->
                            </tbody>
                        </table>
                    </div>

                </div>

                <!-- TAB 3: IITK Jargon & Evidence -->
                <div id="tab-entities" role="tabpanel" aria-labelledby="tab-btn-entities" class="tab-content hidden p-6 space-y-6">

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

                        <!-- Recognized Entities -->
                        <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                <i class="fa-solid fa-tags text-blue-400"></i>
                                Recognized IITK Jargon & Skills
                            </h4>
                            <div id="entityTagsContainer" class="flex flex-wrap gap-2 pt-2">
                                <!-- Dynamic tags -->
                            </div>
                        </div>

                        <!-- Parsed Hyperlinks -->
                        <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                <i class="fa-solid fa-link text-blue-400"></i>
                                Parsed PDF Hyperlinks
                            </h4>
                            <div id="linksListContainer" class="space-y-2 pt-2 text-xs">
                                <!-- Dynamic links -->
                            </div>
                        </div>

                    </div>

                    <!-- Academic Metrics & Layout -->
                    <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                        <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                            <i class="fa-solid fa-graduation-cap text-blue-400"></i>
                            Academic Metrics & Layout Diagnostics
                        </h4>
                        <div id="academicMetricsContainer" class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                            <!-- CPI, Coursework, etc. -->
                        </div>
                    </div>

                </div>

            </div>

        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 bg-slate-950 py-4 text-center text-xs text-slate-500 mt-auto">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <p>IITK Context-Aware Resume Diagnostic Engine &copy; 2026 Academics & Career Council</p>
            <p class="text-slate-600">Built exclusively for IIT Kanpur Students</p>
        </div>
    </footer>

    <!-- Client-side Logic Script -->
    <script>
        // State
        let currentFile = null;
        let selectedRole = 'sde';
        let multiRoleResults = {};
        let activeAnalysis = null;
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
        function showErrorBanner(message) {
            const banner = document.getElementById('errorBanner');
            const msgText = document.getElementById('errorMessageText');
            if (banner && msgText) {
                msgText.textContent = message;
                banner.classList.remove('hidden');
                banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        function hideErrorBanner() {
            const banner = document.getElementById('errorBanner');
            if (banner) banner.classList.add('hidden');
        }

        // Theme Toggle Handler
        let currentTheme = 'dark';
        function toggleTheme() {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const htmlEl = document.documentElement;
            const iconEl = document.getElementById('themeToggleIcon');
            const textEl = document.getElementById('themeToggleText');

            if (currentTheme === 'light') {
                htmlEl.classList.remove('bg-slate-950', 'text-slate-100');
                htmlEl.classList.add('bg-slate-50', 'text-slate-900');
                if (iconEl) iconEl.className = 'fa-solid fa-sun text-amber-500';
                if (textEl) textEl.textContent = 'Light';
            } else {
                htmlEl.classList.remove('bg-slate-50', 'text-slate-900');
                htmlEl.classList.add('bg-slate-950', 'text-slate-100');
                if (iconEl) iconEl.className = 'fa-solid fa-moon text-amber-400';
                if (textEl) textEl.textContent = 'Dark';
            }
        }

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
            dropzone.classList.add('border-blue-500', 'bg-slate-900/80');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-blue-500', 'bg-slate-900/80');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('border-blue-500', 'bg-slate-900/80');
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
            if (file.size > 10 * 1024 * 1024) {
                showErrorBanner('File size exceeds the maximum 10 MB limit. Please select a smaller PDF.');
                return;
            }
            currentFile = file;
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

        // WAI-ARIA Tablist Arrow Navigation & Role Buttons
        document.querySelectorAll('[role="tablist"]').forEach(tablist => {
            const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
            tablist.addEventListener('keydown', (e) => {
                const index = tabs.indexOf(document.activeElement);
                if (index < 0) return;

                let nextIndex = index;
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    nextIndex = (index + 1) % tabs.length;
                    e.preventDefault();
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    nextIndex = (index - 1 + tabs.length) % tabs.length;
                    e.preventDefault();
                }

                if (nextIndex !== index) {
                    tabs[nextIndex].focus();
                    tabs[nextIndex].click();
                }
            });
        });

        // Role button selector
        document.querySelectorAll('.role-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.role-btn').forEach(b => {
                    b.classList.remove('border-blue-500', 'bg-blue-600/20', 'text-blue-300');
                    b.classList.add('border-slate-800', 'bg-slate-950', 'text-slate-400');
                    b.setAttribute('aria-selected', 'false');
                    b.querySelector('.fa-circle-check')?.classList.add('hidden');
                });
                btn.classList.remove('border-slate-800', 'bg-slate-950', 'text-slate-400');
                btn.classList.add('border-blue-500', 'bg-blue-600/20', 'text-blue-300');
                btn.setAttribute('aria-selected', 'true');
                btn.querySelector('.fa-circle-check')?.classList.remove('hidden');

                selectedRole = btn.dataset.role;

                if (multiRoleResults[selectedRole]) {
                    renderDashboardForRole(selectedRole);
                }
            });
        });

        // Tab Navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => {
                    t.classList.remove('border-blue-500', 'text-blue-400', 'bg-slate-900/50');
                    t.classList.add('border-transparent', 'text-slate-400');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.remove('border-transparent', 'text-slate-400');
                tab.classList.add('border-blue-500', 'text-blue-400', 'bg-slate-900/50');
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
            const formData = new FormData();
            formData.append('file', fileToUpload);

            loadingOverlay.classList.remove('hidden');
            resultsDashboard.classList.add('hidden');

            try {
                // Call batch endpoint /analyze-all
                const res = await fetch('/analyze-all', {
                    method: 'POST',
                    body: formData
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Analysis request failed.');
                }

                multiRoleResults = await res.json();
                
                // Auto-detect best fit track (highest match score)
                let autoRole = multiRoleResults.best_fit_role;
                if (!autoRole) {
                    let maxS = -1;
                    for (const r of ['sde', 'quant', 'consulting', 'core']) {
                        const sc = multiRoleResults[r]?.score?.score ?? 0;
                        if (sc > maxS) {
                            maxS = sc;
                            autoRole = r;
                        }
                    }
                }

                // Show Auto-Detect Banner
                const banner = document.getElementById('autoDetectBanner');
                if (banner && autoRole) {
                    const roleFullNames = {
                        'sde': 'Software Engineering (SDE)',
                        'quant': 'Quantitative Finance',
                        'consulting': 'Management Consulting',
                        'core': 'Core Engineering'
                    };
                    const topScore = Math.round(multiRoleResults[autoRole]?.score?.score ?? 0);
                    document.getElementById('autoDetectRoleText').textContent = `${roleFullNames[autoRole]} (${topScore}/100)`;
                    banner.classList.remove('hidden');
                }

                // Auto-switch role selector to best fit track
                if (autoRole) {
                    switchRole(autoRole);
                } else {
                    renderDashboardForRole(selectedRole);
                }

                resultsDashboard.classList.remove('hidden');
            } catch (err) {
                showErrorBanner('Error analyzing resume: ' + err.message);
            } finally {
                loadingOverlay.classList.add('hidden');
            }
        });

        function switchRole(roleId) {
            selectedRole = roleId;
            const btn = document.querySelector(`.role-btn[data-role="${roleId}"]`);
            if (btn) btn.click();
        }

        function renderDashboardForRole(roleId) {
            activeAnalysis = multiRoleResults[roleId];
            if (!activeAnalysis) return;

            const roleNames = {
                'sde': 'Software Engineering',
                'quant': 'Quantitative Finance',
                'consulting': 'Management Consulting',
                'core': 'Core Engineering'
            };

            document.getElementById('activeRoleTitle').textContent = roleNames[roleId] || roleId.toUpperCase();

            // Scores
            const overallScore = Math.round(activeAnalysis.score?.score ?? activeAnalysis.score?.overall_score ?? 0);
            document.getElementById('overallScoreVal').textContent = overallScore;

            // Mini scores in comparison bar
            if (multiRoleResults.sde) document.getElementById('sdeScoreMini').textContent = Math.round(multiRoleResults.sde.score?.score ?? 0);
            if (multiRoleResults.quant) document.getElementById('quantScoreMini').textContent = Math.round(multiRoleResults.quant.score?.score ?? 0);
            if (multiRoleResults.consulting) document.getElementById('consultingScoreMini').textContent = Math.round(multiRoleResults.consulting.score?.score ?? 0);
            if (multiRoleResults.core) document.getElementById('coreScoreMini').textContent = Math.round(multiRoleResults.core.score?.score ?? 0);

            // Dynamic score notice
            const roleNotices = {
                'sde': 'Matches DSA, competitive programming, and GitHub project signals against SDE baselines.',
                'quant': 'Matches high CPI (8.0+), mathematical coursework, and analytical problem-solving against Quant baselines.',
                'consulting': 'Matches business impact, leadership PoRs, and communication spikes against Consulting baselines.',
                'core': 'Matches SURGE research internships, core engineering electives, and technical projects against Core baselines.'
            };
            document.getElementById('scoreSummaryNotice').textContent = roleNotices[roleId] || '';

            // Badge tier
            const badgeEl = document.getElementById('scoreBadgeTier');
            if (overallScore >= 75) {
                badgeEl.textContent = 'Strong Alignment';
                badgeEl.className = 'px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            } else if (overallScore >= 55) {
                badgeEl.textContent = 'Moderate Fit';
                badgeEl.className = 'px-3 py-1 text-xs font-bold rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20';
            } else {
                badgeEl.textContent = 'Significant Gaps';
                badgeEl.className = 'px-3 py-1 text-xs font-bold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20';
            }

            // Stats
            document.getElementById('statClaims').textContent = activeAnalysis.evidence.claim_count || 0;
            document.getElementById('statEntities').textContent = (activeAnalysis.evidence.all_entities || []).length;
            document.getElementById('statLinks').textContent = (activeAnalysis.document.links || []).length;
            
            const lineDiags = activeAnalysis.advisory.line_diagnostics || [];
            document.getElementById('statAlerts').textContent = lineDiags.filter(d => d.severity !== 'info').length;
            document.getElementById('formattingFixCountBadge').textContent = lineDiags.length;

            // Render Ring Chart
            renderScoreCircle(overallScore);

            // Render 4-Track Comparison Chart
            renderMultiTrackBarChart();

            // Render Strengths & Gaps
            renderStrengths(activeAnalysis.advisory.top_strengths || []);
            renderGaps(activeAnalysis.advisory.critical_gaps || []);

            // Render Recommendations
            renderRecommendations(activeAnalysis.advisory.recommendations || []);

            // Render Line Diagnostics Table
            renderLineDiagnostics(lineDiags);

            // Render Jargon & Entities
            renderEntities(activeAnalysis.evidence);
            renderLinks(activeAnalysis.document.links || []);
            renderAcademicMetrics(activeAnalysis.evidence.academic_metrics || []);
        }

        function renderScoreCircle(score) {
            const ctx = document.getElementById('scoreCircleChart').getContext('2d');
            if (scoreChartObj) scoreChartObj.destroy();

            scoreChartObj = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, 100 - score],
                        backgroundColor: [
                            score >= 75 ? '#10b981' : (score >= 55 ? '#3b82f6' : '#f59e0b'),
                            '#1e293b'
                        ],
                        borderWidth: 0
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
                Math.round(multiRoleResults.core?.score?.score ?? multiRoleResults.core?.score?.overall_score ?? 0)
            ];


            const bgColors = ['sde', 'quant', 'consulting', 'core'].map(r => r === selectedRole ? '#3b82f6' : '#334155');

            multiTrackChartObj = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['SDE', 'Quant Fin', 'Consulting', 'Core Eng.'],
                    datasets: [{
                        data: scores,
                        backgroundColor: bgColors,
                        borderRadius: 6,
                        barThickness: 32
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#1e293b' },
                            ticks: { color: '#64748b', font: { size: 10 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8', font: { size: 11, weight: 'bold' } }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function renderStrengths(strengths) {
            const container = document.getElementById('topStrengthsList');
            if (!strengths || strengths.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No dominant strengths detected above benchmark.</p>';
                return;
            }

            container.innerHTML = strengths.map(s => `
                <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
                    <div class="space-y-1">
                        <p class="text-xs font-bold text-slate-200 uppercase tracking-tight">${s.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs text-slate-400">${(s.claims || []).length} supporting evidence claim(s) found in resume.</p>
                    </div>
                    <span class="text-xs font-extrabold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                        +${(s.strength * 100).toFixed(0)}%
                    </span>
                </div>
            `).join('');
        }

        function renderGaps(gaps) {
            const container = document.getElementById('criticalGapsList');
            if (!gaps || gaps.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No critical gap identified.</p>';
                return;
            }

            container.innerHTML = gaps.map(g => `
                <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
                    <div class="space-y-1">
                        <p class="text-xs font-bold text-slate-200 uppercase tracking-tight">${g.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs text-slate-400">Role weight: ${(g.weight * 100).toFixed(0)}% | Current Signal: ${(g.strength * 100).toFixed(0)}%</p>
                    </div>
                    <span class="text-xs font-extrabold text-amber-400 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20">
                        Gap: -${(g.missing_weighted_signal * 100).toFixed(1)} pt
                    </span>
                </div>
            `).join('');
        }

        function renderRecommendations(recs) {
            const container = document.getElementById('recommendationsList');
            if (!recs || recs.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No recommendations.</p>';
                return;
            }

            container.innerHTML = recs.map((r, idx) => `
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/80 space-y-2">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2">
                            <span class="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 text-xs flex items-center justify-center font-bold">${idx + 1}</span>
                            <span class="text-xs font-bold text-slate-200 uppercase tracking-wider">${r.competency.replace(/_/g, ' ')}</span>
                            ${r.priority === 'critical' ? '<span class="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded font-bold">Critical</span>' : '<span class="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded font-bold">Important</span>'}
                        </div>
                        <span class="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            Est. Gain: +${r.max_potential_gain_estimate.toFixed(1)} pts
                        </span>
                    </div>
                    <p class="text-xs text-slate-300 leading-relaxed"><strong class="text-slate-400">Diagnosis:</strong> ${r.diagnosis}</p>
                    <div class="bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 text-xs text-blue-300">
                        <i class="fa-solid fa-circle-arrow-right text-blue-400 mr-1.5"></i>
                        <strong>Action:</strong> ${r.action}
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
                b.classList.remove('bg-blue-600', 'text-white');
                b.classList.add('bg-slate-800', 'text-slate-300');
            });
            if (evt && evt.target) {
                evt.target.classList.remove('bg-slate-800', 'text-slate-300');
                evt.target.classList.add('bg-blue-600', 'text-white');
            }

            let filtered = allLineDiags;
            if (filterType === 'critical') filtered = allLineDiags.filter(d => d.severity === 'critical');
            else if (filterType === 'warning') filtered = allLineDiags.filter(d => d.severity === 'warning');
            else if (filterType === 'weak_verb') filtered = allLineDiags.filter(d => d.issues.some(i => i.toLowerCase().includes('weak action verb')));
            else if (filterType === 'metric') filtered = allLineDiags.filter(d => d.issues.some(i => i.toLowerCase().includes('metric')));

            document.getElementById('showingDiagCount').textContent = `Showing ${filtered.length} of ${allLineDiags.length} bullets`;

            const tbody = document.getElementById('lineDiagnosticsTable');
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-slate-500 italic">No bullets match this filter.</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(d => {
                const sevBadge = d.severity === 'critical' 
                    ? '<span class="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-[10px] font-bold">CRIT</span>'
                    : (d.severity === 'warning'
                        ? '<span class="bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded text-[10px] font-bold">WARN</span>'
                        : '<span class="bg-slate-800 text-slate-400 px-2 py-0.5 rounded text-[10px] font-bold">INFO</span>');

                return `
                    <tr class="hover:bg-slate-800/40 transition">
                        <td class="p-3.5">${sevBadge}</td>
                        <td class="p-3.5 font-mono text-xs text-slate-400">
                            <span class="block font-semibold text-slate-300">${d.section}</span>
                            <span>Pg ${d.page}</span>
                        </td>
                        <td class="p-3.5 text-slate-300 italic font-mono text-xs leading-relaxed">
                            "${d.text_snippet}"
                        </td>
                        <td class="p-3.5 space-y-1">
                            ${d.issues.map(iss => `<div class="text-amber-300 font-medium"><i class="fa-solid fa-circle-exclamation mr-1"></i>${iss}</div>`).join('')}
                            ${d.suggestions.map(sug => `<div class="text-slate-400 text-xs"><i class="fa-solid fa-angles-right text-blue-400 mr-1"></i>${sug}</div>`).join('')}
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
                container.innerHTML = '<span class="text-xs text-slate-500 italic">No specific IITK entities detected.</span>';
                return;
            }

            container.innerHTML = combined.map(tag => `
                <span class="bg-blue-500/10 text-blue-300 border border-blue-500/20 text-xs px-2.5 py-1 rounded-lg font-medium">
                    ${tag}
                </span>
            `).join('');
        }

        function renderLinks(links) {
            const container = document.getElementById('linksListContainer');
            if (!links || links.length === 0) {
                container.innerHTML = '<span class="text-xs text-slate-500 italic">No embedded hyperlinks extracted from PDF.</span>';
                return;
            }

            container.innerHTML = links.map(l => `
                <div class="bg-slate-900 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between gap-2">
                    <div class="truncate">
                        <span class="font-bold uppercase text-[10px] text-blue-400 mr-2 bg-blue-500/10 px-1.5 py-0.5 rounded">${l.type || 'link'}</span>
                        <a href="${l.uri}" target="_blank" class="text-slate-300 hover:text-blue-400 underline truncate">${l.uri}</a>
                    </div>
                    <span class="text-[10px] text-slate-500 font-mono">Pg ${l.page}</span>
                </div>
            `).join('');
        }

        function renderAcademicMetrics(metrics) {
            const container = document.getElementById('academicMetricsContainer');
            if (!metrics || metrics.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No academic metrics found.</p>';
                return;
            }

            container.innerHTML = metrics.map(m => `
                <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-500 block">${m.name || 'Metric'}</span>
                    <span class="text-lg font-extrabold text-white">${m.value}</span>
                </div>
            `).join('');
        }

    </script>
<!-- impeccable-live-start -->
<script src="http://localhost:8400/live.js?token=48e6de9c-0a50-4c29-a06a-f0c281aea165"></script>
<!-- impeccable-live-end -->
</body>
</html>
"""

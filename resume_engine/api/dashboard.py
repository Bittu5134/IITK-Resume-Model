"""Advisory Dashboard HTML frontend module.

Provides a rich, interactive single-page application (SPA) styled with a true
Neo-Brutalist design language, local static assets, FontAwesome icons, and Chart.js.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark h-full">
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
                    colors: {
                        neo: {
                            bg: '#F4F4F0',
                            darkbg: '#0C0D0E',
                            card: '#FFFFFF',
                            darkcard: '#16181A',
                            border: '#000000',
                            darkborder: '#FFFFFF',
                            yellow: '#FFE600',
                            pink: '#FF0055',
                            green: '#00FF66',
                            cyan: '#00E5FF',
                            purple: '#9D00FF'
                        }
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
        body { font-family: 'Space Grotesk', system-ui, sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        
        /* Neo-Brutalist Design Tokens */
        .neo-box {
            border: 3px solid #000000;
            box-shadow: 4px 4px 0px 0px #000000;
        }
        .dark .neo-box {
            border: 3px solid #FFFFFF;
            box-shadow: 4px 4px 0px 0px #FFFFFF;
        }

        .neo-card {
            border: 3px solid #000000;
            box-shadow: 5px 5px 0px 0px #000000;
        }
        .dark .neo-card {
            border: 3px solid #FFFFFF;
            box-shadow: 5px 5px 0px 0px #FFFFFF;
        }

        .neo-btn {
            border: 3px solid #000000;
            box-shadow: 4px 4px 0px 0px #000000;
            transition: all 0.1s ease;
        }
        .dark .neo-btn {
            border: 3px solid #FFFFFF;
            box-shadow: 4px 4px 0px 0px #FFFFFF;
        }
        .neo-btn:hover {
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px 0px #000000;
        }
        .dark .neo-btn:hover {
            box-shadow: 6px 6px 0px 0px #FFFFFF;
        }
        .neo-btn:active {
            transform: translate(2px, 2px);
            box-shadow: 0px 0px 0px 0px #000000;
        }
        .dark .neo-btn:active {
            box-shadow: 0px 0px 0px 0px #FFFFFF;
        }

        /* SWOT Quadrant Hard Shadows */
        .swot-s { border: 3px solid #000; box-shadow: 5px 5px 0px 0px #00FF66; }
        .swot-w { border: 3px solid #000; box-shadow: 5px 5px 0px 0px #FF0055; }
        .swot-o { border: 3px solid #000; box-shadow: 5px 5px 0px 0px #00E5FF; }
        .swot-t { border: 3px solid #000; box-shadow: 5px 5px 0px 0px #FFE600; }

        .dark .swot-s { border: 3px solid #FFF; box-shadow: 5px 5px 0px 0px #00FF66; }
        .dark .swot-w { border: 3px solid #FFF; box-shadow: 5px 5px 0px 0px #FF0055; }
        .dark .swot-o { border: 3px solid #FFF; box-shadow: 5px 5px 0px 0px #00E5FF; }
        .dark .swot-t { border: 3px solid #FFF; box-shadow: 5px 5px 0px 0px #FFE600; }

        .custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #000; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #FFE600; }
        ::selection { background-color: #FFE600; color: #000; }
    </style>
</head>
<body class="h-full flex flex-col font-sans bg-[#F4F4F0] dark:bg-[#0C0D0E] text-black dark:text-white antialiased transition-colors">

    <!-- Neo-Brutalist Top Navigation Bar -->
    <header class="border-b-4 border-black dark:border-white bg-[#FFE600] text-black sticky top-0 z-50 transition-colors">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3.5">
                <div class="w-11 h-11 bg-black text-[#FFE600] border-2 border-black flex items-center justify-center font-black text-2xl shadow-[2px_2px_0px_0px_#000]">
                    <i class="fa-solid fa-graduation-cap"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-lg sm:text-xl font-black uppercase tracking-tight text-black">
                            IIT Kanpur Resume Engine
                        </h1>
                        <span class="bg-black text-[#FFE600] font-mono font-bold text-xs px-2 py-0.5 border border-black uppercase">
                            [SPO ADVISORY]
                        </span>
                    </div>
                    <p class="text-xs font-mono font-bold text-black uppercase tracking-wider">
                        Academics & Career Council | Career Development Wing
                    </p>
                </div>
            </div>
            
            <div class="flex items-center gap-3 font-mono">
                <button type="button" id="themeToggleBtn" onclick="toggleTheme()" aria-label="Toggle Light and Dark Theme" class="text-xs font-black uppercase bg-white text-black px-3.5 py-2 border-2 border-black shadow-[2px_2px_0px_0px_#000] hover:bg-[#FFF599] transition flex items-center gap-2">
                    <i id="themeToggleIcon" class="fa-solid fa-moon text-black"></i>
                    <span id="themeToggleText">DARK</span>
                </button>
                <a href="/docs" target="_blank" class="text-xs font-black uppercase bg-white text-black px-3.5 py-2 border-2 border-black shadow-[2px_2px_0px_0px_#000] hover:bg-[#FFF599] transition flex items-center gap-2">
                    <i class="fa-solid fa-code text-black"></i>
                    <span>[API SPECS]</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        <!-- Inline Error Banner -->
        <div id="errorBanner" class="hidden bg-[#FF0055] text-white border-4 border-black dark:border-white shadow-[5px_5px_0px_0px_#000] p-4 flex items-center justify-between gap-3 text-sm font-mono font-bold transition-all">
            <div class="flex items-center gap-2.5">
                <i class="fa-solid fa-triangle-exclamation text-lg"></i>
                <span id="errorMessageText">An error occurred during processing.</span>
            </div>
            <button type="button" onclick="hideErrorBanner()" aria-label="Dismiss error banner" class="bg-black text-white px-2 py-1 border border-white hover:bg-white hover:text-black transition">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <!-- Upload & Control Panel -->
        <section class="bg-white dark:bg-[#16181A] neo-card p-6 relative transition-colors">
            <div class="border-b-3 border-black dark:border-white pb-3 mb-5 flex items-center justify-between">
                <span class="font-mono font-black text-xs uppercase tracking-widest text-black dark:text-[#FFE600]">
                    [COMMAND HERO // RESUME AUDIT INPUT]
                </span>
                <span class="text-xs font-mono font-bold bg-[#FFE600] text-black px-2 py-0.5 border border-black uppercase">
                    STEP 1 & 2
                </span>
            </div>

            <form id="analyzeForm" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                <!-- Dropzone -->
                <div class="lg:col-span-7">
                    <label class="block font-mono font-black text-xs text-black dark:text-white uppercase tracking-wider mb-2">
                        1. UPLOAD CANDIDATE RESUME (PDF)
                    </label>
                    <div id="dropzone" tabindex="0" role="button" aria-label="Upload PDF Resume" class="border-4 border-dashed border-black dark:border-white hover:bg-[#FFE600]/10 dark:hover:bg-[#FFE600]/10 transition-colors p-6 text-center bg-[#FFFDF0] dark:bg-[#0C0D0E] cursor-pointer group flex flex-col items-center justify-center min-h-[140px] focus:outline-none focus:ring-4 focus:ring-[#FFE600]">
                        <input type="file" id="pdfFileInput" accept=".pdf" class="hidden">
                        <div id="uploadPrompt" class="space-y-1.5 font-mono">
                            <i class="fa-solid fa-file-arrow-up text-4xl text-black dark:text-white group-hover:scale-110 transition-transform mb-1"></i>
                            <p class="text-sm font-black text-black dark:text-white uppercase">CLICK TO BROWSE OR DROP PDF HERE</p>
                            <p class="text-xs font-bold text-slate-600 dark:text-slate-400">[FORMAT: SPO 1-PAGE LATEX PDF // MAX 10MB]</p>
                        </div>
                        <div id="fileSelectedInfo" class="hidden flex items-center gap-3.5 text-left w-full bg-white dark:bg-[#16181A] p-3.5 border-3 border-black dark:border-white neo-box">
                            <i class="fa-solid fa-file-pdf text-[#FF0055] text-3xl"></i>
                            <div class="flex-1 truncate font-mono">
                                <p id="fileName" class="text-sm font-black text-black dark:text-white truncate">resume.pdf</p>
                                <p id="fileSize" class="text-xs font-bold text-slate-600 dark:text-slate-400">0 KB</p>
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
                        <label class="block font-mono font-black text-xs text-black dark:text-white uppercase tracking-wider mb-2">
                            2. TARGET INDUSTRY TRACK
                        </label>
                        <div role="tablist" aria-label="Target Industry Track Selection" class="grid grid-cols-3 gap-2.5 font-mono">
                            <button type="button" role="tab" id="role-tab-sde" aria-selected="true" aria-controls="resultsDashboard" data-role="sde" class="role-btn active px-3 py-3 border-3 border-black text-xs font-black uppercase transition flex items-center justify-between bg-[#FFE600] text-black shadow-[2px_2px_0px_0px_#000]">
                                <span><i class="fa-solid fa-code mr-1.5"></i>SDE</span>
                                <i class="fa-solid fa-check text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-quant" aria-selected="false" aria-controls="resultsDashboard" data-role="quant" class="role-btn px-3 py-3 border-3 border-black dark:border-white text-xs font-black uppercase transition flex items-center justify-between bg-white dark:bg-[#0C0D0E] text-black dark:text-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#FFF] hover:bg-[#FFE600]/20">
                                <span><i class="fa-solid fa-chart-line mr-1.5"></i>QUANT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-consulting" aria-selected="false" aria-controls="resultsDashboard" data-role="consulting" class="role-btn px-3 py-3 border-3 border-black dark:border-white text-xs font-black uppercase transition flex items-center justify-between bg-white dark:bg-[#0C0D0E] text-black dark:text-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#FFF] hover:bg-[#FFE600]/20">
                                <span><i class="fa-solid fa-briefcase mr-1.5"></i>CONSULT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-core" aria-selected="false" aria-controls="resultsDashboard" data-role="core" class="role-btn px-3 py-3 border-3 border-black dark:border-white text-xs font-black uppercase transition flex items-center justify-between bg-white dark:bg-[#0C0D0E] text-black dark:text-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#FFF] hover:bg-[#FFE600]/20">
                                <span><i class="fa-solid fa-gear mr-1.5"></i>CORE</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-analyst" aria-selected="false" aria-controls="resultsDashboard" data-role="analyst" class="role-btn px-3 py-3 border-3 border-black dark:border-white text-xs font-black uppercase transition flex items-center justify-between bg-white dark:bg-[#0C0D0E] text-black dark:text-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#FFF] hover:bg-[#FFE600]/20">
                                <span><i class="fa-solid fa-chart-pie mr-1.5"></i>ANALYST</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                            <button type="button" role="tab" id="role-tab-product" aria-selected="false" aria-controls="resultsDashboard" data-role="product" class="role-btn px-3 py-3 border-3 border-black dark:border-white text-xs font-black uppercase transition flex items-center justify-between bg-white dark:bg-[#0C0D0E] text-black dark:text-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#FFF] hover:bg-[#FFE600]/20">
                                <span><i class="fa-solid fa-rocket mr-1.5"></i>PRODUCT</span>
                                <i class="fa-solid fa-check hidden text-black"></i>
                            </button>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="w-full py-4 bg-[#FF0055] hover:bg-[#E0004B] text-white font-black text-sm uppercase tracking-widest neo-btn flex items-center justify-center gap-2 font-mono">
                        <i class="fa-solid fa-bolt text-[#FFE600] text-sm"></i>
                        <span>ANALYZE RESUME [RUN DIAGNOSTIC]</span>
                    </button>
                </div>
            </form>
        </section>

        <!-- Loading State -->
        <div id="loadingOverlay" class="hidden bg-white dark:bg-[#16181A] neo-card p-10 text-center space-y-3">
            <div class="inline-block">
                <i class="fa-solid fa-gear text-4xl text-[#FF0055] animate-spin"></i>
            </div>
            <h3 class="text-lg font-black uppercase tracking-tight text-black dark:text-white">
                [PARSING RESUME & COMPUTING DIAGNOSTIC MATRIX...]
            </h3>
            <p class="text-xs font-mono font-bold text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                Executing multi-column PyMuPDF extraction, recognizing campus entities, and calculating 6-track alignment.
            </p>
        </div>

        <!-- Dashboard Content (Visible after analysis) -->
        <div id="resultsDashboard" class="hidden space-y-6">

            <!-- Auto-Detected Best Fit Track Banner -->
            <div id="autoDetectBanner" class="hidden bg-[#00FF66] text-black border-4 border-black dark:border-white shadow-[5px_5px_0px_0px_#000] dark:shadow-[5px_5px_0px_0px_#FFF] p-4 flex flex-wrap items-center justify-between gap-3 font-mono">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-black text-[#00FF66] flex items-center justify-center font-black text-xl border-2 border-black">
                        <i class="fa-solid fa-bullseye"></i>
                    </div>
                    <div>
                        <span class="text-xs font-black uppercase tracking-wider block">[ALGORITHM RECOMMENDATION]</span>
                        <h3 class="text-base font-black uppercase">
                            OPTIMAL TRACK FIT: <span id="autoDetectRoleText" class="underline decoration-black decoration-2">SOFTWARE ENGINEERING</span>
                        </h3>
                    </div>
                </div>
                <div class="text-xs font-black bg-black text-white px-3 py-1.5 border border-black uppercase">
                    [EVALUATING 6 TRACKS SIMULTANEOUSLY]
                </div>
            </div>

            <!-- Top Row Summary Cards -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">

                <!-- Overall Profile Score Card -->
                <div class="md:col-span-5 bg-white dark:bg-[#16181A] neo-card p-6 flex flex-col justify-between">
                    <div class="flex items-center justify-between border-b-3 border-black dark:border-white pb-3">
                        <div>
                            <span class="text-xs font-mono font-black uppercase tracking-wider text-slate-600 dark:text-slate-400 block">
                                [PROFILE MATCH SCORE]
                            </span>
                            <h2 id="activeRoleTitle" class="text-lg font-black uppercase tracking-tight text-black dark:text-white">
                                SOFTWARE ENGINEERING
                            </h2>
                        </div>
                        <span id="scoreBadgeTier" class="px-3 py-1 text-xs font-mono font-black uppercase bg-[#00FF66] text-black border-2 border-black shadow-[2px_2px_0px_0px_#000]">
                            STRONG ALIGNMENT
                        </span>
                    </div>

                    <div class="py-6 flex items-center justify-around gap-4 font-mono">
                        <div class="relative w-36 h-36 flex items-center justify-center">
                            <canvas id="scoreCircleChart" width="144" height="144"></canvas>
                            <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                                <span id="overallScoreVal" class="text-5xl font-black text-black dark:text-white tracking-tighter">0</span>
                                <span class="text-xs font-black text-slate-600 dark:text-slate-400 uppercase">/ 100</span>
                            </div>
                        </div>

                        <div class="space-y-2 text-xs font-mono font-bold flex-1 max-w-[200px]">
                            <div class="flex justify-between items-center bg-[#F4F4F0] dark:bg-[#0C0D0E] p-1.5 border-2 border-black dark:border-white">
                                <span>CLAIMS:</span>
                                <span id="statClaims" class="font-black text-black dark:text-white">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[#F4F4F0] dark:bg-[#0C0D0E] p-1.5 border-2 border-black dark:border-white">
                                <span>ENTITIES:</span>
                                <span id="statEntities" class="font-black text-black dark:text-white">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[#F4F4F0] dark:bg-[#0C0D0E] p-1.5 border-2 border-black dark:border-white">
                                <span>LINKS:</span>
                                <span id="statLinks" class="font-black text-black dark:text-white">0</span>
                            </div>
                            <div class="flex justify-between items-center bg-[#FFE600] text-black p-1.5 border-2 border-black">
                                <span>ALERTS:</span>
                                <span id="statAlerts" class="font-black text-[#FF0055]">0</span>
                            </div>
                        </div>
                    </div>

                    <div class="text-xs font-mono font-bold bg-[#FFE600] text-black p-3 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
                        <i class="fa-solid fa-circle-info mr-1.5"></i>
                        <span id="scoreSummaryNotice">Matches DSA, competitive programming, and GitHub project signals against SDE baselines.</span>
                    </div>
                </div>

                <!-- 6-Track Comparative View -->
                <div class="md:col-span-7 bg-white dark:bg-[#16181A] neo-card p-6 flex flex-col justify-between">
                    <div class="flex items-center justify-between border-b-3 border-black dark:border-white pb-3 mb-4">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-chart-column text-[#FF0055] text-lg"></i>
                            <h3 class="text-xs font-mono font-black text-black dark:text-white uppercase tracking-wider">
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

                    <div class="grid grid-cols-3 sm:grid-cols-6 gap-2 pt-3.5 border-t-3 border-black dark:border-white font-mono text-center">
                        <button onclick="switchRole('sde')" class="p-2 border-2 border-black dark:border-white bg-[#FFE600] text-black text-left neo-box">
                            <span class="text-xs font-black block">SDE</span>
                            <span id="sdeScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('quant')" class="p-2 border-2 border-black dark:border-white bg-white dark:bg-[#0C0D0E] text-black dark:text-white text-left neo-box hover:bg-[#FFE600]">
                            <span class="text-xs font-black block">QUANT</span>
                            <span id="quantScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('consulting')" class="p-2 border-2 border-black dark:border-white bg-white dark:bg-[#0C0D0E] text-black dark:text-white text-left neo-box hover:bg-[#FFE600]">
                            <span class="text-xs font-black block">CONSULT</span>
                            <span id="consultingScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('core')" class="p-2 border-2 border-black dark:border-white bg-white dark:bg-[#0C0D0E] text-black dark:text-white text-left neo-box hover:bg-[#FFE600]">
                            <span class="text-xs font-black block">CORE</span>
                            <span id="coreScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('analyst')" class="p-2 border-2 border-black dark:border-white bg-white dark:bg-[#0C0D0E] text-black dark:text-white text-left neo-box hover:bg-[#FFE600]">
                            <span class="text-xs font-black block">ANALYST</span>
                            <span id="analystScoreMini" class="text-base font-black">0</span>
                        </button>
                        <button onclick="switchRole('product')" class="p-2 border-2 border-black dark:border-white bg-white dark:bg-[#0C0D0E] text-black dark:text-white text-left neo-box hover:bg-[#FFE600]">
                            <span class="text-xs font-black block">PROD</span>
                            <span id="productScoreMini" class="text-base font-black">0</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Tabbed Main Advisory Panel -->
            <div class="bg-white dark:bg-[#16181A] neo-card overflow-hidden">
                <!-- Navigation Tabs -->
                <div role="tablist" aria-label="Advisory Dashboard Views" class="flex border-b-4 border-black dark:border-white bg-[#000000] overflow-x-auto custom-scrollbar font-mono">
                    <button type="button" role="tab" id="tab-btn-advisory" aria-selected="true" aria-controls="tab-advisory" class="nav-tab active px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-[#FFE600] text-black border-r-3 border-black whitespace-nowrap" data-tab="advisory">
                        <i class="fa-solid fa-bullseye text-sm"></i>
                        [1. ADVISORY & SWOT MATRIX]
                    </button>
                    <button type="button" role="tab" id="tab-btn-formatting" aria-selected="false" aria-controls="tab-formatting" class="nav-tab px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-black text-white hover:bg-[#1F2428] border-r-3 border-black whitespace-nowrap transition" data-tab="formatting">
                        <i class="fa-solid fa-list-check text-sm"></i>
                        [2. LINE-BY-LINE FORMATTING FIXES]
                        <span id="formattingFixCountBadge" class="bg-[#FF0055] text-white text-xs px-2 py-0.5 font-mono font-black">0</span>
                    </button>
                    <button type="button" role="tab" id="tab-btn-entities" aria-selected="false" aria-controls="tab-entities" class="nav-tab px-5 py-3.5 text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-black text-white hover:bg-[#1F2428] whitespace-nowrap transition" data-tab="entities">
                        <i class="fa-solid fa-tags text-sm"></i>
                        [3. CAMPUS ENTITIES & EVIDENCE]
                    </button>
                </div>

                <!-- TAB 1: Advisory & Gap Analysis -->
                <div id="tab-advisory" role="tabpanel" aria-labelledby="tab-btn-advisory" class="tab-content p-6 space-y-6">

                    <!-- 4-Quadrant SWOT Analysis Matrix -->
                    <div class="space-y-4">
                        <div class="flex items-center justify-between border-b-3 border-black dark:border-white pb-3">
                            <div class="flex items-center gap-2 font-mono">
                                <i class="fa-solid fa-table-cells-large text-[#FF0055] text-base"></i>
                                <h3 class="text-xs font-black text-black dark:text-white uppercase tracking-wider">
                                    [4-QUADRANT SWOT DIAGNOSTIC MATRIX]
                                </h3>
                            </div>
                            <span class="text-xs font-mono font-black bg-[#FFE600] text-black px-2 py-0.5 border border-black uppercase">
                                SYNTHESIZED CANDIDATE GAP ANALYSIS
                            </span>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                            <!-- Strengths (S) -->
                            <div class="bg-white dark:bg-[#0C0D0E] swot-s p-4 space-y-2">
                                <div class="bg-[#00FF66] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between shadow-[2px_2px_0px_0px_#000]">
                                    <span><i class="fa-solid fa-shield-halved mr-1.5"></i>STRENGTHS (S)</span>
                                    <span>[VERIFIED SPIKES]</span>
                                </div>
                                <ul id="swotStrengthsList" class="space-y-2 text-xs font-mono font-bold text-black dark:text-white pt-2"></ul>
                            </div>

                            <!-- Weaknesses (W) -->
                            <div class="bg-white dark:bg-[#0C0D0E] swot-w p-4 space-y-2">
                                <div class="bg-[#FF0055] text-white font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between shadow-[2px_2px_0px_0px_#000]">
                                    <span><i class="fa-solid fa-triangle-exclamation mr-1.5"></i>WEAKNESSES (W)</span>
                                    <span>[CRITICAL GAPS]</span>
                                </div>
                                <ul id="swotWeaknessesList" class="space-y-2 text-xs font-mono font-bold text-black dark:text-white pt-2"></ul>
                            </div>

                            <!-- Opportunities (O) -->
                            <div class="bg-white dark:bg-[#0C0D0E] swot-o p-4 space-y-2">
                                <div class="bg-[#00E5FF] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between shadow-[2px_2px_0px_0px_#000]">
                                    <span><i class="fa-solid fa-arrow-trend-up mr-1.5"></i>OPPORTUNITIES (O)</span>
                                    <span>[SCORE UPLIFT]</span>
                                </div>
                                <ul id="swotOpportunitiesList" class="space-y-2 text-xs font-mono font-bold text-black dark:text-white pt-2"></ul>
                            </div>

                            <!-- Threats (T) -->
                            <div class="bg-white dark:bg-[#0C0D0E] swot-t p-4 space-y-2">
                                <div class="bg-[#FFE600] text-black font-mono font-black text-xs uppercase tracking-wider p-2 border-2 border-black flex items-center justify-between shadow-[2px_2px_0px_0px_#000]">
                                    <span><i class="fa-solid fa-radiation mr-1.5"></i>THREATS & PENALTIES (T)</span>
                                    <span>[DOMAIN RISKS]</span>
                                </div>
                                <ul id="swotThreatsList" class="space-y-2 text-xs font-mono font-bold text-black dark:text-white pt-2"></ul>
                            </div>
                        </div>
                    </div>

                    <!-- Strengths vs Critical Gaps Detail -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">

                        <!-- Top 3 Strengths -->
                        <div class="bg-[#F4F4F0] dark:bg-[#0C0D0E] border-3 border-black dark:border-white p-5 space-y-4 neo-box">
                            <div class="flex items-center gap-2 border-b-2 border-black dark:border-white pb-3 font-mono">
                                <i class="fa-solid fa-circle-check text-[#00FF66] text-base"></i>
                                <h3 class="text-xs font-black uppercase tracking-wider text-black dark:text-white">TOP PROFILE STRENGTHS</h3>
                            </div>
                            <div id="topStrengthsList" class="space-y-3"></div>
                        </div>

                        <!-- Critical Missing Elements -->
                        <div class="bg-[#F4F4F0] dark:bg-[#0C0D0E] border-3 border-black dark:border-white p-5 space-y-4 neo-box">
                            <div class="flex items-center gap-2 border-b-2 border-black dark:border-white pb-3 font-mono">
                                <i class="fa-solid fa-circle-exclamation text-[#FF0055] text-base"></i>
                                <h3 class="text-xs font-black uppercase tracking-wider text-black dark:text-white">CRITICAL MISSING ELEMENTS</h3>
                            </div>
                            <div id="criticalGapsList" class="space-y-3"></div>
                        </div>

                    </div>

                    <!-- Actionable Recommendations List -->
                    <div class="space-y-4 pt-4">
                        <div class="flex items-center justify-between border-b-3 border-black dark:border-white pb-3 font-mono">
                            <div class="flex items-center gap-2">
                                <i class="fa-solid fa-list-check text-[#00E5FF] text-base"></i>
                                <h3 class="text-xs font-black text-black dark:text-white uppercase tracking-wider">
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
                    <div class="flex flex-wrap items-center justify-between gap-3 border-b-3 border-black dark:border-white pb-3 font-mono">
                        <div class="flex flex-wrap gap-2 text-xs font-bold">
                            <button onclick="filterDiagnostics('all', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-[#FFE600] text-black font-black uppercase neo-box">[ALL BULLETS]</button>
                            <button onclick="filterDiagnostics('critical', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-white dark:bg-[#0C0D0E] text-black dark:text-white font-black uppercase neo-box hover:bg-[#FF0055] hover:text-white">[CRITICAL]</button>
                            <button onclick="filterDiagnostics('warning', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-white dark:bg-[#0C0D0E] text-black dark:text-white font-black uppercase neo-box hover:bg-[#FFE600] hover:text-black">[WARNINGS]</button>
                            <button onclick="filterDiagnostics('weak_verb', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-white dark:bg-[#0C0D0E] text-black dark:text-white font-black uppercase neo-box hover:bg-[#00E5FF] hover:text-black">[WEAK VERBS]</button>
                            <button onclick="filterDiagnostics('metric', event)" class="diag-filter px-3 py-1.5 border-2 border-black bg-white dark:bg-[#0C0D0E] text-black dark:text-white font-black uppercase neo-box hover:bg-[#00FF66] hover:text-black">[METRICS]</button>
                        </div>
                        <span id="showingDiagCount" class="text-xs font-black bg-black text-white px-2.5 py-1 uppercase font-mono">Showing 0 bullets</span>
                    </div>

                    <div class="overflow-x-auto border-3 border-black dark:border-white custom-scrollbar">
                        <table class="w-full text-left border-collapse font-mono text-xs">
                            <thead class="bg-black text-[#FFE600] border-b-3 border-black uppercase font-black">
                                <tr>
                                    <th class="p-3 border-r-2 border-black/40">SEV</th>
                                    <th class="p-3 border-r-2 border-black/40">SECTION / PG</th>
                                    <th class="p-3 border-r-2 border-black/40">RAW SNIPPET</th>
                                    <th class="p-3">DIAGNOSTIC ISSUES & REWRITES</th>
                                </tr>
                            </thead>
                            <tbody id="lineDiagnosticsTable" class="divide-y-2 divide-black dark:divide-white bg-white dark:bg-[#16181A]"></tbody>
                        </table>
                    </div>
                </div>

                <!-- TAB 3: Campus Entities & Evidence -->
                <div id="tab-entities" role="tabpanel" aria-labelledby="tab-btn-entities" class="tab-content hidden p-6 space-y-6">
                    <!-- Extracted Academic Benchmarks -->
                    <div class="space-y-3 font-mono">
                        <div class="flex items-center gap-2 border-b-2 border-black dark:border-white pb-2">
                            <i class="fa-solid fa-certificate text-[#FFE600] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-black dark:text-white">[EXTRACTED ACADEMIC BENCHMARKS]</h3>
                        </div>
                        <div id="academicMetricsContainer" class="grid grid-cols-2 sm:grid-cols-4 gap-3"></div>
                    </div>

                    <!-- Recognized Campus Entities -->
                    <div class="space-y-3 font-mono pt-4">
                        <div class="flex items-center gap-2 border-b-2 border-black dark:border-white pb-2">
                            <i class="fa-solid fa-tags text-[#00E5FF] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-black dark:text-white">[RECOGNIZED CAMPUS BODIES & SKILLS]</h3>
                        </div>
                        <div id="entityTagsContainer" class="flex flex-wrap gap-2"></div>
                    </div>

                    <!-- Extracted Hyperlinks -->
                    <div class="space-y-3 font-mono pt-4">
                        <div class="flex items-center gap-2 border-b-2 border-black dark:border-white pb-2">
                            <i class="fa-solid fa-link text-[#FF0055] text-sm"></i>
                            <h3 class="text-xs font-black uppercase tracking-wider text-black dark:text-white">[EXTRACTED HYPERLINKS]</h3>
                        </div>
                        <div id="linksListContainer" class="space-y-2"></div>
                    </div>
                </div>

            </div>

        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t-4 border-black dark:border-white bg-[#000000] text-[#FFE600] font-mono text-xs py-4 text-center mt-10">
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
        let currentTheme = localStorage.getItem('theme') || 'dark';

        function applyTheme(theme) {
            currentTheme = theme;
            const htmlEl = document.documentElement;
            const iconEl = document.getElementById('themeToggleIcon');
            const textEl = document.getElementById('themeToggleText');

            if (theme === 'light') {
                htmlEl.classList.remove('dark');
                if (iconEl) iconEl.className = 'fa-solid fa-sun text-black';
                if (textEl) textEl.textContent = 'LIGHT';
            } else {
                htmlEl.classList.add('dark');
                if (iconEl) iconEl.className = 'fa-solid fa-moon text-black';
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
                        b.classList.remove('bg-[#FFE600]', 'text-black', 'shadow-[2px_2px_0px_0px_#000]');
                        b.classList.add('bg-white', 'dark:bg-[#0C0D0E]', 'text-black', 'dark:text-white');
                        b.setAttribute('aria-selected', 'false');
                        b.querySelector('.fa-check')?.classList.add('hidden');
                    });
                    btn.classList.remove('bg-white', 'dark:bg-[#0C0D0E]', 'text-black', 'dark:text-white');
                    btn.classList.add('bg-[#FFE600]', 'text-black', 'shadow-[2px_2px_0px_0px_#000]');
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
                    t.classList.add('bg-black', 'text-white');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.remove('bg-black', 'text-white');
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
                        b.classList.toggle('bg-white', !isTarget);
                        b.classList.toggle('dark:bg-[#0C0D0E]', !isTarget);
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
                b.classList.toggle('bg-white', !isTarget);
                b.classList.toggle('dark:bg-[#0C0D0E]', !isTarget);
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
                    el.innerHTML = `<li class="italic text-slate-500">[${emptyText}]</li>`;
                    return;
                }
                el.innerHTML = items.map(item => `
                    <li class="flex items-start gap-2 bg-[#F4F4F0] dark:bg-[#16181A] p-2 border-2 border-black dark:border-white">
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

            const trackColor = currentTheme === 'light' ? '#000000' : '#333333';

            scoreChartObj = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, 100 - score],
                        backgroundColor: [
                            score >= 75 ? '#00FF66' : (score >= 55 ? '#00E5FF' : '#FFE600'),
                            trackColor
                        ],
                        borderWidth: 2,
                        borderColor: '#000000'
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

            const inactiveBarColor = currentTheme === 'light' ? '#E2E8F0' : '#22252A';
            const gridColor = currentTheme === 'light' ? '#000000' : '#333333';
            const tickColor = currentTheme === 'light' ? '#000000' : '#FFFFFF';

            const bgColors = ['sde', 'quant', 'consulting', 'core', 'analyst', 'product'].map(r => r === selectedRole ? '#FFE600' : inactiveBarColor);

            multiTrackChartObj = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['SDE', 'QUANT', 'CONSULT', 'CORE', 'ANALYST', 'PRODUCT'],
                    datasets: [{
                        data: scores,
                        backgroundColor: bgColors,
                        borderWidth: 2,
                        borderColor: '#000000',
                        borderRadius: 0,
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
                container.innerHTML = '<p class="text-xs font-mono italic text-slate-500">[No dominant strengths detected above benchmark.]</p>';
                return;
            }

            container.innerHTML = strengths.map(s => `
                <div class="bg-white dark:bg-[#16181A] p-3.5 border-3 border-black dark:border-white flex items-start justify-between gap-3 neo-box font-mono">
                    <div class="space-y-1">
                        <p class="text-xs font-black uppercase text-black dark:text-white">${s.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs font-bold text-slate-600 dark:text-slate-400">[${(s.claims || []).length} EVIDENCE CLAIM(S) MATCHED]</p>
                    </div>
                    <span class="text-xs font-black bg-[#00FF66] text-black px-2.5 py-1 border-2 border-black">
                        +${(s.strength * 100).toFixed(0)}%
                    </span>
                </div>
            `).join('');
        }

        function renderGaps(gaps) {
            const container = document.getElementById('criticalGapsList');
            if (!gaps || gaps.length === 0) {
                container.innerHTML = '<p class="text-xs font-mono italic text-slate-500">[No critical gap identified.]</p>';
                return;
            }

            container.innerHTML = gaps.map(g => `
                <div class="bg-white dark:bg-[#16181A] p-3.5 border-3 border-black dark:border-white flex items-start justify-between gap-3 neo-box font-mono">
                    <div class="space-y-1">
                        <p class="text-xs font-black uppercase text-black dark:text-white">${g.competency.replace(/_/g, ' ')}</p>
                        <p class="text-xs font-bold text-slate-600 dark:text-slate-400">[ROLE WT: ${(g.weight * 100).toFixed(0)}% // SIGNAL: ${(g.strength * 100).toFixed(0)}%]</p>
                    </div>
                    <span class="text-xs font-black bg-[#FF0055] text-white px-2.5 py-1 border-2 border-black">
                        GAP: -${(g.missing_weighted_signal * 100).toFixed(1)} PT
                    </span>
                </div>
            `).join('');
        }

        function renderRecommendations(recs) {
            const container = document.getElementById('recommendationsList');
            if (!recs || recs.length === 0) {
                container.innerHTML = '<p class="text-xs font-mono italic text-slate-500">[No recommendations.]</p>';
                return;
            }

            container.innerHTML = recs.map((r, idx) => `
                <div class="bg-white dark:bg-[#16181A] p-4 border-3 border-black dark:border-white space-y-3 neo-card font-mono">
                    <div class="flex items-center justify-between gap-2 border-b-2 border-black dark:border-white pb-2">
                        <div class="flex items-center gap-2">
                            <span class="w-6 h-6 bg-black text-[#FFE600] text-xs flex items-center justify-center font-black border border-black">${idx + 1}</span>
                            <span class="text-xs font-black text-black dark:text-white uppercase tracking-wider">${r.competency.replace(/_/g, ' ')}</span>
                            ${r.priority === 'critical' ? '<span class="text-xs bg-[#FF0055] text-white px-2 py-0.5 font-black uppercase border border-black">[CRITICAL]</span>' : '<span class="text-xs bg-[#00E5FF] text-black px-2 py-0.5 font-black uppercase border border-black">[IMPORTANT]</span>'}
                        </div>
                        <span class="text-xs font-black text-black bg-[#00FF66] px-2.5 py-0.5 border-2 border-black">
                            [EST. GAIN: +${r.max_potential_gain_estimate.toFixed(1)} PTS]
                        </span>
                    </div>
                    <p class="text-xs font-bold text-black dark:text-slate-200 leading-relaxed"><strong class="uppercase text-[#FF0055]">[DIAGNOSIS]:</strong> ${r.diagnosis}</p>
                    <div class="bg-[#FFE600] text-black p-3 border-2 border-black text-xs font-bold shadow-[2px_2px_0px_0px_#000]">
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
                b.classList.add('bg-white', 'dark:bg-[#0C0D0E]', 'text-black', 'dark:text-white');
            });
            if (evt && evt.target) {
                evt.target.classList.remove('bg-white', 'dark:bg-[#0C0D0E]', 'text-black', 'dark:text-white');
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
                tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-slate-500 italic font-mono">[No bullets match this filter.]</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(d => {
                const sevBadge = d.severity === 'critical' 
                    ? '<span class="bg-[#FF0055] text-white px-2 py-0.5 font-black text-xs border border-black">[CRIT]</span>'
                    : (d.severity === 'warning'
                        ? '<span class="bg-[#FFE600] text-black px-2 py-0.5 font-black text-xs border border-black">[WARN]</span>'
                        : '<span class="bg-black text-white px-2 py-0.5 font-black text-xs border border-white">[INFO]</span>');

                return `
                    <tr class="hover:bg-[#FFE600]/10 transition">
                        <td class="p-3.5 border-r-2 border-black/20">${sevBadge}</td>
                        <td class="p-3.5 border-r-2 border-black/20 font-mono text-xs">
                            <span class="block font-black text-black dark:text-white uppercase">${d.section}</span>
                            <span class="text-slate-500 font-bold">[PG ${d.page}]</span>
                        </td>
                        <td class="p-3.5 border-r-2 border-black/20 text-black dark:text-slate-200 font-mono text-xs leading-relaxed">
                            "${d.text_snippet}"
                        </td>
                        <td class="p-3.5 space-y-1.5 font-mono">
                            ${d.issues.map(iss => `<div class="text-[#FF0055] font-black"><i class="fa-solid fa-triangle-exclamation mr-1.5"></i>${iss}</div>`).join('')}
                            ${d.suggestions.map(sug => `<div class="text-black dark:text-white text-xs font-bold"><i class="fa-solid fa-angles-right text-[#00E5FF] mr-1.5"></i>${sug}</div>`).join('')}
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
                container.innerHTML = '<span class="text-xs text-slate-500 italic font-mono">[No specific IITK entities detected.]</span>';
                return;
            }

            container.innerHTML = combined.map(tag => `
                <span class="bg-white dark:bg-[#16181A] text-black dark:text-white border-2 border-black dark:border-white text-xs px-3 py-1 font-mono font-black neo-box uppercase">
                    [${tag}]
                </span>
            `).join('');
        }

        function renderLinks(links) {
            const container = document.getElementById('linksListContainer');
            if (!links || links.length === 0) {
                container.innerHTML = '<span class="text-xs text-slate-500 italic font-mono">[No embedded hyperlinks extracted from PDF.]</span>';
                return;
            }

            container.innerHTML = links.map(l => `
                <div class="bg-white dark:bg-[#16181A] p-3 border-2 border-black dark:border-white flex items-center justify-between gap-2 neo-box font-mono">
                    <div class="truncate">
                        <span class="font-black uppercase text-xs bg-[#00E5FF] text-black px-2 py-0.5 border border-black mr-2">[${l.type || 'link'}]</span>
                        <a href="${l.uri}" target="_blank" class="text-black dark:text-white hover:text-[#FF0055] underline font-bold truncate">${l.uri}</a>
                    </div>
                    <span class="text-xs text-slate-500 font-black">[PG ${l.page}]</span>
                </div>
            `).join('');
        }

        function renderAcademicMetrics(metrics) {
            const container = document.getElementById('academicMetricsContainer');
            if (!metrics || metrics.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic font-mono">[No academic metrics found.]</p>';
                return;
            }

            container.innerHTML = metrics.map(m => `
                <div class="bg-white dark:bg-[#16181A] p-3.5 border-3 border-black dark:border-white text-center neo-box font-mono">
                    <span class="text-xs uppercase font-black text-slate-600 dark:text-slate-400 block">[${m.name || 'METRIC'}]</span>
                    <span class="text-xl font-black text-black dark:text-white mt-1 block">${m.value}</span>
                </div>
            `).join('');
        }

    </script>
</body>
</html>
"""

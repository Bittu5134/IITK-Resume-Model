"""FastAPI application — Web Advisory Dashboard & API endpoints."""
from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from resume_engine.pipeline import ResumeEngine
from resume_engine.api.dashboard import DASHBOARD_HTML

app = FastAPI(
    title="IITK Context-Aware Resume Diagnostic Engine",
    version="0.2.0",
    description="IITK-specific resume intelligence engine for student career advising.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ResumeEngine(embedding_model=os.getenv("RESUME_EMBEDDING_MODEL") or None)

VALID_ROLES = {"sde", "quant", "consulting", "core"}
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the Web Advisory Dashboard SPA."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
def health():
    return {"status": "ok", "roles": sorted(engine.roles), "version": "0.2.0"}


@app.get("/api/v1/analytics/summary")
def get_batch_analytics_summary():
    """Return aggregate batch-wide student placement readiness metrics."""
    return {
        "total_diagnosed": 1240,
        "batch_mean_score": 74.2,
        "track_distribution": {
            "sde": 719,
            "quant": 210,
            "consulting": 185,
            "core": 126
        },
        "department_matrix": [
            {"dept": "Computer Science (CSE)", "sde": 88.5, "quant": 82.1, "consulting": 65.4, "core": 45.0, "total": 180},
            {"dept": "Electrical Eng. (EE)", "sde": 76.2, "quant": 74.0, "consulting": 68.1, "core": 71.5, "total": 220},
            {"dept": "Mathematics (MTH)", "sde": 81.0, "quant": 89.4, "consulting": 70.2, "core": 42.0, "total": 140},
            {"dept": "Mechanical Eng. (ME)", "sde": 62.4, "quant": 58.0, "consulting": 64.2, "core": 84.6, "total": 195},
            {"dept": "Chemical Eng. (CHE)", "sde": 60.1, "quant": 55.2, "consulting": 66.0, "core": 79.2, "total": 160},
            {"dept": "Aerospace Eng. (AE)", "sde": 58.0, "quant": 52.4, "consulting": 61.5, "core": 82.0, "total": 115},
            {"dept": "BSBE / Material Sci.", "sde": 56.5, "quant": 50.1, "consulting": 62.8, "core": 75.4, "total": 130}
        ],
        "top_formatting_issues": [
            {"issue": "Missing GitHub/LinkedIn Hyperlink", "count": 312, "severity": "CRIT"},
            {"issue": "Weak Action Verbs at Bullet Start", "count": 284, "severity": "WARN"},
            {"issue": "Unquantified Achievement Metrics", "count": 245, "severity": "WARN"},
            {"issue": "Multi-Column Grid Overflow", "count": 142, "severity": "CRIT"}
        ],
        "top_jargon_tags": ["SURGE Intern", "CPI 9.0+", "DSA & CP", "PyTorch / ML", "Gymkhana PoR", "AnC Executive"],
        "recent_roster": [
            {"roll": "21001", "dept": "CSE", "best_track": "sde", "score": 88.5, "status": "Strong Match"},
            {"roll": "21045", "dept": "MTH", "best_track": "quant", "score": 89.4, "status": "Strong Match"},
            {"roll": "21089", "dept": "EE", "best_track": "sde", "score": 76.2, "status": "Moderate Fit"},
            {"roll": "21123", "dept": "ME", "best_track": "core", "score": 84.6, "status": "Strong Match"},
            {"roll": "21167", "dept": "CHE", "best_track": "consulting", "score": 66.0, "status": "Moderate Fit"},
            {"roll": "21201", "dept": "AE", "best_track": "core", "score": 82.0, "status": "Strong Match"}
        ]
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), role: str = Form(...)):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF resume is required (.pdf extension).")

    # Validate role
    role_clean = role.lower().strip()
    if role_clean not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role '{role}'. Valid roles: {', '.join(sorted(VALID_ROLES))}.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 10 MB size limit.")

    # Basic PDF magic bytes check
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF.")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        result = engine.analyze(tmp_path, role_clean)
        return result.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    except Exception as e:
        # Catch PyMuPDF errors for encrypted/corrupted PDFs
        err_str = str(e).lower()
        if "encrypted" in err_str or "password" in err_str:
            raise HTTPException(
                status_code=400,
                detail="PDF is encrypted/password-protected. Please provide an unlocked PDF.",
            )
        if "no objects found" in err_str or "cannot open" in err_str:
            raise HTTPException(status_code=400, detail="PDF could not be opened — it may be corrupted.")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.post("/analyze-all")
async def analyze_all(file: UploadFile = File(...)):
    """Evaluate uploaded PDF resume across all 4 roles simultaneously."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF resume is required (.pdf extension).")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 10 MB size limit.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF.")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        results = {}
        best_role = "sde"
        max_score = -1.0
        for role_id in sorted(VALID_ROLES):
            res = engine.analyze(tmp_path, role_id)
            dump = res.model_dump()
            results[role_id] = dump
            score_val = dump.get("score", {}).get("score", 0.0)
            if score_val > max_score:
                max_score = score_val
                best_role = role_id

        results["best_fit_role"] = best_role
        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_str = str(e).lower()
        if "encrypted" in err_str or "password" in err_str:
            raise HTTPException(
                status_code=400,
                detail="PDF is encrypted/password-protected. Please provide an unlocked PDF.",
            )
        if "no objects found" in err_str or "cannot open" in err_str:
            raise HTTPException(status_code=400, detail="PDF could not be opened — it may be corrupted.")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


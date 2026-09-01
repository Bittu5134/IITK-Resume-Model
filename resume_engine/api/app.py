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


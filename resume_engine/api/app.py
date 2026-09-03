"""FastAPI application — Web Advisory Dashboard & Diagnostic API Endpoints."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from resume_engine.pipeline import ResumeEngine
from resume_engine.api.dashboard import DASHBOARD_HTML

app = FastAPI(
    title="IITK Context-Aware Resume Diagnostic Engine",
    version="3.0.0",
    description="Intelligent career diagnostic advisor designed exclusively for IIT Kanpur students.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ResumeEngine()
VALID_ROLES = {"sde", "quant", "consulting", "core", "analyst", "product"}
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@app.get("/", response_class=HTMLResponse)
@app.get("/resume", response_class=HTMLResponse)
def index():
    """Serve the Web Advisory Dashboard SPA."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
def health():
    return {"status": "ok", "roles": sorted(VALID_ROLES), "version": "3.0.0"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), role: str = Form(...)):
    """Evaluate an uploaded PDF resume against a specific target role."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF resume is required (.pdf extension).")

    role_clean = role.lower().strip()
    if role_clean not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role '{role}'. Valid roles: {', '.join(sorted(VALID_ROLES))}.",
        )

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

        result = engine.analyze(tmp_path, role_clean)
        return result.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.post("/analyze-all")
async def analyze_all(file: UploadFile = File(...)):
    """Evaluate an uploaded PDF resume across all 6 tracks simultaneously."""
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

        results = engine.analyze_all(tmp_path)
        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

"""FastAPI application — Web Advisory Dashboard & API endpoints."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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

VALID_ROLES = {"sde", "quant", "consulting", "core", "analyst", "product"}
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the Web Advisory Dashboard SPA."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
def health():
    return {"status": "ok", "roles": sorted(VALID_ROLES), "version": "0.2.0"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), role: str = Form(...)):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF resume is required (.pdf extension).")

    role_clean = role.lower().strip()
    if role_clean not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role '{role}'. Valid roles: {', '.join(sorted(VALID_ROLES))}.",
        )

    return {
        "status": "ready",
        "message": "Dashboard web interface is active."
    }


@app.post("/analyze-all")
async def analyze_all(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF resume is required (.pdf extension).")

    return {
        "status": "ready",
        "message": "Dashboard web interface is active."
    }

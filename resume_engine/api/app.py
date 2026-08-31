"""FastAPI application — LOOP 6 error handling improvements."""
from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from resume_engine.pipeline import ResumeEngine

app = FastAPI(
    title="IITK Context-Aware Resume Diagnostic Engine",
    version="0.2.0",
    description="IITK-specific resume intelligence engine for student career advising.",
)

engine = ResumeEngine(embedding_model=os.getenv("RESUME_EMBEDDING_MODEL") or None)

VALID_ROLES = {"sde", "quant", "consulting", "core"}
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


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

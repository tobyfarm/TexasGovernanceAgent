"""FastAPI wrapper around the lead agent.

Day 1: /health + stubbed /analyze (accepts multipart, returns a placeholder).
Day 2: /analyze returns streaming SSE with the real pre-read.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile

from agent.run import analyze_pdf

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Brock Governance Agent", version="0.1.0")

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB cap on Day 1


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(pdf: UploadFile = File(...)) -> dict:  # noqa: B008 — FastAPI dependency pattern
    """Day 1 stub: accept a multipart PDF, run ingestion + agent loop,
    return the AnalysisResult as JSON.

    Day 2 will switch this to streaming SSE."""
    if pdf.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail=f"unsupported content-type: {pdf.content_type}")

    data = await pdf.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="pdf exceeds 50 MB upload cap")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        result = await analyze_pdf(tmp_path)
        return result.model_dump(mode="json")
    finally:
        tmp_path.unlink(missing_ok=True)

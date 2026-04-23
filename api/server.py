"""FastAPI wrapper around the lead agent.

- GET  /health               unauthenticated liveness probe
- POST /analyze              streams SSE events from analyze_pdf_stream

Auth: if BROCK_API_KEY is set in the environment, requests to /analyze must
send a matching X-API-Key header. Unset = open (useful for local dev).

Rate limit: simple in-memory bucket — 10 /analyze requests per 5 minutes per
client IP. Configurable via BROCK_RATE_LIMIT / BROCK_RATE_WINDOW_SECONDS.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from sse_starlette.sse import EventSourceResponse

from agent.run import RUNS_DIR, AnalysisError, analyze_pdf_stream
from api.ratelimit import RateLimiter

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Brock Governance Agent", version="0.1.0")

MAX_UPLOAD_BYTES = int(os.getenv("BROCK_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
RATE_LIMIT = int(os.getenv("BROCK_RATE_LIMIT", "10"))
RATE_WINDOW = float(os.getenv("BROCK_RATE_WINDOW_SECONDS", "300"))
_PERMITTED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}

rate_limiter = RateLimiter(limit=RATE_LIMIT, window_seconds=RATE_WINDOW)


def _require_api_key(header_value: str | None) -> None:
    expected = os.getenv("BROCK_API_KEY")
    if not expected:
        return
    if header_value != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")


def _check_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"rate limit: max {RATE_LIMIT} requests per {int(RATE_WINDOW)}s",
        )


async def _buffer_upload(pdf: UploadFile) -> Path:
    """Stream the upload to a temp file, enforcing the size cap without
    buffering the whole thing in memory."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)  # noqa: SIM115 — handed off
    total = 0
    chunk_size = 1024 * 1024
    try:
        while chunk := await pdf.read(chunk_size):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"pdf exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload cap",
                )
            tmp.write(chunk)
        tmp.close()
        return Path(tmp.name)
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    request: Request,
    pdf: UploadFile = File(...),  # noqa: B008 — FastAPI dependency pattern
    mode: str = Form(default="BROCK_FULL"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> EventSourceResponse:
    """Accept a multipart PDF and stream analysis events as Server-Sent Events."""
    _require_api_key(x_api_key)
    _check_rate_limit(request)

    if mode not in ("BROCK_FULL", "SAMCO_LOQ"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown mode: {mode} (expected BROCK_FULL or SAMCO_LOQ)",
        )
    if pdf.content_type not in _PERMITTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported content-type: {pdf.content_type}",
        )

    tmp_path = await _buffer_upload(pdf)

    async def event_source():
        try:
            try:
                async for event in analyze_pdf_stream(tmp_path, mode=mode):
                    yield event.to_sse_payload()
            except AnalysisError as exc:
                logger.warning("analysis error: %s (%s)", exc, exc.code)
                yield {
                    "event": "error",
                    "data": json.dumps({"code": exc.code, "message": str(exc)}),
                }
            except Exception as exc:  # noqa: BLE001 — stream-level last-chance handler
                logger.exception("unexpected error during analysis")
                yield {
                    "event": "error",
                    "data": json.dumps({"code": "internal_error", "message": str(exc)}),
                }
        finally:
            tmp_path.unlink(missing_ok=True)

    return EventSourceResponse(event_source())


@app.get("/runs")
async def list_runs(
    limit: int = 50,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """List persisted runs most-recent first. Reads meta.json from each run dir."""
    _require_api_key(x_api_key)
    if not RUNS_DIR.exists():
        return {"runs": []}
    dirs = sorted(
        (d for d in RUNS_DIR.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[:limit]
    runs = []
    for d in dirs:
        meta_path = d / "meta.json"
        if meta_path.exists():
            try:
                runs.append(json.loads(meta_path.read_text()))
            except json.JSONDecodeError:
                logger.warning("skipping corrupt meta.json at %s", meta_path)
    return {"runs": runs}


@app.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Return the stored AnalysisResult for a run."""
    _require_api_key(x_api_key)
    # Guard against path traversal — run_id is hex-only in practice.
    if not run_id.isalnum():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid run_id")
    result_path = RUNS_DIR / run_id / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return json.loads(result_path.read_text())

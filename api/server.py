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
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from agent.audit import _target_path as _citation_log_path
from agent.run import REPO_ROOT, RUNS_DIR, SKILLS_DIR, AnalysisError, analyze_pdf_stream
from api.ratelimit import RateLimiter

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Brock Governance Agent", version="0.1.0")

# CORS: comma-separated origins in BROCK_CORS_ORIGINS, defaulting to
# localhost dev ports. Set to "*" to allow any origin (not recommended in prod).
_cors_env = os.getenv("BROCK_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
_allow_origins = (
    ["*"] if _cors_env.strip() == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_cors_env.strip() != "*",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

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
    buffering the whole thing in memory. Validates the PDF magic bytes on
    the first chunk."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)  # noqa: SIM115 — handed off
    total = 0
    chunk_size = 1024 * 1024
    header_checked = False
    try:
        while chunk := await pdf.read(chunk_size):
            if not header_checked:
                if not chunk.startswith(b"%PDF-"):
                    tmp.close()
                    Path(tmp.name).unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="upload is not a PDF (missing %PDF- magic bytes)",
                    )
                header_checked = True
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
        if total == 0:
            Path(tmp.name).unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empty upload",
            )
        return Path(tmp.name)
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/detailed")
async def health_detailed() -> dict:
    """Operator diagnostic: is the agent actually in a position to run?"""
    api_key_present = bool(os.getenv("ANTHROPIC_API_KEY"))

    claude_skills = REPO_ROOT / ".claude" / "skills"
    skills_dir_ok = SKILLS_DIR.is_dir()
    symlink_ok = claude_skills.is_symlink() and claude_skills.resolve() == SKILLS_DIR.resolve()

    skill_files = {}
    if skills_dir_ok:
        for sd in sorted(SKILLS_DIR.iterdir()):
            if sd.is_dir():
                skill_files[sd.name] = (sd / "SKILL.md").exists()

    runs_ok = True
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        runs_ok = False

    citation_log = _citation_log_path()

    healthy = api_key_present and skills_dir_ok and runs_ok
    return {
        "status": "ok" if healthy else "degraded",
        "anthropic_api_key_present": api_key_present,
        "skills_dir": str(SKILLS_DIR),
        "skills_dir_ok": skills_dir_ok,
        "claude_skills_symlink_ok": symlink_ok,
        "skills": skill_files,
        "runs_dir": str(RUNS_DIR),
        "runs_dir_writable": runs_ok,
        "citation_log_path": str(citation_log),
        "auth_required": bool(os.getenv("BROCK_API_KEY")),
        "rate_limit": {"limit": RATE_LIMIT, "window_seconds": RATE_WINDOW},
    }


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


@app.get("/runs/{run_id}/citations")
async def get_run_citations(
    run_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Return the citation audit rows emitted during a run.

    Scans the global citation log for matching run_id. Cheap for hundreds of
    runs; swap for a per-run file if the global log gets unwieldy.
    """
    _require_api_key(x_api_key)
    if not run_id.isalnum():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid run_id")
    log_path = _citation_log_path()
    if not log_path.exists():
        return {"run_id": run_id, "citations": []}
    rows = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("run_id") == run_id:
                rows.append(row)
    return {"run_id": run_id, "citations": rows}


@app.get("/runs/{run_id}/eval")
async def get_run_eval(
    run_id: str,
    vs_hand: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Compare the run's generated markdown against a hand-written reference.

    `vs_hand` is a path relative to the repo root, restricted to the
    `examples/` directory so callers can't read arbitrary files. Returns the
    ComparisonReport as JSON — same shape `eval.compare` emits.
    """
    _require_api_key(x_api_key)
    if not run_id.isalnum():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid run_id")

    generated = RUNS_DIR / run_id / "result.md"
    if not generated.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    # Only allow comparing against the checked-in examples/ folder.
    hand = (REPO_ROOT / vs_hand).resolve()
    examples_dir = (REPO_ROOT / "examples").resolve()
    try:
        hand.relative_to(examples_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vs_hand must point into examples/",
        ) from None
    if not hand.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hand version not found")

    from eval.compare import compare

    report = compare(generated, hand)
    payload = report.__dict__.copy()
    payload["score"] = report.score()
    return payload

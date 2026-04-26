"""FastAPI app: /analyze (SSE) + /voice/{run_id} (WebSocket proxy) + static."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import websockets

from agent.events import sse_format
from agent.pipeline import run_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
RUNS_DIR = REPO_ROOT / "runs"

load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)

app = FastAPI(title="Texas Governance Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Serve the SPA if present; otherwise show a tiny status page."""
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {
            "service": "texas-governance-agent",
            "status": "ok",
            "endpoints": ["/analyze (POST)", "/voice/{run_id} (WS)", "/runs/{run_id}"],
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/runs/{run_id}.docx")
async def download_docx(run_id: str):
    """Return the pre-read rendered as a Word document."""
    from agent.exporter import markdown_to_docx

    safe = "".join(c for c in run_id if c.isalnum())
    md_path = RUNS_DIR / f"{safe}.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="run not found")
    md = md_path.read_text()
    docx_bytes = markdown_to_docx(md, title=f"Board Pre-Read \u00b7 {safe}")
    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="board_prep_{safe}.docx"'
            )
        },
    )


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Return a previously-generated pre-read."""
    safe = "".join(c for c in run_id if c.isalnum())
    path = RUNS_DIR / f"{safe}.md"
    if not path.exists():
        return JSONResponse({"error": "run not found"}, status_code=404)
    return FileResponse(path, media_type="text/markdown")


@app.post("/chat/{run_id}")
async def chat(run_id: str, body: dict):
    """Q&A chat: Claude answers questions grounded in the pre-read."""
    from anthropic import AsyncAnthropic

    safe = "".join(c for c in run_id if c.isalnum())
    md_path = RUNS_DIR / f"{safe}.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="run not found")
    pre_read = md_path.read_text()
    user_msg = (body or {}).get("message", "").strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="empty message")

    client = AsyncAnthropic()
    sys_prompt = (
        "You are a board-meeting Q&A companion for a Texas school-district trustee. "
        "Answer the question using only the pre-read below. Be concise (under 120 words). "
        "Quote statute verbatim when cited. Number arguments. If the answer isn't in the "
        "pre-read, say so plainly.\n\n"
        f"<pre_read>\n{pre_read}\n</pre_read>"
    )
    msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=sys_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = msg.content[0].text if msg.content else ""
    return {"response": text}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Stream the 3-stage pipeline as SSE."""
    pdf_bytes = await file.read()

    async def event_stream():
        try:
            async for event in run_pipeline(pdf_bytes):
                yield sse_format(event)
        except Exception as exc:
            yield sse_format(
                {"event": "error", "data": {"stage": "server", "message": str(exc)}}
            )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=headers
    )


@app.websocket("/voice/{run_id}")
async def voice_proxy(ws: WebSocket, run_id: str):
    """Bridge browser <-> local Gemini Live voice server (Agent E)."""
    await ws.accept()
    upstream_url = os.environ.get("VOICE_UPSTREAM_URL", "ws://localhost:8765") + f"/{run_id}"
    try:
        async with websockets.connect(upstream_url, max_size=None) as upstream:

            async def b2u():
                async for msg in ws.iter_bytes():
                    await upstream.send(msg)

            async def u2b():
                async for msg in upstream:
                    if isinstance(msg, bytes):
                        await ws.send_bytes(msg)
                    else:
                        await ws.send_text(msg)

            await asyncio.gather(b2u(), u2b())
    except Exception as exc:
        try:
            await ws.close(code=1011, reason=str(exc)[:120])
        except Exception:
            pass


# Mount /static AFTER routes so it doesn't shadow them.
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

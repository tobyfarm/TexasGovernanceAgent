"""
Gemini 3.1 Flash Live WebSocket bridge.

Wire: browser <-> FastAPI proxy (/voice/{run_id}) <-> this bridge (:8765/{run_id}) <-> Gemini Live.
- Audio in:  16kHz PCM mono (browser -> Gemini)
- Audio out: 24kHz PCM mono (Gemini -> browser)
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import traceback
from pathlib import Path
from urllib.parse import urlparse

import websockets
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
PRINCIPLES = REPO / "skills" / "governance-principles" / "principles.md"

MODEL = "gemini-3.1-flash-live-preview"

# Lazy client init so a missing key produces a friendly error instead of an import-time crash.
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(http_options={"api_version": "v1alpha"})
    return _client


def build_system_instruction(run_id: str) -> str:
    pre_read_path = RUNS / f"{run_id}.md"
    if not pre_read_path.exists():
        raise FileNotFoundError(f"No pre-read at {pre_read_path}")
    pre_read = pre_read_path.read_text()

    principles = ""
    if PRINCIPLES.exists():
        principles = PRINCIPLES.read_text()
        # Truncate to fit comfortably in context. Parts I and IV (top + bottom) are highest signal.
        if len(principles) > 12000:
            principles = principles[:8000] + "\n\n[...]\n\n" + principles[-4000:]

    return f"""You are a board-meeting Q&A companion for a Texas school-district trustee. The trustee may ask anything about the pre-read below. Apply the doctrine.

<pre_read>
{pre_read}
</pre_read>

<principles>
{principles}
</principles>

Rules:
1. Quote statute verbatim when cited.
2. Number arguments. One point per response.
3. Keep replies under 30 seconds of speech.
4. If asked about something not in the pre-read or principles, say so plainly.
5. Audio-first; speak naturally.
"""


async def handle_browser(client_ws, run_id: str) -> None:
    """One browser session = one upstream Gemini Live session."""
    try:
        sys_instr = build_system_instruction(run_id)
    except FileNotFoundError as e:
        try:
            await client_ws.send(json.dumps({"type": "error", "message": str(e)}))
        finally:
            await client_ws.close()
        return

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=sys_instr,
    )

    client = _get_client()
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print(f"[bridge] Gemini session open for run_id={run_id}")

        async def browser_to_gemini():
            try:
                async for msg in client_ws:
                    if isinstance(msg, bytes):
                        await session.send_realtime_input(
                            audio=types.Blob(data=msg, mime_type="audio/pcm;rate=16000")
                        )
                    elif isinstance(msg, str):
                        # Optional control plane (currently unused).
                        try:
                            ctrl = json.loads(msg)
                        except Exception:
                            continue
                        if ctrl.get("type") == "end_turn":
                            # No-op for realtime mode; Gemini handles VAD.
                            pass
            except websockets.ConnectionClosed:
                return

        async def gemini_to_browser():
            try:
                while True:
                    turn = session.receive()
                    async for response in turn:
                        if getattr(response, "data", None):
                            try:
                                await client_ws.send(response.data)  # raw 24kHz PCM bytes
                            except websockets.ConnectionClosed:
                                return
            except Exception as e:
                print(f"[bridge] gemini_to_browser ended: {e}", file=sys.stderr)

        try:
            await asyncio.gather(browser_to_gemini(), gemini_to_browser())
        finally:
            print(f"[bridge] Gemini session closed for run_id={run_id}")


def _extract_run_id(websocket, path: str | None) -> str:
    """The path is either passed as a positional arg (older websockets) or available
    on the websocket object (newer websockets >= 12)."""
    raw = path
    if raw is None:
        raw = getattr(websocket, "path", None) or ""
        if not raw:
            req = getattr(websocket, "request", None)
            if req is not None:
                raw = getattr(req, "path", "") or ""
    if not raw:
        return ""
    # path could be a full URL in some adapters; normalize.
    if raw.startswith("ws://") or raw.startswith("wss://") or raw.startswith("http"):
        raw = urlparse(raw).path
    return raw.lstrip("/").split("/")[0].split("?")[0]


async def _dispatch(websocket, path: str | None = None) -> None:
    run_id = _extract_run_id(websocket, path)
    if not run_id:
        await websocket.close(code=1008, reason="missing run_id")
        return
    print(f"[bridge] new session for run_id={run_id}")
    try:
        await handle_browser(websocket, run_id)
    except Exception as e:
        print(f"[bridge] session error: {e}", file=sys.stderr)
        traceback.print_exc()


def _make_handler():
    """Return a handler with a signature compatible with the installed `websockets` version."""
    serve = websockets.serve

    # Inspect the underlying signature of websockets.serve's handler param when possible.
    # websockets >=10 accepts a 1-arg handler; older versions accept (websocket, path).
    try:
        ws_version = getattr(websockets, "__version__", "0")
        major = int(str(ws_version).split(".")[0])
    except Exception:
        major = 0

    if major >= 10:
        async def handler(websocket):
            await _dispatch(websocket, None)
        return handler
    else:
        async def handler(websocket, path):  # type: ignore[no-redef]
            await _dispatch(websocket, path)
        return handler


async def main() -> None:
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        print("[bridge] FATAL: GOOGLE_API_KEY (or GEMINI_API_KEY) not set", file=sys.stderr)
        sys.exit(1)

    handler = _make_handler()

    print(f"[bridge] websockets version: {getattr(websockets, '__version__', '?')}")
    print("[bridge] listening on ws://localhost:8765")

    try:
        async with websockets.serve(handler, "localhost", 8765, max_size=8 * 1024 * 1024):
            await asyncio.Future()  # run forever
    except TypeError:
        # Fallback if signature mismatch — try the other handler shape.
        async def alt_handler(websocket, path=None):
            await _dispatch(websocket, path)

        async with websockets.serve(alt_handler, "localhost", 8765, max_size=8 * 1024 * 1024):
            await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[bridge] shutdown")

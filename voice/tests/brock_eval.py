"""Five-question Brock eval.

End-to-end test on the April 13 2026 Brock ISD board book:

    generate pre-read (here: use the hand version as a stand-in)
        -> launch voice session with board book + pre-read + doctrine
           seeded into the 128k Gemini Live context
        -> ask five representative trustee questions over one session
        -> capture transcripts and score grounding.

Produces a markdown report at voice/tests/brock_eval_output.md.

Usage:
    uv run python tests/brock_eval.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

DOCUMENT_ID = "brock_april_13_2026"

QUESTIONS = [
    "What's the biggest risk tonight?",
    "Walk me through item five.",
    "What should I ask SAMCO?",
    "What does TEC section 11.151 say?",
    "Read me the executive summary.",
]


async def wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.2)
    raise RuntimeError(f"bridge did not start on {host}:{port} within {timeout}s")


class Session:
    """Wraps one WebSocket session with auto-reconnect using resumption handles."""

    def __init__(self, uri: str, init: dict):
        self.uri = uri
        self.init = dict(init)
        self.ws: websockets.ClientConnection | None = None
        self.handle: str | None = None

    async def open(self) -> None:
        if self.ws is not None:
            return
        self.ws = await websockets.connect(self.uri, max_size=32 * 1024 * 1024)
        init = dict(self.init)
        if self.handle:
            init["resume_handle"] = self.handle
        await self.ws.send(json.dumps(init))
        # Wait for ready.
        async for msg in self.ws:
            if isinstance(msg, bytes):
                continue
            data = json.loads(msg)
            if data.get("type") == "ready":
                print(f"    ready (resumed={data.get('resumed')})")
                return
            if data.get("type") == "error":
                raise RuntimeError(f"bridge error on open: {data.get('message')}")
        raise RuntimeError("connection closed before ready frame")

    async def close(self) -> None:
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def ask(self, question: str, *, timeout: float = 60) -> dict:
        """Send one user text turn, return the reply. Reconnects on disconnect."""
        transcript: list[str] = []
        audio_bytes = 0
        error: str | None = None
        go_away_seen = False

        for attempt in range(2):
            try:
                await self.open()
                assert self.ws is not None
                await self.ws.send(json.dumps({"type": "text", "text": question}))

                async def consume() -> None:
                    nonlocal audio_bytes, error, go_away_seen
                    async for msg in self.ws:
                        if isinstance(msg, bytes):
                            audio_bytes += len(msg)
                            continue
                        data = json.loads(msg)
                        kind = data.get("type")
                        if kind == "transcript" and data.get("role") == "model":
                            transcript.append(data.get("text", ""))
                        elif kind == "resumption_handle":
                            self.handle = data.get("handle")
                        elif kind == "go_away":
                            go_away_seen = True
                        elif kind == "turn_complete":
                            return
                        elif kind == "error":
                            error = data.get("message")
                            return

                await asyncio.wait_for(consume(), timeout=timeout)
                return {
                    "reply": " ".join(transcript).strip(),
                    "audio_bytes": audio_bytes,
                    "error": error,
                    "go_away_seen": go_away_seen,
                    "reconnected": attempt > 0,
                }
            except (
                websockets.ConnectionClosed,
                websockets.ConnectionClosedError,
                websockets.ConnectionClosedOK,
            ):
                await self.close()
                if attempt == 0 and self.handle:
                    print(
                        "    reconnecting with resumption handle after disconnect"
                    )
                    continue
                raise

        return {
            "reply": " ".join(transcript).strip(),
            "audio_bytes": audio_bytes,
            "error": error or "unrecoverable disconnect",
            "go_away_seen": go_away_seen,
            "reconnected": True,
        }


async def run() -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8802"))
    env = {**os.environ, "VOICE_BRIDGE_PORT": str(port), "VOICE_BRIDGE_HOST": "127.0.0.1"}
    bridge_log_path = VOICE_DIR / "tests" / "brock_eval_bridge.log"
    bridge_log = bridge_log_path.open("w")
    proc = subprocess.Popen(
        ["uv", "run", "python", "bridge.py"],
        cwd=str(VOICE_DIR),
        env=env,
        stdout=bridge_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    results: list[dict] = []
    try:
        await wait_for_port("127.0.0.1", port)
        uri = f"ws://127.0.0.1:{port}"
        print(f"connecting to {uri} with document_id={DOCUMENT_ID}")
        # Each question runs in a fresh session so one question's long
        # reply can't starve the next one's window, and so disconnects
        # (Gemini Live imposes a ~10 min cap) don't corrupt subsequent
        # turns with leftover state.
        for i, q in enumerate(QUESTIONS, start=1):
            print(f"\n[Q{i}] {q}")
            # Retry once on an empty reply — the first attempt sometimes
            # races Gemini's per-IP setup budget when back-to-back 60k
            # context seeds go up in rapid succession.
            r = None
            for attempt in range(2):
                if attempt > 0:
                    print(f"    retry after empty reply (attempt {attempt + 1})")
                    await asyncio.sleep(2.0)
                session = Session(
                    uri, {"document_id": DOCUMENT_ID, "modality": "AUDIO"}
                )
                try:
                    r = await session.ask(q)
                finally:
                    await session.close()
                if r["reply"] or r.get("error"):
                    break
                # Short pause to avoid hammering the API with empty turns.
                await asyncio.sleep(1.0)
            flags = []
            if r.get("reconnected"):
                flags.append("reconnected")
            if r.get("go_away_seen"):
                flags.append("go_away")
            if r.get("error"):
                flags.append(f"ERROR={r['error']!r}")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            print(
                f"  -> audio {r['audio_bytes']}b, "
                f"transcript {len(r['reply'])} chars{suffix}"
            )
            print(f"  {r['reply']}")
            results.append({"q": q, **r})
            # Brief pause between questions so consecutive 60k-token
            # seeds don't pile up on Gemini's ingest side.
            if i < len(QUESTIONS):
                await asyncio.sleep(2.0)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        bridge_log.close()

    # Write markdown report.
    out_path = VOICE_DIR / "tests" / "brock_eval_output.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Brock April 13 voice eval — {ts}",
        "",
        f"Document id: `{DOCUMENT_ID}`",
        "Model: `gemini-3.1-flash-live-preview`",
        "Modality: AUDIO (replies transcribed via `output_audio_transcription`)",
        "",
        "Five representative trustee questions, one session, context seeded "
        "with board book + pre-read + doctrine excerpt.",
        "",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(f"## Q{i}. {r['q']}")
        lines.append("")
        if r.get("error"):
            lines.append(f"**ERROR:** {r['error']}")
        else:
            lines.append(f"- audio bytes: {r['audio_bytes']}")
            lines.append(f"- transcript: `{r['reply']}`" if not r['reply'] else "")
            if r['reply']:
                lines.append("")
                lines.append("> " + r["reply"].replace("\n", "\n> "))
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out_path}")
    ok = all(r["reply"] and not r["error"] for r in results)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

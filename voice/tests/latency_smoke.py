"""Measure time-to-first-audio and total-reply latency.

Opens one Gemini Live session with the Brock April 13 context, asks three
questions, and records per-question timing:

- t_ready:          init-sent → ready
- t_first_audio:    text-sent → first binary frame on the wire
- t_first_text:     text-sent → first transcript frame
- t_turn_complete:  text-sent → turn_complete

The demo UX target is sub-second time-to-first-audio. Anything over ~1.5s
feels broken for voice; anything under ~600ms feels magical.

Usage:
    uv run python tests/latency_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
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
]


async def wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            _, w = await asyncio.open_connection(host, port)
            w.close()
            await w.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.2)
    raise RuntimeError(f"bridge did not start on {host}:{port}")


async def run() -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8804"))
    env = {**os.environ, "VOICE_BRIDGE_PORT": str(port), "VOICE_BRIDGE_HOST": "127.0.0.1"}
    log_path = VOICE_DIR / "tests" / "latency_smoke_bridge.log"
    log = log_path.open("w")
    proc = subprocess.Popen(
        ["uv", "run", "python", "bridge.py"],
        cwd=str(VOICE_DIR),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        await wait_for_port("127.0.0.1", port)
        uri = f"ws://127.0.0.1:{port}"
        async with websockets.connect(uri, max_size=32 * 1024 * 1024) as ws:
            t0 = time.perf_counter()
            await ws.send(
                json.dumps({"document_id": DOCUMENT_ID, "modality": "AUDIO"})
            )
            t_ready = None
            async for m in ws:
                if isinstance(m, bytes):
                    continue
                if json.loads(m).get("type") == "ready":
                    t_ready = time.perf_counter() - t0
                    break
            print(f"init→ready: {t_ready*1000:.0f} ms")

            for i, q in enumerate(QUESTIONS, start=1):
                q_sent = time.perf_counter()
                await ws.send(json.dumps({"type": "text", "text": q}))
                t_first_audio = None
                t_first_text = None
                t_turn_complete = None
                audio_bytes = 0
                async for m in ws:
                    if isinstance(m, bytes):
                        if t_first_audio is None:
                            t_first_audio = time.perf_counter() - q_sent
                        audio_bytes += len(m)
                        continue
                    data = json.loads(m)
                    kind = data.get("type")
                    if kind == "transcript" and data.get("role") == "model":
                        if t_first_text is None:
                            t_first_text = time.perf_counter() - q_sent
                    elif kind == "turn_complete":
                        t_turn_complete = time.perf_counter() - q_sent
                        break
                    elif kind == "error":
                        print(f"Q{i} ERROR: {data.get('message')}")
                        return 2

                def ms(x):
                    return f"{x*1000:.0f}ms" if x is not None else "—"

                print(
                    f"Q{i} '{q}'"
                    f"\n   first_audio={ms(t_first_audio)}  "
                    f"first_text={ms(t_first_text)}  "
                    f"turn_complete={ms(t_turn_complete)}  "
                    f"audio={audio_bytes}b"
                )
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

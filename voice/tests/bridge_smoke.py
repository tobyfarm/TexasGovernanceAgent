"""End-to-end bridge smoke test.

Spawns bridge.py as a subprocess, opens a WebSocket to it, sends an init
message + a text question, and collects the server frames until
turn_complete. Exercises the full browser -> bridge -> Gemini -> browser
path without a browser.

Usage:
    uv run python tests/bridge_smoke.py            # default: echo_test, TEXT
    uv run python tests/bridge_smoke.py AUDIO      # request AUDIO modality
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import websockets
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


async def wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.2)
    raise RuntimeError(f"bridge did not start on {host}:{port} within {timeout}s")


async def run(modality: str = "TEXT", document_id: str = "echo_test") -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8799"))
    env = {**os.environ, "VOICE_BRIDGE_PORT": str(port), "VOICE_BRIDGE_HOST": "127.0.0.1"}
    proc = subprocess.Popen(
        ["uv", "run", "python", "bridge.py"],
        cwd=str(VOICE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        await wait_for_port("127.0.0.1", port)
        uri = f"ws://127.0.0.1:{port}"
        print(f"connecting to {uri} ...")
        async with websockets.connect(uri, max_size=16 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"document_id": document_id, "modality": modality}))

            got_ready = False
            got_turn_complete = False
            text_parts: list[str] = []
            transcript_parts: list[str] = []
            audio_bytes = 0
            handle = None

            async def consume() -> None:
                nonlocal got_ready, got_turn_complete, audio_bytes, handle
                async for msg in ws:
                    if isinstance(msg, bytes):
                        audio_bytes += len(msg)
                        continue
                    data = json.loads(msg)
                    kind = data.get("type")
                    if kind == "ready":
                        got_ready = True
                        print(f"  ready (resumed={data.get('resumed')})")
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "text",
                                    "text": (
                                        "In one short sentence, confirm you are "
                                        "reachable."
                                    ),
                                }
                            )
                        )
                    elif kind == "text":
                        text_parts.append(data.get("text", ""))
                    elif kind == "transcript" and data.get("role") == "model":
                        transcript_parts.append(data.get("text", ""))
                    elif kind == "resumption_handle":
                        handle = data.get("handle")
                    elif kind == "turn_complete":
                        got_turn_complete = True
                        return
                    elif kind == "error":
                        print(f"  bridge error: {data.get('message')}")
                        return

            await asyncio.wait_for(consume(), timeout=30)

            text = "".join(text_parts).strip()
            tx = "".join(transcript_parts).strip()
            print(f"  ready={got_ready} turn_complete={got_turn_complete}")
            print(f"  text reply   : {text!r}")
            print(f"  audio transcript: {tx!r}")
            print(f"  audio bytes  : {audio_bytes}")
            print(f"  resumption handle captured: {bool(handle)}")

            ok = got_ready and got_turn_complete and (text or tx or audio_bytes)
            print("RESULT:", "PASS" if ok else "FAIL")
            return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    modality = sys.argv[1].upper() if len(sys.argv) > 1 else "AUDIO"
    document_id = sys.argv[2] if len(sys.argv) > 2 else "echo_test"
    raise SystemExit(asyncio.run(run(modality, document_id)))

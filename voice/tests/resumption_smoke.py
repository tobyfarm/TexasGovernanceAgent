"""Session resumption smoke test.

Verifies the bridge's session resumption mechanic:

1. Open a session, send one user turn, capture the resumption handle.
2. Close the first WebSocket.
3. Open a second session, passing the captured handle in init. The
   bridge must skip context seeding and Gemini must return a
   session-resumption-aware ready frame.

The bridge reports a successful round-trip as ``{type:"ready", resumed:true}``
and a non-empty second-turn reply. Content-level recall across the reset
is a Gemini feature and is not asserted here — the system instruction is
intentionally aggressive about refusing off-topic prompts, which can mask
model-level memory behind a guardrail "outside the board book" reply.

Usage:
    uv run python tests/resumption_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import websockets
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

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


async def one_turn(uri: str, *, init: dict, question: str, timeout: float = 30) -> dict:
    """Open one session, send one user question, return the collected state."""
    state = {
        "ready_resumed": None,
        "handle": None,
        "model_text": [],
        "audio_bytes": 0,
        "turn_complete": False,
        "error": None,
    }
    async with websockets.connect(uri, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps(init))

        async def consume() -> None:
            async for msg in ws:
                if isinstance(msg, bytes):
                    state["audio_bytes"] += len(msg)
                    continue
                data = json.loads(msg)
                kind = data.get("type")
                if kind == "ready":
                    state["ready_resumed"] = bool(data.get("resumed"))
                    await ws.send(
                        json.dumps({"type": "text", "text": question})
                    )
                elif kind == "transcript" and data.get("role") == "model":
                    state["model_text"].append(data.get("text", ""))
                elif kind == "resumption_handle":
                    state["handle"] = data.get("handle")
                elif kind == "turn_complete":
                    state["turn_complete"] = True
                    return
                elif kind == "error":
                    state["error"] = data.get("message")
                    return

        await asyncio.wait_for(consume(), timeout=timeout)
    return state


async def run() -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8801"))
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

        print("step 1: open a fresh session, send a turn, capture the handle")
        s1 = await one_turn(
            uri,
            init={"document_id": "echo_test", "modality": "AUDIO"},
            question="Briefly confirm you are ready to help prep for the meeting.",
        )
        first_reply = " ".join(s1["model_text"]).strip()
        print(f"  first-session ready.resumed  : {s1['ready_resumed']}")
        print(f"  first-session reply          : {first_reply!r}")
        print(f"  first-session turn_complete  : {s1['turn_complete']}")
        print(f"  handle captured              : {bool(s1['handle'])}")
        if not s1["handle"]:
            print("FAIL: no resumption handle was emitted by the bridge")
            return 2
        if s1["ready_resumed"] is not False:
            print("FAIL: fresh session should report resumed=False in ready frame")
            return 2

        print("step 2: reopen with the handle — bridge must skip context seeding")
        s2 = await one_turn(
            uri,
            init={
                "document_id": "echo_test",
                "modality": "AUDIO",
                "resume_handle": s1["handle"],
            },
            question="One-sentence check: are you still with me?",
        )
        second_reply = " ".join(s2["model_text"]).strip()
        print(f"  second-session ready.resumed : {s2['ready_resumed']}")
        print(f"  second-session reply         : {second_reply!r}")
        print(f"  second-session turn_complete : {s2['turn_complete']}")

        ok = (
            s2["ready_resumed"] is True
            and s2["turn_complete"]
            and len(second_reply) > 0
        )
        print("RESULT:", "PASS" if ok else "FAIL")
        if not ok:
            print(
                "  expected resumed=True in ready frame and a non-empty reply "
                "on the resumed session."
            )
        return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

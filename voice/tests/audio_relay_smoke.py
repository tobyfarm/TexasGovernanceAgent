"""Audio-in → audio-out relay smoke test.

Generates a short spoken question with macOS `say`, converts it to the
16 kHz 16-bit PCM format the bridge expects, streams it over the bridge
WebSocket, and collects the Gemini audio reply + transcript.

Proves the bridge forwards binary audio frames correctly and that
`audio_end` commits the turn.

Usage:
    uv run python tests/audio_relay_smoke.py [question]
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import websockets
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def synthesize_pcm16(text: str) -> bytes:
    """Return 16 kHz mono 16-bit PCM for `text` via macOS `say` + ffmpeg."""
    if shutil.which("say") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("`say` and `ffmpeg` are required for this test")
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "say.aiff"
        wav = Path(tmp) / "say.wav"
        subprocess.run(["say", "-o", str(aiff), text], check=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(aiff),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                str(wav),
            ],
            check=True,
        )
        with wave.open(str(wav), "rb") as w:
            assert w.getframerate() == 16000
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            return w.readframes(w.getnframes())


async def wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.2)
    raise RuntimeError(f"bridge did not start on {host}:{port} within {timeout}s")


async def run(question: str) -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8800"))
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
        print(f"synthesizing question audio for: {question!r}")
        pcm = synthesize_pcm16(question)
        frames = [pcm[i : i + 1600] for i in range(0, len(pcm), 1600)]
        print(f"  {len(pcm)} bytes of PCM ({len(frames)} x ~50ms frames)")

        uri = f"ws://127.0.0.1:{port}"
        async with websockets.connect(uri, max_size=16 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"document_id": "echo_test", "modality": "AUDIO"}))

            user_tx_parts: list[str] = []
            model_tx_parts: list[str] = []
            audio_bytes = 0
            got_turn_complete = False
            ready = asyncio.Event()

            async def consume() -> None:
                nonlocal audio_bytes, got_turn_complete
                async for msg in ws:
                    if isinstance(msg, bytes):
                        audio_bytes += len(msg)
                        continue
                    data = json.loads(msg)
                    kind = data.get("type")
                    if kind == "ready":
                        ready.set()
                    elif kind == "transcript":
                        if data.get("role") == "user":
                            user_tx_parts.append(data.get("text", ""))
                        else:
                            model_tx_parts.append(data.get("text", ""))
                    elif kind == "turn_complete":
                        got_turn_complete = True
                        return
                    elif kind == "error":
                        print(f"  bridge error: {data.get('message')}")
                        return

            consumer = asyncio.create_task(consume())
            await asyncio.wait_for(ready.wait(), timeout=15)

            # Stream the audio frames with a 50ms cadence so VAD can
            # detect end-of-utterance naturally. Then signal audio_end
            # to commit the turn.
            for f in frames:
                await ws.send(f)
                await asyncio.sleep(0.05)
            await ws.send(json.dumps({"type": "audio_end"}))

            await asyncio.wait_for(consumer, timeout=40)

            user_tx = " ".join(user_tx_parts).strip()
            model_tx = " ".join(model_tx_parts).strip()
            print(f"  user transcript : {user_tx!r}")
            print(f"  model transcript: {model_tx!r}")
            print(f"  model audio     : {audio_bytes} bytes")
            print(f"  turn_complete   : {got_turn_complete}")

            ok = got_turn_complete and audio_bytes > 0 and model_tx
            print("RESULT:", "PASS" if ok else "FAIL")
            return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Say hello in one short sentence."
    )
    raise SystemExit(asyncio.run(run(q)))

"""Single-session Brock eval.

The demo experience is one trustee asking several questions in one flow,
not five independent cold-start sessions. This variant:

- Opens ONE Gemini Live session (one context seed = one quota bite).
- Asks the five representative questions sequentially.
- Captures the resumption handle on each turn. If Gemini closes the
  underlying socket mid-session (expected after ~10 minutes), we
  transparently reconnect using the handle — Gemini restores the prior
  conversation and we do NOT re-seed the three-block context.

Per-question results are recorded to brock_eval_single_output.md. Bridge
stderr is redirected to brock_eval_single_bridge.log for post-run review.

Usage:
    uv run python tests/brock_eval_single.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import wave
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


class PersistentSession:
    """One logical session that auto-reconnects with the resumption handle.

    Reconnect is only attempted between turns, never mid-turn, so a
    partial reply never contaminates the next question's result.
    """

    def __init__(self, uri: str, init: dict):
        self.uri = uri
        self.init = dict(init)
        self.ws: websockets.ClientConnection | None = None
        self.handle: str | None = None
        self.reconnect_count = 0

    async def _open(self) -> None:
        init = dict(self.init)
        if self.handle:
            init["resume_handle"] = self.handle
        self.ws = await websockets.connect(self.uri, max_size=32 * 1024 * 1024)
        await self.ws.send(json.dumps(init))
        async for msg in self.ws:
            if isinstance(msg, bytes):
                continue
            data = json.loads(msg)
            kind = data.get("type")
            if kind == "ready":
                return
            if kind == "error":
                raise RuntimeError(f"bridge error on open: {data.get('message')}")
            # Ignore any early events that arrive before ready.
        raise RuntimeError("connection closed before ready frame")

    async def ensure_open(self) -> None:
        if self.ws is None:
            await self._open()
            return
        # Probe: if the ws is actually closed, reopen with handle.
        if self.ws.state.name != "OPEN":  # CLOSED / CLOSING
            await self._close_quiet()
            self.reconnect_count += 1
            print(f"    reopening with handle (reconnect #{self.reconnect_count})")
            await self._open()

    async def _close_quiet(self) -> None:
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def close(self) -> None:
        await self._close_quiet()

    async def ask(
        self,
        question: str,
        *,
        timeout: float = 60,
        audio_sink: bytearray | None = None,
    ) -> dict:
        transcript: list[str] = []
        audio_bytes = 0
        error: str | None = None
        go_away = False
        reconnected_this_turn = False

        # Try once, and if the socket dies BEFORE we receive any content,
        # reconnect with the resumption handle and retry the question.
        for attempt in range(2):
            try:
                await self.ensure_open()
                assert self.ws is not None
                await self.ws.send(json.dumps({"type": "text", "text": question}))

                got_turn_complete = False

                async def consume() -> None:
                    nonlocal audio_bytes, error, go_away, got_turn_complete
                    async for msg in self.ws:
                        if isinstance(msg, bytes):
                            audio_bytes += len(msg)
                            if audio_sink is not None:
                                audio_sink.extend(msg)
                            continue
                        data = json.loads(msg)
                        kind = data.get("type")
                        if kind == "transcript" and data.get("role") == "model":
                            transcript.append(data.get("text", ""))
                        elif kind == "resumption_handle":
                            self.handle = data.get("handle")
                        elif kind == "go_away":
                            go_away = True
                        elif kind == "turn_complete":
                            got_turn_complete = True
                            return
                        elif kind == "error":
                            error = data.get("message")
                            return
                        elif kind == "prompt_feedback":
                            br = data.get("block_reason")
                            if br:
                                error = f"safety block: {br} / {data.get('block_reason_message')}"

                await asyncio.wait_for(consume(), timeout=timeout)

                # Reply with content — success. If go_away arrived, the
                # next call to ensure_open() will reopen with the handle.
                if transcript or audio_bytes or error:
                    return {
                        "reply": " ".join(transcript).strip(),
                        "audio_bytes": audio_bytes,
                        "error": error,
                        "go_away_seen": go_away,
                        "turn_complete": got_turn_complete,
                        "reconnected": reconnected_this_turn,
                    }

                # Empty reply AND connection still alive — nothing more to
                # do. Return as is.
                if self.ws and self.ws.state.name == "OPEN":
                    return {
                        "reply": "",
                        "audio_bytes": 0,
                        "error": error,
                        "go_away_seen": go_away,
                        "turn_complete": got_turn_complete,
                        "reconnected": reconnected_this_turn,
                    }

                # Connection closed before any content — reconnect + retry.
                await self._close_quiet()
                if attempt == 0 and self.handle:
                    self.reconnect_count += 1
                    reconnected_this_turn = True
                    print(
                        f"    connection closed empty — reconnecting with handle "
                        f"(reconnect #{self.reconnect_count})"
                    )
                    continue
                return {
                    "reply": "",
                    "audio_bytes": audio_bytes,
                    "error": error or "connection closed with empty reply",
                    "go_away_seen": go_away,
                    "turn_complete": got_turn_complete,
                    "reconnected": reconnected_this_turn,
                }
            except (
                websockets.ConnectionClosed,
                websockets.ConnectionClosedError,
                websockets.ConnectionClosedOK,
            ) as exc:
                await self._close_quiet()
                if attempt == 0 and self.handle and not (transcript or audio_bytes):
                    self.reconnect_count += 1
                    reconnected_this_turn = True
                    print(
                        f"    ConnectionClosed pre-reply — reconnecting with handle "
                        f"(reconnect #{self.reconnect_count})"
                    )
                    continue
                return {
                    "reply": " ".join(transcript).strip(),
                    "audio_bytes": audio_bytes,
                    "error": f"{type(exc).__name__}: {exc}",
                    "go_away_seen": go_away,
                    "turn_complete": False,
                    "reconnected": reconnected_this_turn,
                }

        return {
            "reply": "",
            "audio_bytes": 0,
            "error": "exhausted retries",
            "go_away_seen": go_away,
            "turn_complete": False,
            "reconnected": reconnected_this_turn,
        }


def _save_wav_24khz(path: Path, pcm: bytes) -> None:
    """Write 24 kHz mono 16-bit LE PCM to a WAV file."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


async def run(save_audio: bool = False) -> int:
    port = int(os.environ.get("VOICE_BRIDGE_PORT", "8803"))
    env = {**os.environ, "VOICE_BRIDGE_PORT": str(port), "VOICE_BRIDGE_HOST": "127.0.0.1"}
    bridge_log_path = VOICE_DIR / "tests" / "brock_eval_single_bridge.log"
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
        session = PersistentSession(
            uri, {"document_id": DOCUMENT_ID, "modality": "AUDIO"}
        )
        audio_dir = VOICE_DIR / "tests" / "audio_samples"
        if save_audio:
            audio_dir.mkdir(exist_ok=True)
        try:
            for i, q in enumerate(QUESTIONS, start=1):
                print(f"\n[Q{i}] {q}")
                sink: bytearray | None = bytearray() if save_audio else None
                r = await session.ask(q, audio_sink=sink)
                if save_audio and sink:
                    out = audio_dir / f"q{i}.wav"
                    _save_wav_24khz(out, bytes(sink))
                    r["wav_path"] = str(out.relative_to(VOICE_DIR))
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
                if i < len(QUESTIONS):
                    await asyncio.sleep(0.5)
        finally:
            await session.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        bridge_log.close()

    out_path = VOICE_DIR / "tests" / "brock_eval_single_output.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Brock April 13 voice eval (single session) — {ts}",
        "",
        f"Document id: `{DOCUMENT_ID}`",
        "Model: `gemini-3.1-flash-live-preview`",
        "Modality: AUDIO (replies transcribed via `output_audio_transcription`)",
        "",
        "Five representative trustee questions in **one** session "
        "(context seeded once; resumption handle used to reopen after "
        "any Gemini-side close without re-seeding).",
        "",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(f"## Q{i}. {r['q']}")
        lines.append("")
        meta = []
        if r.get("reconnected"):
            meta.append("reconnected via resumption handle")
        if r.get("go_away_seen"):
            meta.append("go_away observed")
        if meta:
            lines.append(f"_{'; '.join(meta)}_")
            lines.append("")
        if r.get("error"):
            lines.append(f"**ERROR:** {r['error']}")
        lines.append(f"- audio bytes: {r['audio_bytes']}")
        if r["reply"]:
            lines.append("")
            lines.append("> " + r["reply"].replace("\n", "\n> "))
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out_path}")
    ok = all(r["reply"] for r in results)
    print("RESULT:", "PASS" if ok else "PARTIAL/FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-audio",
        action="store_true",
        help="save each turn's 24 kHz PCM reply to tests/audio_samples/qN.wav",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(save_audio=args.save_audio)))

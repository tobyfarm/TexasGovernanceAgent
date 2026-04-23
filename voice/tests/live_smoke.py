"""Live smoke test: open a real Gemini Live session, elicit one turn,
collect the transcribed reply, close.

gemini-3.1-flash-live-preview is audio-first — a response is triggered by
``send_realtime_input`` (text or audio), not by ``send_client_content``.
This smoke test uses the working pattern end-to-end.

Runs against the live API — requires GOOGLE_API_KEY. Not part of the
pytest suite (it is a manual smoke check against a paid endpoint).

Usage:
    uv run python tests/live_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_prompt import SYSTEM_INSTRUCTION  # noqa: E402

MODEL = "gemini-3.1-flash-live-preview"


async def main() -> int:
    client = genai.Client()
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=SYSTEM_INSTRUCTION,
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    print(f"connecting to {MODEL}...")
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("connected. eliciting one turn via realtime text input.")
        await session.send_realtime_input(
            text="Say one short sentence confirming you are reachable, then stop."
        )

        tx_parts: list[str] = []
        audio_bytes = 0

        async def consume() -> None:
            nonlocal audio_bytes
            async for response in session.receive():
                if response.data:
                    audio_bytes += len(response.data)
                sc = response.server_content
                if sc is None:
                    continue
                if sc.output_transcription and sc.output_transcription.text:
                    tx_parts.append(sc.output_transcription.text)
                    print(sc.output_transcription.text, end="", flush=True)
                if sc.turn_complete:
                    print()
                    return

        await asyncio.wait_for(consume(), timeout=30)
        tx = " ".join(tx_parts).strip()
        print(f"--- transcript: {tx!r}")
        print(f"--- audio_bytes: {audio_bytes}")
        if not tx and not audio_bytes:
            print("ERROR: empty reply")
            return 2
        print("smoke test PASSED")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

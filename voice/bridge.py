"""Gemini 3.1 Flash Live WebSocket bridge.

Browser client opens a WebSocket to this server. Per connection we open a
Gemini Live session and transparently relay between the two:

    Browser --[ws]--> bridge --[wss]--> Gemini Live
    Browser <--[ws]-- bridge <--[wss]-- Gemini Live

Day 1 scope: text in, text out. The echo test. Audio (16kHz PCM in /
24kHz PCM out) and the three-block context seeding land Day 2.

Run:
    uv run python bridge.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from pathlib import Path

import websockets
from dotenv import load_dotenv
from google import genai
from google.genai import types
from websockets.asyncio.server import ServerConnection, serve

from context_loader import load_session_context
from system_prompt import SYSTEM_INSTRUCTION

# Load .env from the repo root so GOOGLE_API_KEY is available whether the
# bridge is run from voice/ or the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

MODEL = "gemini-3.1-flash-live-preview"
HOST = os.environ.get("VOICE_BRIDGE_HOST", "localhost")
PORT = int(os.environ.get("VOICE_BRIDGE_PORT", "8765"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("voice.bridge")


def _build_config(
    response_modality: str,
    seeding_context: bool,
    resume_handle: str | None = None,
) -> types.LiveConnectConfig:
    """Build the LiveConnectConfig for one session.

    response_modality: "TEXT" for a text-only client, "AUDIO" for voice.
    seeding_context: True when load_session_context returns history turns
        we need to seed with send_client_content. Gemini 3.1 Flash Live
        requires history_config.initial_history_in_client_content for that.
    resume_handle: a handle from a previous session's session_resumption
        update. When set, Gemini restores the prior context and we skip
        re-seeding the three-block history.
    """
    modality = types.Modality(response_modality.upper())
    config = types.LiveConnectConfig(
        response_modalities=[modality],
        system_instruction=SYSTEM_INSTRUCTION,
        # Minimal thinking keeps voice latency tight. Bump for harder items.
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        # Built-in transcription of the model's audio output and the user's
        # audio input. Feeds the accessibility overlay for Agent D.
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        # Always request resumption handles so a reconnect can pick up
        # where the prior session left off without re-seeding context.
        session_resumption=types.SessionResumptionConfig(handle=resume_handle),
    )
    if seeding_context and resume_handle is None:
        config.history_config = types.HistoryConfig(
            initial_history_in_client_content=True
        )
    return config


async def _browser_to_gemini(ws: ServerConnection, session) -> None:
    """Forward browser frames to Gemini.

    Text frames are JSON control messages: {"type": "text", "text": "..."}
    Binary frames are raw 16kHz 16-bit PCM audio chunks (Day 2).
    """
    async for message in ws:
        if isinstance(message, bytes):
            await session.send_realtime_input(
                audio=types.Blob(data=message, mime_type="audio/pcm;rate=16000")
            )
            continue

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            log.warning("ignored non-JSON text frame: %r", message[:120])
            continue

        kind = payload.get("type")
        if kind == "text":
            await session.send_realtime_input(text=payload.get("text", ""))
        elif kind == "audio_end":
            # Signal end-of-speech so the model can commit its turn.
            await session.send_realtime_input(audio_stream_end=True)
        else:
            log.warning("ignored unknown control frame: %s", kind)


async def _gemini_to_browser(ws: ServerConnection, session) -> None:
    """Forward Gemini server messages back to the browser."""
    async for response in session.receive():
        # .text and .data are convenience properties on LiveServerMessage
        # that concatenate across model_turn.parts — use them directly.
        if response.text:
            await ws.send(json.dumps({"type": "text", "text": response.text}))
        if response.data:
            # Gemini returns 24kHz 16-bit PCM.
            await ws.send(response.data)

        sc = response.server_content
        if sc is not None:
            if sc.output_transcription and sc.output_transcription.text:
                await ws.send(
                    json.dumps(
                        {
                            "type": "transcript",
                            "role": "model",
                            "text": sc.output_transcription.text,
                        }
                    )
                )
            if sc.input_transcription and sc.input_transcription.text:
                await ws.send(
                    json.dumps(
                        {
                            "type": "transcript",
                            "role": "user",
                            "text": sc.input_transcription.text,
                        }
                    )
                )
            if sc.interrupted:
                await ws.send(json.dumps({"type": "interrupted"}))
            if sc.turn_complete:
                await ws.send(json.dumps({"type": "turn_complete"}))

        # Surface prompt-level safety feedback so callers can see why an
        # empty response came back (blocked_reason, safety_ratings, etc.).
        if getattr(response, "prompt_feedback", None):
            pf = response.prompt_feedback
            log.warning("prompt_feedback: %s", pf)
            await ws.send(
                json.dumps(
                    {
                        "type": "prompt_feedback",
                        "block_reason": getattr(pf, "block_reason", None)
                        and str(pf.block_reason),
                        "block_reason_message": getattr(
                            pf, "block_reason_message", None
                        ),
                    }
                )
            )

        # Session lifecycle events: forward so the client can reconnect
        # gracefully before Gemini closes the underlying socket.
        if response.go_away is not None:
            await ws.send(
                json.dumps(
                    {
                        "type": "go_away",
                        "time_left": response.go_away.time_left,
                    }
                )
            )
        if response.session_resumption_update is not None:
            upd = response.session_resumption_update
            if upd.new_handle and upd.resumable:
                await ws.send(
                    json.dumps(
                        {
                            "type": "resumption_handle",
                            "handle": upd.new_handle,
                        }
                    )
                )


async def handle_session(ws: ServerConnection) -> None:
    peer = ws.remote_address
    log.info("client connected from %s", peer)
    try:
        init_msg = await ws.recv()
        init = json.loads(init_msg) if isinstance(init_msg, str) else {}
        document_id = init.get("document_id", "unknown")
        # Clients default to TEXT for text-only harnesses. Flip to "AUDIO"
        # once the browser is ready to play PCM.
        response_modality = init.get("modality", "TEXT").upper()
        # Optional: client-provided handle from a prior session. When set,
        # Gemini restores the prior conversation state and we skip seeding.
        resume_handle = init.get("resume_handle")
        log.info(
            "session init: document_id=%s modality=%s resume=%s",
            document_id,
            response_modality,
            bool(resume_handle),
        )

        client = genai.Client()
        blocks = [] if resume_handle else load_session_context(document_id)
        config = _build_config(
            response_modality,
            seeding_context=bool(blocks),
            resume_handle=resume_handle,
        )

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            if blocks:
                turns = [b.as_turn() for b in blocks]
                await session.send_client_content(turns=turns, turn_complete=False)
                log.info("seeded %d context block(s) for %s", len(turns), document_id)

            # Optional priming turn: the client can ask the model to speak
            # first, e.g. to greet the trustee and offer a starting prompt.
            # gemini-3.1-flash-live-preview only triggers a model turn from
            # send_realtime_input; send_client_content(turn_complete=True)
            # is for seeding, not for eliciting a reply on this variant.
            welcome = init.get("welcome")
            if welcome and not resume_handle:
                await session.send_realtime_input(text=str(welcome))

            await ws.send(json.dumps({"type": "ready", "resumed": bool(resume_handle)}))

            browser_task = asyncio.create_task(_browser_to_gemini(ws, session))
            gemini_task = asyncio.create_task(_gemini_to_browser(ws, session))
            done, pending = await asyncio.wait(
                {browser_task, gemini_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            # As soon as one side ends (browser closes, or Gemini closes),
            # cancel the other so we exit the session context cleanly.
            for task in pending:
                task.cancel()
            for task in pending:
                try:
                    await task
                except (asyncio.CancelledError, websockets.ConnectionClosed):
                    pass
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, websockets.ConnectionClosed):
                    raise exc
    except websockets.ConnectionClosed:
        log.info("client %s disconnected", peer)
    except Exception as exc:  # noqa: BLE001 — surface to client then close
        log.exception("session error: %s", exc)
        try:
            await ws.send(json.dumps({"type": "error", "message": str(exc)}))
        except websockets.ConnectionClosed:
            pass


async def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env at the repo "
            "root and fill it in, or export the variable before running."
        )

    stop = asyncio.Event()

    def _on_signal(*_: object) -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _on_signal)

    async with serve(handle_session, HOST, PORT):
        log.info("voice bridge listening on ws://%s:%d  (model=%s)", HOST, PORT, MODEL)
        await stop.wait()
        log.info("shutting down")


if __name__ == "__main__":
    asyncio.run(main())

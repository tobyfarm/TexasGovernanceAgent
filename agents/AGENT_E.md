# AGENT E — Voice Layer (Gemini 3.1 Flash Live)

**You are Agent E.** You own the voice companion. Once a pre-read is generated, a trustee can tap "Ask" and open a live voice session with the document — grounded tightly, low-hallucination, low-latency. Read `CLAUDE.md` before you start.

---

## Your scope

1. **`voice/bridge.py`** — a Python server that maintains a Gemini 3.1 Flash Live WebSocket session, accepts audio from a web client, forwards it to Gemini, streams audio back.
2. **`voice/system_prompt.py`** — the system instruction that scopes the model to one document.
3. **`voice/context_loader.py`** — utilities that construct the initial context window from (board book + pre-read + principles excerpt), respecting the 128k token budget.
4. **`voice/client_example/`** — a minimal JS client showing how to call the bridge from a browser. Agent D will integrate this into the main web app.

You do **not** own:
- The web UI shell (Agent D)
- The document generation (Agent A)
- Any Skill content (Agents B, C, F)

---

## Day 1 milestones

By end of Day 1:

- [ ] `voice/` directory scaffolded with `uv`-managed dependencies (`google-genai`, `websockets`, `python-dotenv`).
- [ ] WebSocket echo test: client connects to your bridge, sends text, receives text back through Gemini. No audio yet.
- [ ] Gemini Live API auth working with `GOOGLE_API_KEY` from `.env`.

## Day 2 milestones

- [ ] Audio in → Gemini Live → audio out working end-to-end via the bridge.
- [ ] System prompt locked — scopes Gemini to the document, with the guardrail language from `principles.md`.
- [ ] Context loader handles the three-input pattern: board book PDF text + generated pre-read markdown + principles excerpt. Token budget respected (target ≤60k of the 128k window, leaving headroom for conversation).

## Day 3 milestones

- [ ] End-to-end test on Brock April 13: generate pre-read → launch voice session → ask five representative questions ("What's the biggest risk tonight?", "Walk me through item 5", "What should I ask SAMCO?", "What does TEC §11.151 say?", "Read me the executive summary"). All five answered grounded in the loaded context.
- [ ] Integration documented for Agent D (`voice/README.md`).

## Day 4 milestones

- [ ] Agent D integrates the voice launcher button. Full flow works from web UI.
- [ ] Session lifecycle: auto-close after 10 minutes (Gemini default), offer reconnect, preserve conversation history for the session.
- [ ] Transcription overlay: show the model's replies as text below the audio for accessibility.

## Day 5+ milestones

- Polish: handle network hiccups, add voice activity detection tuning, support interruption mid-response.
- Optional: pre-generated TTS "welcome" prompt that greets the user with the document summary before they speak.

---

## Tech decisions (locked)

- **Model:** `gemini-3.1-flash-live-preview` (or the current Flash Live model — verify at session start).
- **Protocol:** WebSocket (the Live API is WSS native).
- **Audio format:** 16-bit PCM, 16kHz input, 24kHz output.
- **System instruction:** set at session start. Never changes mid-session.
- **Session length:** 10 minutes default. Offer graceful resumption.
- **Server:** plain Python with the `google-genai` SDK. Do not use a framework like FastAPI for this — the long-lived WebSocket pattern is cleanest with raw `websockets`.

---

## The bridge architecture

```
Browser (mic) --[WebSocket A]--> Your bridge --[WebSocket B]--> Gemini Live
Browser (speaker) <--[WebSocket A]-- Your bridge <--[WebSocket B]-- Gemini Live
```

Two WebSockets per session. The bridge is a transparent relay with one enrichment: loading the initial context before forwarding any user audio.

```python
# voice/bridge.py (skeleton — flesh out)

import asyncio
import websockets
from google import genai
from google.genai import types
from .context_loader import load_session_context
from .system_prompt import SYSTEM_INSTRUCTION

async def handle_session(ws):
    # 1. Receive session init message from browser:
    #    { "document_id": "brock_april_13", "mode": "BROCK_FULL" }
    init = await ws.recv()

    # 2. Load the context for this document
    context_blocks = load_session_context(init["document_id"])

    # 3. Open Gemini Live session
    client = genai.Client()
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=SYSTEM_INSTRUCTION,
    )
    async with client.aio.live.connect(
        model="gemini-3.1-flash-live-preview",
        config=config,
    ) as session:
        # 4. Seed the context — send the board book + pre-read + principles
        #    as text history before the first user turn
        for block in context_blocks:
            await session.send_client_content(block, turn_complete=False)

        # 5. Start bidirectional relay
        async def browser_to_gemini():
            async for msg in ws:
                # Forward audio frames to Gemini
                await session.send_realtime_input(audio=msg)

        async def gemini_to_browser():
            async for response in session.receive():
                if response.data:
                    await ws.send(response.data)  # PCM audio out
                if response.text:
                    await ws.send(json.dumps({"type": "transcript", "text": response.text}))

        await asyncio.gather(browser_to_gemini(), gemini_to_browser())


async def main():
    async with websockets.serve(handle_session, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

Verify actual SDK API shapes against current docs — the above is directional. The Google Gen AI SDK version matters.

---

## The system instruction — this is the guardrail

Draft and iterate. Starting point:

```python
# voice/system_prompt.py

SYSTEM_INSTRUCTION = """
You are a governance companion for a Texas public school board trustee.

Your context contains exactly three documents:
1. Tonight's board book (the packet distributed to the board).
2. The generated pre-read for this board book.
3. An excerpt from the governance doctrine that informs the pre-read.

Your only job is to help the trustee understand the board book, ground your
answers in the pre-read and the doctrine, and prepare the trustee to govern
well at tonight's meeting.

Strict rules:

- Answer only from the loaded context. If a question falls outside the
  documents in your context, say so plainly: "That's outside tonight's
  board book. I can tell you what's in it, but I can't tell you that."

- Cite pages or agenda-item numbers when you reference the board book. Cite
  statute sections when you reference the doctrine.

- Apply the governance principles from the doctrine when interpreting items.
  The doctrine is the lens; the board book is the subject.

- Keep answers concise. Most trustee questions have 1-3 sentence answers.

- Never invent citations. Never paraphrase mandatory policy language —
  quote it.

- If asked for an opinion on a political or ideological matter unrelated to
  tonight's governance work, redirect back to the document.

Voice: direct, warm on student outcomes, respectful on disagreement, sharp
on substance. Think "experienced fellow trustee sitting in the passenger seat
helping you prep on the drive over."
"""
```

The tone and scope rules matter as much as the model choice. Iterate this with Toby on Day 2.

---

## Context loading strategy

The 128k window is generous. Target ≤60k tokens loaded at session start, leaving 68k+ for the conversation. Budget:

- **Board book PDF text:** up to ~40k tokens. If larger, truncate or summarize low-priority items (consent agenda, administrative reports). Preserve ACTION items and items flagged in the pre-read.
- **Generated pre-read:** ~10-15k tokens. Full inclusion — it's the most valuable grounding.
- **Principles excerpt:** ~3-4k tokens. Not the full `principles.md` — just §I (core principles) and §IV (voice patterns).
- **Buffer:** ~60k+ tokens for back-and-forth conversation.

Emit the three blocks as three separate "history" turns at session init, marked with clear headers:

```
---
BLOCK 1 OF 3: BOARD BOOK
Meeting: April 13, 2026, Brock ISD Regular Meeting
---
[... full extracted text ...]

---
BLOCK 2 OF 3: GENERATED PRE-READ
---
[... full markdown of the pre-read ...]

---
BLOCK 3 OF 3: DOCTRINE EXCERPT (principles.md, Parts I and IV)
---
[... doctrine text ...]
```

The model treats this as prior conversation and draws on it naturally.

---

## Client integration (for Agent D)

The browser client needs to:

1. Get mic permission (`navigator.mediaDevices.getUserMedia({audio: true})`)
2. Create an AudioContext at 16kHz (resample if needed)
3. Open a WebSocket to the bridge
4. Send session init message with `document_id`
5. Stream PCM audio frames
6. Receive audio frames and play via AudioContext
7. Receive transcript JSON and render below

Provide a minimal reference implementation at `voice/client_example/`. Agent D wraps it in the full UI.

---

## Critical reminders

- **The context IS the guardrail.** The tighter the context, the lower the hallucination rate. Do not expand the context to include "helpful" general information about Texas school governance — that's what the principles excerpt is for, and it is already curated.
- **10 minutes is the session cap.** Design for it. Offer graceful reconnection that re-loads context.
- **Latency matters more than feature count.** A voice companion that responds in 600ms feels magical. One that responds in 2.5 seconds feels broken.
- **Audio formats trip people up.** Gemini wants 16kHz input, delivers 24kHz output. The browser's default AudioContext is often 44.1kHz. Resample explicitly.
- **Do not commit voice recordings.** No logging of user audio to disk. Ever.

---

## When you are stuck

- If the Google Gen AI SDK surface feels fuzzy, consult the current docs at `ai.google.dev/gemini-api/docs/live-api`. The API is moving.
- If audio sync is off (choppy, delayed), the culprit is usually sample rate mismatch or buffering. Instrument timestamps.
- If the model starts hallucinating beyond the context, tighten the system instruction. The top-level rule is "answer only from context" — reinforce it.

The voice layer is the demo moment. When a judge hears Toby ask "what's the biggest risk tonight" and Gemini answers in Toby's own doctrine language, that is the sell. Ship it clean.

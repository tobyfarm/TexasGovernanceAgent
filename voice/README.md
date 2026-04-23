# voice/ — Gemini 3.1 Flash Live bridge

Agent E's workstream. A Python WebSocket server that maintains a Gemini
3.1 Flash Live session per browser client and relays audio/text both ways,
scoped to the tonight's board book by a seeded context window.

## Run locally

```bash
# Once, at the repo root:
cp .env.example .env          # then edit .env and fill in GOOGLE_API_KEY

# Start the bridge (from voice/):
uv sync                       # first run only
uv run python bridge.py

# In another shell, serve the example client:
cd voice/client_example
python -m http.server 5173
# open http://localhost:5173/?doc=brock_april_13_2026
```

The `doc=` query parameter becomes the `document_id` in the init message.
Default is `echo_test`, which skips context loading and is useful for
verifying the text roundtrip before adding a PDF.

Environment overrides:

- `VOICE_BRIDGE_HOST` (default `localhost`)
- `VOICE_BRIDGE_PORT` (default `8765`)

## What the bridge does

```
Browser (mic)     --[ws]--> bridge --[wss]--> Gemini Live
Browser (speaker) <--[ws]-- bridge <--[wss]-- Gemini Live
```

Per connection the bridge:

1. Waits for an init message from the client.
2. Loads up to three context blocks for `document_id` via
   `context_loader.load_session_context`.
3. Opens a Gemini Live session on `gemini-3.1-flash-live-preview` with
   `system_instruction` (from `system_prompt.py`), transcription on both
   sides, low-thinking latency tuning, and session resumption enabled.
4. Seeds the context blocks as `send_client_content(turns=..., turn_complete=False)`.
5. Relays bidirectionally until the WebSocket or Gemini session closes.

## Protocol (browser ↔ bridge)

### Text frames (JSON)

Client → bridge:

| `type`        | payload                                              | meaning                                         |
| ------------- | ---------------------------------------------------- | ----------------------------------------------- |
| (init)        | `{document_id, modality, resume_handle?, welcome?}`  | First message. Use `AUDIO` for the demo model.  |

> **Modality note.** `gemini-3.1-flash-live-preview` is audio-first — it
> does not respond to TEXT-only sessions (the server returns a 1011
> internal error on `send_realtime_input(text=…)` when the configured
> response modality is TEXT). Always open with `modality: "AUDIO"` and
> read replies off the `transcript` frames plus the binary PCM stream.
> TEXT mode in the bridge is kept for future-compat with TEXT-capable
> live models.
| `text`        | `{type:"text", text:"…"}`                            | Typed user input.                               |
| `audio_end`   | `{type:"audio_end"}`                                 | Push-to-talk release — commits the audio turn.  |

Optional init fields:

- `resume_handle` — a handle from a prior session's `resumption_handle`
  event. When set, Gemini restores the prior conversation and the bridge
  skips re-seeding the three-block context.
- `welcome` — a user-role priming turn sent with `turn_complete=true`
  right after context seeding. The model responds before the trustee
  speaks. Example: `"Greet me briefly and offer to walk me through
  tonight's biggest risks."` Ignored on resumed sessions.

Bridge → client:

| `type`               | payload                                | meaning                                                    |
| -------------------- | -------------------------------------- | ---------------------------------------------------------- |
| `ready`              | `{resumed: bool}`                      | Gemini session open; context seeded. Start sending input.  |
| `text`               | `{text: "…"}`                          | Streaming text reply (TEXT modality).                      |
| `transcript`         | `{role: "user"\|"model", text: "…"}`   | Transcription of audio. Render beneath audio for a11y.     |
| `interrupted`        | `{}`                                   | User barge-in detected. Reset playback buffer.             |
| `turn_complete`      | `{}`                                   | End of one model turn. Reset per-turn UI state.            |
| `go_away`            | `{time_left: "…"}`                     | Gemini will close the session soon. Reconnect to resume.   |
| `resumption_handle`  | `{handle: "…"}`                        | Pass this back in the next init to resume the conversation.|
| `error`              | `{message: "…"}`                       | Fatal error — session about to close.                      |

### Binary frames

- **Client → bridge:** raw little-endian 16-bit PCM at **16 kHz, mono**.
  Chunk size is not strict; ~20–50 ms chunks are comfortable. The example
  worklet in `client_example/audio-worklet.js` emits 50 ms frames.
- **Bridge → client:** raw little-endian 16-bit PCM at **24 kHz, mono**.
  Play back via an AudioContext at 24 kHz. Queue chunks back-to-back to
  avoid gaps; the example client does this with `AudioBufferSourceNode`.

## Session lifecycle

- **Sessions last up to ~10 minutes.** Gemini emits a `go_away` message
  ~60 s before closing, and a `session_resumption_update` with a handle
  you can use to reopen a new session that picks up the prior context.
  The bridge forwards both events so the browser can reconnect seamlessly.
- **On reconnect**, the client reuses the stored `resumption_handle`.
  When the bridge sees it in the init message, it skips the full
  three-block re-seed — Gemini restores the prior context.
- **On go_away without a handle yet,** just reconnect and accept the
  fresh context seed.

## Context scoping — where the guardrail lives

The system instruction (`system_prompt.py`) restricts the model to the
loaded context and names three blocks: tonight's board book, the
generated pre-read, and the governance doctrine excerpt (§I + §IV of
`skills/governance-principles/principles.md`).

`context_loader.py` assembles those blocks from disk:

- **Board book:** `examples/{document_id}.pdf` (pypdf extraction,
  per-page headers, budget ≤160k chars / ~40k tokens).
- **Pre-read:** `examples/{document_id}_output.md` (budget ≤60k chars /
  ~15k tokens).
- **Doctrine:** `skills/governance-principles/principles.md`, sections
  I and IV, with §IV preserved in full and §I truncated tail-first when
  necessary (combined budget ≤24k chars / ~6k tokens).

Total seed target ≤60k tokens out of the 128k window, leaving ≥68k for
conversation.

Missing source files are logged and skipped, so partial setups still
work (e.g., before a PDF has been dropped into `examples/`). The
`echo_test` document id deliberately skips context loading and is the
fastest way to verify Gemini auth and the WebSocket plumbing.

## Integration notes for Agent D

- The bridge is a stateless process. One `bridge.py` can serve many
  concurrent trustees; each WebSocket gets its own Gemini session.
- The example client (`client_example/index.html` +
  `client_example/audio-worklet.js`) is a reference, not production UI.
  Agent D should port its two pieces verbatim into the Next.js app:
  the PCM capture worklet, and the 24 kHz AudioContext playback queue.
  Everything else (layout, state, reconnect UX) is Agent D's call.
- Don't proxy the bridge through Vercel serverless — WebSockets don't
  fit. Run `bridge.py` on its own host (Fly, Railway, a Cloud Run with
  HTTP/2, etc.) and point the Next.js app at `wss://…`.
- Never log user audio to disk. The bridge doesn't; keep it that way in
  the hosted deployment.

## Files

- `bridge.py` — WebSocket server + Gemini relay.
- `system_prompt.py` — guardrail system instruction.
- `context_loader.py` — three-block context assembly.
- `client_example/index.html` — reference browser client (text + voice).
- `client_example/audio-worklet.js` — 16 kHz PCM capture worklet.
- `pyproject.toml` / `uv.lock` — pinned dependencies.

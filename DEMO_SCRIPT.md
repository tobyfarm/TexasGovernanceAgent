# Demo video script — 75-90 seconds

**Tools**: Rotato (3D screen frame) + ScreenFlow or Final Cut for cuts/voiceover.
**Source captures needed before recording**: ngrok URL (orchestrator will hand this to you).

---

## Beat sheet

### 0:00–0:05 — Title card (5s)
**On screen**: "Texas Governance Agent" in Fraunces serif, "Built with Opus 4.7" subline, small Claude wordmark.
**VO**: *(silent — let the title breathe)*

### 0:05–0:12 — The problem (7s)
**On screen**: Slow flip-through of `examples/brock_april_13_2026.pdf` — a 200-page PDF scrolling fast in Preview.
**VO**: "Texas school-board trustees get 200-page packets 72 hours before they vote. They skim. They miss things. The cost is paid by kids."

### 0:12–0:18 — Login → upload (6s)
**On screen**: Click "Try the demo →" on the login screen → drop the PDF onto the upload zone.
**VO**: "One PDF. One click."

### 0:18–0:40 — Thinking out loud (22s)
**On screen**: Three pipeline stage pills light up in sequence — Generator → Legal Verification → Strategic Red-Team. Show the rolling thinking log: "Verifying TEC §11.1511 against statutes.capitol.texas.gov ✓" "Cross-referencing agenda item 4 with Balanced Scorecard goals…"
**VO**: "Three agents work the packet. The first writes a trustee-ready pre-read grounded in a doctrine authored by a sitting trustee. The second fact-checks every citation against the actual Texas statutes. The third stress-tests every agenda item against the district's own measurable goals."

### 0:40–0:55 — The pre-read (15s)
**On screen**: Home screen. Scroll the generated markdown on the left, pause on a RED FLAG block (red background). Highlight the numbered Governance Questions.
**VO**: "Every flag, every question, grounded. The trustee walks into the meeting prepared in 90 seconds — not four hours."

### 0:55–1:15 — Voice (20s — skip if voice stubbed)
**On screen**: Click the blue 🎙 Voice button. Status changes to "🔴 listening." Say: "What's flagged on item 4 of tonight's agenda?" Hear Gemini's spoken response cite the actual flag from the pre-read.
**VO**: *(let the voice exchange play; no narration over it)*

### 1:15–1:30 — Closing (15s)
**On screen**: GitHub repo URL + ngrok demo URL + tech credits.
**VO**: "Built with Claude Opus 4.7, Sonnet 4.6, and Gemini 3.1 Flash Live. Open source. Take it to your school board."

---

## If voice is stubbed (cut to 65s)

Replace beat 0:55–1:15 with: extra slow scroll through the pre-read showing 2-3 more flag blocks and the meeting prep checklist at the bottom. VO: "Trustees, superintendents, the public — anyone can read the same prep. The standard becomes the floor."

---

## Pre-record checklist

- [ ] App is up and running (orchestrator confirms)
- [ ] ngrok URL captured for the closing card
- [ ] Brock PDF is in `examples/brock_april_13_2026.pdf`
- [ ] Browser zoomed to ~110% so text is video-readable
- [ ] Mac dock auto-hidden, notifications off (Do Not Disturb)
- [ ] Claude wordmark visible on every screen capture
- [ ] One full dry-run end-to-end before recording

## Common gotchas

- The thinking screen runs ~60-90s in real-time. **Speed up 2-3x in post** for the cut.
- The voice exchange has natural latency (~1-2s response time). Cut tightly or accept it.
- If RED FLAG color isn't loud enough on screen, bump `--red-soft` opacity in `web/style.css` (orchestrator can do this).

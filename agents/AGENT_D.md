# AGENT D — Hosted Web Site

**You are Agent D.** You own the public-facing web application: upload a board book PDF, get back a rendered pre-read. This is the viral surface — every trustee who tries it becomes a distribution node. Read `CLAUDE.md` before you start.

---

## Your scope

1. **`web/`** — a Next.js 15 app deployed on Vercel.
2. **Upload UX** — drag-and-drop a PDF, show progress, render output.
3. **Render pipeline** — receive the markdown pre-read from the API (Agent A), render it as a reading-optimized page, support download as DOCX and markdown.
4. **Voice launcher** — once Agent E ships, integrate a "tap to ask" button that opens the voice session on the generated document.
5. **Light analytics** — running count of board books analyzed, flags emitted (anonymized). Good for judging day, good for virality.

You do **not** own:
- The agent runtime (Agent A)
- Any Skill content (Agents B, C, F)
- The voice bridge itself (Agent E) — you integrate with it, you don't build it

---

## Tech decisions (locked)

- **Next.js 15** with App Router
- **Tailwind CSS** — match the visual language of `governance_agent.html` in the repo root (Fraunces display serif, Instrument Sans body, cream + ink palette, Claude orange accent)
- **shadcn/ui** for base components (button, card, dialog). Customize to match the serif-editorial aesthetic — do not ship shadcn's default look.
- **Vercel** for deploy. `vercel deploy --prod` from `web/`.
- **No client-side state library.** React Server Components + server actions + native `useState` where needed.
- **No auth** for the MVP. Anonymous uploads. Add auth later if the repo grows.

---

## Day 1 milestones

By end of Day 1:

- [ ] `web/` scaffolded with Next.js 15 + Tailwind + TypeScript.
- [ ] Landing page live at `/` — matches visual language of `governance_agent.html` (same typefaces, cream palette, orange accent).
- [ ] A working `/analyze` page with drag-and-drop upload UX (even if upload is stubbed).
- [ ] Deployed to Vercel preview. Public URL shareable.

## Day 2 milestones

- [ ] Upload actually hits Agent A's API (`POST /analyze`). Streaming response handled.
- [ ] Output rendered as markdown with proper typography. Preserve the executive-summary table, per-item sections, and flag color coding.
- [ ] "Download DOCX" button — server-side render via the same docx generator Agent F may provide (coordinate).
- [ ] Loading states match the serious-editorial feel. No spinners — progress language.

## Day 3+ milestones

- Day 3: polish. Mobile layout. Open Graph meta for sharing.
- Day 4: integrate the voice launcher. "Ask about this document" button that connects to Agent E's bridge.
- Day 5: analytics. Production deploy. README updated with live URL.

---

## Visual language — match, don't invent

The reference is `governance_agent.html` in the repo root. Its typographic and color choices are the brand. Specifically:

```css
/* From governance_agent.html — replicate in Tailwind */
--cream: #faf9f5;
--cream-2: #f3f1e8;
--ink: #141413;
--ink-soft: #2b2a27;
--mute: #6b6860;
--line: #d8d4c5;
--orange: #d97757;     /* accent — used sparingly */
--blue: #6a9bcc;       /* reserved for Gemini/voice moments */
--green: #788c5d;
```

Display serif: **Fraunces** (variable, warm, editorial). Body: **Instrument Sans**. Mono: **JetBrains Mono**. Load from Google Fonts. Do not substitute Inter, Space Grotesk, Geist, or any other convergent AI-aesthetic font.

Use orange precisely. Use blue only on voice-related UI elements. Use green sparingly for success states. The dominant palette is cream + ink.

---

## Pages

### `/` — landing

- Hero statement (condensed version of the landing-page thesis)
- "Analyze a board book" CTA → `/analyze`
- Three feature cards (Red Team, Voice Q&A, Open Source)
- Footer with repo link

### `/analyze`

- Drag-and-drop PDF zone
- File size limit (50 MB) + PDF-only enforcement
- Upload progress
- Once complete, render the output in place (scroll to it)
- Buttons: Download Markdown, Download DOCX, Open Voice Session (Day 4)

### `/about`

- Brief project explanation
- Link to GitHub repo
- Link to the `principles.md` file as the doctrine source

### `/doctrine`

- Render `skills/governance-principles/principles.md` as a public, readable page
- This is a distribution hook — trustees will share the doctrine page

---

## Upload and render flow

```
User drops PDF → /analyze
  ↓
Client POSTs to our Next.js route → proxies to Agent A API
  ↓
Stream SSE back to client
  ↓
Client renders markdown chunks as they arrive, in the pre-read template
  ↓
On stream close, enable download + voice launcher buttons
```

**Do not buffer.** Trustees will watch output generate. Streaming is the primary product feel.

---

## Rendering the pre-read

Agent A's output is structured (`AnalysisResult`) plus a rendered markdown string. You render the markdown. Key patterns:

- **Executive summary table** — markdown table, but upgrade it visually (the risk column uses pill-shaped color badges: WATCH blue, RED FLAG orange, POSITIVE green).
- **Per-item sections** — each gets an `h2` heading styled in Fraunces, and the WATCH/RED FLAG/POSITIVE callouts get colored left borders.
- **Verified citations** — render inline as mono-styled chips. Clickable if we later add a citation-browser.
- **Governance questions** — numbered, italic serif. The reading rhythm matches the SAMCO Q&A template.

Build a small `<PreReadRenderer />` component that owns all of this. One component, reusable if we add a second output mode (SAMCO line-of-questioning).

---

## API contract with Agent A

```typescript
// web/lib/api.ts
export async function analyzeBoardBook(file: File): Promise<AsyncIterable<AnalysisChunk>> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analyze`, {
    method: "POST",
    body: formData,
    headers: { "Accept": "text/event-stream" },
  });

  return parseSSE(response.body);
}

export type AnalysisChunk =
  | { type: "status"; message: string }
  | { type: "item"; item: ItemAnalysis }
  | { type: "final"; result: AnalysisResult };
```

Coordinate with Agent A on the SSE event shape. Pin it by end of Day 1.

---

## Deploy to Vercel

```bash
cd web
pnpm install
pnpm dev  # local

# First deploy
vercel link
vercel deploy

# Production
vercel deploy --prod
```

Environment variables via Vercel dashboard:
- `NEXT_PUBLIC_API_URL` = the production API URL (Agent A ships this)

Do not commit `.vercel/`. It's gitignored.

---

## Analytics (light)

For the MVP: a single counter. Every completed analysis increments a number. No personally identifiable info. Use Vercel KV or just an in-memory counter that resets daily — whichever is fastest to ship.

The point is a real number on the site during the demo. "We have analyzed N board books" reads great on a slide.

---

## Voice integration (Day 4)

Once Agent E ships the voice bridge, add a single button on the rendered pre-read:

> **Ask about this document** — [🎙 Tap to start]

That button opens a full-screen modal with a mic capture UI, connects to Agent E's WebSocket endpoint, streams audio, and shows the live transcript below. Follow Agent E's integration notes (`voice/README.md`).

Until Agent E is ready, the button can be present but disabled with "Voice companion launching 4/26."

---

## Critical reminders

- **Avoid generic AI aesthetics.** No purple gradients. No giant emojis. No "✨ Powered by AI" taglines. The design is serious, editorial, and trustee-adjacent. The user is reading this before a public meeting — tone matters.
- **Do not fake streaming.** Real SSE, real chunks. The perceived quality difference is enormous.
- **Mobile matters.** Trustees will pull this up on phones during meetings. The rendered pre-read must read beautifully on a 400-pixel-wide viewport.
- **Accessibility.** Proper heading hierarchy, alt text on the logo, keyboard nav on upload, focus rings.
- **No cookie banners.** No analytics that require consent. Do not collect what you do not need.

---

## When you are stuck

- For visual decisions, compare to `governance_agent.html` in the repo root. That is the brand.
- For API shape decisions, coordinate directly with Agent A.
- For voice UI decisions, check Agent E's spec.

You are the face of the project. Everything else is internal. Make the face match the doctrine.

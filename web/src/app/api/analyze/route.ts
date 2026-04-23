/**
 * Fallback /api/analyze route — streams the canonical Brock hand-written
 * pre-read as SSE, so the UI is fully demo-able without Agent A running.
 *
 * The client hits this when NEXT_PUBLIC_API_URL is unset. Once Agent A is
 * deployed, point NEXT_PUBLIC_API_URL at the real API and this route becomes
 * a local dev-only shim.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STAGES = [
  "Opening the packet",
  "Extracting 166 pages",
  "Identifying agenda items",
  "Consulting TEC · TGC · TAC corpus",
  "Applying governance principles",
  "Verifying citations",
  "Flagging risks",
  "Assembling the pre-read",
];

export async function POST(req: Request) {
  // Just accept and discard the upload in the demo shim.
  try {
    await req.formData();
  } catch {
    // non-fatal
  }

  // Canonical hand-written reference pre-read, shared with the rest of the
  // repo. Keeping a single source of truth — if the reference is edited,
  // the demo stream picks it up automatically.
  const fixturePath = path.join(
    process.cwd(),
    "..",
    "examples",
    "brock_april_13_2026_prereadhand.md",
  );

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (obj: unknown) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(obj)}\n\n`),
        );
      };

      // Stream status lines for the editorial progress feel.
      for (const message of STAGES) {
        send({ type: "status", message });
        await sleep(420);
      }

      let markdown: string;
      try {
        markdown = await readFile(fixturePath, "utf8");
      } catch (err) {
        send({
          type: "error",
          message: `Could not load fixture: ${(err as Error).message}`,
        });
        controller.close();
        return;
      }

      send({
        type: "final",
        result: {
          district: "Brock ISD",
          meetingDate: "April 13, 2026",
          executiveSummary: [],
          items: [],
          meetingPrepChecklist: [],
          renderedMarkdown: markdown,
        },
      });

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

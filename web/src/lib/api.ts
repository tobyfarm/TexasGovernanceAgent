/**
 * Client for the Agent A analysis API.
 *
 * Contract (pin by end of Day 1 with Agent A):
 *   POST {NEXT_PUBLIC_API_URL}/analyze
 *     body: FormData with "file" = board-book PDF
 *     response: text/event-stream, one JSON object per "data:" line,
 *               each one an AnalysisChunk
 */

export type RiskFlag = "WATCH" | "RED_FLAG" | "POSITIVE";

export type Citation = {
  authority: string; // e.g. "TEC §11.151(b)"
  quote: string;
  verified: boolean;
};

export type ItemAnalysis = {
  id: string;
  agendaNumber?: string;
  title: string;
  whatIsHappening: string;
  keyData: string[];
  legalFramework: Citation[];
  governanceQuestions: string[];
  flags: Array<{ level: RiskFlag; note: string }>;
};

export type AnalysisResult = {
  district: string;
  meetingDate: string;
  executiveSummary: Array<{
    agenda: string;
    title: string;
    topFlag: RiskFlag | null;
    oneLiner: string;
  }>;
  items: ItemAnalysis[];
  meetingPrepChecklist: string[];
  renderedMarkdown: string;
};

export type AnalysisChunk =
  | { type: "status"; message: string }
  | { type: "item"; item: ItemAnalysis }
  | { type: "final"; result: AnalysisResult }
  | { type: "error"; message: string };

/**
 * Resolves to the Agent A API when NEXT_PUBLIC_API_URL is set.
 * Otherwise falls back to the local /api/analyze route which streams a
 * fixture pre-read — the site stays fully demo-able without the backend.
 */
function resolveAnalyzeEndpoint(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (baseUrl) return `${baseUrl}/analyze`;
  return "/api/analyze";
}

export function isUsingFixture(): boolean {
  return !process.env.NEXT_PUBLIC_API_URL;
}

export async function* analyzeBoardBook(
  file: File,
  signal?: AbortSignal,
): AsyncGenerator<AnalysisChunk> {
  const endpoint = resolveAnalyzeEndpoint();
  const demo = isUsingFixture();

  // Demo mode doesn't use the uploaded file — the route just streams the
  // canonical fixture. Issue a GET so the PDF body doesn't need to travel
  // through Vercel's 4.5MB serverless-function payload limit.
  const init: RequestInit = demo
    ? { method: "GET", headers: { Accept: "text/event-stream" }, signal }
    : (() => {
        const formData = new FormData();
        formData.append("file", file);
        return {
          method: "POST",
          body: formData,
          headers: { Accept: "text/event-stream" },
          signal,
        };
      })();

  const response = await fetch(endpoint, init);

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(
      `Analysis request failed: HTTP ${response.status}${text ? ` — ${text}` : ""}`,
    );
  }
  if (!response.body) {
    throw new Error("Analysis response had no body");
  }

  yield* parseSSE(response.body);
}

/**
 * Minimal SSE parser. Handles multi-line "data:" events per the EventSource
 * spec, ignores comments, and yields the parsed JSON envelope.
 */
export async function* parseSSE(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<AnalysisChunk> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary: number;
      // SSE events are separated by blank line — \n\n or \r\n\r\n.
      while (
        (boundary = findEventBoundary(buffer)) !== -1
      ) {
        const raw = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary).replace(/^\r?\n\r?\n/, "");
        const chunk = parseEvent(raw);
        if (chunk) yield chunk;
      }
    }
    // Flush any trailing event without explicit blank line.
    const tail = buffer.trim();
    if (tail) {
      const chunk = parseEvent(tail);
      if (chunk) yield chunk;
    }
  } finally {
    reader.releaseLock();
  }
}

function findEventBoundary(s: string): number {
  const a = s.indexOf("\n\n");
  const b = s.indexOf("\r\n\r\n");
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function parseEvent(raw: string): AnalysisChunk | null {
  const dataLines: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith(":")) continue; // comment
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  const payload = dataLines.join("\n");
  if (payload === "[DONE]") return null;
  try {
    return JSON.parse(payload) as AnalysisChunk;
  } catch {
    return { type: "error", message: `malformed event: ${payload.slice(0, 120)}` };
  }
}

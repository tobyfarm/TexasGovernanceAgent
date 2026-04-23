/**
 * Anonymous analysis counter.
 *
 * Increments a single integer. No PII. No cookies. No per-user tracking.
 *
 * Storage tiers:
 *   1. If VERCEL_KV_REST_API_URL + VERCEL_KV_REST_API_TOKEN are set, use KV.
 *   2. Otherwise, in-memory counter that resets on each server restart —
 *      fine for dev + early demo. Upgrade to KV when traffic matters.
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const KEY = "governance-agent:analyses";

let memoryCount = 0;

async function kvRequest(
  path: string,
  init?: RequestInit,
): Promise<Response | null> {
  const url = process.env.KV_REST_API_URL ?? process.env.VERCEL_KV_REST_API_URL;
  const token =
    process.env.KV_REST_API_TOKEN ?? process.env.VERCEL_KV_REST_API_TOKEN;
  if (!url || !token) return null;
  return fetch(`${url}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
}

async function increment(): Promise<number> {
  const kv = await kvRequest(`/incr/${encodeURIComponent(KEY)}`);
  if (kv && kv.ok) {
    const { result } = (await kv.json()) as { result: number };
    return result;
  }
  memoryCount += 1;
  return memoryCount;
}

async function read(): Promise<number> {
  const kv = await kvRequest(`/get/${encodeURIComponent(KEY)}`);
  if (kv && kv.ok) {
    const { result } = (await kv.json()) as { result: string | number | null };
    const parsed = typeof result === "string" ? parseInt(result, 10) : result;
    return Number.isFinite(parsed ?? NaN) ? (parsed as number) : 0;
  }
  return memoryCount;
}

export async function GET() {
  const count = await read();
  return Response.json(
    { count },
    { headers: { "Cache-Control": "no-store" } },
  );
}

export async function POST() {
  const count = await increment();
  return Response.json(
    { count },
    { headers: { "Cache-Control": "no-store" } },
  );
}

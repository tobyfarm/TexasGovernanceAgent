import { headers } from "next/headers";

async function getCount(): Promise<number> {
  try {
    const h = await headers();
    const host = h.get("host");
    const proto = h.get("x-forwarded-proto") ?? "http";
    if (!host) return 0;
    const res = await fetch(`${proto}://${host}/api/counter`, {
      cache: "no-store",
    });
    if (!res.ok) return 0;
    const { count } = (await res.json()) as { count: number };
    return count ?? 0;
  } catch {
    return 0;
  }
}

export async function AnalysisCounter() {
  const count = await getCount();
  // Hide the line entirely if we haven't counted anything yet — empty is
  // louder than a zero.
  if (count <= 0) return null;
  return (
    <div className="flex items-center gap-3 mt-8 text-[13px] text-mute tracking-[0.02em]">
      <span className="inline-block h-px w-6 bg-orange" aria-hidden />
      <span>
        <strong className="text-ink" style={{ fontWeight: 500 }}>
          {count.toLocaleString()}
        </strong>{" "}
        board book{count === 1 ? "" : "s"} analyzed
      </span>
    </div>
  );
}

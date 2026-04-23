"use client";

import { useCallback } from "react";

type Props = {
  markdown: string;
  district: string;
  meetingDate: string;
};

export function ResultActions({ markdown, district, meetingDate }: Props) {
  const filenameBase = slugify(`${district}-${meetingDate}-preread`);

  const onDownloadMd = useCallback(() => {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    triggerDownload(blob, `${filenameBase}.md`);
  }, [markdown, filenameBase]);

  const onDownloadDocx = useCallback(async () => {
    const response = await fetch("/api/download/docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown, title: `${district} · ${meetingDate}` }),
    });
    if (!response.ok) {
      alert("DOCX export failed. Download markdown instead.");
      return;
    }
    const blob = await response.blob();
    triggerDownload(blob, `${filenameBase}.docx`);
  }, [markdown, district, meetingDate, filenameBase]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        onClick={onDownloadMd}
        className="inline-flex items-center gap-2 bg-ink text-cream px-4 py-2.5 text-[13px] tracking-[0.01em] hover:bg-orange transition-colors"
        style={{ borderRadius: 2 }}
      >
        Download markdown
        <span aria-hidden>↓</span>
      </button>
      <button
        onClick={onDownloadDocx}
        className="inline-flex items-center gap-2 text-ink-soft border border-line px-4 py-2.5 text-[13px] tracking-[0.01em] hover:border-orange hover:text-orange transition-colors"
        style={{ borderRadius: 2, background: "var(--cream)" }}
      >
        Download DOCX
        <span aria-hidden>↓</span>
      </button>
      <VoiceLauncherStub />
    </div>
  );
}

function VoiceLauncherStub() {
  // Stub per AGENT_D.md §Voice integration: present but disabled until Agent E ships.
  return (
    <button
      disabled
      className="inline-flex items-center gap-2 text-mute border border-line px-4 py-2.5 text-[13px] tracking-[0.01em] cursor-not-allowed"
      style={{ borderRadius: 2, background: "transparent" }}
      title="Voice companion launching 4/26"
    >
      <span aria-hidden>🎙</span>
      Ask about this document
      <span className="text-[11px] text-blue-deep ml-1">· launching 4/26</span>
    </button>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

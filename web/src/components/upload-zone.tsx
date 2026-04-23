"use client";

import { useCallback, useRef, useState } from "react";
import {
  analyzeBoardBook,
  type AnalysisResult,
  isUsingFixture,
} from "@/lib/api";
import { PreReadRenderer } from "./pre-read-renderer";
import { ResultActions } from "./result-actions";

const MAX_BYTES = 50 * 1024 * 1024;

type Status =
  | { kind: "idle" }
  | { kind: "ready"; file: File }
  | { kind: "working"; file: File; stage: string; streamingMd: string }
  | { kind: "done"; file: File; result: AnalysisResult }
  | { kind: "error"; message: string };

export function UploadZone() {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndStage = useCallback((file: File) => {
    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setStatus({
        kind: "error",
        message: "That file isn't a PDF. The agent only reads PDF board books.",
      });
      return;
    }
    if (file.size > MAX_BYTES) {
      setStatus({
        kind: "error",
        message: `That PDF is ${(file.size / 1024 / 1024).toFixed(1)} MB. The current limit is 50 MB.`,
      });
      return;
    }
    setStatus({ kind: "ready", file });
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) validateAndStage(file);
    },
    [validateAndStage],
  );

  const onFilePicked = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) validateAndStage(file);
    },
    [validateAndStage],
  );

  const onAnalyze = useCallback(async () => {
    if (status.kind !== "ready") return;

    const file = status.file;
    setStatus({
      kind: "working",
      file,
      stage: "Opening the packet",
      streamingMd: "",
    });

    try {
      for await (const chunk of analyzeBoardBook(file)) {
        if (chunk.type === "status") {
          setStatus((s) =>
            s.kind === "working" ? { ...s, stage: chunk.message } : s,
          );
        } else if (chunk.type === "item") {
          // Partial item — render into the streaming buffer.
          // (Agent A may or may not emit these in v1; handle gracefully.)
        } else if (chunk.type === "final") {
          setStatus({ kind: "done", file, result: chunk.result });
          // Fire-and-forget increment.
          fetch("/api/counter", { method: "POST" }).catch(() => {});
        } else if (chunk.type === "error") {
          setStatus({ kind: "error", message: chunk.message });
          return;
        }
      }
    } catch (err) {
      setStatus({
        kind: "error",
        message: (err as Error).message ?? "Something went wrong.",
      });
    }
  }, [status]);

  const reset = useCallback(() => {
    setStatus({ kind: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  // When analysis is complete, render result panel in place of the drop zone.
  if (status.kind === "done") {
    return <ResultPanel file={status.file} result={status.result} onReset={reset} />;
  }

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className="relative border transition-colors"
        style={{
          borderStyle: "dashed",
          borderWidth: "1px",
          borderColor: isDragging ? "var(--orange)" : "var(--line)",
          background: isDragging
            ? "rgba(217, 119, 87, 0.04)"
            : "var(--cream)",
          padding: "72px 40px",
          minHeight: 320,
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={onFilePicked}
          className="sr-only"
          id="board-book-input"
          tabIndex={-1}
          aria-hidden="true"
        />

        {status.kind === "idle" && (
          <IdleContent
            isDragging={isDragging}
            onChooseFile={() => inputRef.current?.click()}
          />
        )}

        {status.kind === "ready" && (
          <ReadyContent
            file={status.file}
            onAnalyze={onAnalyze}
            onReset={reset}
          />
        )}

        {status.kind === "working" && (
          <WorkingContent file={status.file} stage={status.stage} />
        )}

        {status.kind === "error" && (
          <ErrorContent message={status.message} onReset={reset} />
        )}
      </div>

      <p className="mt-4 text-[12px] text-mute tracking-[0.02em]">
        PDF only · 50 MB max · Anonymous · Nothing stored longer than the
        session
        {isUsingFixture() && (
          <>
            {" · "}
            <span className="text-orange-deep">
              Demo mode — streaming canonical Brock reference pre-read
            </span>
          </>
        )}
      </p>
    </div>
  );
}

function IdleContent({
  isDragging,
  onChooseFile,
}: {
  isDragging: boolean;
  onChooseFile: () => void;
}) {
  return (
    <div className="flex flex-col items-start gap-6">
      <div
        className="text-orange"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        {isDragging ? "Release to load" : "Step 01"}
      </div>
      <h3
        className="serif text-ink"
        style={{
          fontSize: 32,
          fontWeight: 380,
          lineHeight: 1.1,
          letterSpacing: "-0.02em",
          fontVariationSettings: "'SOFT' 50",
          maxWidth: 520,
        }}
      >
        Drop a board book PDF here.
      </h3>
      <p
        className="text-ink-soft max-w-[520px]"
        style={{ fontSize: 15, lineHeight: 1.6 }}
      >
        The analysis runs in under a minute. You&apos;ll get an executive
        summary table, a per-item deep dive with verified citations, and a
        meeting-prep checklist.
      </p>
      <button
        type="button"
        onClick={onChooseFile}
        className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-3 text-[14px] tracking-[0.01em] hover:bg-orange transition-colors"
        style={{ borderRadius: 2 }}
      >
        Choose a file
        <span aria-hidden>↑</span>
      </button>
    </div>
  );
}

function ReadyContent({
  file,
  onAnalyze,
  onReset,
}: {
  file: File;
  onAnalyze: () => void;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-col items-start gap-6">
      <div
        className="text-orange"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        Step 02 — Ready to analyze
      </div>
      <div className="flex items-baseline gap-4 flex-wrap">
        <h3
          className="serif text-ink"
          style={{
            fontSize: 26,
            fontWeight: 380,
            letterSpacing: "-0.015em",
            fontVariationSettings: "'SOFT' 50",
          }}
        >
          {file.name}
        </h3>
        <span
          className="text-mute"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            letterSpacing: "0.05em",
          }}
        >
          {(file.size / 1024 / 1024).toFixed(1)} MB
        </span>
      </div>
      <p className="text-ink-soft" style={{ fontSize: 15, lineHeight: 1.6 }}>
        The agent will walk every agenda item through the four governance
        Skills. Expect the first chunk in roughly fifteen seconds.
      </p>
      <div className="flex items-center gap-4">
        <button
          onClick={onAnalyze}
          className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-3 text-[14px] tracking-[0.01em] hover:bg-orange transition-colors"
          style={{ borderRadius: 2 }}
        >
          Run the red team
          <span aria-hidden>→</span>
        </button>
        <button
          onClick={onReset}
          className="text-[14px] text-ink-soft hover:text-orange transition-colors"
        >
          Choose a different file
        </button>
      </div>
    </div>
  );
}

function WorkingContent({ file, stage }: { file: File; stage: string }) {
  return (
    <div className="flex flex-col items-start gap-6">
      <div
        className="text-orange flex items-center gap-3"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        <span
          className="inline-block h-2 w-2 rounded-full bg-orange animate-pulse"
          aria-hidden
        />
        Analyzing
      </div>
      <h3
        className="serif text-ink"
        style={{
          fontSize: 28,
          fontWeight: 380,
          lineHeight: 1.15,
          letterSpacing: "-0.015em",
          fontVariationSettings: "'SOFT' 50",
        }}
      >
        {stage}
        <span className="wonk-italic text-orange">…</span>
      </h3>
      <p
        className="text-mute"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          letterSpacing: "0.05em",
        }}
      >
        {file.name}
      </p>
    </div>
  );
}

function ErrorContent({
  message,
  onReset,
}: {
  message: string;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-col items-start gap-6">
      <div
        className="text-orange-deep"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        Paused
      </div>
      <p
        className="serif text-ink"
        style={{
          fontSize: 22,
          fontWeight: 380,
          lineHeight: 1.3,
          letterSpacing: "-0.015em",
          fontVariationSettings: "'SOFT' 40",
          maxWidth: 560,
        }}
      >
        {message}
      </p>
      <button
        onClick={onReset}
        className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-3 text-[14px] tracking-[0.01em] hover:bg-orange transition-colors"
        style={{ borderRadius: 2 }}
      >
        Start over
      </button>
    </div>
  );
}

function ResultPanel({
  file,
  result,
  onReset,
}: {
  file: File;
  result: AnalysisResult;
  onReset: () => void;
}) {
  return (
    <div className="w-full">
      <div className="flex items-baseline justify-between gap-4 flex-wrap border-t border-line pt-6 mb-8">
        <div>
          <div
            className="text-orange mb-2"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
            }}
          >
            Pre-read · {result.district} · {result.meetingDate}
          </div>
          <div
            className="text-mute"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              letterSpacing: "0.02em",
            }}
          >
            From {file.name}
          </div>
        </div>
        <button
          onClick={onReset}
          className="text-[14px] text-ink-soft hover:text-orange transition-colors"
        >
          Analyze another board book
        </button>
      </div>

      <ResultActions
        markdown={result.renderedMarkdown}
        district={result.district}
        meetingDate={result.meetingDate}
      />

      <div className="mt-10 border-t border-line pt-10">
        <PreReadRenderer markdown={result.renderedMarkdown} />
      </div>
    </div>
  );
}

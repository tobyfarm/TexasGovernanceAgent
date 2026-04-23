import type { Metadata } from "next";
import Link from "next/link";
import { TopNav } from "@/components/top-nav";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = {
  title: "About · Governance Agent",
  description:
    "A two-stage AI agent for Texas school trustees. Built by a sitting trustee. Open-source. MIT licensed.",
};

export default function AboutPage() {
  return (
    <>
      <TopNav />

      <section className="pt-[180px] pb-24">
        <div className="container-narrow">
          <div className="eyebrow mb-10 flex items-center gap-3">
            <span className="inline-block h-px w-7 bg-orange" aria-hidden />
            <span>About · the project</span>
          </div>

          <h1 className="section-title text-ink max-w-[820px] mb-8">
            A Red Team for board books,{" "}
            <em className="wonk-italic text-orange">
              authored by the trustees who read them.
            </em>
          </h1>

          <div
            className="max-w-[680px] space-y-6 text-ink-soft mb-16"
            style={{ fontSize: 17, lineHeight: 1.7 }}
          >
            <p>
              Texas trustees hold the exclusive power to govern student
              outcomes (TEC §11.151(b)). They&apos;re also the last line of
              defense against bad data, blanket citations, role drift, and
              delegation without oversight. The artifacts that carry that
              duty — board packets, strategic plans, monitoring reports — are
              produced by humans under pressure, with incomplete context.
            </p>
            <p>
              This agent does what an experienced trustee would do in four
              hours of hand analysis, in under sixty seconds. It reads every
              page. It maps every agenda item to statute. It flags every
              governance claim against a calibrated taxonomy. It writes the
              pre-read.
            </p>
            <p>
              The governance doctrine that drives the Red Team lives in a
              single markdown file. It is versioned, forkable, and authored
              by a sitting trustee. The whole thing is MIT licensed and
              self-hostable — no vendor lock-in, no black box.
            </p>
          </div>

          <h2
            className="serif text-ink mb-6"
            style={{
              fontSize: 32,
              fontWeight: 360,
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
              fontVariationSettings: "'SOFT' 50, 'opsz' 96",
            }}
          >
            How it works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-16">
            <Stage
              num="01"
              label="Claude · Analysis"
              title="Reads and writes the pre-read"
              body="A Claude Agent SDK loop walks the packet item by item, applying four domain Skills — statute-mapper, governance-principles, risk-flagger, output-formatter — against a bundled corpus of Texas statute and board policy. Output is a structured markdown pre-read."
              accent="orange"
            />
            <Stage
              num="02"
              label="Gemini · Live Q&A"
              title="Makes it conversational"
              body="Gemini 3.1 Flash Live opens a WebSocket session with the board book, the pre-read, and the doctrine pre-loaded in its 128k context window. The trustee speaks. The model answers in real time, constrained to that one document."
              accent="blue"
            />
          </div>

          <h2
            className="serif text-ink mb-6"
            style={{
              fontSize: 32,
              fontWeight: 360,
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
              fontVariationSettings: "'SOFT' 50, 'opsz' 96",
            }}
          >
            Links
          </h2>

          <ul className="list-none space-y-4 max-w-[680px]">
            <AboutLink
              label="Source code"
              href="https://github.com/royai/governance-agent"
              sublabel="MIT licensed · Self-hostable"
              external
            />
            <AboutLink
              label="The doctrine"
              href="/doctrine"
              sublabel="Governance principles · versioned markdown"
            />
            <AboutLink
              label="Run the Red Team"
              href="/analyze"
              sublabel="Drop a board book PDF"
            />
          </ul>

          <div className="mt-20 pt-10 border-t border-line flex items-center gap-4 serif italic text-ink-soft text-[17px] wonk-italic">
            <span
              className="inline-block h-px w-10 bg-orange flex-shrink-0"
              aria-hidden
            />
            <span style={{ letterSpacing: "-0.01em" }}>
              By{" "}
              <strong
                className="not-italic text-ink"
                style={{ fontWeight: 500, fontVariationSettings: "'SOFT' 40" }}
              >
                Toby Farmer
              </strong>
              {" "}— Elected Trustee, Brock ISD · Founder & CEO, Roy AI
            </span>
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}

function Stage({
  num,
  label,
  title,
  body,
  accent,
}: {
  num: string;
  label: string;
  title: string;
  body: string;
  accent: "orange" | "blue";
}) {
  const accentColor =
    accent === "blue" ? "text-blue-deep" : "text-orange";
  return (
    <div className="border-t border-line pt-6">
      <div
        className={`${accentColor} mb-3`}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        Stage {num} — {label}
      </div>
      <h3
        className="serif text-ink mb-3"
        style={{
          fontSize: 22,
          fontWeight: 400,
          letterSpacing: "-0.015em",
          lineHeight: 1.2,
          fontVariationSettings: "'SOFT' 50",
        }}
      >
        {title}
      </h3>
      <p
        className="text-ink-soft"
        style={{ fontSize: 15, lineHeight: 1.6 }}
      >
        {body}
      </p>
    </div>
  );
}

function AboutLink({
  label,
  href,
  sublabel,
  external,
}: {
  label: string;
  href: string;
  sublabel: string;
  external?: boolean;
}) {
  const inner = (
    <div className="flex items-baseline justify-between gap-4 py-3 border-b border-line group cursor-pointer">
      <span
        className="serif text-ink group-hover:text-orange transition-colors"
        style={{
          fontSize: 22,
          fontWeight: 380,
          letterSpacing: "-0.015em",
          fontVariationSettings: "'SOFT' 50",
        }}
      >
        {label}
        <span className="ml-3 text-mute" aria-hidden>
          {external ? "↗" : "→"}
        </span>
      </span>
      <span
        className="text-mute text-right hidden sm:inline"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.05em",
        }}
      >
        {sublabel}
      </span>
    </div>
  );
  return (
    <li>
      {external ? (
        <a href={href} target="_blank" rel="noreferrer">
          {inner}
        </a>
      ) : (
        <Link href={href}>{inner}</Link>
      )}
    </li>
  );
}

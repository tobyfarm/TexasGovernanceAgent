import Link from "next/link";
import { TopNav } from "@/components/top-nav";
import { SiteFooter } from "@/components/site-footer";
import { AnalysisCounter } from "@/components/analysis-counter";

export default function Home() {
  return (
    <>
      <TopNav />

      {/* HERO */}
      <section className="pt-[180px] pb-24 relative">
        <div className="container-wide">
          <div className="eyebrow mb-12 flex items-center gap-3">
            <span className="inline-block h-px w-7 bg-orange" aria-hidden />
            <span>
              Anthropic Hackathon · April 2026 · A Governance Agent for Texas
              Public Schools
            </span>
          </div>

          <h1 className="display text-ink max-w-[1100px]">
            Student outcomes are a function of
            <br />
            <em className="wonk-italic text-orange">governance quality.</em>
            <br />
            Governance quality is now automatable.
          </h1>

          <p className="hero-sub mt-10 max-w-[720px]">
            An open-source AI agent that turns dense board books into
            trustee-ready pre-reads, grounded in Texas statute and
            operator-level governance principles — with a live voice layer that
            lets any school board member interrogate the document
            conversationally.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/analyze"
              className="inline-flex items-center gap-2 bg-ink text-cream px-6 py-3.5 text-[15px] tracking-[0.01em] hover:bg-orange transition-colors"
              style={{ borderRadius: 2 }}
            >
              Analyze a board book
              <span aria-hidden>→</span>
            </Link>
            <a
              href="https://github.com/royai/governance-agent"
              className="inline-flex items-center gap-2 text-ink-soft text-[15px] hover:text-orange transition-colors"
              target="_blank"
              rel="noreferrer"
            >
              Read the source
              <span aria-hidden>↗</span>
            </a>
          </div>

          <AnalysisCounter />

          <div className="mt-16 flex items-center gap-4 serif italic text-ink-soft text-[17px] wonk-italic">
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

          <div className="mt-[72px] flex flex-wrap gap-x-14 gap-y-8 text-[13px] text-mute tracking-[0.02em]">
            <MetaItem
              label="Reference deployment"
              value="Brock ISD · Parker County, TX"
            />
            <MetaItem
              label="Analysis stack"
              value="Claude Agent SDK · Skills"
            />
            <MetaItem label="Live Q&A layer" value="Gemini 3.1 Flash Live" />
            <MetaItem label="Distribution" value="MIT · Self-hostable" />
          </div>
        </div>
      </section>

      {/* THREE-UP FEATURES */}
      <section
        className="py-24 relative"
        style={{ backgroundColor: "var(--cream-2)" }}
      >
        <div className="container-wide">
          <div className="flex items-center gap-4 label-mono mb-8">
            <span className="text-orange" style={{ fontSize: 12 }}>
              01
            </span>
            <span>What it does</span>
            <span className="h-px bg-line flex-1 max-w-20" aria-hidden />
          </div>

          <h2 className="section-title text-ink max-w-[900px] mb-8">
            Three things a trustee needs before a public meeting.{" "}
            <em className="wonk-italic text-orange">One workflow.</em>
          </h2>

          <p className="section-lede max-w-[720px] mb-14">
            The output is a single document in the format an experienced trustee
            would write by hand — ready to read, ready to cite, ready to
            question.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mt-14">
            <FeatureCell
              num="01"
              title="Board Book Red Team"
              body="Every agenda item mapped to TEC, TGC, TAC, and local policy. Every governance claim flagged WATCH, RED FLAG, or POSITIVE against a calibrated taxonomy. Every citation verified against the bundled statute corpus."
            />
            <FeatureCell
              num="02"
              title="Voice Q&A"
              body="Open the pre-read, tap once, ask anything. A live Gemini 3.1 Flash session loaded with the board book, the pre-read, and the principles excerpt — constrained to the document in front of you."
              accent="blue"
            />
            <FeatureCell
              num="03"
              title="Open Source"
              body="MIT licensed. Self-hostable. The governance doctrine lives in a single markdown file that any trustee can fork, question, or version. No vendor lock-in. No black box."
            />
          </div>
        </div>
      </section>

      {/* PULL QUOTE + THESIS */}
      <section className="py-24">
        <div className="container-wide">
          <div className="flex items-center gap-4 label-mono mb-8">
            <span className="text-orange" style={{ fontSize: 12 }}>
              02
            </span>
            <span>The thesis</span>
            <span className="h-px bg-line flex-1 max-w-20" aria-hidden />
          </div>

          <blockquote
            className="pull text-ink max-w-[900px] my-12"
            style={{ borderLeft: "2px solid var(--orange)", paddingLeft: 36 }}
          >
            When governance breaks, student outcomes follow.{" "}
            <em className="wonk-italic">
              TEA intervention is the late-stage symptom of a problem that was
              already visible in the board book six months earlier.
            </em>
          </blockquote>

          <div
            className="max-w-[700px] text-ink-soft space-y-5"
            style={{ fontSize: 17, lineHeight: 1.7 }}
          >
            <p>
              Under TEC §11.151(b), Texas trustees hold the{" "}
              <strong className="text-ink" style={{ fontWeight: 600 }}>
                exclusive power to govern
              </strong>
              . Under §11.1511 and §11.1515, they must adopt measurable goals,
              establish performance targets, and monitor progress.
            </p>
            <p>
              In practice, the artifacts that carry governance — agenda
              packets, strategic plans, monitoring reports — are produced by
              humans under pressure, with incomplete context. The duty gets
              diluted in the paperwork.
            </p>
            <p>
              This agent compresses four hours of hand analysis into sixty
              seconds. Same format. Same discipline. Same citations.
            </p>
          </div>
        </div>
      </section>

      {/* CTA BAND */}
      <section
        className="py-24"
        style={{ backgroundColor: "var(--cream-2)" }}
      >
        <div className="container-wide">
          <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-12 items-end">
            <h2 className="section-title text-ink">
              Drop in a board book.{" "}
              <em className="wonk-italic text-orange">Get the pre-read.</em>
            </h2>
            <div className="flex md:justify-end">
              <Link
                href="/analyze"
                className="inline-flex items-center gap-2 bg-ink text-cream px-6 py-3.5 text-[15px] tracking-[0.01em] hover:bg-orange transition-colors"
                style={{ borderRadius: 2 }}
              >
                Analyze a board book
                <span aria-hidden>→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div
        className="text-[11px] uppercase tracking-[0.15em] text-mute mb-2"
        style={{ fontFamily: "var(--font-sans)" }}
      >
        {label}
      </div>
      <div
        className="serif text-ink"
        style={{
          fontSize: 18,
          fontWeight: 400,
          letterSpacing: "-0.01em",
          fontVariationSettings: "'SOFT' 40",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function FeatureCell({
  num,
  title,
  body,
  accent = "orange",
}: {
  num: string;
  title: string;
  body: string;
  accent?: "orange" | "blue";
}) {
  const numColor = accent === "blue" ? "text-blue-deep" : "text-orange";
  return (
    <div className="border-t border-line pt-6">
      <div
        className={`${numColor} mb-4`}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.05em",
        }}
      >
        MODE {num}
      </div>
      <h3
        className="serif text-ink mb-3"
        style={{
          fontSize: 24,
          fontWeight: 380,
          letterSpacing: "-0.015em",
          lineHeight: 1.15,
          fontVariationSettings: "'SOFT' 60",
        }}
      >
        {title}
      </h3>
      <p className="text-ink-soft" style={{ fontSize: 15, lineHeight: 1.55 }}>
        {body}
      </p>
    </div>
  );
}

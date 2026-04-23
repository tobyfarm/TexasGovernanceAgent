import type { Metadata } from "next";
import { TopNav } from "@/components/top-nav";
import { SiteFooter } from "@/components/site-footer";
import { UploadZone } from "@/components/upload-zone";

export const metadata: Metadata = {
  title: "Analyze a board book · Governance Agent",
  description:
    "Drop a board book PDF. Get a trustee-ready pre-read in under a minute.",
};

export default function AnalyzePage() {
  return (
    <>
      <TopNav />

      <section className="pt-[180px] pb-16">
        <div className="container-narrow">
          <div className="eyebrow mb-10 flex items-center gap-3">
            <span className="inline-block h-px w-7 bg-orange" aria-hidden />
            <span>Analyze · Stage 01 · Claude</span>
          </div>

          <h1 className="section-title text-ink mb-8 max-w-[820px]">
            Drop a board book.{" "}
            <em className="wonk-italic text-orange">
              Get the trustee pre-read.
            </em>
          </h1>

          <p className="section-lede max-w-[680px] mb-14">
            Every agenda item walked through the four governance Skills. Every
            statute citation verified against the bundled corpus. Every
            governance claim flagged on the same WATCH / RED FLAG / POSITIVE
            taxonomy an experienced trustee would use.
          </p>

          <UploadZone />

          <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 border-t border-line pt-10">
            <FlowStep
              num="01"
              title="Parse"
              body="Pages become agenda items. Tables preserved. Attachments indexed."
            />
            <FlowStep
              num="02"
              title="Analyze"
              body="Statute-mapper, governance-principles, risk-flagger applied item by item."
            />
            <FlowStep
              num="03"
              title="Verify"
              body="Every citation checked against bundled TEC, TGC, TAC, MSRB corpus. Hallucinations dropped."
            />
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}

function FlowStep({
  num,
  title,
  body,
}: {
  num: string;
  title: string;
  body: string;
}) {
  return (
    <div>
      <div
        className="text-orange mb-3"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        Step {num}
      </div>
      <h3
        className="serif text-ink mb-2"
        style={{
          fontSize: 20,
          fontWeight: 380,
          letterSpacing: "-0.015em",
          fontVariationSettings: "'SOFT' 50",
        }}
      >
        {title}
      </h3>
      <p className="text-ink-soft" style={{ fontSize: 14, lineHeight: 1.55 }}>
        {body}
      </p>
    </div>
  );
}

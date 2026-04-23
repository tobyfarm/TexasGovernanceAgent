import type { Metadata } from "next";
import { TopNav } from "@/components/top-nav";
import { SiteFooter } from "@/components/site-footer";
import { PreReadRenderer } from "@/components/pre-read-renderer";
import { readPrinciples } from "@/lib/doctrine";

export const metadata: Metadata = {
  title: "The doctrine · Governance Agent",
  description:
    "The operator-level governance principles that drive the Red Team. Authored by a sitting Texas trustee. Versioned. Forkable.",
};

export default async function DoctrinePage() {
  const { markdown, missing } = await readPrinciples();

  return (
    <>
      <TopNav />

      <section className="pt-[180px] pb-16">
        <div className="container-narrow">
          <div className="eyebrow mb-10 flex items-center gap-3">
            <span className="inline-block h-px w-7 bg-orange" aria-hidden />
            <span>The source of truth · versioned · MIT</span>
          </div>

          <h1 className="section-title text-ink max-w-[820px] mb-8">
            The doctrine.{" "}
            <em className="wonk-italic text-orange">
              Where the governance IP lives.
            </em>
          </h1>

          <p className="section-lede max-w-[680px] mb-10">
            Every WATCH, every RED FLAG, every POSITIVE the agent emits is
            pattern-matched against this file. It is authored by a sitting
            trustee, versioned in git, and distributed under MIT. Fork it.
            Question it. Improve it.
          </p>

          <div className="flex flex-wrap gap-3 mb-14">
            <a
              href="https://github.com/royai/governance-agent/blob/main/skills/governance-principles/principles.md"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-ink-soft border border-line px-4 py-2.5 text-[13px] tracking-[0.01em] hover:border-orange hover:text-orange transition-colors"
              style={{ borderRadius: 2, background: "var(--cream)" }}
            >
              View on GitHub
              <span aria-hidden>↗</span>
            </a>
            <a
              href="/analyze"
              className="inline-flex items-center gap-2 bg-ink text-cream px-4 py-2.5 text-[13px] tracking-[0.01em] hover:bg-orange transition-colors"
              style={{ borderRadius: 2 }}
            >
              Run the Red Team
              <span aria-hidden>→</span>
            </a>
          </div>

          {missing && (
            <div
              className="mb-10 border-l-2 pl-5 py-3"
              style={{
                borderColor: "var(--blue)",
                background: "rgba(106, 155, 204, 0.12)",
              }}
            >
              <div
                className="mb-1 text-blue-deep"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                }}
              >
                Notice
              </div>
              <p
                className="text-ink-soft"
                style={{ fontSize: 15, lineHeight: 1.55 }}
              >
                The principles file hasn&apos;t shipped to this deploy yet.
                Check the repo for the latest.
              </p>
            </div>
          )}

          <div className="border-t border-line pt-10">
            <PreReadRenderer markdown={markdown} />
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}

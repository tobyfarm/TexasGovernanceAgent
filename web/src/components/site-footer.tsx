export function SiteFooter() {
  return (
    <footer className="bg-ink text-cream pt-20 pb-10 mt-20">
      <div className="container-wide grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-12">
        <div>
          <h4
            className="serif text-cream"
            style={{
              fontSize: "32px",
              fontWeight: 300,
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
              fontVariationSettings: "'SOFT' 50",
              maxWidth: "500px",
              marginBottom: "16px",
            }}
          >
            Student outcomes are a function of{" "}
            <em className="wonk-italic text-orange">governance quality.</em>
          </h4>
          <p className="text-mid-gray text-[14px] max-w-[400px]">
            Open-source. MIT licensed. Self-hostable. Built by a sitting trustee,
            for trustees.
          </p>
        </div>

        <div>
          <div className="label-mono text-mid-gray mb-4">Project</div>
          <ul className="list-none space-y-1.5">
            <li className="text-[14px] text-cream">
              <a
                href="https://github.com/royai/governance-agent"
                className="hover:text-orange transition-colors"
                target="_blank"
                rel="noreferrer"
              >
                GitHub repo
              </a>
            </li>
            <li className="text-[14px] text-cream">
              <a
                href="/doctrine"
                className="hover:text-orange transition-colors"
              >
                The doctrine
              </a>
            </li>
            <li className="text-[14px] text-cream">
              <a
                href="/about"
                className="hover:text-orange transition-colors"
              >
                About
              </a>
            </li>
          </ul>
        </div>

        <div>
          <div className="label-mono text-mid-gray mb-4">Built with</div>
          <ul className="list-none space-y-1.5">
            <li className="text-[14px] text-cream">Claude Agent SDK</li>
            <li className="text-[14px] text-cream">Gemini 3.1 Flash Live</li>
            <li className="text-[14px] text-cream">Next.js · Vercel</li>
          </ul>
        </div>
      </div>

      <div
        className="mt-14 pt-6 border-t border-white/10 mx-auto max-w-[1240px] flex flex-wrap items-center justify-between gap-4 px-10"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          letterSpacing: "0.05em",
          color: "var(--mid-gray)",
        }}
      >
        <span>© 2026 Roy AI · MIT License</span>
        <span>Reference deployment · Brock ISD · Parker County, Texas</span>
      </div>
    </footer>
  );
}

import Link from "next/link";

export function TopNav() {
  return (
    <nav
      className="fixed inset-x-0 top-0 z-50 border-b border-black/5"
      style={{
        background: "rgba(250, 249, 245, 0.82)",
        backdropFilter: "blur(16px) saturate(120%)",
        WebkitBackdropFilter: "blur(16px) saturate(120%)",
      }}
    >
      <div className="container-wide flex items-center justify-between py-[18px]">
        <Link href="/" className="flex items-baseline gap-[10px] no-underline">
          <span
            className="inline-block h-2 w-2 rounded-full bg-orange"
            style={{ transform: "translateY(-2px)" }}
            aria-hidden
          />
          <span
            className="serif text-ink"
            style={{
              fontWeight: 500,
              fontSize: "19px",
              letterSpacing: "-0.015em",
            }}
          >
            Governance Agent
          </span>
          <span className="hidden sm:inline text-mute text-[14px] uppercase tracking-[0.02em] font-normal">
            · Roy AI × Claude
          </span>
        </Link>
        <ul className="hidden md:flex list-none gap-8 items-center">
          <li>
            <Link
              href="/analyze"
              className="text-[14px] text-ink-soft hover:text-orange transition-colors tracking-[0.01em]"
            >
              Analyze
            </Link>
          </li>
          <li>
            <Link
              href="/doctrine"
              className="text-[14px] text-ink-soft hover:text-orange transition-colors tracking-[0.01em]"
            >
              Doctrine
            </Link>
          </li>
          <li>
            <Link
              href="/about"
              className="text-[14px] text-ink-soft hover:text-orange transition-colors tracking-[0.01em]"
            >
              About
            </Link>
          </li>
          <li>
            <a
              href="https://github.com/royai/governance-agent"
              className="text-[14px] text-ink-soft hover:text-orange transition-colors tracking-[0.01em]"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </li>
        </ul>
      </div>
    </nav>
  );
}

"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";

type Props = {
  markdown: string;
  className?: string;
};

const FLAG_PATTERN = /^(RED FLAG|WATCH|POSITIVE)\b[: \-—]*/i;

export function PreReadRenderer({ markdown, className }: Props) {
  return (
    <article
      className={`pre-read ${className ?? ""}`}
      style={{ maxWidth: "68ch" }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}

const components: Components = {
  h1: ({ children }) => (
    <h1
      className="serif text-ink mb-8 mt-10"
      style={{
        fontSize: "clamp(32px, 4vw, 48px)",
        fontWeight: 340,
        letterSpacing: "-0.025em",
        lineHeight: 1.05,
        fontVariationSettings: "'SOFT' 60, 'opsz' 144",
      }}
    >
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2
      className="serif text-ink mt-16 mb-5"
      style={{
        fontSize: 32,
        fontWeight: 360,
        letterSpacing: "-0.02em",
        lineHeight: 1.1,
        fontVariationSettings: "'SOFT' 50, 'opsz' 96",
      }}
    >
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3
      className="serif text-ink mt-10 mb-3"
      style={{
        fontSize: 22,
        fontWeight: 400,
        letterSpacing: "-0.015em",
        lineHeight: 1.2,
        fontVariationSettings: "'SOFT' 50",
      }}
    >
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4
      className="mt-8 mb-2 text-orange"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        letterSpacing: "0.15em",
        textTransform: "uppercase",
      }}
    >
      {children}
    </h4>
  ),
  p: ({ children }) => {
    // Detect WATCH / RED FLAG / POSITIVE at the head of the paragraph and
    // render as a colored callout. Handles both plain-text openings
    // ("RED FLAG: ...") and bold wrappers ("**RED FLAG** ...") which GFM
    // turns into a leading <strong> child.
    const detected = detectLeadingFlag(children);
    if (detected) {
      return (
        <FlagCallout level={detected.level}>{detected.rest}</FlagCallout>
      );
    }
    return (
      <p
        className="text-ink-soft mb-5"
        style={{ fontSize: 17, lineHeight: 1.7 }}
      >
        {children}
      </p>
    );
  },
  ul: ({ children }) => (
    <ul className="list-none ml-0 my-5 space-y-2">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-none ml-0 my-5 space-y-3 counter-reset-item">
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => {
    // GfM passes `ordered` only to ol/ul. For li we use the wrapping element type.
    const isOrdered = (props as { ordered?: boolean }).ordered;
    if (isOrdered) {
      return (
        <li
          className="serif italic text-ink pl-8 relative"
          style={{
            fontSize: 19,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
            fontVariationSettings: "'SOFT' 100, 'WONK' 1",
          }}
        >
          {children}
        </li>
      );
    }
    return (
      <li
        className="text-ink-soft pl-6 relative"
        style={{ fontSize: 16, lineHeight: 1.6 }}
      >
        <span
          className="absolute left-0 text-orange"
          style={{ fontFamily: "var(--font-serif)" }}
          aria-hidden
        >
          ↳
        </span>
        {children}
      </li>
    );
  },
  blockquote: ({ children }) => (
    <blockquote
      className="serif text-ink my-8"
      style={{
        borderLeft: "2px solid var(--orange)",
        paddingLeft: 28,
        fontSize: 20,
        lineHeight: 1.35,
        fontStyle: "italic",
        fontWeight: 320,
        letterSpacing: "-0.015em",
        fontVariationSettings: "'SOFT' 100, 'WONK' 1",
      }}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children }) => {
    const isInline = !className;
    if (isInline) {
      return <InlineCite>{children}</InlineCite>;
    }
    return (
      <code
        className="block p-4 border border-line bg-cream text-ink-soft overflow-x-auto"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          lineHeight: 1.55,
        }}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="my-6">{children}</pre>,
  table: ({ children }) => (
    <div className="my-8 overflow-x-auto border border-line">
      <table className="w-full border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ background: "var(--cream-2)" }}>{children}</thead>
  ),
  th: ({ children }) => (
    <th
      className="text-left text-mute px-4 py-3 border-b border-line"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        fontWeight: 500,
      }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => {
    const level = detectCellFlag(children);
    if (level) {
      return (
        <td
          className="px-4 py-3 border-b border-line align-top"
          style={{ fontSize: 14 }}
        >
          <FlagBadge level={level} />
        </td>
      );
    }
    return (
      <td
        className="px-4 py-3 border-b border-line text-ink-soft align-top"
        style={{ fontSize: 14, lineHeight: 1.5 }}
      >
        {children}
      </td>
    );
  },
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-orange-deep underline decoration-orange/40 underline-offset-2 hover:text-orange transition-colors"
    >
      {children}
    </a>
  ),
  hr: () => (
    <hr className="my-12 border-0 border-t border-line" />
  ),
  strong: ({ children }) => (
    <strong className="text-ink" style={{ fontWeight: 600 }}>
      {children}
    </strong>
  ),
  em: ({ children }) => (
    <em className="wonk-italic text-ink">{children}</em>
  ),
};

/* --- flag helpers --- */

type FlagLevel = "RED_FLAG" | "WATCH" | "POSITIVE";

function flagStyle(level: FlagLevel) {
  switch (level) {
    case "RED_FLAG":
      return {
        bg: "rgba(217, 119, 87, 0.16)",
        text: "var(--orange-deep)",
        border: "var(--orange)",
        label: "RED FLAG",
      };
    case "WATCH":
      return {
        bg: "rgba(106, 155, 204, 0.16)",
        text: "var(--blue-deep)",
        border: "var(--blue)",
        label: "WATCH",
      };
    case "POSITIVE":
      return {
        bg: "rgba(120, 140, 93, 0.16)",
        text: "var(--green-deep)",
        border: "var(--green)",
        label: "POSITIVE",
      };
  }
}

function FlagBadge({ level }: { level: FlagLevel }) {
  const s = flagStyle(level);
  return (
    <span
      className="inline-block"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        padding: "2px 8px",
        borderRadius: 2,
        background: s.bg,
        color: s.text,
      }}
    >
      {s.label}
    </span>
  );
}

function FlagCallout({
  level,
  children,
}: {
  level: FlagLevel;
  children: ReactNode;
}) {
  const s = flagStyle(level);
  return (
    <div
      className="my-6 pl-5 py-3"
      style={{
        borderLeft: `3px solid ${s.border}`,
        background: s.bg,
      }}
    >
      <div className="mb-1">
        <FlagBadge level={level} />
      </div>
      <p className="text-ink-soft" style={{ fontSize: 16, lineHeight: 1.55 }}>
        {children}
      </p>
    </div>
  );
}

function InlineCite({ children }: { children: ReactNode }) {
  return (
    <code
      className="cite-chip"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        letterSpacing: "-0.005em",
        color: "var(--orange-deep)",
        background: "rgba(217, 119, 87, 0.10)",
        padding: "1px 6px",
        borderRadius: 2,
      }}
    >
      {children}
    </code>
  );
}

/* --- helpers for content inspection --- */

/**
 * Flatten the first leaf of a React tree to raw text, for prefix detection.
 * Walks `<strong>`, `<em>`, and arrays; stops at the first text leaf.
 */
function firstLeafText(node: ReactNode): string | null {
  if (node == null || typeof node === "boolean") return null;
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) {
    for (const c of node) {
      const t = firstLeafText(c);
      if (t) return t;
    }
    return null;
  }
  // React element — peek at its children.
  const el = node as { props?: { children?: ReactNode } };
  if (el && typeof el === "object" && "props" in el) {
    return firstLeafText(el.props?.children ?? null);
  }
  return null;
}

/**
 * Detect a leading flag keyword and return the unconsumed rest of the tree.
 *
 * Handles:
 *   - plain text:    "RED FLAG: foo"
 *   - bold wrapper:  "**RED FLAG**: foo"   (first child is <strong>RED FLAG</strong>)
 */
function detectLeadingFlag(
  children: ReactNode,
): { level: FlagLevel; rest: ReactNode } | null {
  const first = firstLeafText(children);
  if (!first) return null;
  const m = FLAG_PATTERN.exec(first);
  if (!m) return null;
  const level = m[1].toUpperCase().replace(" ", "_") as FlagLevel;

  // Scan the children array and drop everything through the matched keyword.
  if (typeof children === "string") {
    return { level, rest: children.replace(FLAG_PATTERN, "") };
  }
  if (!Array.isArray(children)) {
    // Single element — almost always a <strong>. Drop it entirely and let
    // the rest fall through as empty prose; the callout keyword carries.
    return { level, rest: "" };
  }

  const out: ReactNode[] = [];
  let consumed = false;
  for (const c of children) {
    if (consumed) {
      out.push(c);
      continue;
    }
    if (typeof c === "string") {
      const stripped = c.replace(FLAG_PATTERN, "");
      if (stripped !== c || FLAG_PATTERN.test(c)) {
        consumed = true;
        if (stripped) out.push(stripped);
        continue;
      }
      // Stray whitespace before the flag — skip.
      if (c.trim() === "") continue;
      // First text doesn't match flag; abort.
      out.push(c);
      consumed = true;
      continue;
    }
    // Non-string element — if it contains the flag, drop the whole element.
    const peek = firstLeafText(c);
    if (peek && FLAG_PATTERN.test(peek)) {
      consumed = true;
      continue;
    }
    // Otherwise keep and stop consuming.
    out.push(c);
    consumed = true;
  }
  return { level, rest: out };
}

/**
 * Table-cell flag detection. Recognizes WATCH / RED FLAG / POSITIVE and
 * also the HIGH / MEDIUM / LOW risk-level shorthand used in the Brock
 * executive-summary table.
 */
function detectCellFlag(children: ReactNode): FlagLevel | null {
  const raw = firstLeafText(children);
  if (!raw) return null;
  const t = raw.trim().toUpperCase();
  if (/^RED\s*FLAG\b/.test(t)) return "RED_FLAG";
  if (/^WATCH\b/.test(t)) return "WATCH";
  if (/^POSITIVE\b/.test(t)) return "POSITIVE";
  if (/^HIGH\b/.test(t)) return "RED_FLAG";
  if (/^MEDIUM\b/.test(t)) return "WATCH";
  if (/^LOW\b/.test(t)) return "POSITIVE";
  return null;
}

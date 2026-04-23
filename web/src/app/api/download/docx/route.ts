/**
 * Minimal markdown → DOCX converter. Handles headings, paragraphs, lists,
 * bold/italic runs, fenced tables, and inline code. Not a full CommonMark
 * renderer — this is the pre-read template shape only. Agent F may replace
 * this with a shared generator later; the HTTP shape stays the same.
 */

import { NextResponse } from "next/server";
import {
  Document,
  Packer,
  Paragraph,
  HeadingLevel,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
} from "docx";

export const runtime = "nodejs";

type Body = { markdown: string; title: string };

export async function POST(req: Request) {
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const { markdown, title } = body;
  if (!markdown || typeof markdown !== "string") {
    return NextResponse.json({ error: "markdown required" }, { status: 400 });
  }

  const children = renderMarkdown(markdown);

  const doc = new Document({
    creator: "Governance Agent · Roy AI",
    title,
    styles: {
      default: {
        document: {
          run: { font: "Calibri", size: 22 }, // 11pt
        },
      },
    },
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);

  return new Response(new Uint8Array(buffer), {
    headers: {
      "Content-Type":
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "Content-Disposition": "attachment",
    },
  });
}

/* ------------------------------------------------------------------ */
/* Markdown rendering                                                  */
/* ------------------------------------------------------------------ */

function renderMarkdown(md: string): (Paragraph | Table)[] {
  const out: (Paragraph | Table)[] = [];
  const lines = md.split(/\r?\n/);
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (!line.trim()) {
      i++;
      continue;
    }

    // Heading
    const heading = /^(#{1,4})\s+(.+?)\s*#*\s*$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const text = stripMdEmphasis(heading[2]);
      out.push(
        new Paragraph({
          heading:
            level === 1
              ? HeadingLevel.HEADING_1
              : level === 2
                ? HeadingLevel.HEADING_2
                : level === 3
                  ? HeadingLevel.HEADING_3
                  : HeadingLevel.HEADING_4,
          children: parseRuns(text),
          spacing: { before: 280, after: 160 },
        }),
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}\s*$/.test(line)) {
      out.push(
        new Paragraph({
          text: "",
          border: {
            bottom: { color: "CCCCCC", style: "single", size: 6, space: 1 },
          },
          spacing: { before: 120, after: 120 },
        }),
      );
      i++;
      continue;
    }

    // Table: detect header | separator line | body
    if (line.trim().startsWith("|") && isTableSeparator(lines[i + 1])) {
      const { table, consumed } = parseTable(lines, i);
      out.push(table);
      i += consumed;
      continue;
    }

    // Bullet list
    if (/^\s*[-*]\s+/.test(line)) {
      const { paragraphs, consumed } = parseList(lines, i, false);
      out.push(...paragraphs);
      i += consumed;
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const { paragraphs, consumed } = parseList(lines, i, true);
      out.push(...paragraphs);
      i += consumed;
      continue;
    }

    // Blockquote
    if (line.startsWith(">")) {
      const quoted = line.replace(/^>\s?/, "");
      out.push(
        new Paragraph({
          children: parseRuns(quoted),
          indent: { left: 360 },
          spacing: { before: 120, after: 120 },
          border: {
            left: { color: "D97757", style: "single", size: 12, space: 8 },
          },
        }),
      );
      i++;
      continue;
    }

    // Default: paragraph (merge adjacent non-blank lines)
    const paraLines: string[] = [line];
    let j = i + 1;
    while (j < lines.length && lines[j].trim() && !isBlockStart(lines[j])) {
      paraLines.push(lines[j]);
      j++;
    }
    out.push(
      new Paragraph({
        children: parseRuns(paraLines.join(" ")),
        spacing: { before: 100, after: 100 },
      }),
    );
    i = j;
  }

  return out;
}

function isBlockStart(line: string): boolean {
  if (/^#{1,6}\s+/.test(line)) return true;
  if (/^\s*[-*]\s+/.test(line)) return true;
  if (/^\s*\d+\.\s+/.test(line)) return true;
  if (line.startsWith(">")) return true;
  if (line.trim().startsWith("|")) return true;
  if (/^[-*_]{3,}\s*$/.test(line)) return true;
  return false;
}

function parseList(
  lines: string[],
  start: number,
  ordered: boolean,
): { paragraphs: Paragraph[]; consumed: number } {
  const paragraphs: Paragraph[] = [];
  let i = start;
  let ordinal = 1;
  while (i < lines.length) {
    const line = lines[i];
    const m = ordered
      ? /^\s*(\d+)\.\s+(.*)$/.exec(line)
      : /^\s*[-*]\s+(.*)$/.exec(line);
    if (!m) break;
    const content = ordered ? m[2] : m[1];
    paragraphs.push(
      new Paragraph({
        children: [
          new TextRun({
            text: ordered ? `${ordinal}.  ` : "•  ",
            color: "D97757",
          }),
          ...parseRuns(content),
        ],
        indent: { left: 360, hanging: 260 },
        spacing: { before: 60, after: 60 },
      }),
    );
    ordinal++;
    i++;
  }
  return { paragraphs, consumed: i - start };
}

function isTableSeparator(line: string | undefined): boolean {
  if (!line) return false;
  const stripped = line.trim();
  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(stripped);
}

function parseTable(
  lines: string[],
  start: number,
): { table: Table; consumed: number } {
  const rows: string[][] = [];
  rows.push(splitRow(lines[start]));
  let i = start + 2; // skip header + separator
  while (i < lines.length && lines[i].trim().startsWith("|")) {
    rows.push(splitRow(lines[i]));
    i++;
  }

  const cols = rows[0].length;
  const table = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: rows.map(
      (row, rIdx) =>
        new TableRow({
          tableHeader: rIdx === 0,
          children: Array.from({ length: cols }).map((_, cIdx) => {
            const cell = row[cIdx] ?? "";
            return new TableCell({
              children: [
                new Paragraph({
                  children: parseRuns(cell),
                  alignment:
                    rIdx === 0 ? AlignmentType.LEFT : AlignmentType.LEFT,
                }),
              ],
              width: { size: Math.floor(100 / cols), type: WidthType.PERCENTAGE },
              shading: rIdx === 0 ? { fill: "F3F1E8" } : undefined,
            });
          }),
        }),
    ),
  });

  return { table, consumed: i - start };
}

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\||\|$/g, "");
  return trimmed.split("|").map((c) => c.trim());
}

/* Inline runs: bold, italic, code */

function parseRuns(text: string): TextRun[] {
  const runs: TextRun[] = [];
  // Normalize markdown escapes like \&
  text = text.replace(/\\(.)/g, "$1");

  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      runs.push(new TextRun(text.slice(last, m.index)));
    }
    const token = m[0];
    if (token.startsWith("**")) {
      runs.push(new TextRun({ text: token.slice(2, -2), bold: true }));
    } else if (token.startsWith("`")) {
      runs.push(
        new TextRun({
          text: token.slice(1, -1),
          font: "Consolas",
          color: "B85F3F",
        }),
      );
    } else {
      runs.push(new TextRun({ text: token.slice(1, -1), italics: true }));
    }
    last = re.lastIndex;
  }
  if (last < text.length) {
    runs.push(new TextRun(text.slice(last)));
  }
  return runs.length ? runs : [new TextRun(text)];
}

function stripMdEmphasis(s: string): string {
  // Leave the markers so parseRuns reads them; this helper exists only
  // in case we want to strip later. For now it's a pass-through.
  return s;
}

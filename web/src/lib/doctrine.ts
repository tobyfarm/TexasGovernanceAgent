import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Loads the governance doctrine source of truth.
 * The file lives in skills/governance-principles/principles.md at the repo
 * root. This site is deployed from web/ so we walk up one level.
 *
 * Agent C owns the doctrine content. If it's missing, we fall back to a
 * friendly placeholder instead of failing the build — the site still loads.
 */
export async function readPrinciples(): Promise<{
  markdown: string;
  missing: boolean;
}> {
  const filePath = path.join(
    process.cwd(),
    "..",
    "skills",
    "governance-principles",
    "principles.md",
  );
  try {
    const markdown = await readFile(filePath, "utf8");
    return { markdown, missing: false };
  } catch {
    return {
      markdown:
        "# The doctrine is still being authored.\n\nThe governance principles that drive the Red Team agent live in `skills/governance-principles/principles.md`. That file is owned by Agent C and will be published here as soon as it's written.\n\nIn the meantime, read the [project README](https://github.com/royai/governance-agent) or the architecture overview on the [about page](/about).",
      missing: true,
    };
  }
}

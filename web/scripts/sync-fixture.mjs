/**
 * Syncs the canonical reference pre-read into web/src/fixtures so the
 * demo SSE route can serve it at runtime.
 *
 * Vercel only deploys the web/ directory, so anything outside it (like
 * the canonical artifact in ../examples/) won't be in the function's
 * runtime filesystem. Running this on prebuild keeps the local copy
 * in lockstep with the upstream source of truth.
 *
 * Skips silently if the canonical file isn't present (e.g. CI checking
 * out only the web/ subdir, or a tarball'd build context).
 */

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");

const sources = [
  resolve(repoRoot, "examples", "brock_april_13_2026_prereadhand.md"),
];
const dest = resolve(here, "..", "src", "fixtures", "brock-prereadhand.md");

const source = sources.find((p) => existsSync(p));
if (!source) {
  console.warn(
    `[sync-fixture] canonical pre-read not found in:\n  ${sources.join("\n  ")}\n  Skipping — using whatever is already at ${dest}`,
  );
  process.exit(0);
}

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(source, dest);
console.log(`[sync-fixture] copied\n  ${source}\n  → ${dest}`);

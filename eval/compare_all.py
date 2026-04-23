"""Compare every recent run against a reference hand version.

Usage:
    uv run python -m eval.compare_all
        --hand examples/brock_april_13_2026_prereadhand.md
        [--limit 10]

Produces a table of eval metrics across runs for quick Day-3 calibration:

    run_id       generated_at          words   ratio  hdr   miss_cite  score
    8c1b3d24…    2026-04-23T07:50      32536   2.631  0.04      29     0.099
    0370b107…    2026-04-22T23:43      15420   1.246  0.35      15     0.421
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.compare import compare

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "logs" / "runs"


def _list_runs(limit: int) -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    dirs = sorted(
        (d for d in RUNS_DIR.iterdir() if d.is_dir() and (d / "result.md").exists()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank recent runs against a hand reference.")
    parser.add_argument("--hand", type=Path, required=True, help="Hand-version markdown path.")
    parser.add_argument("--limit", type=int, default=20, help="Max runs to consider.")
    parser.add_argument("--json", action="store_true", help="Emit JSON rather than a table.")
    args = parser.parse_args(argv)

    if not args.hand.exists():
        print(f"error: hand not found: {args.hand}", file=sys.stderr)
        return 2

    rows = []
    for run_dir in _list_runs(args.limit):
        result_md = run_dir / "result.md"
        meta_path = run_dir / "meta.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                pass
        try:
            report = compare(result_md, args.hand)
        except Exception as exc:  # noqa: BLE001 — surface issue but keep going
            rows.append(
                {
                    "run_id": run_dir.name,
                    "error": str(exc),
                }
            )
            continue
        words = len(result_md.read_text().split())
        rows.append(
            {
                "run_id": run_dir.name,
                "generated_at": meta.get("generated_at", ""),
                "mode": meta.get("mode", ""),
                "item_count": meta.get("item_count", 0),
                "words": words,
                "word_count_ratio": report.word_count_ratio,
                "header_overlap": report.header_overlap,
                "missing_citations": len(report.citations_only_in_hand),
                "score": report.score(),
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    # Plain-text table
    header = (
        f"{'run_id':<14} {'generated_at':<20} {'items':>5} {'words':>7} "
        f"{'ratio':>6} {'hdr':>5} {'miss':>5} {'score':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        if "error" in r:
            print(f"{r['run_id'][:12]:<14} ERROR: {r['error']}")
            continue
        print(
            f"{r['run_id'][:12]:<14} {r['generated_at'][:19]:<20} "
            f"{r['item_count']:>5} {r['words']:>7} "
            f"{r['word_count_ratio']:>6.3f} {r['header_overlap']:>5.2f} "
            f"{r['missing_citations']:>5} {r['score']:>6.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

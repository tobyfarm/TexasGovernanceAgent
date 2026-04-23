"""Side-by-side comparator for generated vs hand-written pre-reads.

The Day 3 eval compares `examples/<x>_output.md` against `examples/<x>_prereadhand.md`
along dimensions the acceptance test cares about:

    - Structure: section headers match (executive summary → per-item → checklist)
    - Citation coverage: every statute authority the hand version cites is
      present in the generated version (and vice versa — extras are flagged)
    - Flag counts: the number of WATCH / RED_FLAG / POSITIVE markers is in the
      same ballpark as the hand version
    - Length parity: word count ratio in [0.5x, 2x]

This is a *coarse* comparator. The human eval is still load-bearing. The point
is to surface deltas so Agents B/C/F know which Skill needs tuning overnight.

CLI:
    uv run python -m eval.compare <generated.md> <hand.md>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# TEC §x.y(z), TGC §551.074, TAC §61.1, Local Policy CE (LEGAL), MSRB G-17, ...
_CITATION_RE = re.compile(
    r"\b(?:TEC|TGC|TAC|TEX\.?\s+EDUC\.?\s+CODE|TEX\.?\s+GOV\.?\s+CODE|MSRB|19\s*TAC)\s*§?\s*[\w\.\-()]+",
    re.IGNORECASE,
)
_FLAG_RE = re.compile(r"\b(RED[\s_-]?FLAG|WATCH|POSITIVE)\b", re.IGNORECASE)
_HEADER_RE = re.compile(r"^#+\s+(.*?)\s*$", re.MULTILINE)


@dataclass
class ComparisonReport:
    generated_path: str
    hand_path: str
    word_count_ratio: float
    header_overlap: float
    citations_only_in_hand: list[str] = field(default_factory=list)
    citations_only_in_generated: list[str] = field(default_factory=list)
    flag_counts_generated: dict[str, int] = field(default_factory=dict)
    flag_counts_hand: dict[str, int] = field(default_factory=dict)

    def score(self) -> float:
        """Heuristic 0-1 quality score. Useful for trend watching, not pass/fail."""
        len_score = 1.0 - min(abs(self.word_count_ratio - 1.0), 1.0)
        missing_cites = len(self.citations_only_in_hand)
        cov_score = (
            1.0 if missing_cites == 0 else max(0.0, 1.0 - missing_cites / (missing_cites + 10))
        )
        return round((len_score + cov_score + self.header_overlap) / 3, 3)


def _norm(text: str) -> str:
    return text.strip().lower()


def _extract_citations(text: str) -> set[str]:
    return {_norm(m.group(0)) for m in _CITATION_RE.finditer(text)}


def _flag_counts(text: str) -> dict[str, int]:
    counts = {"RED_FLAG": 0, "WATCH": 0, "POSITIVE": 0}
    for m in _FLAG_RE.finditer(text):
        label = m.group(1).upper().replace(" ", "_").replace("-", "_")
        if label in ("RED_FLAG", "REDFLAG"):
            counts["RED_FLAG"] += 1
        elif label == "WATCH":
            counts["WATCH"] += 1
        elif label == "POSITIVE":
            counts["POSITIVE"] += 1
    return counts


def _headers(text: str) -> set[str]:
    return {_norm(m.group(1)) for m in _HEADER_RE.finditer(text)}


def compare(generated: Path, hand: Path) -> ComparisonReport:
    gtext = generated.read_text(encoding="utf-8")
    htext = hand.read_text(encoding="utf-8")

    gwords = len(gtext.split())
    hwords = len(htext.split()) or 1
    ratio = gwords / hwords

    gheaders = _headers(gtext)
    hheaders = _headers(htext)
    overlap = len(gheaders & hheaders) / max(len(hheaders), 1)

    gcites = _extract_citations(gtext)
    hcites = _extract_citations(htext)

    return ComparisonReport(
        generated_path=str(generated),
        hand_path=str(hand),
        word_count_ratio=round(ratio, 3),
        header_overlap=round(overlap, 3),
        citations_only_in_hand=sorted(hcites - gcites),
        citations_only_in_generated=sorted(gcites - hcites),
        flag_counts_generated=_flag_counts(gtext),
        flag_counts_hand=_flag_counts(htext),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare generated pre-read vs hand version.")
    parser.add_argument("generated", type=Path)
    parser.add_argument("hand", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human prose.")
    args = parser.parse_args(argv)

    if not args.generated.exists():
        print(f"error: not found: {args.generated}", file=sys.stderr)
        return 2
    if not args.hand.exists():
        print(f"error: not found: {args.hand}", file=sys.stderr)
        return 2

    report = compare(args.generated, args.hand)

    if args.json:
        print(json.dumps(report.__dict__, indent=2))
        return 0

    print(f"generated : {report.generated_path}")
    print(f"hand      : {report.hand_path}")
    print(f"word count ratio : {report.word_count_ratio}  (target ~1.0)")
    print(f"header overlap   : {report.header_overlap}  (1.0 = every hand header present)")
    print(
        f"flag counts      : generated={report.flag_counts_generated}  hand={report.flag_counts_hand}"
    )
    print(f"citations only in hand      : {len(report.citations_only_in_hand)}")
    for c in report.citations_only_in_hand[:10]:
        print(f"    - {c}")
    print(f"citations only in generated : {len(report.citations_only_in_generated)}")
    for c in report.citations_only_in_generated[:10]:
        print(f"    + {c}")
    print(f"heuristic score : {report.score()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

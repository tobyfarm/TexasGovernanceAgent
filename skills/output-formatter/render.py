# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2>=3.1"]
# ///
"""Output formatter renderer for Agent F.

Consumes an AnalysisResult (pydantic model from agent/types.py, or an
equivalent dict) and returns markdown rendered through the appropriate
Jinja2 template.

Two modes:
  BROCK_FULL  -> templates/brock_full.md   (default)
  SAMCO_LOQ   -> templates/samco_loq.md

Programmatic use (from Agent A, after the pipeline assembles AnalysisResult):

    # agent A imports this via a sys.path shim — see SKILL.md.
    from render import render, render_to_file

    markdown = render(analysis_result)

CLI use (subprocess-style integration):

    uv run python skills/output-formatter/render.py \\
        --from-json logs/runs/abc/result.json \\
        --out logs/runs/abc/result.md \\
        [--metadata-json path/to/meta.json]

Run with no args to produce dummy renders into examples/ for eyeballing:

    uv run python skills/output-formatter/render.py
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SKILL_DIR / "templates"

_TEMPLATES = {
    "BROCK_FULL": "brock_full.md",
    "SAMCO_LOQ": "samco_loq.md",
}

# Raw flag severities (Agent A / Agent C shape) mapped to the HIGH/MEDIUM/LOW
# risk vocabulary the hand pre-read uses in the Executive Summary table.
# The hand version's risk level is a curated judgment, not a strict max-
# severity, so this mapping is a lossy fallback. When Agent C grows a
# per-item `risk_level` field, the adapter will prefer it.
_SEVERITY_TO_RISK_LEVEL: dict[str, str] = {
    "RED_FLAG": "HIGH",
    "WATCH": "MEDIUM",
    "POSITIVE": "LOW",
    "NONE": "LOW",
}

# Defaults filled in when meeting_metadata is sparse (Agent A currently emits
# just {source, run_id}). Callers should override via metadata_overrides=...
# or the `--metadata-json` CLI flag when they have real values.
_DEFAULT_META: dict[str, Any] = {
    "district_name_upper": "DISTRICT",
    "meeting_type": "Regular Meeting",
    "meeting_date": "(meeting date not provided)",
    "meeting_time": "(time not provided)",
    "location": "(location not provided)",
    "trustee_name": "(trustee name not provided)",
    "page_count": "(page count not provided)",
}


# ---------------------------------------------------------------------------
# Normalization — adapt Agent A's AnalysisResult shape to template shape.
# ---------------------------------------------------------------------------


def _as_dict(analysis_result: Any) -> dict[str, Any]:
    if hasattr(analysis_result, "model_dump"):
        return analysis_result.model_dump(mode="json")
    return deepcopy(dict(analysis_result))


def _normalize_meeting_metadata(
    raw: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    meta = dict(_DEFAULT_META)
    if raw:
        meta.update({k: v for k, v in raw.items() if v is not None})
    if overrides:
        meta.update({k: v for k, v in overrides.items() if v is not None})
    return meta


def _is_template_shape_row(row: dict[str, Any]) -> bool:
    return "item_title" in row and "key_finding" in row and "risk_level" in row


def _normalize_executive_summary_row(
    row: dict[str, Any],
    item_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Accept either the template shape or Agent A's raw shape; emit template shape."""
    if _is_template_shape_row(row):
        return row

    item_id = row.get("item_id", "")
    item_title = row.get("title") or f"Item {item_id}"
    raw_risk = row.get("risk", "NONE")
    risk_level = _SEVERITY_TO_RISK_LEVEL.get(raw_risk, "LOW")

    # key_finding fallback: first flag's summary from the matching item.
    item = item_by_id.get(item_id, {})
    flags = item.get("flags") or []
    if flags:
        first = flags[0]
        key_finding = first.get("summary", "").strip()
    else:
        key_finding = item.get("summary", "").strip().split("\n", 1)[0]

    if not key_finding:
        key_finding = "(no analyst finding)"

    return {
        "item_title": item_title,
        "key_finding": key_finding,
        "risk_level": risk_level,
    }


def _items_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for it in items:
        nested = it.get("item") or {}
        item_id = nested.get("item_id") or it.get("item_id") or ""
        if item_id:
            out[item_id] = it
    return out


def _normalize(
    data: dict[str, Any],
    *,
    metadata_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = deepcopy(data)

    normalized["meeting_metadata"] = _normalize_meeting_metadata(
        normalized.get("meeting_metadata"), metadata_overrides
    )

    items = normalized.get("items") or []
    item_by_id = _items_by_id(items)

    rows = normalized.get("executive_summary_table") or []
    normalized["executive_summary_table"] = [
        _normalize_executive_summary_row(r, item_by_id) for r in rows
    ]

    # prep_checklist absence is expected from Agent A today — leave empty.
    # The template already handles the empty case (see templates/brock_full.md).
    normalized.setdefault("prep_checklist", [])

    return normalized


# ---------------------------------------------------------------------------
# Public rendering API.
# ---------------------------------------------------------------------------


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def render(
    analysis_result: Any,
    *,
    metadata_overrides: dict[str, Any] | None = None,
) -> str:
    """Render an AnalysisResult (pydantic model or dict) to markdown.

    `metadata_overrides` merges into `meeting_metadata`, winning over both
    the analysis result's own metadata and the defaults. Use this to inject
    trustee_name, location, meeting_date, etc. when Agent A's pipeline
    doesn't have them — they're configuration, not analysis output.
    """
    data = _as_dict(analysis_result)
    mode = data.get("output_mode") or "BROCK_FULL"
    if mode not in _TEMPLATES:
        raise ValueError(f"Unknown output_mode: {mode!r}")

    if mode == "BROCK_FULL":
        data = _normalize(data, metadata_overrides=metadata_overrides)
    else:
        # SAMCO_LOQ has a different shape (loq_target, timeline, etc.) —
        # only meeting_metadata needs normalization.
        data["meeting_metadata"] = _normalize_meeting_metadata(
            data.get("meeting_metadata"), metadata_overrides
        )

    if mode == "BROCK_FULL" and not data.get("items"):
        raise ValueError("BROCK_FULL render requires at least one item")

    template = _env().get_template(_TEMPLATES[mode])
    return template.render(**data)


def render_to_file(
    analysis_result: Any,
    out_path: Path,
    *,
    metadata_overrides: dict[str, Any] | None = None,
) -> Path:
    markdown = render(analysis_result, metadata_overrides=metadata_overrides)
    out_path.write_text(markdown)
    return out_path


# ---------------------------------------------------------------------------
# CLI — subprocess-style integration for Agent A.
# ---------------------------------------------------------------------------


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render an AnalysisResult JSON to markdown via an Agent F template."
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        help="Path to an AnalysisResult JSON file (as emitted by Agent A).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Destination markdown file. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--metadata-json",
        type=Path,
        help="Optional JSON file whose top-level object is merged into meeting_metadata.",
    )
    args = parser.parse_args(argv)

    if args.from_json is None:
        # No input → produce the dummy renders for eyeballing.
        _render_dummies()
        return 0

    data = json.loads(args.from_json.read_text())

    overrides: dict[str, Any] | None = None
    if args.metadata_json:
        overrides = json.loads(args.metadata_json.read_text())

    markdown = render(data, metadata_overrides=overrides)
    if args.out:
        args.out.write_text(markdown)
        print(f"wrote {args.out}  ({len(markdown):,} chars)", file=sys.stderr)
    else:
        sys.stdout.write(markdown)
    return 0


def _render_dummies() -> None:
    # Late import so the CLI path doesn't depend on the fixture being present.
    sys.path.insert(0, str(SKILL_DIR))
    from _dummy_data import (  # type: ignore[import-not-found]
        AGENT_A_SHAPED_DUMMY,
        BROCK_APRIL_13_DUMMY,
        SAMCO_LOQ_DUMMY,
    )

    examples_dir = SKILL_DIR.parent.parent / "examples"

    full_out = render(BROCK_APRIL_13_DUMMY)
    full_dest = examples_dir / "brock_april_13_2026_dummy_render.md"
    full_dest.write_text(full_out)
    print(f"wrote {full_dest}  ({len(full_out):,} chars)")

    loq_out = render(SAMCO_LOQ_DUMMY)
    loq_dest = examples_dir / "samco_bond_loq_dummy_render.md"
    loq_dest.write_text(loq_out)
    print(f"wrote {loq_dest}  ({len(loq_out):,} chars)")

    agent_a_out = render(
        AGENT_A_SHAPED_DUMMY,
        metadata_overrides={
            "district_name_upper": "BROCK ISD",
            "meeting_type": "Regular Meeting",
            "meeting_date": "April 13, 2026",
            "meeting_time": "6:00 PM",
            "location": "BHS Cafeteria",
            "trustee_name": "Toby Farmer",
            "page_count": 166,
        },
    )
    agent_a_dest = examples_dir / "brock_april_13_2026_agent_a_shape_render.md"
    agent_a_dest.write_text(agent_a_out)
    print(f"wrote {agent_a_dest}  ({len(agent_a_out):,} chars)")


if __name__ == "__main__":
    sys.exit(_cli())

# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2>=3.1"]
# ///
"""Output formatter renderer for Agent F.

Consumes an AnalysisResult (pydantic model or equivalent dict) and returns
markdown rendered through the appropriate Jinja2 template.

Two modes:
  BROCK_FULL  -> templates/brock_full.md   (default)
  SAMCO_LOQ   -> templates/samco_loq.md

Run directly to produce a dummy render of the Brock April 13 pre-read:
    uv run python skills/output-formatter/render.py

The rendered file is written to examples/brock_april_13_2026_dummy_render.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SKILL_DIR / "templates"

_TEMPLATES = {
    "BROCK_FULL": "brock_full.md",
    "SAMCO_LOQ": "samco_loq.md",
}


def _as_dict(analysis_result: Any) -> dict[str, Any]:
    if hasattr(analysis_result, "model_dump"):
        return analysis_result.model_dump()
    return dict(analysis_result)


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def render(analysis_result: Any) -> str:
    data = _as_dict(analysis_result)
    mode = data.get("output_mode", "BROCK_FULL")
    if mode not in _TEMPLATES:
        raise ValueError(f"Unknown output_mode: {mode!r}")
    template = _env().get_template(_TEMPLATES[mode])
    return template.render(**data)


def _main() -> None:
    from _dummy_data import BROCK_APRIL_13_DUMMY, SAMCO_LOQ_DUMMY

    examples_dir = SKILL_DIR.parent.parent / "examples"

    full_out = render(BROCK_APRIL_13_DUMMY)
    full_dest = examples_dir / "brock_april_13_2026_dummy_render.md"
    full_dest.write_text(full_out)
    print(f"wrote {full_dest}  ({len(full_out):,} chars)")

    loq_out = render(SAMCO_LOQ_DUMMY)
    loq_dest = examples_dir / "samco_bond_loq_dummy_render.md"
    loq_dest.write_text(loq_out)
    print(f"wrote {loq_dest}  ({len(loq_out):,} chars)")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(SKILL_DIR))
    _main()

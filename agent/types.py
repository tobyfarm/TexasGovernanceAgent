"""Interface contract consumed by every downstream workstream.

Owned by Agent A. Changes here ripple to Agents B/C/D/E/F and must be coordinated
through Toby. See `agents/AGENT_A.md` §"Interface contract".

CLI: `python -m agent.types --schema` prints the AnalysisResult JSON Schema so
Agent D (web) can generate TypeScript types from it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ItemType = Literal["ACTION", "DISCUSSION", "CONSENT", "INFORMATIONAL", "CLOSED_SESSION"]
Severity = Literal["RED_FLAG", "WATCH", "POSITIVE"]
OutputMode = Literal["BROCK_FULL", "SAMCO_LOQ"]


class AgendaItem(BaseModel):
    item_id: str
    title: str
    pages: tuple[int, int]
    raw_text: str
    item_type: ItemType
    attachments: list[str] = Field(default_factory=list)


class Flag(BaseModel):
    severity: Severity
    pattern_id: str
    summary: str
    detail: str
    citations: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    authority: str
    quoted_text: str | None = None
    verified: bool = False


class ItemAnalysis(BaseModel):
    item: AgendaItem
    summary: str
    key_data: str
    legal_framework: str
    flags: list[Flag] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    source_pdf: str
    generated_at: datetime
    meeting_metadata: dict = Field(default_factory=dict)
    executive_summary_table: list[dict] = Field(default_factory=list)
    items: list[ItemAnalysis] = Field(default_factory=list)
    prep_checklist: list[str] = Field(default_factory=list)
    output_mode: OutputMode = "BROCK_FULL"


_EXPORTED_MODELS = {
    "AgendaItem": AgendaItem,
    "Flag": Flag,
    "Citation": Citation,
    "ItemAnalysis": ItemAnalysis,
    "AnalysisResult": AnalysisResult,
}


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export Agent A's pydantic contract as JSON Schema."
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print a combined JSON Schema with all public models.",
    )
    parser.add_argument(
        "--model",
        choices=sorted(_EXPORTED_MODELS.keys()),
        default=None,
        help="Print JSON Schema for a single model.",
    )
    args = parser.parse_args(argv)

    if args.model:
        print(json.dumps(_EXPORTED_MODELS[args.model].model_json_schema(), indent=2))
        return 0
    if args.schema:
        schemas = {name: cls.model_json_schema() for name, cls in _EXPORTED_MODELS.items()}
        print(json.dumps({"$defs": schemas}, indent=2))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_main())

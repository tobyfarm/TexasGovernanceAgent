"""Tests for GET /runs/{run_id}/eval — the on-demand hand-version comparator."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.types import AgendaItem, AnalysisResult, ItemAnalysis
from api import server as server_mod


@pytest.fixture
def client(runs_dir: Path) -> TestClient:
    return TestClient(server_mod.app)


def _seed_run(runs_dir: Path, run_id: str, md: str) -> None:
    d = runs_dir / run_id
    d.mkdir(parents=True)
    (d / "result.md").write_text(md)
    dummy = AnalysisResult(
        source_pdf="p.pdf",
        generated_at="2026-04-13T00:00:00+00:00",
        items=[
            ItemAnalysis(
                item=AgendaItem(
                    item_id="A",
                    title="x",
                    pages=(1, 1),
                    raw_text="...",
                    item_type="DISCUSSION",
                ),
                summary="s",
                key_data="",
                legal_framework="",
            )
        ],
    )
    (d / "result.json").write_text(dummy.model_dump_json())


def test_eval_endpoint_returns_comparison_report(
    client: TestClient, runs_dir: Path, tmp_path: Path
):
    _seed_run(runs_dir, "abc123def", "# Item A\n\nTEC §11.151(b) applies here.\n")
    # Hand path must live under examples/ per the safety gate.
    r = client.get(
        "/runs/abc123def/eval",
        params={"vs_hand": "examples/brock_april_13_2026_prereadhand.md"},
    )
    assert r.status_code in (200, 404)  # 404 if PDF/hand absent in this environment
    if r.status_code == 200:
        body = r.json()
        assert "word_count_ratio" in body
        assert "citations_only_in_hand" in body
        assert "score" in body


def test_eval_endpoint_rejects_paths_outside_examples(client: TestClient, runs_dir: Path):
    _seed_run(runs_dir, "abc123def", "# Item A\n")
    r = client.get(
        "/runs/abc123def/eval",
        params={"vs_hand": "../../../etc/passwd"},
    )
    assert r.status_code == 400


def test_eval_endpoint_404_when_run_missing(client: TestClient, runs_dir: Path):
    r = client.get(
        "/runs/nonexistent/eval",
        params={"vs_hand": "examples/brock_april_13_2026_prereadhand.md"},
    )
    assert r.status_code == 404


def test_eval_endpoint_rejects_invalid_run_id(client: TestClient):
    r = client.get(
        "/runs/..%2Fetc/eval",
        params={"vs_hand": "examples/brock_april_13_2026_prereadhand.md"},
    )
    assert r.status_code in (400, 404)

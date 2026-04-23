"""API surface tests. /health is required Day 1; /analyze is tested for
accept/reject behavior without hitting the model."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_rejects_non_pdf_content_type():
    r = client.post(
        "/analyze",
        files={"pdf": ("note.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415

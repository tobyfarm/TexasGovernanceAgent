"""PDF text extraction (pypdf, page-joined)."""

from __future__ import annotations

import io

from pypdf import PdfReader


def extract_text(pdf_bytes: bytes) -> str:
    """Return the full text of a PDF, pages joined with double newlines."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(f"[Page {i}]\n{text}".strip())
    return "\n\n".join(pages)

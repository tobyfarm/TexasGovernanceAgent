"""SSE event formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def sse_format(event: dict[str, Any]) -> str:
    """Render `{"event": ..., "data": {...}}` as an SSE wire frame.

    Format:
        event: <name>\n
        data: <json>\n\n
    """
    name = event.get("event", "message")
    data = event.get("data", {})
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {name}\ndata: {payload}\n\n"

"""
Server-Sent Events (SSE) helpers for real-time agent progress streaming.
"""

import json


def sse_event(event_type: str, data: dict | str) -> str:
    """Format a single Server-Sent Event frame."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"

"""Shared constants and escaping for coverage report HTML."""

from __future__ import annotations

import html

REPORT_AGENT_NAME = "Req2Release"
REPORT_DEVELOPER = "Mayur Gunjal"


def esc(text: str) -> str:
    return html.escape(text, quote=True)

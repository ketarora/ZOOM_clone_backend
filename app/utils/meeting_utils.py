"""Utility helpers for meeting ID generation and normalisation."""

from __future__ import annotations

import re
import secrets

from app.config import settings

# Zoom-style ID pattern: "XXX XXX XXXX"
_MEETING_ID_PATTERN = re.compile(r"^(\d{3}) (\d{3}) (\d{4})$")
# Matches compact digit strings of 9 or 10 digits (handles both formats).
_DIGIT_ONLY = re.compile(r"^\d{9,10}$")


def generate_meeting_id() -> str:
    """Return a unique Zoom-style meeting ID in the format ``XXX XXX XXXX``.

    Uses ``secrets.randbelow`` (cryptographically random) rather than
    ``random`` to avoid predictable IDs.
    """
    p1 = 100 + secrets.randbelow(900)
    p2 = 100 + secrets.randbelow(900)
    p3 = 1000 + secrets.randbelow(9000)
    return f"{p1} {p2} {p3}"


def generate_invite_link(meeting_id: str) -> str:
    """Construct a shareable join URL for the given meeting ID."""
    compact = meeting_id.replace(" ", "")
    base = settings.base_url.rstrip("/")
    return f"{base}/join/{compact}"


def normalize_meeting_id(raw: str) -> str:
    """Coerce any common meeting-ID representation to ``XXX XXX XXXX``.

    Accepted input formats
    ----------------------
    * ``"123 456 7890"``  — already canonical, returned as-is
    * ``"123-456-7890"``  — hyphenated
    * ``"1234567890"``    — 10-digit compact
    * ``"123456789"``     — 9-digit compact (edge case)

    Returns the original string unchanged if it does not match any known
    format, so callers can fall back to an exact-match DB query.
    """
    if _MEETING_ID_PATTERN.match(raw):
        return raw

    digits = re.sub(r"[\s\-]", "", raw)
    if len(digits) == 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"

    return raw

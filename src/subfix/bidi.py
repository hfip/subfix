"""Right-to-left helpers.

Two different problems are handled here:

1. Stray bidi control characters left behind by translation tools. They are
   invisible but they scramble punctuation inside a player, so they are
   stripped by default.
2. Lines that contain Arabic but *start* with a Latin word or a neutral
   character. The Unicode bidi algorithm then picks a left-to-right base
   direction, which puts trailing punctuation on the wrong side. Prefixing an
   RLM (U+200F) fixes the paragraph direction.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Tuple

RLM = "\u200f"

MARK_CHARS = "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
MARK_RE = re.compile("[" + MARK_CHARS + "]")

ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]")


def strip_marks(text: str) -> str:
    """Remove invisible bidi control characters."""
    return MARK_RE.sub("", text)


def _first_strong_direction(text: str) -> str:
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in ("L", "R", "AL"):
            return direction
    return ""


def needs_rtl_mark(line: str) -> bool:
    """True when an Arabic line starts with a strong LTR character."""
    if not ARABIC_RE.search(line):
        return False
    stripped = line.lstrip()
    if not stripped or stripped.startswith(RLM):
        return False
    return _first_strong_direction(stripped) == "L"


def add_rtl_marks(text: str) -> Tuple[str, int]:
    """Prefix RLM to lines that need it. Returns ``(text, marked_line_count)``."""
    marked = 0
    output = []
    for line in text.split("\n"):
        if needs_rtl_mark(line):
            leading = line[: len(line) - len(line.lstrip())]
            line = leading + RLM + line[len(leading) :]
            marked += 1
        output.append(line)
    return "\n".join(output), marked

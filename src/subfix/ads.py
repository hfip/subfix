"""Detection of watermarks, credits and ad lines inside subtitles.

The rules are intentionally conservative: strong signals (URLs, handles,
social brands) are removed anywhere, while weak signals ("ترجمة", "subtitles
by") are only removed near the start or the end of the file, where credits
actually live.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

MAX_AD_LINE_LENGTH = 120

STRONG_PATTERNS = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"www\.\S+", re.IGNORECASE),
    re.compile(r"\b[\w-]+\.(?:com|net|org|me|tv|link|info|xyz|top|co|io)\b", re.IGNORECASE),
    re.compile(r"\bt\.me/\S+", re.IGNORECASE),
    re.compile(r"@[A-Za-z0-9_]{3,}"),
    re.compile(
        r"(?:تليجرام|تلجرام|تيليجرام|تويتر|انستقرام|إنستغرام|فيسبوك|فيس\s?بوك|واتساب|سناب\s?شات)",
    ),
    re.compile(r"(?:قناتنا|قناتي|قناتى|حسابنا|صفحتنا|موقعنا)\s*(?:على|علي|في|فى|:)"),
    re.compile(
        r"(?:تابعونا|اشتركوا|اشترك)\s*(?:في|فى|على)\s*"
        r"(?:قناتنا|قناتي|القناة|حسابنا|صفحتنا)"
    ),
    re.compile(r"(?:لا|لآ)\s*تنس(?:ى|ي|وا)\s*(?:ال)?(?:اشتراك|إشتراك|متابعة|إعجاب|اعجاب)"),
]

WEAK_PATTERNS = [
    re.compile(r"^\s*(?:ترجمة|ترجمه|إعداد|اعداد|تنسيق|تدقيق|مراجعة)\s*[:：]?\s*\S"),
    re.compile(r"^\s*(?:تابعونا|تابعنا|اشترك|اشتركوا)\b"),
    re.compile(
        r"\b(?:subtitles?|subs?|translated|transcribed|encoded|ripped|synced|corrected|"
        r"resynced|edited)\s+by\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*[-=_*~#]{3,}\s*$"),
    re.compile(r"^\s*(?:جميع|كل)\s+الحقوق\s+محفوظة"),
    re.compile(r"^\s*(?:شكرا|شكراً|thanks)\s*(?:للمشاهدة|على\s+المشاهدة|for\s+watching)\.?!?"),
    re.compile(r"\b(?:all rights reserved|free download|download from)\b", re.IGNORECASE),
]


def is_ad_line(line: str, at_edge: bool) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > MAX_AD_LINE_LENGTH:
        return False
    if any(pattern.search(stripped) for pattern in STRONG_PATTERNS):
        return True
    if at_edge and any(pattern.search(stripped) for pattern in WEAK_PATTERNS):
        return True
    return False


def filter_lines(lines: Sequence[str], at_edge: bool) -> Tuple[List[str], int]:
    """Drop ad lines. Returns ``(kept_lines, removed_count)``."""
    kept: List[str] = []
    removed = 0
    for line in lines:
        if is_ad_line(line, at_edge):
            removed += 1
        else:
            kept.append(line)
    return kept, removed

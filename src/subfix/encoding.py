"""Encoding detection and repair for subtitle files.

Arabic subtitle files in the wild are usually one of:

* UTF-8 (the good case)
* Windows-1256 / ISO-8859-6 (legacy Arabic encodings)
* UTF-8 text that was decoded with latin-1 or cp1256 and re-saved --
  the classic ``Ø§Ù„Ø³Ù„Ø§Ù…`` / ``ط§ظ„ط³ظ„ط§ظ…`` mojibake

This module detects all of them and always returns a clean Unicode string.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

ARABIC_BLOCKS = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)

# Characters that only appear when UTF-8 Arabic was mis-decoded as a legacy
# single byte encoding (latin-1, cp1256 or cp1252).
MOJIBAKE_CHARS = frozenset("ÃÂØÙÐÑâ€Å¡Ã¢")
MOJIBAKE_NOISE = frozenset("ÃÂÐÑØÙÞßæç¤¦§¨©«¬®¯±²³´µ¶·¸¹º»¼½¾¿×÷˜™š›œ\u00ad")

LEGACY_ENCODINGS = ("cp1256", "iso-8859-6", "cp1252", "latin-1")


def is_arabic(char: str) -> bool:
    code = ord(char)
    return any(low <= code <= high for low, high in ARABIC_BLOCKS)


def arabic_ratio(text: str) -> float:
    """Fraction of letters in *text* that are Arabic."""
    letters = 0
    arabic = 0
    for char in text:
        if char.isalpha():
            letters += 1
            if is_arabic(char):
                arabic += 1
    return arabic / letters if letters else 0.0


def printable_ratio(text: str) -> float:
    """Fraction of characters that look like real text (no U+FFFD, no controls)."""
    if not text:
        return 0.0
    bad = 0
    for char in text:
        if char == "\ufffd":
            bad += 1
        elif ord(char) < 32 and char not in "\n\r\t":
            bad += 1
    return 1.0 - bad / len(text)


def noise_ratio(text: str) -> float:
    """Fraction of characters that are typical mojibake artefacts."""
    if not text:
        return 0.0
    return sum(1 for char in text if char in MOJIBAKE_NOISE) / len(text)


def plausibility(text: str) -> float:
    """Higher is better. Rewards Arabic letters, punishes mojibake noise."""
    return arabic_ratio(text) + 1.5 * printable_ratio(text) - 2.0 * noise_ratio(text)


def looks_mojibake(text: str) -> bool:
    """Heuristic: does this look like UTF-8 Arabic read as latin-1/cp1256?"""
    if not text:
        return False
    if noise_ratio(text) > 0.03:
        return True
    if arabic_ratio(text) >= 0.08:
        return False
    hits = 0
    for char in text:
        if char in MOJIBAKE_CHARS or 0x80 <= ord(char) <= 0xFF:
            hits += 1
    return hits / len(text) > 0.15


def repair_mojibake(text: str) -> Optional[str]:
    """Reverse a latin-1/cp1256 round-trip. Returns None if it does not help."""
    best: Optional[str] = None
    best_score = plausibility(text)
    for encoding in ("latin-1", "cp1256", "cp1252"):
        try:
            raw = text.encode(encoding)
        except UnicodeEncodeError:
            continue
        try:
            fixed = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        score = plausibility(fixed)
        if score > best_score + 0.1:
            best, best_score = fixed, score
    return best


def _clean_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")


def decode_bytes(data: bytes) -> Tuple[str, str, List[str]]:
    """Decode subtitle bytes into text.

    Returns ``(text, encoding_label, notes)``. The returned text always uses
    ``\\n`` line endings and has no BOM.
    """
    notes: List[str] = []

    if data.isascii():
        return _clean_newlines(data.decode("ascii")), "utf-8", notes

    if data.startswith(b"\xef\xbb\xbf"):
        return _clean_newlines(data[3:].decode("utf-8", errors="replace")), "utf-8", notes

    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            text = data.decode("utf-16")
        except UnicodeDecodeError:
            text = data.decode("utf-16", errors="replace")
        notes.append("decoded UTF-16")
        return _clean_newlines(text), "utf-16", notes

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None

    if text is not None:
        if looks_mojibake(text):
            fixed = repair_mojibake(text)
            if fixed is not None:
                notes.append("repaired UTF-8 mojibake")
                return _clean_newlines(fixed), "utf-8 (repaired)", notes
        return _clean_newlines(text), "utf-8", notes

    best = ""
    best_encoding = "cp1256"
    best_score = -1.0
    for encoding in LEGACY_ENCODINGS:
        candidate = data.decode(encoding, errors="replace")
        score = arabic_ratio(candidate) * 2 + printable_ratio(candidate)
        if score > best_score:
            best, best_encoding, best_score = candidate, encoding, score

    notes.append("decoded %s" % best_encoding)
    return _clean_newlines(best), best_encoding, notes

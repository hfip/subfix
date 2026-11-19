"""SRT timestamp parsing, validation and formatting."""

from __future__ import annotations

import re
from typing import Optional, Tuple

TIME_RE = re.compile(r"(?P<h>\d{1,3}):(?P<m>\d{1,2}):(?P<s>\d{1,2})[,.](?P<frac>\d{1,4})")

CUE_RE = re.compile(
    r"^(?P<a>\d{1,3}:\d{1,2}:\d{1,2}[,.]\d{1,4})"
    r"\s*-->\s*"
    r"(?P<b>\d{1,3}:\d{1,2}:\d{1,2}[,.]\d{1,4})"
    r"(?P<rest>\s.*)?$"
)

DEFAULT_MIN_DURATION_MS = 700


def parse_time(value: str) -> Optional[Tuple[int, int]]:
    """Parse a timestamp into ``(milliseconds, issue_count)``.

    ``issue_count`` counts things SubFix had to normalise, such as
    ``00:00:75,000`` or a four digit millisecond field.
    """
    match = TIME_RE.search(value)
    if match is None:
        return None

    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    fraction = match.group("frac")

    issues = 0
    if minutes > 59 or seconds > 59:
        issues += 1
    if len(fraction) != 3:
        issues += 1

    if len(fraction) > 3:
        milliseconds = int(fraction) // 10 ** (len(fraction) - 3)
    else:
        milliseconds = int(fraction) * 10 ** (3 - len(fraction))
    total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds
    return total, issues


def format_time(milliseconds: int) -> str:
    """Format milliseconds as ``HH:MM:SS,mmm``."""
    milliseconds = max(0, int(milliseconds))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, millis)


def normalize_span(
    start: int,
    end: int,
    min_duration: int = DEFAULT_MIN_DURATION_MS,
) -> Tuple[int, int, int]:
    """Make a cue span sane. Returns ``(start, end, fix_count)``."""
    fixes = 0
    if start < 0:
        start = 0
        fixes += 1
    if end <= start:
        end = start + 1500
        fixes += 1
    elif end - start < min_duration:
        end = start + min_duration
        fixes += 1
    return start, end, fixes


def parse_shift(spec: str) -> int:
    """Parse a user supplied shift like ``+1.5s``, ``-800ms`` or ``00:00:02,500``."""
    spec = spec.strip()
    if not spec:
        raise ValueError("empty shift value")

    sign = -1 if spec[0] == "-" else 1
    subject = spec.lstrip("+-")

    if ":" in subject:
        match = re.match(r"^(\d{1,2}):(\d{1,2}):(\d{1,2})(?:[,.](\d{1,3}))?$", subject)
        if match is None:
            raise ValueError("bad shift value: %r" % spec)
        hours, minutes, seconds = (int(match.group(i)) for i in (1, 2, 3))
        fraction = (match.group(4) or "0").ljust(3, "0")
        total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(fraction)
        return sign * total

    if subject.endswith("ms"):
        return sign * int(round(float(subject[:-2])))
    if subject.endswith("s"):
        return sign * int(round(float(subject[:-1]) * 1000))
    return sign * int(round(float(subject) * 1000))

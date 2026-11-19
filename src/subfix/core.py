"""The fix pipeline: parse, clean, rewrite."""

from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import ads, bidi, timestamps
from .encoding import decode_bytes

BLOCK_SPLIT_RE = re.compile(r"\n[ \t]*\n")


@dataclass
class Cue:
    start: int
    end: int
    text: str


@dataclass
class FixOptions:
    remove_ads: bool = True
    strip_bidi_marks: bool = True
    add_rtl_marks: bool = True
    shift_ms: int = 0
    min_duration_ms: int = timestamps.DEFAULT_MIN_DURATION_MS


@dataclass
class FixResult:
    text: str = ""
    cues_before: int = 0
    cues_after: int = 0
    ads_removed: int = 0
    empty_removed: int = 0
    timing_fixed: int = 0
    bidi_stripped: int = 0
    rtl_marked: int = 0
    sorted: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.text)


@dataclass
class FileReport:
    path: Path
    ok: bool = True
    changed: bool = False
    encoding: str = "utf-8"
    cues: int = 0
    ads_removed: int = 0
    empty_removed: int = 0
    timing_fixed: int = 0
    rtl_marked: int = 0
    sorted: bool = False
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = ["%d cues" % self.cues]
        if self.encoding != "utf-8":
            parts.append("%s -> utf-8" % self.encoding)
        if self.ads_removed:
            parts.append("ads %d" % self.ads_removed)
        if self.timing_fixed:
            parts.append("timing %d" % self.timing_fixed)
        if self.rtl_marked:
            parts.append("rtl %d" % self.rtl_marked)
        if self.empty_removed:
            parts.append("empty %d" % self.empty_removed)
        if self.sorted:
            parts.append("sorted")
        return " · ".join(parts)

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "ok": self.ok,
            "changed": self.changed,
            "encoding": self.encoding,
            "cues": self.cues,
            "ads_removed": self.ads_removed,
            "empty_removed": self.empty_removed,
            "timing_fixed": self.timing_fixed,
            "rtl_marked": self.rtl_marked,
            "sorted": self.sorted,
            "error": self.error,
            "notes": self.notes,
        }


def parse_srt(text: str) -> List[Cue]:
    """Parse SRT content into cues, tolerating missing indices and bad timing."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    cues: List[Cue] = []

    for block in BLOCK_SPLIT_RE.split(text.strip("\n")):
        if not block.strip():
            continue
        lines = block.split("\n")

        time_index = None
        for index, line in enumerate(lines[:3]):
            if "-->" in line:
                time_index = index
                break
        if time_index is None:
            continue

        match = timestamps.CUE_RE.match(lines[time_index].strip())
        if match is None:
            continue

        parsed_start = timestamps.parse_time(match.group("a"))
        parsed_end = timestamps.parse_time(match.group("b"))
        if parsed_start is None or parsed_end is None:
            continue

        body = "\n".join(lines[time_index + 1 :]).strip("\n")
        cues.append(Cue(start=parsed_start[0], end=parsed_end[0], text=body))

    return cues


def serialize_srt(cues: List[Cue]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "%d\n%s --> %s\n%s"
            % (index, timestamps.format_time(cue.start), timestamps.format_time(cue.end), cue.text)
        )
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"


def _clean_lines(lines: List[str], opts: FixOptions, result: FixResult, at_edge: bool):
    cleaned: List[str] = []
    for line in lines:
        line = line.rstrip()
        if opts.strip_bidi_marks:
            without_marks = bidi.strip_marks(line)
            if without_marks != line:
                result.bidi_stripped += 1
            line = without_marks
        cleaned.append(line)

    if opts.remove_ads:
        cleaned, removed = ads.filter_lines(cleaned, at_edge=at_edge)
        result.ads_removed += removed

    return [line for line in cleaned if line.strip()]


def fix_text(text: str, opts: Optional[FixOptions] = None) -> FixResult:
    """Apply every enabled fix to SRT *text* and return the new content."""
    opts = opts or FixOptions()
    cues = parse_srt(text)
    result = FixResult(cues_before=len(cues))
    if not cues:
        return result

    total = len(cues)
    fixed_cues: List[Cue] = []

    for index, cue in enumerate(cues):
        at_edge = index < 3 or index >= total - 3
        lines = _clean_lines(cue.text.split("\n"), opts, result, at_edge)
        if not lines:
            result.empty_removed += 1
            continue

        body = unicodedata.normalize("NFC", "\n".join(lines))

        if opts.add_rtl_marks:
            body, marked = bidi.add_rtl_marks(body)
            result.rtl_marked += marked

        start, end, fixes = timestamps.normalize_span(cue.start, cue.end, opts.min_duration_ms)
        result.timing_fixed += fixes

        if opts.shift_ms:
            start += opts.shift_ms
            end += opts.shift_ms
            if start < 0:
                start = 0
                end = max(end, opts.min_duration_ms)

        fixed_cues.append(Cue(start=start, end=end, text=body))

    starts = [cue.start for cue in fixed_cues]
    if starts != sorted(starts):
        fixed_cues.sort(key=lambda cue: cue.start)
        result.sorted = True

    result.cues_after = len(fixed_cues)
    result.text = serialize_srt(fixed_cues)
    return result


def process_file(
    path: Path,
    opts: Optional[FixOptions] = None,
    dry_run: bool = False,
    backup: bool = True,
) -> FileReport:
    """Fix one file on disk and report what changed."""
    opts = opts or FixOptions()
    path = Path(path)
    report = FileReport(path=path)

    try:
        data = path.read_bytes()
    except OSError as error:
        report.ok = False
        report.error = str(error)
        return report

    text, encoding, notes = decode_bytes(data)
    report.encoding = encoding
    report.notes = notes

    result = fix_text(text, opts)
    if result.cues_before == 0:
        report.ok = False
        report.error = "no SRT cues found"
        return report
    if result.cues_after == 0:
        report.ok = False
        report.error = "every cue was removed, original kept"
        return report

    new_bytes = result.text.encode("utf-8")
    report.changed = new_bytes != data
    report.cues = result.cues_after
    report.ads_removed = result.ads_removed
    report.empty_removed = result.empty_removed
    report.timing_fixed = result.timing_fixed
    report.rtl_marked = result.rtl_marked
    report.sorted = result.sorted

    if not report.changed or dry_run:
        return report

    try:
        if backup:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        path.write_bytes(new_bytes)
    except OSError as error:
        report.ok = False
        report.error = str(error)

    return report

"""Command line interface for SubFix."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

from . import __version__
from .core import FixOptions, FileReport, process_file
from .timestamps import parse_shift

GREEN = "32"
RED = "31"
YELLOW = "33"
DIM = "2"
BOLD = "1"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Painter:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return "\x1b[%sm%s\x1b[0m" % (code, text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subfix",
        description="Fix broken Arabic subtitles in one command: "
        "encoding, timing, RTL and ad lines.",
        epilog="example: subfix -r ~/Movies/Subs --shift +0.5s",
    )
    parser.add_argument("paths", nargs="+", help="SRT files or directories")
    parser.add_argument("-r", "--recursive", action="store_true", help="recurse into directories")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show what would change")
    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="exit with 1 if any file needs fixing (nothing is written)",
    )
    parser.add_argument("--no-ads", action="store_true", help="keep watermark/ad lines")
    parser.add_argument("--no-bidi", action="store_true", help="keep invisible bidi characters")
    parser.add_argument("--no-rtl", action="store_true", help="do not add RLM to mixed lines")
    parser.add_argument("--no-backup", action="store_true", help="do not write .bak files")
    parser.add_argument(
        "--shift",
        metavar="SPEC",
        help="shift all timings, e.g. +1.5s, -800ms or 00:00:02,500",
    )
    parser.add_argument("--json", action="store_true", help="machine readable output")
    parser.add_argument("-q", "--quiet", action="store_true", help="only print the summary")
    parser.add_argument("-V", "--version", action="version", version="subfix " + __version__)
    return parser


def collect_files(paths: Sequence[str], recursive: bool) -> List[Path]:
    files: List[Path] = []
    seen = set()
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            candidates = sorted(
                item
                for item in path.glob(pattern)
                if item.is_file() and item.suffix.lower() == ".srt"
            )
        elif path.is_file():
            candidates = [path]
        else:
            raise FileNotFoundError("no such file or directory: %s" % raw)

        for candidate in candidates:
            key = candidate.resolve()
            if key in seen:
                continue
            seen.add(key)
            files.append(candidate)
    return files


def _print_report(report: FileReport, paint: Painter, width: int, quiet: bool) -> None:
    name = report.path.name
    padded = name.ljust(width)

    if not report.ok:
        if not quiet:
            print("  %s %s  %s" % (paint(RED, "x"), padded, paint(RED, report.error or "failed")))
        return

    if not report.changed:
        if not quiet:
            print("  %s %s  %s" % (paint(DIM, "="), padded, paint(DIM, "already clean")))
        return

    if not quiet:
        print("  %s %s  %s" % (paint(GREEN, "+"), padded, paint(DIM, report.summary)))


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    paint = Painter(_supports_color() and not args.json)

    try:
        files = collect_files(args.paths, args.recursive)
    except FileNotFoundError as error:
        print(paint(RED, "error: ") + str(error), file=sys.stderr)
        return 2

    if not files:
        print(paint(YELLOW, "no .srt files found"), file=sys.stderr)
        return 2

    try:
        shift = parse_shift(args.shift) if args.shift else 0
    except ValueError as error:
        print(paint(RED, "error: ") + str(error), file=sys.stderr)
        return 2

    opts = FixOptions(
        remove_ads=not args.no_ads,
        strip_bidi_marks=not args.no_bidi,
        add_rtl_marks=not args.no_rtl,
        shift_ms=shift,
    )

    reports = [
        process_file(path, opts, dry_run=args.dry_run or args.check, backup=not args.no_backup)
        for path in files
    ]

    failed = [report for report in reports if not report.ok]
    changed = [report for report in reports if report.ok and report.changed]
    clean = [report for report in reports if report.ok and not report.changed]

    if args.json:
        payload = {
            "version": __version__,
            "files": [report.to_dict() for report in reports],
            "summary": {
                "total": len(reports),
                "changed": len(changed),
                "clean": len(clean),
                "failed": len(failed),
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1 if failed or (args.check and changed) else 0

    width = min(40, max((len(report.path.name) for report in reports), default=10))
    for report in reports:
        _print_report(report, paint, width, args.quiet)

    verb = "would fix" if (args.dry_run or args.check) else "fixed"
    summary = "%d %s, %d clean, %d failed" % (len(changed), verb, len(clean), len(failed))
    print()
    print(paint(BOLD, "SubFix %s" % __version__) + paint(DIM, "  ·  " + summary))

    if changed and not (args.dry_run or args.check) and not args.no_backup:
        print(paint(DIM, "backups written as *.srt.bak"))

    if failed:
        return 2
    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

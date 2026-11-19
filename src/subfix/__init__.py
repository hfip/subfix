"""SubFix - fix broken Arabic subtitles in one command."""

from .core import (
    Cue,
    FileReport,
    FixOptions,
    FixResult,
    fix_text,
    parse_srt,
    process_file,
    serialize_srt,
)

__version__ = "0.1.0"

__all__ = [
    "Cue",
    "FileReport",
    "FixOptions",
    "FixResult",
    "fix_text",
    "parse_srt",
    "process_file",
    "serialize_srt",
    "__version__",
]

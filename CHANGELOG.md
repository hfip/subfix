# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-19

### Added

- Encoding detection and conversion to UTF-8 (Windows-1256, ISO-8859-6, UTF-16, BOM handling).
- Mojibake repair for UTF-8 Arabic text that was decoded as latin-1, cp1256 or cp1252.
- SRT parser tolerant of missing indices and malformed timestamps.
- Timestamp normalisation: out-of-range fields, `.` separators, four digit fractions.
- Span repair: end before start, overlapping short flashes, minimum cue duration.
- Sorting by start time and renumbering from 1.
- RTL fix: strips invisible bidi controls and adds RLM to mixed-direction lines.
- Conservative ad and watermark removal for URLs, handles, social brands and credits.
- Empty cue removal with a guard that refuses to empty a whole file.
- CLI with `--recursive`, `--dry-run`, `--check`, `--shift`, `--json`, `--no-backup`.
- Automatic `.srt.bak` backups.
- 57 tests, zero runtime dependencies.

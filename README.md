<p align="center">
  <img src="assets/header.svg" alt="SubFix — fix broken Arabic subtitles in one command" width="100%">
</p>

<p align="center">
  <a href="https://github.com/hfip/subfix/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/hfip/subfix/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="Zero dependencies" src="https://img.shields.io/badge/dependencies-0-8b5cf6">
  <img alt="MIT license" src="https://img.shields.io/badge/license-MIT-22c55e">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-64748b">
</p>

<p align="center">
  <b>One command. Broken Arabic .srt in, clean Arabic .srt out.</b><br>
  Fixes encoding, mojibake, timing, RTL direction and leftover watermark lines — no dependencies, no upload, nothing leaves your machine.
</p>

---

## The problem

Arabic subtitle files are usually broken in the same five ways:

```
3
00:00:07.000 --> 00:00:06.200
Ø§Ù„Ø³Ù„Ø§Ù… Ø¹Ù„ÙŠÙƒÙ…            ← mojibake + broken timing
```

Open it in Infuse, VLC or Plex and you get scrambled letters, a flash of text, and
punctuation on the wrong side. Renaming, re-downloading or opening a text editor
doesn't help — the file needs to be decoded, repaired and re-encoded properly.

**SubFix does exactly that, for a whole folder, in one command.**

```
3
00:00:07,000 --> 00:00:08,500
السلام عليكم
```

## What it fixes

| Problem | What you see | What SubFix does |
| --- | --- | --- |
| Legacy encoding | Windows-1256 / ISO-8859-6 bytes | re-encodes the file as UTF-8 |
| Mojibake | `Ø§Ù„Ø³Ù„Ø§Ù…` or `ط§ظ„ط³ظ„ط§ظ…` | reverses the accidental double decode |
| Bad timestamps | `00:00:75,1234`, `.` instead of `,` | clamps fields and writes `HH:MM:SS,mmm` |
| Broken spans | end before start, 80 ms flashes | guarantees a sane end time and minimum duration |
| Order & numbering | cues out of order, index `7`, `7`, `9` | sorts by start time and renumbers `1..n` |
| Mixed direction | `iPhone الجديد` renders LTR | prefixes an RLM so the line is right-to-left |
| Invisible junk | stray `LRM` / `RLM` / `RLE` characters | strips them |
| Ads & watermarks | `www.site.com`, `@handle`, `ترجمة: …` | removes them (edge-aware, see below) |
| Empty cues | whitespace-only blocks | drops them |

Ad removal is deliberately conservative: strong signals (URLs, `@handles`, social
brands) are removed anywhere, while weak signals like `ترجمة:` or `subtitles by`
are only removed in the first and last three cues. Anything that would empty a
whole file is refused instead of written.

## Install

Requires Python 3.9+. No runtime dependencies.

```bash
git clone https://github.com/hfip/subfix.git
cd subfix
pipx install .        # recommended: isolated, gives you the `subfix` command
# or
python -m pip install .
```

> A PyPI release is planned. Until then, install from the repository as above.

## Usage

```bash
subfix movie.srt                  # fix one file
subfix -r ~/Movies/Subs           # fix every .srt inside a folder
subfix -n -r .                    # preview: show what would change
subfix --check -r .               # CI/pre-commit mode: exit 1 if anything needs fixing
subfix --shift +1.2s movie.srt    # audio out of sync? shift everything
subfix --json -r . | jq           # machine readable report
```

```
  + movie.srt  2 cues · cp1256 -> utf-8 · ads 2 · timing 1 · rtl 1 · empty 2

SubFix 0.1.0  ·  1 fixed, 0 clean, 0 failed
backups written as *.srt.bak
```

### Options

| Flag | Description |
| --- | --- |
| `-r, --recursive` | recurse into subdirectories |
| `-n, --dry-run` | report only, never write |
| `-c, --check` | exit `1` when a file needs fixing (writes nothing) |
| `--shift SPEC` | shift all timings: `+1.5s`, `-800ms`, `00:00:02,500` |
| `--no-ads` | keep watermark/ad lines |
| `--no-bidi` | keep invisible bidi characters |
| `--no-rtl` | do not add RLM marks |
| `--no-backup` | do not write `*.srt.bak` files |
| `--json` | machine readable output |
| `-q, --quiet` | only print the summary |

Exit codes: `0` success, `1` changes needed with `--check`, `2` error.

## Safety

- Every modified file gets a `.srt.bak` backup next to it (disable with `--no-backup`).
- `--dry-run` writes nothing.
- Files with no parseable cues are left untouched and reported as failed.
- **Cue blocks it cannot parse are never dropped.** A block with a broken arrow (`->`)
  or an impossible timestamp makes SubFix refuse the whole file, report the line, and
  keep the original.
- An operation that would remove **every** cue is refused; the original is kept.
- Everything runs locally. There is no network code in this package.

## Use as a library

```python
from subfix import FixOptions, fix_text

result = fix_text(open("movie.srt", encoding="utf-8").read(), FixOptions(shift_ms=1200))

print(result.text)  # repaired SRT
print(result.ads_removed)  # 2
print(result.timing_fixed)  # 1
```

## FAQ

**Does it work with Infuse / VLC / Plex / Jellyfin?**
Yes. The output is plain UTF-8 SRT, which every player accepts. Styling tags like
`<i>` and `{\an8}` are preserved.

**Does it support `.ass` / `.ssa` / `.vtt`?**
Not yet — SRT only. The parser is isolated, so adding formats is a contained change.

**Will it break my perfectly good subtitles?**
Run `subfix -n -r .` first. A clean file is reported as `already clean` and is not
rewritten (`--check` makes this easy to automate).

## بالعربي

<div dir="rtl" align="right">

كثير من ملفات الترجمة العربية تجيك مكسّرة: إما بترميز قديم (Windows-1256)، أو
نص عربي انحفظ مرتين فطلع `Ø§Ù„Ø³Ù„Ø§Ù…`، أو توقيتات خربانة، أو أسطر دعائية
ملصوقة. **SubFix** يصلّح كل هذا بأمر واحد:

```bash
subfix -r ~/Movies/Subs
```

- ما يرفع أي شي على الإنترنت، كله يشتغل على جهازك.
- يحفظ نسخة احتياطية `.srt.bak` قبل أي تعديل.
- جرّب `subfix -n -r ./subs` أول مرة عشان تشوف التغييرات بدون ما تنكتب.
- يقبل ملفات Infuse وVLC وPlex وJellyfin بدون أي إعداد.

</div>

## Contributing

Issues and pull requests are welcome. Please run the checks before opening a PR:

```bash
pip install -e . pytest ruff
pytest
ruff check . && ruff format --check .
```

If you have a broken subtitle file that SubFix gets wrong, attach it to an issue —
real-world files are the best test suite.

## License

[MIT](LICENSE) © 2026 Abdulluh.X
